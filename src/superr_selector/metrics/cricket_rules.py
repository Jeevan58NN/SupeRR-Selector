from __future__ import annotations
import math

BALLS_PER_OVER=6

def legal_ball(extra_code: int) -> bool:
    return int(extra_code) not in {1,2}

def batter_ball_faced(extra_code: int) -> bool:
    return int(extra_code) != 2

def powerplay_balls(allotted_legal_balls: int) -> int:
    return math.ceil(0.30*int(allotted_legal_balls))

def death_balls(allotted_legal_balls: int) -> int:
    overs=math.ceil(int(allotted_legal_balls)/BALLS_PER_OVER)
    return math.ceil(0.25*overs)*BALLS_PER_OVER

def current_run_rate(team_runs: float, legal_balls: int) -> float | None:
    return float(team_runs)*6/int(legal_balls) if int(legal_balls)>0 else (0.0 if int(legal_balls)==0 else None)

def required_run_rate(target: float, score: float, legal_balls_remaining: int) -> float | None:
    if int(legal_balls_remaining)<=0:
        return None
    return (float(target)-float(score))*6/int(legal_balls_remaining)
