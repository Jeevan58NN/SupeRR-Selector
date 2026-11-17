import argparse
from pathlib import Path
import pandas as pd
from superr_selector.data.loader import load,manifest,validate
from superr_selector.match_state.reconstruct import reconstruct
from superr_selector.pressure.detect import detect_pressure, resolve_overlaps
from superr_selector.scoring.rating import score_scenario
from superr_selector.scoring.compare import compare_scenarios
from superr_selector.metrics.context_exports import export_context_metrics

def _write(df,path):
    tmp=path.with_suffix(path.suffix+".tmp")
    df.to_csv(tmp,index=False)
    tmp.replace(path)

def _masters(tables,root):
    m=tables["matches.csv"]; c=tables["competitions.csv"]; x=tables["playing_eleven.csv"]; p=tables["competition_team_player_mapping.csv"]
    master=p.sort_values(["player_id","comp_id","team_id"]).drop_duplicates("player_id")[["player_id","player_name"]]
    _write(master,root/"data"/"processed"/"player_master.csv")
    _write(tables["teams.csv"].drop_duplicates(["comp_id","team_id"]),root/"data"/"processed"/"team_master.csv")
    match=m.merge(c,on="comp_id",how="left",validate="many_to_one")
    _write(match,root/"data"/"processed"/"match_master.csv")
    app=x.merge(m[["match_id","comp_id"]],on="match_id",how="left",validate="many_to_one")
    app=app[app.is_played.fillna(False)|app.is_impact.eq(1)].drop_duplicates(["match_id","player_id"])
    app=app.merge(master[["player_id","player_name"]],on="player_id",how="left",validate="many_to_one")
    _write(app,root/"data"/"processed"/"playing_appearances.csv")

def _overall_metrics(d,tables,root):
    x=tables["playing_eleven.csv"]
    app=x[x.is_played.fillna(False)|x.is_impact.eq(1)].drop_duplicates(["match_id","player_id"])
    apps=app.groupby("player_id").match_id.nunique().rename("matches")
    bat=d.copy(); bat["match_innings"]=bat.match_id.astype(str)+"-"+bat.innings.astype(str); bat["balls_faced"]=bat.is_ball_faced.astype(int); bat["dot"]=bat.batter_dot.astype(int)
    bat["dismissed"]=bat.dismissed_player_id.eq(bat.striker_id)&bat.is_wicket
    bm=bat.groupby("striker_id").agg(batter_innings=("match_innings","nunique"),runs=("batter_runs","sum"),balls=("balls_faced","sum"),fours=("is_four","sum"),sixes=("is_six","sum"),dots=("dot","sum"),dismissals=("dismissed","sum"),matches_in_sample=("match_id","nunique")).reset_index().rename(columns={"striker_id":"player_id"})
    bm["strike_rate"]=bm.runs*100/bm.balls.replace(0,pd.NA); bm["average"]=bm.runs/bm.dismissals.replace(0,pd.NA); bm["dot_pct"]=bm.dots*100/bm.balls.replace(0,pd.NA); bm["boundary_pct"]=(bm.fours+bm.sixes)*100/bm.balls.replace(0,pd.NA)
    bm=bm.merge(apps,on="player_id",how="left"); _write(bm,root/"data"/"processed"/"batting_overall_metrics.csv")
    bowl=d.copy(); bowl["match_innings"]=bowl.match_id.astype(str)+"-"+bowl.innings.astype(str); bowl["bowler_dot"]=(bowl.is_legal_ball & bowl.batter_runs.eq(0)).astype(int); bowl["bowler_wicket"]=bowl.is_wicket & ~bowl.dismissal_type.fillna("").str.lower().isin(["run out","retired hurt","obstructing the field"])
    wm=bowl.groupby("bowler_id").agg(bowler_innings=("match_innings","nunique"),deliveries=("delivery_id","count"),legal_balls=("is_legal_ball","sum"),runs_proxy=("bowler_runs_proxy_delivery","sum"),wickets=("bowler_wicket","sum"),dots=("bowler_dot","sum"),matches_in_sample=("match_id","nunique")).reset_index().rename(columns={"bowler_id":"player_id"})
    wm["economy_proxy"]=wm.runs_proxy*6/wm.legal_balls.replace(0,pd.NA); wm["dot_pct"]=wm.dots*100/wm.legal_balls.replace(0,pd.NA); wm=wm.merge(apps,on="player_id",how="left"); _write(wm,root/"data"/"processed"/"bowling_overall_metrics.csv")

def run(root, selected_scenario=None):
    root=Path(root).resolve(); t=load(root); schema=validate(t)
    d,s,ix=reconstruct(t["ball_by_ball.csv"],t["matches.csv"],t["competitions.csv"])
    interim=root/"data"/"interim"; interim.mkdir(parents=True,exist_ok=True)
    _write(manifest(root),interim/"source_file_manifest.csv")
    duplicate_report=pd.DataFrame([
        {"file_name":"ball_by_ball.csv","present":(root/"ball_by_ball.csv").is_file(),"sha256":manifest(root).set_index("file_name").loc["ball_by_ball.csv","sha256"],"exact_duplicate_rows":int(t["ball_by_ball.csv"].duplicated().sum()),"canonical_source":True,"decision":"use one supplied canonical ball dataset"},
        {"file_name":"ball_by_ball_repaired(1).csv","present":(root/"ball_by_ball_repaired(1).csv").is_file(),"sha256":None,"exact_duplicate_rows":None,"canonical_source":False,"decision":"not supplied; cannot compare content/hash"},
        {"file_name":"ball_by_ball(1).csv","present":(root/"ball_by_ball(1).csv").is_file(),"sha256":None,"exact_duplicate_rows":None,"canonical_source":False,"decision":"not supplied; cannot compare content/hash"},
    ])
    _write(duplicate_report,interim/"duplicate_file_report.csv")
    _write(schema,interim/"schema_validation.csv")
    q=[]
    for name,df in t.items():
        q.append({"source_file":name,"rows":len(df),"columns":len(df.columns),"exact_duplicate_rows":int(df.duplicated().sum()),"missing_cells":int(df.isna().sum().sum()),"matches":int(df.match_id.nunique()) if "match_id" in df else None})
    _write(pd.DataFrame(q),interim/"data_quality_summary.csv")
    processed=root/"data"/"processed"; processed.mkdir(parents=True,exist_ok=True)
    _write(d,processed/"cleaned_deliveries.csv")
    _masters(t,root); _overall_metrics(d,t,root); export_context_metrics(s,root)
    scenarios=("strict_exact_context","proxy_inclusive")
    if selected_scenario is not None and selected_scenario not in scenarios:
        raise ValueError("Unknown scenario: "+selected_scenario)
    # State schemas stay synchronized even when rebuilding one scenario only.
    for scenario in scenarios:
        dest=root/"data"/"outputs"/scenario; dest.mkdir(parents=True,exist_ok=True)
        out=s.copy(); out["scenario"]=scenario
        out["score_quality"]=out.is_score_exact_before.map({True:"exact",False:"unavailable_after_uncertain_extra" if scenario=="strict_exact_context" else "proxy_lower_bound"})
        _write(out,dest/"delivery_match_state.csv")
        _write(ix,dest/"innings_summary.csv")
        _write(ix,dest/"score_reconstruction.csv")
    selected=[selected_scenario] if selected_scenario else list(scenarios)
    result={}
    for scenario in selected:
        print("Detecting and writing:",scenario,flush=True)
        episodes,members,labels,intensity=detect_pressure(s,scenario)
        print(f"Detected {len(episodes)} episodes and {len(labels)} labeled deliveries.",flush=True)
        overlap=resolve_overlaps(labels)
        print(f"Resolved {len(overlap)} overlapping delivery clusters.",flush=True)
        dest=root/"data"/"outputs"/scenario
        for frame,name in [
                           (episodes[episodes.situation_id.str.startswith("B") & ~episodes.situation_id.str.startswith("BW")],"batting_pressure_episodes.csv"),
                           (episodes[episodes.situation_id.str.startswith("BW")],"bowling_pressure_episodes.csv"),
                           (members[members.player_role.eq("batter")] if len(members) else members,"batting_pressure_membership.csv"),
                           (members[members.player_role.eq("bowler")] if len(members) else members,"bowling_pressure_membership.csv"),
                           (labels,"delivery_pressure_labels.csv"),(intensity,"pressure_intensity_history.csv")]:
            _write(frame,dest/name)
        _write(overlap,dest/"overlap_resolution_log.csv")
        print("Calculating player ratings:",scenario,flush=True)
        score_scenario(root,scenario)
        result[scenario]=dest
    if selected_scenario is None:
        compare_scenarios(root)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,required=True); p.add_argument("--scenario",choices=["strict_exact_context","proxy_inclusive"]); a=p.parse_args()
    for k,v in run(a.root,a.scenario).items(): print(k,v,flush=True)



