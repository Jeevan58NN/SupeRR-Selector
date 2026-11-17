from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import pandas as pd

WIDE=2
SEVERITY = {
    "B1":"critical","B2":"moderate","B3":"high","B4":"moderate","B5":"critical",
    "B6":"high","B7":"critical","B8":"critical","B9":"critical","B10":"critical",
    "B11":"high","B12":"moderate","B13":"critical","B14":"moderate","B15":"supporting",
    "BW1":"critical","BW2":"high","BW3":"high","BW4":"high","BW5":"high","BW6":"high",
    "BW7":"critical","BW8":"critical","BW9":"high","BW10":"high","BW11":"high",
    "BW12":"high","BW13":"high","BW14":"high","BW15":"critical","BW16":"high",
}
WEIGHT={"critical":5.0,"high":4.0,"moderate":3.0,"supporting":0.5}
OVERLAP_CLUSTERS={"late_chase_rate":["B1","B9"],"wicket_collapse":["B5","B7","B8"]}
OVERLAP_PRIORITY={"B1":2,"B9":1,"B5":1,"B7":2,"B8":3}

def _clip(x):
    return max(0.0,min(1.0,float(x))) if pd.notna(x) else 0.0

def _intensity(r, role, code):
    if role=="batter":
        rrr=r.rrr_before_exact if r.scenario=="strict_exact_context" else r.rrr_before_proxy
        crr=r.crr_before_exact if r.scenario=="strict_exact_context" else r.crr_before_proxy
        wickets=float(r.team_wickets_before)
        rem=float(r.balls_remaining_before)/max(float(r.allotted_legal_balls),1)
        if int(r.innings)==2 and pd.notna(rrr):
            run_pressure=1/(1+math.exp(-max(-20,min(20,(float(rrr)-8)/3))))
            return _clip(.62*run_pressure+.28*wickets/10+.10*rem)
        low_rate=_clip((8-float(crr))/8) if pd.notna(crr) else 0
        return _clip(.58*wickets/10+.30*low_rate+.12*rem)
    rrr=r.rrr_before_exact if r.scenario=="strict_exact_context" else r.rrr_before_proxy
    hand=float(r.wickets_in_hand_before)
    phase=.2 if bool(r.is_death) else (.1 if bool(r.is_powerplay) else 0)
    if code=="BW7" and pd.notna(rrr):
        comfortable=1/(1+math.exp(-max(-20,min(20,(8-float(rrr))/3))))
        return _clip(.68*comfortable+.22*hand/10+.10*phase)
    if code=="BW8" and pd.notna(r.runs_required_exact_before if r.scenario=="strict_exact_context" else r.runs_required_proxy_before):
        needed=r.runs_required_exact_before if r.scenario=="strict_exact_context" else r.runs_required_proxy_before
        return _clip(.65*(1-float(needed)/13)+.25*hand/10+.10*phase)
    if bool(getattr(r,"is_free_hit",False)):
        return .75 if bool(r.is_death) or bool(r.is_powerplay) else .55
    run_signal=0.0
    if pd.notna(rrr): run_signal=_clip(float(rrr)/18)
    return _clip(.45*hand/10+.40*run_signal+.15*phase)

def _context(r, scenario):
    if scenario=="strict_exact_context":
        return (r.team_score_before_exact,r.team_score_after_exact,r.crr_before_exact,
                r.rrr_before_exact,r.target_exact,r.partnership_runs_before_exact)
    return (r.team_score_before_proxy,r.team_score_after_proxy,r.crr_before_proxy,
            r.rrr_before_proxy,r.target_proxy_lower_bound,r.partnership_runs_before_proxy)

def detect_pressure(state: pd.DataFrame, scenario: str):
    """Return episode, player-membership, delivery-label, and intensity tables.

    Windows are generated independently for every situation. Trigger rows and
    response windows are kept distinct in the episode record.
    """
    if scenario not in {"strict_exact_context","proxy_inclusive"}:
        raise ValueError("Unknown scenario: "+scenario)
    s=state.copy()
    s["scenario"]=scenario
    episode_rows=[]; member_rows=[]; label_rows=[]; intensity_rows=[]
    groups=list(s.groupby(["match_id","innings"],sort=False))
    for group_number,((mid,inn),g0) in enumerate(groups,1):
        if group_number%100==0: print(f"Pressure detector innings {group_number}/{len(groups)}",flush=True)
        g=g0.sort_values(["overid","over_ball_num","delivery_id"],kind="stable").reset_index(drop=True)
        n=len(g)
        if n==0 or int(inn)>=3 or bool(g.is_incomplete_innings.fillna(True).all()):
            continue
        windows=[]
        def add(code,trigger,start,end,reason,stage="main",player_filter=None,batter_filter=None):
            if start is None or end is None or start>end or start>=n: return
            start=max(0,int(start)); end=min(n-1,int(end)); trigger=max(0,min(n-1,int(trigger)))
            windows.append({"situation_id":code,"trigger_i":trigger,"start_i":start,"end_i":end,
                            "reason":reason,"stage":stage,"player_filter":player_filter,
                            "batter_filter":batter_filter})
        innings_complete=not bool(g.is_incomplete_innings.fillna(True).any())
        allotted=int(g.allotted_legal_balls.iloc[0]); final_over=math.ceil(allotted/6)
        pp=int(g.powerplay_balls.iloc[0])
        rr=g.rrr_before_exact if scenario=="strict_exact_context" else g.rrr_before_proxy
        score_before=g.team_score_before_exact if scenario=="strict_exact_context" else g.team_score_before_proxy
        score_after=g.team_score_after_exact if scenario=="strict_exact_context" else g.team_score_after_proxy
        crr=g.crr_before_exact if scenario=="strict_exact_context" else g.crr_before_proxy
        partnership=g.partnership_runs_before_exact if scenario=="strict_exact_context" else g.partnership_runs_before_proxy
        boundary=g.team_batter_boundary.fillna(False).astype(bool).to_numpy()
        legal=g.is_legal_ball.fillna(False).astype(bool).to_numpy()
        wickets=g.team_wickets_before.fillna(0).astype(int).to_numpy()
        wickets_after=g.team_wickets_after.fillna(0).astype(int).to_numpy() if "team_wickets_after" in g else wickets
        overs=g.overid.fillna(0).astype(int).to_numpy()
        legal_before=g.legal_ball_before.fillna(0).astype(int).to_numpy()
        legal_after=g.legal_ball_after.fillna(0).astype(int).to_numpy()
        runs_req=(g.runs_required_exact_before if scenario=="strict_exact_context" else g.runs_required_proxy_before)
        # Batting situations.
        if int(inn)==2 and innings_complete:
            q=[i for i in range(n) if overs[i]==final_over and pd.notna(rr.iloc[i]) and rr.iloc[i]>=12]
            if q: add("B1",q[0],q[0],n-1,"Final over; exact/proxy RRR >= 12")
            q=[i for i in range(n) if legal_before[i]>=max(allotted-30,0) and pd.notna(rr.iloc[i]) and rr.iloc[i]>12.5]
            if q: add("B9",q[0],q[0],n-1,"Final five allotted overs; RRR > 12.5")
            final=[i for i in range(n) if legal[i] and legal_before[i]==allotted-1 and pd.notna(runs_req.iloc[i]) and 1<=runs_req.iloc[i]<=7]
            for i in final: add("B13",i,i,i,"Final legal ball; 1-7 runs required")
            final_indices=[i for i in range(n) if overs[i]==final_over]
            if final_indices:
                f=final_indices[0]
                if pd.notna(runs_req.iloc[f]) and 1<=float(runs_req.iloc[f])<=12:
                    add("BW8",f,f,next((j for j in range(f,n) if overs[j]!=final_over),n)-1,"Final over starts with 1-12 required")
            q=[i for i in range(n) if legal_before[i]>=max(allotted-30,0) and pd.notna(rr.iloc[i]) and rr.iloc[i]<8]
            if q: add("BW7",q[0],q[0],n-1,"Final five overs; RRR < 8 for bowling side")
            finalball=[i for i in range(n) if legal[i] and legal_before[i]==allotted-1 and pd.notna(runs_req.iloc[i]) and 1<=runs_req.iloc[i]<=2]
            for i in finalball: add("BW15",i,i,i,"Final legal ball; 1-2 runs required")
        q=[i for i in range(n) if legal_before[i]>=max(allotted-30,0) and int(g.wickets_in_hand_before.iloc[i])<=3]
        if q: add("B10",q[0],q[0],n-1,"Final five allotted overs; <=3 wickets in hand")
        # B2: boundary-free first 18 legal balls; response begins after those balls.
        first3=[i for i in range(n) if legal_before[i]<18]
        completed3=[i for i in range(n) if legal_after[i]>=18]
        if first3 and completed3 and not boundary[first3].any():
            trig=completed3[0]; start=trig+1
            if start<n: add("B2",trig,start,n-1,"No batter-credited team boundary in first 18 legal balls")
        # B3: four consecutive batter-dot balls; evaluate only this batter's recovery.
        streak=defaultdict(list)
        for i,r in enumerate(g.itertuples()):
            pid=int(r.striker_id)
            if bool(r.batter_dot): streak[pid].append(i)
            elif bool(r.is_ball_faced): streak[pid]=[]
            if len(streak[pid])>=4:
                trigger=i; response=[]; end=i
                for j in range(i+1,n):
                    rrj=g.iloc[j]
                    if int(rrj.striker_id)!=pid or not bool(rrj.is_ball_faced): continue
                    response.append(j); end=j
                    if int(rrj.runs)>0 or (bool(rrj.is_wicket) and pd.notna(rrj.dismissed_player_id) and int(rrj.dismissed_player_id)==pid): break
                    if len(response)>=10: break
                if response: add("B3",trigger,response[0],end,"Four consecutive batter dots; recovery window",player_filter=pid)
                streak[pid]=[]
        # B4: low-rate striker starts a partnership episode until that batter is dismissed.
        active=None
        for i,r in enumerate(g.itertuples()):
            if active is None and int(r.batter_balls_before)>=10 and pd.notna(r.batter_sr_before) and float(r.batter_sr_before)<100:
                active=int(r.striker_id); start=i
            if active is not None and bool(r.is_wicket) and pd.notna(r.dismissed_player_id) and pd.notna(r.dismissed_player_id) and int(r.dismissed_player_id)==active:
                add("B4",start,start,i,"Striker has faced 10+ balls at SR < 100; active until dismissal",player_filter=None)
                active=None
        if active is not None: add("B4",start,start,n-1,"Low-strike-rate episode continues to innings end")
        # Collapse triggers.
        q=[i for i in range(n) if bool(g.is_powerplay.iloc[i]) and wickets_after[i]>=3 and wickets[i]<3]
        if q and q[0]+1<n: add("B5",q[0],q[0]+1,n-1,"Third wicket falls within Powerplay")
        q=[i for i in range(n) if legal_after[i]<=60 and wickets_after[i]>=5 and wickets[i]<5]
        if q and q[0]+1<n: add("B7",q[0],q[0]+1,n-1,"Fifth wicket falls within first ten overs")
        # B6 after completion of the allocated Powerplay.
        q=[i for i in range(n) if legal_after[i]>=pp and legal_before[i]<pp]
        if q:
            t=q[0]; value=score_after.iloc[t]
            if pd.notna(value) and value<35 and t+1<n: add("B6",t,t+1,n-1,"Powerplay ends below 35 runs")
        # B8 three wickets in rolling 12 legal balls; episode ends at 20-run partnership.
        wk_indices=[i for i in range(n) if wickets_after[i]>wickets[i]]
        b8_active_end=-1
        for wi in wk_indices:
            if wi<=b8_active_end: continue
            lo=legal_after[wi]-12
            recent=[j for j in wk_indices if lo<legal_after[j]<=legal_after[wi]]
            if len(recent)>=3 and recent[-1]==wi:
                start=wi+1
                if start<n:
                    end=n-1
                    for j in range(start,n):
                        if pd.notna(partnership.iloc[j]) and partnership.iloc[j]>=20: end=j; break
                    add("B8",wi,start,end,"Three wickets within twelve legal balls; stop at 20-run stand")
                    b8_active_end=end
        # B11 rolling 18-ball batter-boundary drought, ending after four response boundaries.
        legal_idxs=[i for i in range(n) if legal[i]]
        pos=17
        while pos<len(legal_idxs):
            seq=legal_idxs[pos-17:pos+1]
            if not boundary[seq].any():
                start=seq[-1]+1
                if start<n:
                    count=0; end=n-1
                    for j in range(start,n):
                        count+=int(boundary[j])
                        if count>=4: end=j; break
                    add("B11",seq[-1],start,end,"18 legal balls without batter boundary; recover to four boundaries")
                    if count<4: break
                    nextpos=next((k for k,index in enumerate(legal_idxs) if index>end),len(legal_idxs))
                    pos=max(pos+1,nextpos+17)
                else: break
            else: pos+=1
        # B12 three complete consecutive low-rate overs, recover until CRR reaches 10.
        over_groups=[(o,[i for i in range(n) if overs[i]==o]) for o in dict.fromkeys(overs.tolist())]
        lowovers=[]
        for o,inds in over_groups:
            if not inds: continue
            a,b=inds[0],inds[-1]; lcount=int(legal_after[b]-legal_before[a])
            ra=score_before.iloc[a]; rb=score_after.iloc[b]
            rate=((rb-ra)*6/lcount) if lcount>0 and pd.notna(ra) and pd.notna(rb) else np.nan
            if pd.notna(rate) and rate<7: lowovers.append((o,b))
            else: lowovers=[]
            if len(lowovers)>=3 and lowovers[-1][0]==lowovers[-2][0]+1==lowovers[-3][0]+2:
                start=b+1
                if start<n:
                    end=n-1
                    for j in range(start,n):
                        if pd.notna(crr.iloc[j]) and crr.iloc[j]>=10: end=j; break
                    add("B12",b,start,end,"Three consecutive completed overs below RR 7; recover to CRR 10")
                lowovers=[]
        # B14 over 5/6 when pre-over CRR is below eight; only that over is scored.
        for o,inds in over_groups:
            if o in {5,6} and inds and pd.notna(crr.iloc[inds[0]]) and crr.iloc[inds[0]]<8:
                add("B14",inds[0],inds[0],inds[-1],"Over 5 or 6 begins with CRR < 8")
        # B15 is explicitly supporting evidence across knockout innings.
        if bool(g.knock_out.fillna(0).iloc[0]):
            add("B15",0,0,n-1,"Supplied match metadata marks knockout; supporting evidence")
        # Bowling situations.
        # BW1: three consecutive batter-credited boundaries by one bowler in an over.
        for o,inds in over_groups:
            streaks=defaultdict(list)
            for i in inds:
                r=g.iloc[i]; bow=int(r.bowler_id)
                if int(r.extra_code)==WIDE: continue
                if bool(r.team_batter_boundary): streaks[bow].append(i)
                else:
                    for k in list(streaks): streaks[k]=[]
                if len(streaks[bow])>=3:
                    trigger=i; start=i+1
                    if start<=inds[-1]: add("BW1",trigger,start,inds[-1],"Bowler concedes three consecutive batter boundaries",stage="same_over_recovery",player_filter=bow)
                    # Original bowler's next subsequent over.
                    next_over=next(((oo,ii) for oo,ii in over_groups if oo>o and int(g.bowler_id.iloc[ii[0]])==bow),None)
                    if next_over: add("BW1",trigger,next_over[1][0],next_over[1][-1],"Original bowler's next over",stage="next_over_recovery",player_filter=bow)
                    streaks[bow]=[]
        # BW2: three consecutive illegal deliveries by the same bowler in one over.
        for o,inds in over_groups:
            seq=[]
            for i in inds:
                r=g.iloc[i]
                if int(r.extra_code) in {1,2}: seq.append(i)
                else: seq=[]
                if len(seq)>=3 and len({int(g.bowler_id.iloc[j]) for j in seq[-3:]})==1:
                    trig=i
                    if i<inds[-1]: add("BW2",trig,i+1,inds[-1],"Three consecutive wides/no-balls; same-over recovery",stage="control_recovery",player_filter=int(r.bowler_id))
                    seq=[]
        # BW3 free hits are individual delivery opportunities.
        for i,r in enumerate(g.itertuples()):
            if bool(r.is_free_hit): add("BW3",i,i,i,"Applicable free-hit delivery",player_filter=int(r.bowler_id))
        # BW4 high scoring Powerplay over from over 3 onward.
        for o,inds in over_groups:
            if o>=3 and inds and bool(g.is_powerplay.iloc[inds[0]]) and pd.notna(crr.iloc[inds[0]]) and crr.iloc[inds[0]]>12:
                add("BW4",inds[0],inds[0],inds[-1],"Powerplay over 3+ starts with CRR > 12")
        # BW5 70 without loss, continue until three wickets.
        q=[i for i in range(n) if pd.notna(score_after.iloc[i]) and score_after.iloc[i]>=70 and wickets_after[i]==0]
        if q:
            trig=q[0]; start=trig+1
            if start<n:
                end=next((j for j in range(start,n) if wickets_after[j]>=3),n-1)
                add("BW5",trig,start,end,"Team reaches 70 without loss; stop at three wickets")
        # BW6 partnership reaches sixty until that stand is broken.
        q=[i for i in range(n) if pd.notna(partnership.iloc[i]) and partnership.iloc[i]>=60]
        if q:
            trig=q[0]; start=trig+1; pid=int(g.partnership_id.iloc[trig])
            end=next((j for j in range(start,n) if int(g.partnership_id.iloc[j])!=pid),n-1)
            if start<n: add("BW6",trig,start,end,"Partnership reaches 60; evaluate bowlers until broken")
        # BW9 from fixed 16th over onward with >=8 wickets in hand.
        q=[i for i in range(n) if overs[i]>=16 and int(g.wickets_in_hand_before.iloc[i])>=8]
        if q: add("BW9",q[0],q[0],n-1,"From 16th over with at least eight wickets in hand")
        # BW10 bowling to a batter after their century; pair remains identifiable.
        centuries=set()
        for i,r in enumerate(g.itertuples()):
            batter=int(r.striker_id)
            if batter not in centuries and int(r.batter_runs_before)>=100:
                end=next((j for j in range(i,n) if bool(g.is_wicket.iloc[j]) and pd.notna(g.dismissed_player_id.iloc[j]) and int(g.dismissed_player_id.iloc[j])==batter),n-1)
                add("BW10",i,i,end,"Bowling to batter after reaching 100",batter_filter=batter)
                centuries.add(batter)
            if bool(r.is_wicket) and pd.notna(r.dismissed_player_id) and int(r.dismissed_player_id)==batter:
                centuries.discard(batter)
        # BW11 19th over only; use start-of-over RRR.
        for o,inds in over_groups:
            if o==19 and int(inn)==2 and inds and pd.notna(rr.iloc[inds[0]]) and rr.iloc[inds[0]]<12:
                add("BW11",inds[0],inds[0],inds[-1],"19th over starts with RRR < 12")
        # BW12 reaches 100 within first ten overs; response through innings end.
        q=[i for i in range(n) if legal_after[i]<=60 and pd.notna(score_after.iloc[i]) and score_after.iloc[i]>=100]
        if q and q[0]+1<n: add("BW12",q[0],q[0]+1,n-1,"Opposition reaches 100 within first ten overs")
        # BW13 after ten completed overs with <=1 wicket down.
        q=[i for i in range(n) if legal_after[i]>=60 and legal_before[i]<60 and wickets_after[i]<=1]
        if q and q[0]+1<n: add("BW13",q[0],q[0]+1,n-1,"Ten overs completed with zero/one wicket lost")
        # BW14 two distinct follow-up analyses after a 15+ run bowler over.
        for o,inds in over_groups:
            bow=int(g.bowler_id.iloc[inds[0]])
            a,b=inds[0],inds[-1]
            bowler_rows=g.iloc[inds]
            if scenario=="strict_exact_context":
                exact_bowling=bowler_rows.bowler_runs_exact_delivery
                conceded=float(exact_bowling.sum()) if exact_bowling.notna().all() else np.nan
            else:
                conceded=float(bowler_rows.bowler_runs_proxy_delivery.sum())
            if pd.notna(conceded) and conceded>=15:
                following=next(((oo,ii) for oo,ii in over_groups if oo>o),None)
                if following: add("BW14",b,following[1][0],following[1][-1],"Next bowler's over after a 15+ run over",stage="next_bowler_over")
                original=next(((oo,ii) for oo,ii in over_groups if oo>o and int(g.bowler_id.iloc[ii[0]])==bow),None)
                if original: add("BW14",b,original[1][0],original[1][-1],"Original bowler's next over after a 15+ run over",stage="original_bowler_recovery",player_filter=bow)
        # BW16 low target, scaled by first innings allocation.
        if int(inn)==2:
            target=g.target_exact.iloc[0] if scenario=="strict_exact_context" else g.target_proxy_lower_bound.iloc[0]
            firstall=int(g.first_innings_allotted_legal_balls.iloc[0]) if "first_innings_allotted_legal_balls" in g else 120
            if pd.notna(target):
                scaled=150*firstall/120
                if float(target)<scaled: add("BW16",0,0,n-1,"Defending target below length-scaled 150 threshold")
        # Create stable episodes and delivery/member tables.
        counters=defaultdict(int)
        for w in sorted(windows,key=lambda x:(x["situation_id"],x["trigger_i"],x["stage"])):
            code=w["situation_id"]; counters[code]+=1
            seq=counters[code]; eid=f"{scenario}-{mid}-{inn}-{code}-{seq:03d}-{w['stage']}"
            part=g.iloc[w["start_i"]:w["end_i"]+1]
            if w["player_filter"] is not None:
                part=part[part.bowler_id.eq(w["player_filter"]) if code.startswith("BW") else part.striker_id.eq(w["player_filter"])]
            if w["batter_filter"] is not None:
                part=part[part.striker_id.eq(w["batter_filter"])]
            if part.empty: continue
            rtrigger=g.iloc[w["trigger_i"]]
            episode_rows.append({"episode_id":eid,"scenario":scenario,"match_id":int(mid),"innings":int(inn),
                "situation_id":code,"episode_sequence":seq,"stage":w["stage"],
                "trigger_delivery_id":str(rtrigger.delivery_id),"start_delivery_id":str(g.delivery_id.iloc[w["start_i"]]),
                "end_delivery_id":str(g.delivery_id.iloc[w["end_i"]]),"trigger_legal_ball":int(rtrigger.legal_ball_before),
                "start_legal_ball":int(g.legal_ball_before.iloc[w["start_i"]]),"end_legal_ball":int(g.legal_ball_after.iloc[w["end_i"]]),
                "trigger_reason":w["reason"],"evaluation_deliveries":len(part),"severity":SEVERITY[code],
                "severity_weight":WEIGHT[SEVERITY[code]],"score_quality":str(rtrigger.score_quality_before),
                "is_incomplete_innings":bool(rtrigger.is_incomplete_innings)})
            role="bowler" if code.startswith("BW") else "batter"
            groupcol="bowler_id" if role=="bowler" else "striker_id"
            for player,pg in part.groupby(groupcol):
                player=int(player)
                balls=int(pg.is_ball_faced.sum()) if role=="batter" else int(pg.is_legal_ball.sum())
                runs=int(pg.runs.sum()) if role=="batter" else int(pg.bowler_runs_proxy_delivery.sum())
                dismissals=int((pg.is_wicket & pg.dismissed_player_id.fillna(-1).astype(int).eq(player)).sum()) if role=="batter" else int(pg.dismissal_type.fillna("").str.lower().isin(["bowled","caught","caught and bowled","lbw","stumped","hit wicket"]).sum())
                member_rows.append({"episode_id":eid,"scenario":scenario,"match_id":int(mid),"innings":int(inn),
                    "situation_id":code,"player_id":player,"player_role":role,"stage":w["stage"],
                    "delivery_count":len(pg),"balls":balls,"runs":runs,"dismissals":dismissals,
                    "boundaries":int(pg.team_batter_boundary.sum()),
                    "opposition_team_id":int((pg.bowling_team_id if role=="batter" else pg.batting_team_id).iloc[0]),
                    "comp_id":int(pg.comp_id.iloc[0]),
                    "batting_position_mode":int(pg.batting_order.mode().iloc[0]) if pg.batting_order.notna().any() else None,
                    "competition_pool":"IPL" if "IPL" in str(pg.comp_name.iloc[0]).upper() else ("T20I" if str(pg.match_format.iloc[0]).upper()=="T20I" else "Other T20"),
                    "trigger_participant":bool(player in set(g.iloc[w["trigger_i"]:w["trigger_i"]+1][groupcol].dropna().astype(int)))})
            for j,row in part.iterrows():
                intensity=_intensity(row,role,code)
                intensity_rows.append({"episode_id":eid,"delivery_id":str(row.delivery_id),"match_id":int(mid),"innings":int(inn),
                    "situation_id":code,"player_role":role,"pressure_intensity":intensity,"faded_pressure":intensity<=0.20,
                    "scenario":scenario})
                label_rows.append({"delivery_id":str(row.delivery_id),"match_id":int(mid),"innings":int(inn),
                    "scenario":scenario,"situation_id":code,"episode_id":eid,"player_role":role,
                    "pressure_intensity":intensity,"severity":SEVERITY[code],"severity_weight":WEIGHT[SEVERITY[code]],
                    "is_trigger_delivery":j==w["trigger_i"],"stage":w["stage"]})
    episodes=pd.DataFrame(episode_rows)
    members=pd.DataFrame(member_rows)
    labels=pd.DataFrame(label_rows)
    intensity=pd.DataFrame(intensity_rows)
    return episodes,members,labels,intensity

def resolve_overlaps(labels: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    if labels.empty: return pd.DataFrame(columns=["delivery_id","cluster_id","active_situations","selected_situation","shared_weight_before","shared_weight_after","shared_contribution_factor"])
    for delivery,group in labels.groupby("delivery_id",sort=False):
        active=set(group.situation_id.astype(str))
        for cluster_id,codes in OVERLAP_CLUSTERS.items():
            present=sorted(active.intersection(codes))
            if len(present)<2: continue
            subset=group[group.situation_id.isin(present)]
            chosen=sorted(present,key=lambda code:(-float(subset.loc[subset.situation_id.eq(code),"pressure_intensity"].max()),-OVERLAP_PRIORITY.get(code,0),code))[0]
            before=float(subset.severity_weight.sum()); after=float(subset.loc[subset.situation_id.eq(chosen),"severity_weight"].max())
            rows.append({"delivery_id":delivery,"cluster_id":cluster_id,"active_situations":"|".join(present),
                         "selected_situation":chosen,"shared_weight_before":before,"shared_weight_after":after,
                         "shared_contribution_factor":after/before if before else 1.0})
    return pd.DataFrame(rows)
