import math
import re
import numpy as np
import pandas as pd

NO_EXTRA, NO_BALL, WIDE = 6, 1, 2

def allotted_balls(meta, innings):
    col="first_inn_revised_overs" if innings==1 else "second_inn_revised_overs"
    x=meta.get(col)
    if pd.notna(x) and float(x)>0:
        x=float(x)
        return int(x) if math.isclose(x%6,0,abs_tol=1e-8) else int(math.ceil(x*6))
    return 120

def reconstruct(ball, matches, comps):
    d=ball.merge(matches[["match_id","comp_id","match_date","stage","knock_out","first_inn_revised_overs","second_inn_revised_overs","revised_target","result","home_team_id","away_team_id"]],on="match_id",how="left",validate="many_to_one")
    d=d.merge(comps[["comp_id","comp_name","match_format","season"]],on="comp_id",how="left",validate="many_to_one")
    d=d.sort_values(["match_id","innings","overid","over_ball_num","innings_ball_num"],kind="stable").reset_index(drop=True)
    d["delivery_id"]=d.match_id.astype(str)+"-"+d.innings.astype(str)+"-"+(d.groupby(["match_id","innings"],sort=False).cumcount()+1).astype(str)
    d["extra_code"]=pd.to_numeric(d.extras1_runs,errors="coerce").fillna(NO_EXTRA).astype(int)
    d["batter_runs"]=pd.to_numeric(d.runs,errors="coerce").fillna(0).astype(int)
    d["is_legal_ball"]=~d.extra_code.isin([NO_BALL,WIDE])
    d["is_ball_faced"]=d.extra_code.ne(WIDE)
    d["batter_dot"]=d.is_ball_faced & d.batter_runs.eq(0)
    d["team_batter_boundary"]=d.is_four.fillna(False).astype(bool)|d.is_six.fillna(False).astype(bool)
    d["verified_no_extra"]=d.extra_code.eq(NO_EXTRA)&pd.to_numeric(d.extras_2_runs,errors="coerce").fillna(0).eq(0)
    d["team_runs_proxy_delivery"]=d.batter_runs+d.extra_code.map({NO_BALL:1,WIDE:1,3:1,4:1}).fillna(0).astype(int)
    d["bowler_runs_exact_delivery"]=d.batter_runs.where(d.verified_no_extra|d.extra_code.isin([3,4]),np.nan)
    d["bowler_runs_proxy_delivery"]=d.batter_runs+d.extra_code.map({NO_BALL:1,WIDE:1}).fillna(0).astype(int)

    mi=matches.set_index("match_id")
    states=[]; innings=[]
    for (mid,inn),g in d.groupby(["match_id","innings"],sort=False):
        meta=mi.loc[mid]; allotted=allotted_balls(meta,int(inn)); first_allotted=allotted_balls(meta,1); pp=math.ceil(.30*allotted); death=math.ceil(.25*math.ceil(allotted/6))*6
        score=0; proxy=0; exact=True; legal=0; wkts=0; pruns=0; pruns_proxy=0; pid=1; free_hit_pending=False
        br={}; bf={}
        for r in g.itertuples():
            code=int(r.extra_code); striker=int(r.striker_id); before=legal
            free_hit_now=free_hit_pending
            if code==NO_BALL: free_hit_pending=True
            elif code==WIDE: free_hit_pending=free_hit_pending
            else: free_hit_pending=False
            rem=max(allotted-before,0); exact_before=exact
            sr=(br.get(striker,0)*100/bf.get(striker,0)) if bf.get(striker,0) else np.nan
            states.append({"delivery_id":r.delivery_id,"match_id":int(mid),"innings":int(inn),"overid":int(r.overid),"over_ball_num":int(r.over_ball_num),
             "batting_team_id":int(r.batting_team_id),"bowling_team_id":int(r.bowling_team_id),"first_innings_allotted_legal_balls":first_allotted,
             "is_free_hit":free_hit_now,
             "legal_ball_before":before,"legal_ball_after":before+int(r.is_legal_ball),"balls_remaining_before":rem,
             "allotted_legal_balls":allotted,"powerplay_balls":pp,"death_balls":death,
             "is_powerplay":before<pp,"is_death":before>=max(allotted-death,0),"is_middle":pp<=before<max(allotted-death,0),
             "team_score_before_exact":score if exact_before else np.nan,"team_score_before_proxy":proxy,
             "is_score_exact_before":exact_before,"team_wickets_before":wkts,"wickets_in_hand_before":max(10-wkts,0),
             "crr_before_exact":(score*6/before if before else 0) if exact_before else np.nan,
             "crr_before_proxy":proxy*6/before if before else 0,
             "batter_runs_before":br.get(striker,0),"batter_balls_before":bf.get(striker,0),"batter_sr_before":sr,
             "partnership_id":pid,"partnership_runs_before_exact":pruns if exact_before else np.nan,"partnership_runs_before_proxy":pruns_proxy,
             "score_quality_before":"exact" if exact_before else "proxy_lower_bound",
             "has_missing_extras":(code!=NO_EXTRA) or (pd.notna(r.extras_2_runs) and int(r.extras_2_runs)!=0),"is_delivery_reliable":True,"source_file":"ball_by_ball.csv"})
            legal+=int(r.is_legal_ball)
            proxy+=int(r.team_runs_proxy_delivery)
            pruns_proxy+=int(r.team_runs_proxy_delivery)
            verified_no_extra=(code==NO_EXTRA and pd.notna(r.extras_2_runs) and int(r.extras_2_runs)==0)
            if verified_no_extra and exact: score+=int(r.batter_runs); pruns+=int(r.batter_runs)
            elif not verified_no_extra: exact=False
            br[striker]=br.get(striker,0)+int(r.batter_runs)
            if bool(r.is_ball_faced): bf[striker]=bf.get(striker,0)+1
            if bool(r.is_wicket): wkts+=1; pid+=1; pruns=0; pruns_proxy=0
            states[-1]["team_score_after_exact"]=score if exact else np.nan
            states[-1]["team_score_after_proxy"]=proxy
            states[-1]["is_score_exact_after"]=exact
            states[-1]["team_wickets_after"]=wkts
        complete=wkts>=10 or legal>=allotted
        innings.append({"match_id":int(mid),"innings":int(inn),"batting_team_id":int(g.batting_team_id.iloc[0]),
          "bowling_team_id":int(g.bowling_team_id.iloc[0]),"delivery_count":len(g),"legal_balls":legal,
          "allotted_legal_balls":allotted,"runs_exact":score if exact else np.nan,"runs_proxy_lower_bound":proxy,
          "is_score_exact":exact,"score_quality":"exact" if exact else "proxy_lower_bound","wickets_lost":wkts,
          "is_complete":complete,"is_super_over_candidate":int(inn)>=3,
          "first_delivery_over":int(g.overid.iloc[0]),"first_delivery_ball":int(g.over_ball_num.iloc[0]),"last_delivery_over":int(g.overid.iloc[-1]),"last_delivery_ball":int(g.over_ball_num.iloc[-1])})
    s=pd.DataFrame(states); ix=pd.DataFrame(innings)
    targets={}
    for mid,g in ix.groupby("match_id"):
        first=g[g.innings.eq(1)]
        meta=mi.loc[mid]; given=meta.get("revised_target")
        dls=bool(re.search(r"DLS|D/L",str(meta.get("result","")),re.I))
        if pd.notna(given) and float(given)>0: targets[mid]=(float(given),float(given),"metadata",True)
        elif len(first) and bool(first.iloc[0].is_complete) and not dls:
            f=first.iloc[0]; targets[mid]=(float(f.runs_exact+1) if f.is_score_exact else np.nan,float(f.runs_proxy_lower_bound+1),"first_innings_plus_one",bool(f.is_score_exact))
        else: targets[mid]=(np.nan,np.nan,"unavailable_or_DLS_unverified",False)
    s["target_exact"]=s.match_id.map(lambda x:targets[int(x)][0])
    s["target_proxy_lower_bound"]=s.match_id.map(lambda x:targets[int(x)][1])
    s["target_source"]=s.match_id.map(lambda x:targets[int(x)][2])
    s["is_target_exact"]=s.innings.eq(2)&s.match_id.map(lambda x:targets[int(x)][3])
    s["runs_required_exact_before"]=np.where(s.is_target_exact,s.target_exact-s.team_score_before_exact,np.nan)
    s["runs_required_proxy_before"]=np.where(s.innings.eq(2),s.target_proxy_lower_bound-s.team_score_before_proxy,np.nan)
    s["rrr_before_exact"]=np.where(s.is_target_exact&s.balls_remaining_before.gt(0),s.runs_required_exact_before*6/s.balls_remaining_before,np.nan)
    s["rrr_before_proxy"]=np.where(s.innings.eq(2)&s.target_proxy_lower_bound.notna()&s.balls_remaining_before.gt(0),s.runs_required_proxy_before*6/s.balls_remaining_before,np.nan)
    # An officially recorded early chase can be complete before the allotment,
    # but only when the delivery feed starts at the innings opening.
    for idx,row in ix.iterrows():
        if int(row.innings)==2 and not bool(row.is_complete):
            meta=mi.loc[int(row.match_id)]
            winner=meta.get("win_team_id",np.nan)
            result=str(meta.get("result",""))
            full_feed=(int(row.first_delivery_over)==1 and int(row.first_delivery_ball)==1)
            official_win=pd.notna(winner) and int(winner)==int(row.batting_team_id)
            if full_feed and official_win and "no result" not in result.lower():
                ix.loc[idx,"is_complete"]=True
    incomplete_map={(int(r.match_id),int(r.innings)):not bool(r.is_complete) for r in ix.itertuples()}
    s["is_incomplete_innings"]=[incomplete_map.get((int(mid),int(inn)),True) for mid,inn in zip(s.match_id,s.innings)]
    s=s.merge(d[["delivery_id","striker_id","non_striker_id","bowler_id","runs","extras1_runs","extras_2_runs","extras_type","is_wicket","dismissal_type","dismissed_player_id","is_four","is_six","batting_order","comp_id","comp_name","match_format","season","match_date","knock_out","stage","result","team_batter_boundary","is_legal_ball","is_ball_faced","batter_dot","extra_code","team_runs_proxy_delivery","bowler_runs_proxy_delivery","bowler_runs_exact_delivery","verified_no_extra"]],on="delivery_id",how="left",validate="one_to_one")
    target_rows=[{"match_id":int(k),"target_exact":v[0],"target_proxy_lower_bound":v[1],"target_source":v[2],"is_target_exact":v[3]} for k,v in targets.items()]
    ix=ix.merge(pd.DataFrame(target_rows),on="match_id",how="left",validate="many_to_one")
    return d,s,ix
