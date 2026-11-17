from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import json

BOWLER_WICKETS={"bowled","caught","caught and bowled","lbw","stumped","hit wicket"}
ROLE_WEIGHTS={"batter":{"scoring":0.65,"survival":0.35},"bowler":{"control":0.70,"wickets":0.30}}
OVERLAP_PRIORITY={"B1":2,"B9":1,"B5":1,"B7":2,"B8":3}
OVERLAP_CLUSTERS={"late_chase_rate":["B1","B9"],"wicket_collapse":["B5","B7","B8"]}

def _tier(name, pool, tier_cfg):
    n=str(name).strip().lower()
    if pool=="IPL": return "IPL"
    if n.endswith(" a"): return "A-team pool"
    aliases={"united states of america":"usa","u.s.a.":"usa"}
    n=aliases.get(n,n)
    for tier,teams in tier_cfg["teams"].items():
        if n in {str(x).lower() for x in teams}: return tier
    return "Lowest international tier" if pool=="T20I" else "Other T20"

def _position_group(x):
    if pd.isna(x): return "unknown"
    x=int(x)
    if x<=2: return "opener"
    if x<=5: return "top_middle"
    if x<=7: return "finisher"
    return "tail"

def _phase(row):
    if bool(row.is_powerplay): return "powerplay"
    if bool(row.is_death): return "death"
    return "middle"

def match_consistency(values,evidence_n=None,prior_k=30.0,sample_weights=None):
    values=np.asarray(list(values),dtype=float)
    n=len(values)
    if n==0: return np.nan
    weights=np.ones(n,dtype=float) if sample_weights is None else np.asarray(sample_weights,dtype=float)
    if len(weights)!=n or weights.sum()<=0: weights=np.ones(n,dtype=float)
    good=float(np.average(values>50,weights=weights)); exceptional=float(np.average(values>=65,weights=weights))
    mean=float(np.average(values,weights=weights))
    dispersion=float(np.sqrt(np.average((values-mean)**2,weights=weights))) if n>=2 else None
    stability=100-min(dispersion*2,100) if dispersion is not None else 50.0
    raw=.50*good*100+.25*exceptional*100+.25*stability
    evidence_n=float(n if evidence_n is None else max(evidence_n,0.0))
    return (evidence_n/(evidence_n+prior_k))*raw+(prior_k/(evidence_n+prior_k))*50

def shrink_score(observed,n_eff,k=5.0,prior=50.0):
    n_eff=max(float(n_eff),0.0)
    return (n_eff*float(observed)+float(k)*float(prior))/(n_eff+float(k)) if n_eff+float(k)>0 else float(prior)

def combined_evidence_matches(pressure_matches, normal_innings):
    """Conservative effective evidence: both pressure matches and normal innings must support the rating."""
    p=max(float(pressure_matches),0.0); n=max(float(normal_innings),0.0)
    return (2*p*n/(p+n)) if p+n else 0.0

def _normal_scores(bat_normal,bowl_normal,normal_prior_innings=10.0):
    parts=[]
    for role,frame in [("batter",bat_normal),("bowler",bowl_normal)]:
        z=frame.copy()
        if z.empty: continue
        if role=="batter": z["normal_raw"]=z.strike_rate_or_economy-.35*z.dot_pct
        else: z["normal_raw"]=-.70*z.strike_rate_or_economy+.30*z.dot_pct+.30*np.where(z.balls.gt(0),z.dismissals*100/z.balls,0)
        overall=_robust_stats(z,"normal_raw")
        group_stats={}
        for key,g in z.groupby("normal_role_group",dropna=False):
            stat=_robust_stats(g,"normal_raw")
            if stat and stat[3]>=5: group_stats[str(key)]=stat
        raw=[]
        for row in z.itertuples(index=False):
            stat=group_stats.get(str(row.normal_role_group),overall)
            med,scale=stat[0],stat[1]
            raw.append(float(np.clip(50+10*(float(row.normal_raw)-med)/scale,0,100)))
        tier_factor=pd.to_numeric(z.normal_opponent_weight,errors="coerce").fillna(.7).clip(0,1)
        z["normal_rating_raw"]=50+(np.asarray(raw)-50)*tier_factor
        z["normal_rating"]=(z.innings_in_sample*z.normal_rating_raw+normal_prior_innings*50)/(z.innings_in_sample+normal_prior_innings)
        z["player_role"]=role
        parts.append(z[["player_id","player_role","normal_rating","normal_rating_raw","matches_in_sample","innings_in_sample","strike_rate_or_economy","dot_pct","dismissals","balls","faded_pressure_deliveries","normal_role_group","normal_opponent_weight"]])
    if not parts: return pd.DataFrame(columns=["player_id","player_role","normal_rating","normal_rating_raw","normal_matches","normal_innings","normal_rate","dot_pct","dismissals","balls","faded_pressure_deliveries","normal_role_group","normal_opponent_weight"])
    return pd.concat(parts,ignore_index=True).rename(columns={"strike_rate_or_economy":"normal_rate","matches_in_sample":"normal_matches","innings_in_sample":"normal_innings"})

def _robust_stats(frame, metric):
    x=pd.to_numeric(frame[metric],errors="coerce").dropna().to_numpy(float)
    if len(x)==0: return None
    med=float(np.median(x)); mad=float(np.median(np.abs(x-med)))
    if mad>0: scale=1.4826*mad
    else:
        q25,q75=np.percentile(x,[25,75]); scale=(q75-q25)/1.349
        if not np.isfinite(scale) or scale==0: scale=float(np.std(x,ddof=1)) if len(x)>1 else 0
        if not np.isfinite(scale) or scale==0: scale=10.0
    return med,scale,len(x),frame.player_id.nunique()

def _normalize(obs, metric, direction, fallback_groups):
    vals=[]; counts=[]; used=[]
    maps=[]
    for cols in fallback_groups:
        mapping={}
        for key,grp in obs.groupby(cols,dropna=False,sort=False):
            if not isinstance(key,tuple): key=(key,)
            stat=_robust_stats(grp,metric)
            if stat and stat[3]>=5: mapping[key]=stat
        maps.append((cols,mapping))
    for row in obs.itertuples(index=False):
        result=None; usedcols=None
        for cols,mapping in maps:
            key=tuple(getattr(row,c) for c in cols)
            result=mapping.get(key)
            if result is not None: usedcols="|".join(cols); break
        if result is None:
            result=_robust_stats(obs,metric); usedcols="role_population"
        if result is None or pd.isna(getattr(row,metric)):
            vals.append(np.nan); counts.append(0); used.append("unavailable"); continue
        med,scale,n,_=result
        z=(float(getattr(row,metric))-med)/scale*direction
        vals.append(float(np.clip(50+10*z,0,100))); counts.append(n); used.append(usedcols)
    return pd.Series(vals,index=obs.index),pd.Series(counts,index=obs.index),pd.Series(used,index=obs.index)

def _overlap_factor(labels, overlap):
    if overlap.empty: return pd.Series(1.0,index=labels.index)
    lookup={}
    for r in overlap.itertuples(index=False):
        for code in str(r.active_situations).split("|"):
            lookup[(str(r.delivery_id),code)]=(float(r.shared_contribution_factor) if code==r.selected_situation else 0.0)
    return pd.Series([lookup.get((str(r.delivery_id),str(r.situation_id)),1.0) for r in labels.itertuples(index=False)],index=labels.index)

def score_scenario(root: Path, scenario: str, prior_k: float=30.0, consistency_weight: float=.20,
                   normal_prior_innings: float|None=None):
    root=Path(root); out=root/"data"/"outputs"/scenario; processed=root/"data"/"processed"
    if normal_prior_innings is None:
        with open(root/"config"/"scoring_weights.yaml",encoding="utf-8") as f:
            normal_prior_innings=float(json.load(f).get("normal_prior_strength_innings",10))
    labels=pd.read_csv(out/"delivery_pressure_labels.csv",low_memory=False)
    episodes=pd.concat([pd.read_csv(out/"batting_pressure_episodes.csv",low_memory=False),
                        pd.read_csv(out/"bowling_pressure_episodes.csv",low_memory=False)],ignore_index=True)
    statecols=["delivery_id","match_id","innings","striker_id","bowler_id","batting_team_id","bowling_team_id",
        "runs","dismissed_player_id","is_wicket","dismissal_type","is_legal_ball","is_ball_faced","batter_dot",
        "team_batter_boundary","bowler_runs_proxy_delivery","bowler_runs_exact_delivery","is_powerplay","is_middle","is_death","batting_order",
        "comp_id","comp_name","match_format","season","knock_out","match_date","is_score_exact_before",
        "target_exact","target_proxy_lower_bound","team_score_after_exact","team_score_after_proxy","balls_remaining_before",
        "rrr_before_exact","rrr_before_proxy"]
    state=pd.read_csv(out/"delivery_match_state.csv",usecols=lambda c:c in statecols,low_memory=False)
    labels=labels.merge(state,on=["delivery_id","match_id","innings"],how="left",validate="many_to_one")
    labels["player_id"]=np.where(labels.player_role.eq("batter"),labels.striker_id,labels.bowler_id)
    labels=labels[labels.player_id.notna()].copy(); labels["player_id"]=labels.player_id.astype(int)
    labels["opposition_team_id"]=np.where(labels.player_role.eq("batter"),labels.bowling_team_id,labels.batting_team_id).astype(int)
    labels["competition_pool"]=np.where(labels.comp_name.str.contains("IPL",case=False,na=False),"IPL",
        np.where(labels.match_format.str.upper().eq("T20I"),"T20I","Other T20"))
    labels["phase_role"]=[_phase(r) for r in labels.itertuples()]
    labels["position_group"]=[_position_group(x) if role=="batter" else "bowler" for x,role in zip(labels.batting_order,labels.player_role)]
    labels["runs_num"]=pd.to_numeric(labels.runs,errors="coerce").fillna(0)
    labels["outs"]=labels.is_wicket.fillna(False)&labels.dismissed_player_id.fillna(-1).astype(int).eq(labels.player_id)
    labels["bowler_wicket"]=labels.is_wicket.fillna(False)&labels.dismissal_type.fillna("").str.lower().isin(BOWLER_WICKETS)
    labels["bowler_runs_metric"]=labels.bowler_runs_proxy_delivery if scenario=="proxy_inclusive" else labels.bowler_runs_exact_delivery
    if scenario=="strict_exact_context":
        labels["balls"]=np.where(labels.player_role.eq("batter"),labels.is_ball_faced.astype(int),(labels.is_legal_ball & labels.bowler_runs_metric.notna()).astype(int))
    else:
        labels["balls"]=np.where(labels.player_role.eq("batter"),labels.is_ball_faced.astype(int),labels.is_legal_ball.astype(int))
    labels["player_runs"]=np.where(labels.player_role.eq("batter"),labels.runs_num,labels.bowler_runs_metric)
    labels["dots"]=np.where(labels.player_role.eq("batter"),labels.batter_dot.astype(int),
        (labels.is_legal_ball & labels.bowler_runs_metric.eq(0)).astype(int))
    labels["dismissals"]=np.where(labels.player_role.eq("batter"),labels.outs.astype(int),labels.bowler_wicket.astype(int))
    labels["boundaries"]=labels.team_batter_boundary.astype(int)
    if scenario=="strict_exact_context":
        target=pd.to_numeric(labels.target_exact,errors="coerce")
        score_after=pd.to_numeric(labels.team_score_after_exact,errors="coerce")
        rrr_before=pd.to_numeric(labels.rrr_before_exact,errors="coerce")
    else:
        target=pd.to_numeric(labels.target_proxy_lower_bound,errors="coerce")
        score_after=pd.to_numeric(labels.team_score_after_proxy,errors="coerce")
        rrr_before=pd.to_numeric(labels.rrr_before_proxy,errors="coerce")
    balls_after=pd.to_numeric(labels.balls_remaining_before,errors="coerce")-labels.is_legal_ball.astype(int)
    rrr_after=((target-score_after).clip(lower=0))*6/balls_after.where(balls_after.gt(0))
    labels["rrr_reduction"]=rrr_before-rrr_after
    labels["opponent_team_key"]=labels.comp_id.astype(str)+"-"+labels.opposition_team_id.astype(str)
    teammap=pd.read_csv(root/"teams.csv").drop_duplicates(["comp_id","team_id"]).set_index(["comp_id","team_id"]).team_name
    labels["opposition_name"]=[teammap.get((int(c),int(t)),"Unknown team") for c,t in zip(labels.comp_id,labels.opposition_team_id)]
    with open(root/"config"/"opponent_tiers.yaml",encoding="utf-8") as f: tier_cfg=json.load(f)
    labels["opponent_tier"]=[_tier(n,p,tier_cfg) for n,p in zip(labels.opposition_name,labels.competition_pool)]
    labels["opponent_weight"]=labels.opponent_tier.map(tier_cfg["weights"]).fillna(1.0).astype(float)
    overlap=pd.read_csv(out/"overlap_resolution_log.csv",low_memory=False)
    labels["shared_contribution_factor"]=_overlap_factor(labels,overlap)
    labels["opportunity_weight"]=labels.severity_weight*labels.pressure_intensity*labels.shared_contribution_factor
    # One player cannot count the same delivery twice for a situation if two
    # repeat triggers overlap. Preserve episode rows elsewhere for audit.
    labels=labels.sort_values(["delivery_id","player_role","player_id","situation_id","pressure_intensity"],ascending=[True,True,True,True,False])
    labels=labels.drop_duplicates(["delivery_id","player_role","player_id","situation_id"],keep="first")
    # Delivery-level normal and pressure references count each player-delivery
    # once; overlapping situation tags remain available separately above.
    label_unique=labels.sort_values("pressure_intensity",ascending=False).drop_duplicates(
        ["delivery_id","player_role","player_id"],keep="first")
    high_pairs=set(zip(label_unique.loc[label_unique.pressure_intensity.gt(.20),"delivery_id"].astype(str),
                       label_unique.loc[label_unique.pressure_intensity.gt(.20),"player_role"],
                       label_unique.loc[label_unique.pressure_intensity.gt(.20),"player_id"].astype(int)))
    faded=label_unique[label_unique.pressure_intensity.le(.20)].groupby(["player_role","player_id"]).delivery_id.nunique()
    def summarize_role(role):
        is_bat=role=="batter"
        idcol="striker_id" if is_bat else "bowler_id"
        x=state.copy(); x["player_id"]=pd.to_numeric(x[idcol],errors="coerce")
        x=x[x.player_id.notna()].copy(); x["player_id"]=x.player_id.astype(int)
        x["player_role"]=role
        x["opponent_team_id"]=x.bowling_team_id if is_bat else x.batting_team_id
        pool=np.where(x.comp_name.str.contains("IPL",case=False,na=False),"IPL",np.where(x.match_format.str.upper().eq("T20I"),"T20I","Other T20"))
        x["normal_opponent_tier"]=[_tier(teammap.get((int(c),int(t)),"Unknown team"),str(pl),tier_cfg) for c,t,pl in zip(x.comp_id,x.opponent_team_id,pool)]
        x["normal_opponent_weight"]=x.normal_opponent_tier.map(tier_cfg["weights"]).fillna(.7).astype(float)
        if is_bat: x["normal_role_group"]=[_position_group(v) for v in x.batting_order]
        else: x["normal_role_group"]=[_phase(r) for r in x.itertuples()]
        x["high_pressure"]=[(str(d),role,int(pid)) in high_pairs for d,pid in zip(x.delivery_id,x.player_id)]
        x["normal_reference"]=~x.high_pressure
        bowler_metric=x.bowler_runs_proxy_delivery if scenario=="proxy_inclusive" else x.bowler_runs_exact_delivery
        x["balls"]=x.is_ball_faced.astype(int) if is_bat else (x.is_legal_ball.astype(int) if scenario=="proxy_inclusive" else (x.is_legal_ball & bowler_metric.notna()).astype(int))
        x["runs_value"]=pd.to_numeric(x.runs,errors="coerce").fillna(0) if is_bat else pd.to_numeric(bowler_metric,errors="coerce")
        x["dots_value"]=x.batter_dot.astype(int) if is_bat else (x.is_legal_ball & bowler_metric.eq(0)).astype(int)
        x["outs_value"]=(x.is_wicket.fillna(False)&x.dismissed_player_id.fillna(-1).astype(int).eq(x.player_id)).astype(int) if is_bat else (x.is_wicket.fillna(False)&x.dismissal_type.fillna("").str.lower().isin(BOWLER_WICKETS)).astype(int)
        def agg(frame,kind):
            g=frame.groupby("player_id").agg(matches_in_sample=("match_id","nunique"),innings_in_sample=("match_id",lambda v:frame.loc[v.index,["match_id","innings"]].drop_duplicates().shape[0]),
                runs=("runs_value","sum"),balls=("balls","sum"),dots=("dots_value","sum"),dismissals=("outs_value","sum"),
                boundaries=("team_batter_boundary","sum"),deliveries=("delivery_id","nunique")).reset_index()
            g["strike_rate_or_economy"]=np.where(g.balls.gt(0),g.runs*100/g.balls if is_bat else g.runs*6/g.balls,np.nan)
            g["dot_pct"]=np.where(g.balls.gt(0),g.dots*100/g.balls,np.nan)
            g["average_or_wickets_per_100"]=np.where(g.dismissals.gt(0),g.runs/g.dismissals if is_bat else g.dismissals*100/g.balls.replace(0,np.nan),np.nan)
            g["reference_type"]=kind
            role_group=frame.groupby("player_id").normal_role_group.agg(lambda s:s.mode().iloc[0] if not s.mode().empty else "unknown")
            opp_weight=frame.groupby("player_id").normal_opponent_weight.mean()
            g=g.merge(role_group.rename("normal_role_group"),on="player_id",how="left").merge(opp_weight.rename("normal_opponent_weight"),on="player_id",how="left")
            return g
        normal=agg(x[x.normal_reference],"normal_including_faded_pressure")
        press=agg(x[x.high_pressure],"pressure_intensity_above_0.20")
        faded_counts=faded.get(role)
        if faded_counts is not None:
            normal["faded_pressure_deliveries"]=[int(faded_counts.get(int(pid),0)) for pid in normal.player_id]
        else: normal["faded_pressure_deliveries"]=0
        return normal,press
    bat_normal,bat_pressure=summarize_role("batter")
    bowl_normal,bowl_pressure=summarize_role("bowler")
    for frame,name in [(bat_normal,"batting_normal_performance.csv"),(bowl_normal,"bowling_normal_performance.csv"),
                       (bat_pressure,"batting_pressure_performance.csv"),(bowl_pressure,"bowling_pressure_performance.csv")]:
        frame.to_csv(out/name,index=False)
    # Opponent tier scales the performance departure from a neutral peer score.
    group=["player_id","player_role","match_id","situation_id"]
    obs=labels.groupby(group,as_index=False).agg(
        runs=("player_runs","sum"),balls=("balls","sum"),dots=("dots","sum"),
        dismissals=("dismissals","sum"),boundaries=("boundaries","sum"),
        matches_in_sample=("match_id","nunique"),episodes=("episode_id","nunique"),
        pressure_deliveries=("delivery_id","nunique"),exact_context_deliveries=("is_score_exact_before","sum"),
        mean_rrr_reduction=("rrr_reduction","mean"),
        mean_intensity=("pressure_intensity","mean"),opponent_weight=("opponent_weight","mean"),opportunity_weight=("opportunity_weight","sum"),
        opponent_tier=("opponent_tier",lambda x:x.mode().iloc[0] if not x.mode().empty else "unknown"),
        competition_pool=("competition_pool",lambda x:x.mode().iloc[0] if not x.mode().empty else "unknown"),
        phase_role=("phase_role",lambda x:x.mode().iloc[0] if not x.mode().empty else "unknown"),
        position_group=("position_group",lambda x:x.mode().iloc[0] if not x.mode().empty else "unknown"),
        knock_out=("knock_out","max"),
    )
    obs["rate"]=np.where(obs.balls.gt(0),obs.runs*100/obs.balls,np.nan)
    obs["dot_pct"]=np.where(obs.balls.gt(0),obs.dots*100/obs.balls,np.nan)
    obs["dismissal_rate"]=np.where(obs.balls.gt(0),obs.dismissals*100/obs.balls,np.nan)
    obs["economy"]=np.where(obs.balls.gt(0),obs.runs*6/obs.balls,np.nan)
    obs["wicket_rate"]=np.where(obs.balls.gt(0),obs.dismissals*100/obs.balls,np.nan)
    obs["boundary_rate"]=np.where(obs.balls.gt(0),obs.boundaries*100/obs.balls,np.nan)
    obs["scoring_signal"]=np.where(obs.player_role.eq("batter"),obs.rate-.35*obs.dot_pct,np.nan)
    obs["control_signal"]=np.where(obs.player_role.eq("bowler"),-.7*obs.economy+.3*obs.dot_pct,np.nan)
    obs["wicket_signal"]=np.where(obs.player_role.eq("bowler"),obs.wicket_rate,np.nan)
    obs["boundary_prevention_signal"]=-obs.boundary_rate
    obs["chase_progress_signal"]=obs.mean_rrr_reduction
    obs["chase_defence_signal"]=-obs.mean_rrr_reduction
    player_master=pd.read_csv(processed/"player_master.csv")
    appear=pd.read_csv(processed/"playing_appearances.csv")
    appearance_counts=appear.groupby("player_id").match_id.nunique().rename("matches").reset_index()
    # Situation- and context-specific peer fallback. Role is never discarded.
    obs["peer_score"]=np.nan; obs["peer_score_raw"]=np.nan; obs["benchmark_n"]=0; obs["benchmark_level"]=""
    fallback=[
        ["situation_id","player_role","competition_pool","opponent_tier","phase_role","position_group"],
        ["situation_id","player_role","competition_pool","phase_role","position_group"],
        ["situation_id","player_role","competition_pool","phase_role"],
        ["situation_id","player_role","competition_pool"],
        ["situation_id","player_role"],
        ["player_role"],
    ]
    for role in ["batter","bowler"]:
        ix=obs.player_role.eq(role)
        if role=="batter":
            metric_weights=[("scoring_signal",.45,1),("runs",.15,1),("boundary_rate",.20,1),("chase_progress_signal",.20,1)]
        else:
            metric_weights=[("control_signal",.45,1),("wicket_signal",.30,1),("boundary_prevention_signal",.15,1),("chase_defence_signal",.10,1)]
        zparts=[]
        part_weights=[]
        for value,weight,direction in metric_weights:
            z,n,level=_normalize(obs.loc[ix].copy(),value,direction,fallback)
            zparts.append(z); part_weights.append(weight)
            obs.loc[ix,"benchmark_n"]=np.maximum(obs.loc[ix,"benchmark_n"].to_numpy(),n.to_numpy())
            obs.loc[ix,"benchmark_level"]=level.to_numpy()
        zmat=pd.concat(zparts,axis=1)
        wvec=np.asarray(part_weights,dtype=float)
        score=zmat.mul(wvec,axis=1).sum(axis=1,min_count=1)/zmat.notna().mul(wvec).sum(axis=1).replace(0,np.nan)
        tier_weights=obs.loc[ix,"opponent_weight"].to_numpy(float)
        obs.loc[ix,"peer_score_raw"]=score.to_numpy(float)
        obs.loc[ix,"peer_score"]=np.clip(50.0+(score.to_numpy(float)-50.0)*tier_weights,0,100)
    # Situation ratings retain separate evidence and scores; missing context is
    # not converted into a zero performance.
    match_scores=[]
    for (player,role,match),g in obs.groupby(["player_id","player_role","match_id"],sort=False):
        usable=g[g.peer_score.notna() & g.opportunity_weight.gt(0)]
        if usable.empty: continue
        w=usable.opportunity_weight.to_numpy(float)
        match_score=float(np.average(usable.peer_score.to_numpy(float),weights=w))
        opponent_weight=float(np.average(usable.opponent_weight.to_numpy(float),weights=w))
        match_scores.append({"player_id":int(player),"player_role":role,"match_id":int(match),
            "match_score":match_score,"match_score_unweighted_opponent":float(np.average(usable.peer_score_raw.to_numpy(float),weights=w)),"match_opportunity_weight":opponent_weight,
            "situations_in_match":int(usable.situation_id.nunique()),"episodes_in_match":int(usable.episodes.sum()),
            "pressure_deliveries":int(usable.pressure_deliveries.sum()),"knock_out":int(usable.knock_out.max())})
    match_df=pd.DataFrame(match_scores)
    # Pressure match evidence is paired with the player's independent normal-innings sample.
    # Episodes/deliveries never masquerade as independent matches.
    normal_sample={}
    for role,frame in [("batter",bat_normal),("bowler",bowl_normal)]:
        for row in frame.itertuples(index=False):
            normal_sample[(int(row.player_id),role)]=(int(row.innings_in_sample),int(row.matches_in_sample))
    normal_scores=_normal_scores(bat_normal,bowl_normal,normal_prior_innings)
    normal_lookup={(int(r.player_id),r.player_role):r._asdict() for r in normal_scores.itertuples(index=False)}
    reliability=[]; ratings=[]
    rng=np.random.default_rng(20261116)
    for (player,role),g in match_df.groupby(["player_id","player_role"],sort=False):
        vals=g.match_score.to_numpy(float); weights=g.match_opportunity_weight.to_numpy(float)
        pressure_n=float(weights.sum())
        observed=float(np.average(vals,weights=weights)) if len(vals) else np.nan
        normal_innings,normal_matches=normal_sample.get((int(player),role),(0,0))
        normal_row=normal_lookup.get((int(player),role),{})
        normal_rating=float(normal_row.get("normal_rating",50.0))
        normal_rating_raw=normal_row.get("normal_rating_raw",np.nan)
        normal_rate=normal_row.get("normal_rate",np.nan)
        n_eff=combined_evidence_matches(pressure_n,normal_innings)
        adjusted=shrink_score(observed,n_eff,prior_k,50) if n_eff else np.nan
        n=len(vals)
        good=float(np.average(vals>50,weights=weights)) if n else np.nan
        excellent=float(np.average(vals>=65,weights=weights)) if n else np.nan
        consistency=match_consistency(vals,evidence_n=n_eff,prior_k=prior_k,sample_weights=weights) if n else np.nan
        sd=float(np.std(vals,ddof=1)) if n>=2 else np.nan
        final=(.70-consistency_weight)*adjusted+consistency_weight*consistency+.30*normal_rating if pd.notna(adjusted) and pd.notna(consistency) else np.nan
        if n:
            boot=[]
            for _ in range(300):
                idx=rng.integers(0,n,n); bv=vals[idx]; bw=weights[idx]
                bo=float(np.average(bv,weights=bw)) if bw.sum() else 50
                boot_n=combined_evidence_matches(float(bw.sum()),normal_innings)
                ba=(boot_n*bo+prior_k*50)/(boot_n+prior_k)
                bc=match_consistency(bv,evidence_n=boot_n,prior_k=prior_k,sample_weights=bw)
                boot.append((.70-consistency_weight)*ba+consistency_weight*bc+.30*normal_rating)
            lo,hi=np.percentile(boot,[2.5,97.5])
        else: lo=hi=np.nan
        row={"player_id":int(player),"player_role":role,"observed_score":observed,"adjusted_pressure_score":adjusted,
             "consistency_score":consistency,"final_rating":final,"confidence_low":lo,"confidence_high":hi,
             "normal_rating":normal_rating,"normal_rating_raw":normal_rating_raw,"normal_rate":normal_rate,"normal_innings":normal_innings,"normal_matches":normal_matches,
             "normal_role_group":normal_row.get("normal_role_group"),"normal_opponent_weight":normal_row.get("normal_opponent_weight"),
             "pressure_matches":n,"weighted_pressure_matches":pressure_n,"pressure_episodes":int(g.episodes_in_match.sum()),
             "pressure_deliveries":int(g.pressure_deliveries.sum()),"situations_observed":int(obs.loc[(obs.player_id==player)&(obs.player_role==role),"situation_id"].nunique()),
             "mean_good_match_rate":good,"mean_exceptional_match_rate":excellent,
             "opponent_tier_coverage":"|".join(sorted(obs.loc[(obs.player_id==player)&(obs.player_role==role),"opponent_tier"].dropna().unique()))}
        ratings.append(row)
        reliability.append({"player_id":int(player),"player_role":role,"pressure_matches":n,
            "weighted_pressure_matches":pressure_n,"normal_innings":normal_innings,"normal_matches":normal_matches,"n_effective_matches":n_eff,
            "pressure_episodes":int(g.episodes_in_match.sum()),"pressure_deliveries":int(g.pressure_deliveries.sum()),
            "exact_context_deliveries":int(obs.loc[(obs.player_id==player)&(obs.player_role==role),"exact_context_deliveries"].sum()),
            "proxy_context_deliveries":int(obs.loc[(obs.player_id==player)&(obs.player_role==role),"pressure_deliveries"].sum()-obs.loc[(obs.player_id==player)&(obs.player_role==role),"exact_context_deliveries"].sum()),
            "situations_with_evidence":int(obs.loc[(obs.player_id==player)&(obs.player_role==role),"situation_id"].nunique()),
            "confidence_label":"high" if n_eff>=25 else ("moderate" if n_eff>=8 else "low"),
            "consistency_status":"evidenced" if n>=3 else "insufficient_matches","ci_low":lo,"ci_high":hi})
    rating=pd.DataFrame(ratings).merge(player_master,on="player_id",how="left",validate="many_to_one").merge(appearance_counts,on="player_id",how="left")
    rating["matches"]=rating.matches.fillna(0).astype(int)
    rating["pressure_impact"]=rating.final_rating-rating.normal_rating
    rating=rating.merge(pd.DataFrame(reliability)[["player_id","player_role","confidence_label","consistency_status","n_effective_matches","exact_context_deliveries","proxy_context_deliveries"]],on=["player_id","player_role"],how="left",validate="one_to_one")
    rating=rating[(rating.matches>0)&rating.final_rating.notna()].copy()
    # Knockout adjustment is applied only inside the proposed 0.50-point band.
    for role in ["batter","bowler"]:
        mask=rating.player_role.eq(role); base=rating.loc[mask,"final_rating"].to_numpy()
        ko_map=match_df[match_df.player_role.eq(role)].groupby("player_id").apply(
            lambda x:float(np.average(x.loc[x.knock_out.eq(1),"match_score"],weights=x.loc[x.knock_out.eq(1),"match_opportunity_weight"])) if x.knock_out.eq(1).any() else np.nan)
        adjustments=[]
        for i,row in rating.loc[mask].iterrows():
            near=np.any((np.abs(base-row.final_rating)>0)&(np.abs(base-row.final_rating)<=.5))
            ko=ko_map.get(row.player_id,np.nan)
            adjustments.append(float(np.clip((ko-50)/100,-.5,.5)) if near and pd.notna(ko) else 0.0)
        rating.loc[mask,"knockout_adjustment"]=adjustments
    rating["knockout_adjustment"]=rating.knockout_adjustment.fillna(0)
    rating["ranking_score"]=rating.final_rating+rating.knockout_adjustment
    rating=rating.sort_values(["player_role","ranking_score","pressure_matches"],ascending=[True,False,False])
    ranking_rows=[]
    for role in ["batter","bowler"]:
        r=rating[rating.player_role.eq(role)].copy()
        r["rank"]=np.arange(1,len(r)+1); ranking_rows.append(r)
    ranks=pd.concat(ranking_rows,ignore_index=True)
    # Write all stage scores and player ratings.
    outdir=root/"data"/"outputs"/scenario
    obs.to_csv(outdir/"situation_observations.csv",index=False)
    sit=obs[obs.peer_score.notna()].groupby(["player_id","player_role","situation_id"],as_index=False).apply(
        lambda g:pd.Series({"situation_score":float(np.average(g.peer_score,weights=np.maximum(g.opportunity_weight,1e-9))),
            "matches_in_sample":int(g.match_id.nunique()),"episodes":int(g.episodes.sum()),"deliveries":int(g.pressure_deliveries.sum()),
            "mean_intensity":float(g.mean_intensity.mean()),"mean_opponent_weight":float(g.opponent_weight.mean()),
            "benchmark_fallback":"|".join(sorted(g.benchmark_level.unique()))}))
    if "player_id" not in sit.columns and isinstance(sit.index,pd.MultiIndex): sit=sit.reset_index()
    sit=sit.merge(player_master,on="player_id",how="left",validate="many_to_one")
    sit.to_csv(outdir/"situation_ratings.csv",index=False)
    sit[sit.player_role.eq("batter")].to_csv(outdir/"batting_situation_ratings.csv",index=False)
    sit[sit.player_role.eq("bowler")].to_csv(outdir/"bowling_situation_ratings.csv",index=False)
    top_sit=sit.sort_values("situation_score").groupby(["player_id","player_role"],as_index=False).head(1)[["player_id","player_role","situation_id","situation_score"]].rename(columns={"situation_id":"weakest_situation","situation_score":"weakest_situation_score"})
    best_sit=sit.sort_values("situation_score").groupby(["player_id","player_role"],as_index=False).tail(1)[["player_id","player_role","situation_id","situation_score"]].rename(columns={"situation_id":"strongest_situation","situation_score":"strongest_situation_score"})
    ranks=ranks.merge(top_sit,on=["player_id","player_role"],how="left",validate="one_to_one").merge(best_sit,on=["player_id","player_role"],how="left",validate="one_to_one")
    # Episode scores are descriptive response measurements, kept independent
    # from the match-level shrinkage used for final ranks.
    episode_scores=labels.groupby(["episode_id","scenario","match_id","innings","situation_id","player_role","player_id"],as_index=False).agg(
        deliveries=("delivery_id","nunique"),runs=("player_runs","sum"),balls=("balls","sum"),dots=("dots","sum"),
        dismissals=("dismissals","sum"),boundaries=("boundaries","sum"),mean_intensity=("pressure_intensity","mean"),
        exact_context_deliveries=("is_score_exact_before","sum"),shared_weight=("opportunity_weight","sum"))
    episode_scores["rate"]=np.where(episode_scores.balls.gt(0),episode_scores.runs*100/episode_scores.balls,np.nan)
    episode_scores.to_csv(outdir/"player_episode_scores.csv",index=False)
    match_df.to_csv(outdir/"player_match_scores.csv",index=False)
    pd.DataFrame(reliability).to_csv(outdir/"player_reliability.csv",index=False)
    ranks.to_csv(outdir/"all_player_rankings.csv",index=False)
    ranks[ranks.player_role.eq("batter")].to_csv(outdir/"all_batter_rankings.csv",index=False)
    ranks[ranks.player_role.eq("bowler")].to_csv(outdir/"all_bowler_rankings.csv",index=False)
    ranks[ranks.player_role.eq("batter")].head(10).to_csv(outdir/"top10_batters.csv",index=False)
    ranks[ranks.player_role.eq("bowler")].head(10).to_csv(outdir/"top10_bowlers.csv",index=False)
    tier=obs[obs.peer_score.notna()].groupby(["player_id","player_role","opponent_tier"],as_index=False).apply(
        lambda g:pd.Series({"context_score":float(np.average(g.peer_score,weights=np.maximum(g.opportunity_weight,1e-9))),
           "matches_in_sample":int(g.match_id.nunique()),"episodes":int(g.episodes.sum()),"deliveries":int(g.pressure_deliveries.sum()),
           "mean_intensity":float(g.mean_intensity.mean())}))
    if "player_id" not in tier.columns and isinstance(tier.index,pd.MultiIndex): tier=tier.reset_index()
    tier.to_csv(outdir/"player_opponent_tier_performance.csv",index=False)
    comparison=ranks[["player_id","player_name","player_role","ranking_score","normal_rating","normal_rating_raw","normal_matches","pressure_impact","pressure_matches","confidence_label"]].copy()
    comparison.to_csv(outdir/"pressure_vs_normal_comparison.csv",index=False)
    ranks[ranks.player_role.eq("batter")][["player_id","player_name","normal_rate","normal_rating","normal_rating_raw","normal_matches","pressure_impact","pressure_matches"]].to_csv(outdir/"batting_normal_vs_pressure.csv",index=False)
    ranks[ranks.player_role.eq("bowler")][["player_id","player_name","normal_rate","normal_rating","pressure_impact","pressure_matches"]].to_csv(outdir/"bowling_normal_vs_pressure.csv",index=False)
    ranks.to_csv(outdir/"all_player_rankings.csv",index=False)
    ranks[ranks.player_role.eq("batter")].to_csv(outdir/"all_batter_rankings.csv",index=False)
    ranks[ranks.player_role.eq("bowler")].to_csv(outdir/"all_bowler_rankings.csv",index=False)
    ranks[ranks.player_role.eq("batter")].head(10).to_csv(outdir/"top10_batters.csv",index=False)
    ranks[ranks.player_role.eq("bowler")].head(10).to_csv(outdir/"top10_bowlers.csv",index=False)
    # Sensitivity varies prior strength and consistency weight; the 30% normal
    # component stays fixed, so the pressure component is the remaining weight.
    # A separate unweighted-opponent view checks dependence on tier weighting.
    sensitivity=[]
    for k in [3.0,5.0,8.0,12.0,20.0,30.0,40.0]:
        for cw in [.20,.30,.40,.50]:
            tmp=[]
            for (player,role),g in match_df.groupby(["player_id","player_role"],sort=False):
                v=g.match_score.to_numpy(float); w=g.match_opportunity_weight.to_numpy(float); n=len(v)
                if not n: continue
                observed=float(np.average(v,weights=w)); pressure_weight=float(w.sum())
                normal_innings=normal_sample.get((int(player),role),(0,0))[0]
                neff=combined_evidence_matches(pressure_weight,normal_innings)
                adjusted=(neff*observed+k*50)/(neff+k)
                avg=float(np.average(v,weights=w)); sd=float(np.sqrt(np.average((v-avg)**2,weights=w))) if n>1 else 25.0
                good=float(np.average(v>50,weights=w)); excellent=float(np.average(v>=65,weights=w))
                # Keep this sensitivity calculation aligned with match_consistency().
                raw=.50*good*100+.25*excellent*100+.25*(100-min(sd*2,100))
                cons=(neff/(neff+k))*raw+(k/(neff+k))*50
                normal_rating=float(normal_lookup.get((int(player),role),{}).get("normal_rating",50.0))
                tmp.append({"player_id":int(player),"player_role":role,"score":(1-.30-cw)*adjusted+cw*cons+.30*normal_rating})
            tv=pd.DataFrame(tmp)
            for role,gr in tv.groupby("player_role"):
                gr=gr.sort_values("score",ascending=False).reset_index(drop=True)
                for rank,row in enumerate(gr.itertuples(),1):
                    sensitivity.append({"variant":f"k{k:g}_consistency{cw:.2f}","player_id":int(row.player_id),"player_role":role,"rank":rank,"score":row.score})
    unweighted=[]
    for (player,role),g in match_df.groupby(["player_id","player_role"],sort=False):
        v=g.match_score_unweighted_opponent.to_numpy(float); w=g.match_opportunity_weight.to_numpy(float); n=len(v)
        observed=float(np.average(v,weights=w)) if w.sum() else float(v.mean())
        normal_innings=normal_sample.get((int(player),role),(0,0))[0]
        neff=combined_evidence_matches(float(w.sum()),normal_innings)
        k=prior_k; adjusted=(neff*observed+k*50)/(neff+k)
        avg=float(np.average(v,weights=w)) if w.sum() else 50.0
        sd=float(np.sqrt(np.average((v-avg)**2,weights=w))) if n>1 and w.sum() else 25.0
        good=float(np.average(v>50,weights=w)) if w.sum() else 0.5
        excellent=float(np.average(v>=65,weights=w)) if w.sum() else 0.0
        raw=.50*good*100+.25*excellent*100+.25*(100-min(sd*2,100))
        cons=(neff/(neff+k))*raw+(k/(neff+k))*50
        normal_rating=float(normal_lookup.get((int(player),role),{}).get("normal_rating",50.0))
        unweighted.append({"player_id":int(player),"player_role":role,"score":.50*adjusted+.20*cons+.30*normal_rating})
    uv=pd.DataFrame(unweighted)
    for role,gr in uv.groupby("player_role"):
        gr=gr.sort_values("score",ascending=False).reset_index(drop=True)
        for rank,row in enumerate(gr.itertuples(),1):
            sensitivity.append({"variant":"opponent_unweighted","player_id":int(row.player_id),"player_role":role,"rank":rank,"score":row.score})
    # Check whether a small normal-role sample is driving the final order.
    # The pressure model stays fixed; only innings-level normal shrinkage varies.
    for normal_k in [5.0,10.0,15.0]:
        variant_rows=[]
        for row in ranks.itertuples(index=False):
            raw=row.normal_rating_raw
            innings=float(row.normal_innings)
            normal_value=(innings*float(raw)+normal_k*50)/(innings+normal_k) if pd.notna(raw) else 50.0
            score=.50*float(row.adjusted_pressure_score)+.20*float(row.consistency_score)+.30*normal_value+float(row.knockout_adjustment)
            variant_rows.append({"player_id":int(row.player_id),"player_role":row.player_role,"score":score})
        nr=pd.DataFrame(variant_rows)
        for role,gr in nr.groupby("player_role"):
            gr=gr.sort_values("score",ascending=False).reset_index(drop=True)
            for rank,row in enumerate(gr.itertuples(),1):
                sensitivity.append({"variant":f"normal_prior_innings_{normal_k:g}","player_id":int(row.player_id),"player_role":role,"rank":rank,"score":row.score})
    sens=pd.DataFrame(sensitivity)
    if len(sens):
        base=ranks[["player_id","player_role","rank"]].rename(columns={"rank":"base_rank"})
        sens=sens.merge(base,on=["player_id","player_role"],how="left")
        sens["rank_change"]=sens.base_rank-sens["rank"]; sens["in_top10"]=sens["rank"]<=10
    sens.to_csv(outdir/"ranking_sensitivity.csv",index=False)
    return ranks,obs,match_df










