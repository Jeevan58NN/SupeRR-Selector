"""Synthetic activation coverage for every documented pressure situation."""
import unittest

import pandas as pd

from superr_selector.match_state.reconstruct import reconstruct
from superr_selector.pressure.detect import detect_pressure


def fixture_state(runs=0, knock_out=0):
    rows=[]
    for innings in (1,2):
        for ix in range(120):
            rows.append({
                "match_id":1,"innings":innings,"overid":ix//6+1,"over_ball_num":ix%6+1,
                "innings_ball_num":ix+1,"batting_team_id":10 if innings==1 else 20,
                "bowling_team_id":20 if innings==1 else 10,"striker_id":100+innings,
                "striker_name":"Batter","non_striker_id":200+innings,"non_striker_name":"Partner",
                "bowler_id":300+innings,"bowler_name":"Bowler","batting_order":1,
                "runs":runs[ix] if isinstance(runs,list) else runs,"is_four":(runs[ix] if isinstance(runs,list) else runs)==4,
                "is_six":(runs[ix] if isinstance(runs,list) else runs)==6,"is_wicket":False,
                "dismissal_type_id":None,"dismissal_type":None,"dismissed_player_id":None,
                "extras_type":None,"extras1_runs":6,"extras_2_runs":0,"is_free_hit":False,
            })
    ball=pd.DataFrame(rows)
    match=pd.DataFrame([{"match_id":1,"comp_id":1,"match_date":"2025-01-01","stage":"Final" if knock_out else "League",
        "knock_out":knock_out,"first_inn_revised_overs":120,"second_inn_revised_overs":120,
        "revised_target":None,"result":"No Result","home_team_id":10,"away_team_id":20,"win_team_id":None}])
    comp=pd.DataFrame([{"comp_id":1,"comp_name":"Test T20","match_format":"T20I","season":"2025"}])
    _,state,_=reconstruct(ball,match,comp)
    return state


def activate(state, code):
    inn=2 if code in {"B1","B9","B13","BW7","BW8","BW11","BW15","BW16"} else 1
    indices=state.index[state.innings.eq(inn)].tolist()
    def put(i,col,value): state.loc[indices[i],col]=value
    if code=="B1": put(114,"rrr_before_exact",12)
    elif code=="B3":
        for i in range(4): put(i,"batter_dot",True)
        put(4,"runs",1)
    elif code=="B4":
        put(10,"batter_balls_before",10); put(10,"batter_sr_before",0)
    elif code in {"B5","B7","B8"}:
        wicket_indices={"B5":[2,5,7],"B7":[3,8,13,17,20],"B8":[2,5,8]}[code]
        for i in wicket_indices:
            put(i,"is_wicket",True); put(i,"dismissed_player_id",101)
            put(i,"team_wickets_before",wicket_indices.index(i)); put(i,"team_wickets_after",wicket_indices.index(i)+1)
        if code=="B8":
            for i in range(9,14): put(i,"partnership_runs_before_exact",(i-9)*4); put(i,"partnership_runs_before_proxy",(i-9)*4)
            put(14,"partnership_runs_before_exact",20); put(14,"partnership_runs_before_proxy",20)
    elif code=="B9": put(90,"rrr_before_exact",13)
    elif code=="B10": put(90,"team_wickets_before",7); put(90,"wickets_in_hand_before",3)
    elif code=="B11":
        for i in [30,36,42,48]: put(i,"team_batter_boundary",True)
    elif code=="B13": put(119,"runs_required_exact_before",3)
    elif code=="B14": put(24,"crr_before_exact",7.9)
    elif code=="B15": state["knock_out"]=1
    elif code=="BW1":
        for i in [6,7,8]: put(i,"team_batter_boundary",True)
    elif code=="BW2":
        for i,extra in enumerate([1,2,1]):
            put(i,"extra_code",extra); put(i,"is_legal_ball",False)
    elif code=="BW3": put(15,"is_free_hit",True)
    elif code=="BW4": put(12,"crr_before_exact",13)
    elif code=="BW5": put(34,"team_score_after_exact",70); put(34,"team_wickets_after",0)
    elif code=="BW6": put(30,"partnership_runs_before_exact",60)
    elif code=="BW7": put(90,"rrr_before_exact",7)
    elif code=="BW8": put(114,"runs_required_exact_before",8)
    elif code=="BW9": put(90,"wickets_in_hand_before",8)
    elif code=="BW10": put(20,"batter_runs_before",100)
    elif code=="BW11": put(108,"rrr_before_exact",11)
    elif code=="BW13": put(59,"team_wickets_after",1)
    elif code=="BW14":
        for i in range(6): put(i,"bowler_runs_exact_delivery",3)
        for i in range(6,12): put(i,"bowler_id",302); put(i,"bowler_runs_exact_delivery",0)
        for i in range(12,18): put(i,"bowler_id",301); put(i,"bowler_runs_exact_delivery",0)
    elif code=="BW15": put(119,"runs_required_exact_before",2)
    elif code=="BW16": put(0,"target_exact",1)
    return state


class PressureTriggerCoverageTests(unittest.TestCase):
    def test_all_31_situations_have_a_synthetic_activation_case(self):
        codes=[*(f"B{i}" for i in range(1,16)),*(f"BW{i}" for i in range(1,17))]
        missed=[]
        for code in codes:
            state=activate(fixture_state(runs=2 if code in {"BW5","BW6","BW12","BW14"} else 0,
                                         knock_out=1 if code=="B15" else 0),code)
            episodes,_,_,_=detect_pressure(state,"strict_exact_context")
            if episodes.empty or not episodes.situation_id.eq(code).any(): missed.append(code)
        self.assertEqual(missed,[])

    def test_bw14_keeps_the_two_recovery_stages_separate(self):
        state=activate(fixture_state(runs=3),"BW14")
        episodes,_,_,_=detect_pressure(state,"strict_exact_context")
        stages=set(episodes.loc[episodes.situation_id.eq("BW14"),"stage"])
        self.assertIn("next_bowler_over",stages)
        self.assertIn("original_bowler_recovery",stages)


if __name__=="__main__": unittest.main()
