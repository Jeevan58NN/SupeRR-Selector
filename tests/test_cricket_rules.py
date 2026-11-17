import unittest
from superr_selector.metrics.cricket_rules import legal_ball,batter_ball_faced,powerplay_balls,death_balls,current_run_rate,required_run_rate

class CricketRuleTests(unittest.TestCase):
    def test_legality_and_balls_faced(self):
        self.assertFalse(legal_ball(1)); self.assertFalse(legal_ball(2))
        self.assertTrue(legal_ball(3)); self.assertTrue(legal_ball(4)); self.assertTrue(legal_ball(6))
        self.assertFalse(batter_ball_faced(2))
        self.assertTrue(batter_ball_faced(1)); self.assertTrue(batter_ball_faced(3)); self.assertTrue(batter_ball_faced(6))
    def test_phase_lengths(self):
        self.assertEqual([powerplay_balls(x) for x in [30,60,96,120]],[9,18,29,36])
        self.assertEqual([death_balls(x) for x in [30,60,96,120]],[12,18,24,30])
    def test_run_rates_use_legal_balls(self):
        self.assertEqual(current_run_rate(48,36),8)
        self.assertEqual(required_run_rate(151,71,30),16)
        self.assertIsNone(required_run_rate(151,71,0))

if __name__=="__main__": unittest.main()
