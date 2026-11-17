from pathlib import Path
import json
import pandas as pd
from superr_selector.scoring.rating import _tier

BOWLER_WICKETS={"bowled","caught","caught and bowled","lbw","stumped","hit wicket"}

def _write(df,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    df.to_csv(tmp,index=False)
    tmp.replace(path)

def export_context_metrics(state:pd.DataFrame,root:Path):
    root=Path(root)
    x=state.copy().sort_values(["match_id","innings","legal_ball_before","overid","over_ball_num"],kind="stable")
    keys=["match_id","innings"]
    x["match_innings"]=x.match_id.astype(str)+"-"+x.innings.astype(str)
    phase_source=x.assign(_pp=x.is_powerplay & x.is_legal_ball,_mid=x.is_middle & x.is_legal_ball,_death=x.is_death & x.is_legal_ball)
    phase=phase_source.groupby(keys,as_index=False).agg(
        allotted_legal_balls=("allotted_legal_balls","max"),powerplay_balls=("powerplay_balls","max"),death_balls=("death_balls","max"),
        first_innings_allotted_legal_balls=("first_innings_allotted_legal_balls","max"),is_incomplete_innings=("is_incomplete_innings","max"),
        phase_legal_balls_powerplay=("_pp","sum"),phase_legal_balls_middle=("_mid","sum"),phase_legal_balls_death=("_death","sum"))
    _write(phase,root/"data"/"processed"/"phase_allocation.csv")
    entries=x.dropna(subset=["striker_id"]).drop_duplicates(keys+["striker_id"],keep="first").copy()
    entries=entries.rename(columns={"striker_id":"player_id","overid":"entry_over","over_ball_num":"entry_ball","legal_ball_before":"entry_legal_ball","team_score_before_exact":"entry_score_exact","team_score_before_proxy":"entry_score_proxy","team_wickets_before":"entry_wickets_lost","wickets_in_hand_before":"entry_wickets_in_hand","balls_remaining_before":"entry_balls_remaining","crr_before_exact":"entry_crr_exact","crr_before_proxy":"entry_crr_proxy","rrr_before_exact":"entry_rrr_exact","rrr_before_proxy":"entry_rrr_proxy"})
    entry_cols=["match_id","innings","player_id","batting_order","entry_over","entry_ball","entry_legal_ball","entry_score_exact","entry_score_proxy","entry_wickets_lost","entry_wickets_in_hand","entry_balls_remaining","entry_crr_exact","entry_crr_proxy","entry_rrr_exact","entry_rrr_proxy","partnership_id","is_powerplay","is_middle","is_death","is_score_exact_before","is_incomplete_innings"]
    _write(entries[entry_cols],root/"data"/"processed"/"batter_entries.csv")
    def batter_ids(values):
        ids=sorted(set(pd.to_numeric(values,errors="coerce").dropna().astype(int)))
        return "|".join(map(str,ids))
    partnerships=x.groupby(keys+["partnership_id"],dropna=False,sort=False).agg(
        start_legal_ball=("legal_ball_before","min"),end_legal_ball=("legal_ball_after","max"),
        batter_ids=("striker_id",batter_ids),delivery_count=("delivery_id","nunique"),legal_balls=("is_legal_ball","sum"),
        runs_proxy=("team_runs_proxy_delivery","sum"),exact_no_extra=("verified_no_extra","all"),wickets=("is_wicket","sum"),
        score_before_exact=("team_score_before_exact","first"),score_after_exact=("team_score_after_exact","last"),
        score_before_proxy=("team_score_before_proxy","first"),score_after_proxy=("team_score_after_proxy","last"),
        incomplete=("is_incomplete_innings","max")).reset_index()
    partnerships["runs_exact"]=partnerships.score_after_exact-partnerships.score_before_exact
    partnerships["exact_available"]=partnerships.exact_no_extra & partnerships.score_before_exact.notna() & partnerships.score_after_exact.notna()
    partnerships.loc[~partnerships.exact_available,"runs_exact"]=pd.NA
    partnerships["score_quality"]=partnerships.exact_available.map({True:"exact_no_extra_only",False:"proxy_lower_bound_only"})
    _write(partnerships,root/"data"/"processed"/"partnerships.csv")
    y=x.copy()
    y["bowler_wicket"]=(y.is_wicket.fillna(False)&y.dismissal_type.fillna("").str.lower().isin(BOWLER_WICKETS)).astype(int)
    y["wide_count"]=y.extra_code.eq(2).astype(int)
    y["no_ball_count"]=y.extra_code.eq(1).astype(int)
    y["bowler_dot_exact"]=(y.is_legal_ball & y.bowler_runs_exact_delivery.eq(0)).astype(int)
    over=y.groupby(keys+["overid","bowler_id"],dropna=False,as_index=False).agg(
        deliveries=("delivery_id","nunique"),legal_balls=("is_legal_ball","sum"),batter_runs=("runs","sum"),
        runs_conceded_proxy=("bowler_runs_proxy_delivery","sum"),runs_conceded_exact=("bowler_runs_exact_delivery","sum"),
        exact_run_deliveries=("bowler_runs_exact_delivery","count"),dots=("bowler_dot_exact","sum"),bowler_wickets=("bowler_wicket","sum"),
        wides=("wide_count","sum"),no_balls=("no_ball_count","sum"),is_powerplay=("is_powerplay","max"),is_middle=("is_middle","max"),
        is_death=("is_death","max"),batting_team_id=("batting_team_id","first"),bowling_team_id=("bowling_team_id","first"),
        comp_id=("comp_id","first"),season=("season","first"))
    over["economy_exact"]=over.runs_conceded_exact*6/over.legal_balls.replace(0,pd.NA)
    over.loc[over.exact_run_deliveries.ne(over.deliveries),"economy_exact"]=pd.NA
    over["economy_proxy"]=over.runs_conceded_proxy*6/over.legal_balls.replace(0,pd.NA)
    _write(over,root/"data"/"processed"/"bowler_spell_summary.csv")
    x["phase"]=x.apply(lambda r:"powerplay" if r.is_powerplay else ("death" if r.is_death else "middle"),axis=1)
    bat=x.dropna(subset=["striker_id"]).copy()
    bat["player_id"]=bat.striker_id
    bat["dots"]=bat.batter_dot.astype(int)
    bat["boundaries"]=bat.team_batter_boundary.astype(int)
    bat["dismissed_by_batter"]=(bat.is_wicket & bat.dismissed_player_id.fillna(-1).astype(int).eq(bat.striker_id)).astype(int)
    for groups,name in [(["phase"],"batting_phase_metrics.csv"),(["overid"],"batting_over_metrics.csv"),(["batting_order"],"batting_position_metrics.csv")]:
        g=bat.groupby(["player_id"]+groups,dropna=False,as_index=False).agg(
            matches_in_sample=("match_id","nunique"),innings_in_sample=("match_innings","nunique"),runs=("runs","sum"),
            balls_faced=("is_ball_faced","sum"),dots=("dots","sum"),boundaries=("boundaries","sum"),dismissals=("dismissed_by_batter","sum"))
        g["strike_rate"]=g.runs*100/g.balls_faced.replace(0,pd.NA)
        g["dot_pct"]=g.dots*100/g.balls_faced.replace(0,pd.NA)
        _write(g,root/"data"/"processed"/name)
    bowl=x.dropna(subset=["bowler_id"]).copy()
    bowl["player_id"]=bowl.bowler_id
    bowl["dots"]=(bowl.is_legal_ball & bowl.bowler_runs_exact_delivery.eq(0)).astype(int)
    bowl["bowler_wickets"]=(bowl.is_wicket.fillna(False)&bowl.dismissal_type.fillna("").str.lower().isin(BOWLER_WICKETS)).astype(int)
    for groups,name in [(["phase"],"bowling_phase_metrics.csv"),(["overid"],"bowling_over_metrics.csv")]:
        g=bowl.groupby(["player_id"]+groups,dropna=False,as_index=False).agg(
            matches_in_sample=("match_id","nunique"),innings_in_sample=("match_innings","nunique"),deliveries=("delivery_id","nunique"),
            legal_balls=("is_legal_ball","sum"),runs_conceded_proxy=("bowler_runs_proxy_delivery","sum"),
            runs_conceded_exact=("bowler_runs_exact_delivery","sum"),exact_run_deliveries=("bowler_runs_exact_delivery","count"),
            exact_legal_balls=("bowler_runs_exact_delivery",lambda s:int((bowl.loc[s.index,"is_legal_ball"] & s.notna()).sum())),dots=("dots","sum"),wickets=("bowler_wickets","sum"))
        g["economy_proxy"]=g.runs_conceded_proxy*6/g.legal_balls.replace(0,pd.NA)
        g["economy_exact"]=g.runs_conceded_exact*6/g.legal_balls.replace(0,pd.NA)
        g.loc[g.exact_run_deliveries.ne(g.deliveries),"economy_exact"]=pd.NA
        g["dot_pct_exact"]=g.dots*100/g.exact_legal_balls.replace(0,pd.NA)
        _write(g,root/"data"/"processed"/name)

    # Player context tables support year, competition, opponent and entry-state
    # exploration without requiring the dashboard to recompute cricket metrics.
    state=x.copy()
    state["year"]=pd.to_numeric(state.season,errors="coerce")
    state["phase"]=["powerplay" if r.is_powerplay else ("death" if r.is_death else "middle") for r in state.itertuples()]
    teamfile=root/"teams.csv"
    teammap=(pd.read_csv(teamfile).drop_duplicates(["comp_id","team_id"]).set_index(["comp_id","team_id"]).team_name if teamfile.exists() else pd.Series(dtype=object))
    tierfile=root/"config"/"opponent_tiers.yaml"
    if tierfile.exists():
        with open(tierfile,encoding="utf-8") as f: tier_cfg=json.load(f)
    else: tier_cfg={"teams":{}}
    for role,idcol,oppcol,name in [("batter","striker_id","bowling_team_id","batting_context_metrics.csv"),
                                   ("bowler","bowler_id","batting_team_id","bowling_context_metrics.csv")]:
        z=state.dropna(subset=[idcol]).copy().rename(columns={idcol:"player_id",oppcol:"opponent_team_id"})
        z["role"]=role
        entry=z.drop_duplicates(["match_id","innings","player_id"],keep="first")[["match_id","innings","player_id","team_wickets_before","team_score_before_proxy"]].rename(columns={"team_wickets_before":"entry_wickets_lost","team_score_before_proxy":"entry_score_proxy"})
        entry["entry_wicket_band"]=(entry.entry_wickets_lost//2*2).clip(upper=8).astype(str)+"-"+(entry.entry_wickets_lost//2*2+1).clip(upper=9).astype(str)
        entry["entry_score_band"]=(entry.entry_score_proxy//10*10).astype(str)+"-"+(entry.entry_score_proxy//10*10+9).astype(str)
        z=z.merge(entry[["match_id","innings","player_id","entry_wicket_band","entry_score_band"]],on=["match_id","innings","player_id"],how="left",validate="many_to_one")
        z["opponent_name"]=[teammap.get((int(c),int(t)),"Unknown team") for c,t in zip(z.comp_id,z.opponent_team_id)]
        comp_names=z.comp_name if "comp_name" in z else pd.Series("",index=z.index)
        formats=z.match_format if "match_format" in z else pd.Series("",index=z.index)
        z["competition_pool"]=["IPL" if "IPL" in str(c).upper() else ("T20I" if str(f).upper()=="T20I" else "Other T20") for c,f in zip(comp_names,formats)]
        z["opponent_tier"]=[_tier(n,p,tier_cfg) for n,p in zip(z.opponent_name,z.competition_pool)]
        if role=="batter":
            z["balls_metric"]=z.is_ball_faced.astype(int)
            z["runs_metric"]=pd.to_numeric(z.runs,errors="coerce").fillna(0)
            z["dots_metric"]=z.batter_dot.astype(int)
            z["outs_metric"]=(z.is_wicket.fillna(False)&z.dismissed_player_id.fillna(-1).astype(int).eq(z.player_id)).astype(int)
        else:
            z["balls_metric"]=z.is_legal_ball.astype(int)
            z["runs_metric"]=pd.to_numeric(z.bowler_runs_proxy_delivery,errors="coerce")
            z["dots_metric"]=(z.is_legal_ball&z.bowler_runs_proxy_delivery.eq(0)).astype(int)
            z["outs_metric"]=(z.is_wicket.fillna(False)&z.dismissal_type.fillna("").str.lower().isin(BOWLER_WICKETS)).astype(int)
        z["boundaries_metric"]=z.team_batter_boundary.astype(int)
        dims=[d for d in ["comp_id","comp_name","match_format","season","year","innings","phase","overid","opponent_team_id","opponent_name","opponent_tier","team_wickets_before","entry_wicket_band","entry_score_band","batting_order"] if d in z.columns]
        context_rows=[]
        for dimension in dims:
            g=z.groupby(["player_id",dimension],dropna=False,as_index=False).agg(matches_in_sample=("match_id","nunique"),innings_in_sample=("match_innings","nunique"),
                deliveries=("delivery_id","nunique"),runs=("runs_metric","sum"),balls=("balls_metric","sum"),dots=("dots_metric","sum"),dismissals=("outs_metric","sum"),boundaries=("boundaries_metric","sum"))
            g["context_dimension"]=dimension
            g["context_value"]=g[dimension].astype("string")
            if role=="batter": g["strike_rate"]=g.runs*100/g.balls.replace(0,pd.NA)
            else: g["economy_proxy"]=g.runs*6/g.balls.replace(0,pd.NA)
            context_rows.append(g.drop(columns=[dimension]))
        _write(pd.concat(context_rows,ignore_index=True),root/"data"/"processed"/name)


