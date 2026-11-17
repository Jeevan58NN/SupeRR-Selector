import tempfile
import unittest
from pathlib import Path
import pandas as pd
from superr_selector.metrics.context_exports import export_context_metrics

class ContextExportTests(unittest.TestCase):
    def test_phase_uses_legal_balls_and_exports_batter_entry(self):
        x=pd.DataFrame([
            {"match_id":1,"innings":1,"legal_ball_before":0,"legal_ball_after":1,"overid":1,"over_ball_num":1,"allotted_legal_balls":12,"powerplay_balls":4,"death_balls":6,"first_innings_allotted_legal_balls":12,"is_incomplete_innings":False,"is_powerplay":True,"is_middle":False,"is_death":False,"is_legal_ball":True,"striker_id":10,"non_striker_id":11,"batting_order":1,"delivery_id":"1-1-1","team_score_before_exact":0,"team_score_after_exact":1,"team_score_before_proxy":0,"team_score_after_proxy":1,"runs":1,"is_ball_faced":True,"batter_dot":False,"team_batter_boundary":False,"dismissed_player_id":None,"is_wicket":False,"extra_code":6,"verified_no_extra":True,"partnership_id":1,"team_runs_proxy_delivery":1,"bowler_runs_exact_delivery":1,"bowler_runs_proxy_delivery":1,"dismissal_type":None,"bowler_id":20,"batting_team_id":2,"bowling_team_id":3,"comp_id":4,"season":2025,"balls_remaining_before":12,"team_wickets_before":0,"wickets_in_hand_before":10,"crr_before_exact":0,"crr_before_proxy":0,"rrr_before_exact":None,"rrr_before_proxy":None,"is_score_exact_before":True,"is_target_exact":False},
            {"match_id":1,"innings":1,"legal_ball_before":1,"legal_ball_after":1,"overid":1,"over_ball_num":2,"allotted_legal_balls":12,"powerplay_balls":4,"death_balls":6,"first_innings_allotted_legal_balls":12,"is_incomplete_innings":False,"is_powerplay":True,"is_middle":False,"is_death":False,"is_legal_ball":False,"striker_id":10,"non_striker_id":11,"batting_order":1,"delivery_id":"1-1-2","team_score_before_exact":None,"team_score_after_exact":None,"team_score_before_proxy":27,"team_score_after_proxy":28,"runs":0,"is_ball_faced":False,"batter_dot":False,"team_batter_boundary":False,"dismissed_player_id":None,"is_wicket":False,"extra_code":2,"verified_no_extra":False,"partnership_id":1,"team_runs_proxy_delivery":1,"bowler_runs_exact_delivery":None,"bowler_runs_proxy_delivery":1,"dismissal_type":None,"bowler_id":20,"batting_team_id":2,"bowling_team_id":3,"comp_id":4,"season":2025,"balls_remaining_before":11,"team_wickets_before":4,"wickets_in_hand_before":6,"crr_before_exact":6,"crr_before_proxy":6,"rrr_before_exact":None,"rrr_before_proxy":None,"is_score_exact_before":False,"is_target_exact":False},
        ])
        with tempfile.TemporaryDirectory() as tmp:
            export_context_metrics(x,Path(tmp))
            phase=pd.read_csv(Path(tmp)/"data/processed/phase_allocation.csv")
            entry=pd.read_csv(Path(tmp)/"data/processed/batter_entries.csv")
            context=pd.read_csv(Path(tmp)/"data/processed/batting_context_metrics.csv")
            self.assertEqual(int(phase.phase_legal_balls_powerplay.iloc[0]),1)
            self.assertEqual(int(len(entry)),1)
            self.assertEqual(int(entry.player_id.iloc[0]),10)
            entry_context=context[(context.player_id.eq(10))&(context.context_dimension.eq("entry_score_band"))]
            self.assertEqual(entry_context.context_value.tolist(),["0-9"])
            wicket_context=context[(context.player_id.eq(10))&(context.context_dimension.eq("entry_wicket_band"))]
            self.assertEqual(wicket_context.context_value.tolist(),["0-1"])

if __name__=="__main__": unittest.main()
