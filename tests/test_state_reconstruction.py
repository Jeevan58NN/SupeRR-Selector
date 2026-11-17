import unittest
import pandas as pd
from superr_selector.match_state.reconstruct import reconstruct
from superr_selector.pressure.detect import detect_pressure

def build_inputs(extras):
    rows=[]
    for inn,seq in extras.items():
        for ix,(code,runs) in enumerate(seq,1):
            rows.append({"match_id":1,"innings":inn,"overid":(ix-1)//6+1,"over_ball_num":(ix-1)%6+1,
             "innings_ball_num":ix,"batting_team_id":10 if inn==1 else 20,"bowling_team_id":20 if inn==1 else 10,
             "striker_id":100+inn,"striker_name":"Batter","non_striker_id":200+inn,"non_striker_name":"Partner",
             "bowler_id":300+inn,"bowler_name":"Bowler","batting_order":1,"runs":runs,"is_four":runs==4,"is_six":runs==6,
             "is_wicket":False,"dismissal_type_id":None,"dismissal_type":None,"dismissed_player_id":None,
             "extras_type":None if code==6 else {1:"Overstep",2:"wide",3:"legbyes",4:"byes",5:"other"}.get(code,"Penalty"),
             "extras1_runs":code,"extras_2_runs":0,"is_free_hit":False})
    ball=pd.DataFrame(rows)
    match=pd.DataFrame([{"match_id":1,"comp_id":1,"match_date":"2025-01-01","stage":"League","knock_out":0,
       "first_inn_revised_overs":24,"second_inn_revised_overs":24,"revised_target":None,"result":"No Result",
       "home_team_id":10,"away_team_id":20,"win_team_id":None}])
    comp=pd.DataFrame([{"comp_id":1,"comp_name":"Test T20","match_format":"T20I","season":"2025"}])
    return ball,match,comp

class StateReconstructionTests(unittest.TestCase):
    def test_legal_positions_and_strict_score_reliability(self):
        ball,match,comp=build_inputs({1:[(6,1),(2,0),(1,0),(3,0),(4,0),(5,0)]})
        _,state,_=reconstruct(ball,match,comp)
        self.assertEqual(state.legal_ball_before.tolist(),[0,1,1,1,2,3])
        self.assertEqual(state.is_ball_faced.tolist(),[True,False,True,True,True,True])
        self.assertTrue(state.is_score_exact_before.iloc[0])
        self.assertFalse(state.is_score_exact_before.iloc[2])
        self.assertTrue(state.is_score_exact_after.iloc[0])
        self.assertFalse(state.is_score_exact_after.iloc[1])
        self.assertTrue(state.is_incomplete_innings.all())
    def test_boundary_drought_episode_has_response_window(self):
        seq=[(6,0)]*18+[(6,1)]*6
        ball,match,comp=build_inputs({1:seq})
        _,state,_=reconstruct(ball,match,comp)
        episodes,members,labels,intensity=detect_pressure(state,"strict_exact_context")
        b2=episodes[episodes.situation_id.eq("B2")]
        self.assertEqual(len(b2),1)
        self.assertEqual(int(b2.iloc[0].start_legal_ball),18)
        self.assertEqual(len(members[members.situation_id.eq("B2")]),1)
        self.assertTrue((intensity.pressure_intensity.between(0,1)).all())

    def test_free_hit_carries_across_illegal_deliveries(self):
        # A wide on a free hit does not consume the free-hit opportunity.
        ball,match,comp=build_inputs({1:[(1,0),(2,0),(6,0),(6,0)]})
        _,state,_=reconstruct(ball,match,comp)
        self.assertEqual(state.is_free_hit.tolist(),[False,True,True,False])
        self.assertEqual(state.legal_ball_after.tolist(),[0,0,1,2])

    def test_collapse_episode_starts_after_trigger_wicket(self):
        ball,match,comp=build_inputs({1:[(6,0)]*120})
        # Trigger the third wicket on legal ball 8, inside the powerplay.
        for i in [1,3,7]:
            ball.loc[i,"is_wicket"] = True
            ball.loc[i,"dismissal_type"] = "bowled"
            ball.loc[i,"dismissed_player_id"] = 101
        _,state,_=reconstruct(ball,match,comp)
        episodes,_,labels,_=detect_pressure(state,"strict_exact_context")
        b5=episodes[episodes.situation_id.eq("B5")]
        self.assertEqual(len(b5),1)
        self.assertEqual(b5.iloc[0].trigger_delivery_id,"1-1-8")
        self.assertEqual(b5.iloc[0].start_delivery_id,"1-1-9")
        self.assertFalse(labels[labels.situation_id.eq("B5")].delivery_id.eq("1-1-8").any())

    def test_shortened_innings_phase_allocation_uses_legal_balls(self):
        ball,match,comp=build_inputs({1:[(6,0)]*30})
        match.loc[0,"first_inn_revised_overs"] = 66
        _,state,_=reconstruct(ball,match,comp)
        self.assertEqual(state.allotted_legal_balls.iloc[0],66)
        self.assertEqual(state.powerplay_balls.iloc[0],20)
        self.assertEqual(state.death_balls.iloc[0],18)

if __name__=="__main__": unittest.main()
