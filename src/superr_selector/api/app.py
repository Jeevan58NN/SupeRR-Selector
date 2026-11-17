from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Literal
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT=Path(os.environ.get("SUPERR_ROOT", Path(__file__).resolve().parents[3])).resolve()
SCENARIOS={"strict_exact_context","proxy_inclusive"}
app=FastAPI(title="SupeRR Selector API",version="2.0.0",description="Precomputed cricket pressure analytics from supplied datasets.")
app.add_middleware(CORSMiddleware,allow_origins=["http://127.0.0.1:5173","http://localhost:5173"],allow_methods=["GET"],allow_headers=["*"])

def frame(path:Path)->pd.DataFrame:
    if not path.exists(): raise HTTPException(503,detail=f"Analytical output not ready: {path.name}")
    return pd.read_csv(path,low_memory=False)
def scenario_path(scenario:str)->Path:
    if scenario not in SCENARIOS: raise HTTPException(422,detail="scenario must be strict_exact_context or proxy_inclusive")
    return ROOT/"data"/"outputs"/scenario
def clean(df:pd.DataFrame):
    return df.astype(object).where(pd.notna(df),None).to_dict(orient="records")
def ranked(scenario:str,role:str):
    if role not in {"batter","bowler"}: raise HTTPException(422,detail="role must be batter or bowler")
    return frame(scenario_path(scenario)/f"all_{role}_rankings.csv")

@app.get("/api/health")
def health():
    return {"status":"ok","project":"SupeRR Selector","version":"2.0.0","data_ready":all((scenario_path(s)/"all_player_rankings.csv").exists() for s in SCENARIOS)}

@app.get("/api/dashboard/summary")
def dashboard_summary(scenario:str="proxy_inclusive"):
    d=scenario_path(scenario); rank=frame(d/"all_player_rankings.csv")
    episodes=pd.concat([frame(d/"batting_pressure_episodes.csv"),frame(d/"bowling_pressure_episodes.csv")],ignore_index=True)
    quality=frame(ROOT/"data"/"interim"/"data_quality_summary.csv")
    lookup=quality.set_index("source_file").to_dict(orient="index")
    ball=lookup.get("ball_by_ball.csv",{}); matches=lookup.get("matches.csv",{})
    players=frame(ROOT/"data"/"processed"/"player_master.csv")
    return {"scenario":scenario,"players":int(players.player_id.nunique()),"matches_covered":int(ball.get("matches") or 0),"metadata_matches":int(matches.get("matches") or 0),"deliveries":int(ball.get("rows") or 0),"episodes":int(episodes.episode_id.nunique()),"pressure_episodes":int(episodes.episode_id.nunique()),"batters_evaluated":int(rank.loc[rank.player_role.eq("batter"),"player_id"].nunique()),"bowlers_evaluated":int(rank.loc[rank.player_role.eq("bowler"),"player_id"].nunique()),"top_batter":clean(rank[rank.player_role.eq("batter")].head(1))[0] if (rank.player_role=="batter").any() else None,"top_bowler":clean(rank[rank.player_role.eq("bowler")].head(1))[0] if (rank.player_role=="bowler").any() else None,"quality":clean(quality)}
@app.get("/api/rankings/{role}")
def rankings(role:Literal["batter","bowler"],scenario:str="proxy_inclusive",page:int=1,page_size:int=50,sort_by:str="ranking_score",direction:Literal["asc","desc"]="desc",search:str=""):
    if page<1 or not 1<=page_size<=200: raise HTTPException(422,detail="page must be >=1 and page_size 1–200")
    df=ranked(scenario,role)
    if search: df=df[df.player_name.fillna("").str.contains(search,case=False,regex=False)]
    if sort_by not in df.columns: raise HTTPException(422,detail="unknown sort_by field")
    df=df.sort_values(sort_by,ascending=direction=="asc",na_position="last")
    total=len(df); start=(page-1)*page_size
    return {"scenario":scenario,"role":role,"page":page,"page_size":page_size,"total":total,"items":clean(df.iloc[start:start+page_size])}

@app.get("/api/players/search")
def player_search(q:str="",limit:int=25):
    if not 1<=limit<=100: raise HTTPException(422,detail="limit must be 1–100")
    p=frame(ROOT/"data"/"processed"/"player_master.csv")
    if q: p=p[p.player_name.fillna("").str.contains(q,case=False,regex=False)]
    return clean(p.sort_values("player_name").head(limit))

@app.get("/api/players/{player_id:int}")
def player_profile(player_id:int,scenario:str="proxy_inclusive"):
    d=scenario_path(scenario)
    master=frame(ROOT/"data"/"processed"/"player_master.csv")
    player_row=master[master.player_id.eq(player_id)]
    if player_row.empty: raise HTTPException(404,detail="unknown player_id")
    rankings=pd.concat([ranked(scenario,"batter"),ranked(scenario,"bowler")],ignore_index=True)
    rating_rows=rankings[rankings.player_id.eq(player_id)]
    situations=frame(d/"situation_ratings.csv"); situations=situations[situations.player_id.eq(player_id)]
    result={"scenario":scenario,"player":{"player_id":player_id,"player_name":player_row.player_name.iloc[0],
        "ratings":clean(rating_rows)},"batting":None,"bowling":None,"situations":clean(situations.sort_values("situation_score",ascending=False))}
    for role,file in [("batter","batting_overall_metrics.csv"),("bowler","bowling_overall_metrics.csv")]:
        m=frame(ROOT/"data"/"processed"/file); m=m[m.player_id.eq(player_id)]
        if not m.empty: result["batting" if role=="batter" else "bowling"]=clean(m)[0]
    normal_bat=frame(d/"batting_normal_performance.csv"); normal_bat=normal_bat[normal_bat.player_id.eq(player_id)]
    normal_bowl=frame(d/"bowling_normal_performance.csv"); normal_bowl=normal_bowl[normal_bowl.player_id.eq(player_id)]
    bat_innings=int(normal_bat.iloc[0].innings_in_sample) if not normal_bat.empty else 0
    bowl_innings=int(normal_bowl.iloc[0].innings_in_sample) if not normal_bowl.empty else 0
    with open(ROOT/"config"/"role_definitions.yaml",encoding="utf-8") as f: role_cfg=json.load(f)
    role_threshold=int(role_cfg.get("all_rounder_min_innings",15))
    if bat_innings>=role_threshold and bowl_innings>=role_threshold: player_type="All-rounder"
    elif bat_innings>bowl_innings and bat_innings>0: player_type="Batter"
    elif bowl_innings>0: player_type="Bowler"
    elif bat_innings>0: player_type="Batter"
    else: player_type="No recorded role"
    batter_rating=rating_rows[rating_rows.player_role.eq("batter")]
    bowler_rating=rating_rows[rating_rows.player_role.eq("bowler")]
    result["player"].update({"player_type":player_type,"batting_rank":int(batter_rating.iloc[0]["rank"]) if not batter_rating.empty else None,
        "bowling_rank":int(bowler_rating.iloc[0]["rank"]) if not bowler_rating.empty else None,
        "all_rounder_min_innings":role_threshold,"normal_batting_innings":bat_innings,"normal_bowling_innings":bowl_innings})
    return result

@app.get("/api/players/{player_id:int}/breakdowns")
def player_breakdowns(player_id:int,role:Literal["batter","bowler"]|None=None):
    result={}
    for key,file in [("batter","batting_context_metrics.csv"),("bowler","bowling_context_metrics.csv")]:
        if role and role!=key: continue
        path=ROOT/"data"/"processed"/file
        if path.exists():
            x=frame(path); result[key]=clean(x[x.player_id.eq(player_id)])
        else: result[key]=[]
    return result

@app.get("/api/players/compare")
def compare_players(ids:str,scenario:str="proxy_inclusive"):
    d=scenario_path(scenario); parsed=[]
    try: parsed=[int(v.strip()) for v in ids.split(",") if v.strip()]
    except ValueError: raise HTTPException(422,detail="ids must be comma-separated integer player IDs")
    if not 2<=len(parsed)<=4: raise HTTPException(422,detail="select 2–4 players")
    x=pd.concat([ranked(scenario,"batter"),ranked(scenario,"bowler")],ignore_index=True); x=x[x.player_id.isin(parsed)]
    sit=frame(d/"situation_ratings.csv"); return {"scenario":scenario,"players":clean(x),"situations":clean(sit[sit.player_id.isin(parsed)])}

@app.get("/api/situations")
def situations(role:Literal["batting","bowling"]="batting",scenario:str="proxy_inclusive",situation_id:str="",player_id:int|None=None):
    d=scenario_path(scenario); file=f"{role}_situation_ratings.csv"; x=frame(d/file)
    if situation_id: x=x[x.situation_id.eq(situation_id)]
    if player_id is not None: x=x[x.player_id.eq(player_id)]
    return {"scenario":scenario,"role":role,"items":clean(x.sort_values("situation_score",ascending=False))}

@app.get("/api/situations/{situation_id}")
def situation_detail(situation_id:str,scenario:str="proxy_inclusive"):
    d=scenario_path(scenario); allx=frame(d/"situation_ratings.csv"); x=allx[allx.situation_id.eq(situation_id)]
    valid={f"B{i}" for i in range(1,16)}|{f"BW{i}" for i in range(1,17)}
    if x.empty and situation_id not in valid: raise HTTPException(404,detail="unknown situation_id")
    return {"scenario":scenario,"situation_id":situation_id,"performers":clean(x.sort_values("situation_score",ascending=False).head(25)),"evidence_available":not x.empty,"episodes":int(pd.concat([frame(d/"batting_pressure_episodes.csv"),frame(d/"bowling_pressure_episodes.csv")]).query("situation_id == @situation_id").episode_id.nunique())}

@app.get("/api/episodes")
def episodes(scenario:str="proxy_inclusive",role:Literal["batting","bowling"]="batting",match_id:int|None=None,situation_id:str="",page:int=1,page_size:int=50):
    if page<1 or not 1<=page_size<=200: raise HTTPException(422,detail="page must be >=1 and page_size 1–200")
    d=scenario_path(scenario); x=frame(d/f"{role}_pressure_episodes.csv")
    if match_id is not None: x=x[x.match_id.eq(match_id)]
    if situation_id: x=x[x.situation_id.eq(situation_id)]
    total=len(x); start=(page-1)*page_size
    return {"page":page,"page_size":page_size,"total":total,"items":clean(x.iloc[start:start+page_size])}

@app.get("/api/matches")
def matches(q:str="",limit:int=100):
    x=frame(ROOT/"matches.csv"); cols=[c for c in ["match_id","match_date","comp_id","team1_id","team2_id","winner_team_id","is_knock_out"] if c in x]
    x=x[cols]
    if q: x=x[x.astype(str).apply(lambda c:c.str.contains(q,case=False,regex=False)).any(axis=1)]
    return clean(x.head(min(max(limit,1),200)))

@app.get("/api/data-quality")
def data_quality():
    return {"files":clean(frame(ROOT/"data"/"interim"/"source_file_manifest.csv")),"summary":clean(frame(ROOT/"data"/"interim"/"data_quality_summary.csv")),"scenario_comparison":clean(frame(ROOT/"data"/"outputs"/"scenario_comparison"/"scenario_rank_changes.csv").head(200))}

@app.get("/api/methodology")
def methodology():
    p=ROOT/"docs"/"METHODOLOGY.md"
    return {"markdown":p.read_text(encoding="utf-8") if p.exists() else "Methodology documentation is being prepared."}






@app.get("/api/matches/{match_id}")
def match_detail(match_id:int,scenario:str="proxy_inclusive",innings:int|None=None,page:int=1,page_size:int=72):
    if page<1 or not 1<=page_size<=300: raise HTTPException(422,detail="page must be >=1 and page_size 1–300")
    d=scenario_path(scenario); state_path=d/"delivery_match_state.csv"
    state=pd.read_csv(state_path,low_memory=False); state=state[state.match_id.eq(match_id)]
    if innings is not None: state=state[state.innings.eq(innings)]
    if state.empty: raise HTTPException(404,detail="match or innings has no ball-by-ball records")
    labels=frame(d/"delivery_pressure_labels.csv")
    labels=labels[labels.match_id.eq(match_id)]
    active=labels.groupby("delivery_id").agg(active_situations=("situation_id",lambda s:"|".join(sorted(set(s)))),pressure_intensity=("pressure_intensity","max"))
    state=state.merge(active,on="delivery_id",how="left")
    state["active_situations"]=state.active_situations.fillna("")
    state["pressure_intensity"]=state.pressure_intensity.fillna(0)
    total=len(state); start=(page-1)*page_size
    return {"match_id":match_id,"scenario":scenario,"innings":sorted(state.innings.dropna().unique().tolist()),"page":page,"page_size":page_size,"total_deliveries":total,"items":clean(state.iloc[start:start+page_size])}

@app.get("/api/scenarios/comparison")
def scenario_comparison(role:Literal["batter","bowler"]|None=None):
    x=frame(ROOT/"data"/"outputs"/"scenario_comparison"/"scenario_rank_changes.csv")
    if role: x=x[x.player_role.eq(role)]
    return {"rows":int(len(x)),"items":clean(x)}

@app.get("/api/players/{player_id}/normal")
def player_normal(player_id:int):
    out={}
    for role,file in [("batter","batting_normal_performance.csv"),("bowler","bowling_normal_performance.csv")]:
        f=frame(scenario_path("proxy_inclusive")/file); rows=f[f.player_id.eq(player_id)]
        out[role]=clean(rows)
    return out

@app.get("/api/players/{player_id}/pressure")
def player_pressure(player_id:int,scenario:str="proxy_inclusive"):
    d=scenario_path(scenario); x=frame(d/"situation_ratings.csv"); x=x[x.player_id.eq(player_id)]
    if x.empty: return {"scenario":scenario,"player_id":player_id,"items":[]}
    return {"scenario":scenario,"player_id":player_id,"items":clean(x.sort_values("situation_score",ascending=False))}


web=ROOT/"frontend"/"dist"
if web.exists():
    app.mount("/",StaticFiles(directory=web,html=True),name="dashboard")



