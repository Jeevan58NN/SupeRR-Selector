import unittest
import json
from pathlib import Path
from superr_selector.scoring.rating import match_consistency,shrink_score,_tier,combined_evidence_matches,_normal_scores

class RatingModelTests(unittest.TestCase):
    def test_one_match_never_becomes_perfect_consistency(self):
        self.assertLess(match_consistency([100]),100)
        self.assertLess(match_consistency([100]),70)
    def test_stable_poor_performance_is_not_rewarded_as_good_consistency(self):
        self.assertLess(match_consistency([20]*20),50)
    def test_repeated_good_matches_are_stronger_consistency_evidence(self):
        self.assertGreater(match_consistency([70]*30),match_consistency([70]))
    def test_more_evidence_shrinks_less_but_does_not_add_raw_points(self):
        self.assertLess(shrink_score(80,1,5),shrink_score(80,30,5))
        self.assertLess(shrink_score(40,30,5),shrink_score(40,1,5))
    def test_pressure_matches_and_normal_innings_both_support_rating(self):
        self.assertEqual(combined_evidence_matches(0,20),0)
        self.assertEqual(combined_evidence_matches(10,10),10)
        self.assertLess(combined_evidence_matches(2,100),combined_evidence_matches(20,100))
        self.assertLess(combined_evidence_matches(20,2),combined_evidence_matches(20,20))
    def test_normal_role_rating_shrinks_small_innings_sample_more(self):
        import pandas as pd
        normal=pd.DataFrame({
            "player_id":[1,2,3,4,5,6],"strike_rate_or_economy":[200,80,90,100,110,120],
            "dot_pct":[10,60,55,50,45,40],"balls":[10]*6,"dismissals":[0]*6,
            "innings_in_sample":[1,20,20,20,20,20],"matches_in_sample":[1,20,20,20,20,20],
            "faded_pressure_deliveries":[0]*6,"normal_role_group":["opener"]*6,
            "normal_opponent_weight":[1.0]*6,
        })
        five=_normal_scores(normal,pd.DataFrame(),5.0).set_index("player_id")
        ten=_normal_scores(normal,pd.DataFrame(),10.0).set_index("player_id")
        self.assertLess(abs(ten.loc[1,"normal_rating"]-50),abs(five.loc[1,"normal_rating"]-50))
    def test_supplied_us_team_alias_maps_to_user_defined_tier_three(self):
        cfg=json.loads((Path(__file__).resolve().parents[1]/"config"/"opponent_tiers.yaml").read_text(encoding="utf-8-sig"))
        self.assertEqual(_tier("United States Of America","T20I",cfg),"International Tier 3")

if __name__=='__main__': unittest.main()
