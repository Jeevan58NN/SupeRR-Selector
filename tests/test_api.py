from pathlib import Path
import os
import pandas as pd
import superr_selector.api.app as api

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("SUPERR_ROOT",str(ROOT))
def test_health_and_precomputed_summary():
    assert api.health()["status"]=="ok"
    summary=api.dashboard_summary
    from unittest.mock import patch
    def fake_frame(path):
        name=Path(path).name
        if name=="all_player_rankings.csv":
            return pd.DataFrame([{"player_id":1,"player_name":"Example","player_role":"batter","ranking_score":70.0}])
        if name in {"batting_pressure_episodes.csv","bowling_pressure_episodes.csv"}:
            return pd.DataFrame([{"episode_id":name,"situation_id":"B2"}])
        if name=="data_quality_summary.csv":
            return pd.DataFrame([{"source_file":"ball_by_ball.csv","matches":2,"rows":12},{"source_file":"matches.csv","matches":3,"rows":3}])
        return pd.DataFrame([{"player_id":1,"player_name":"Example"}])
    with patch.object(api,"frame",side_effect=fake_frame):
        data=summary("strict_exact_context")
    assert data["matches_covered"]==2
    assert data["episodes"]==2

def test_rankings_are_paginated_and_include_real_names():
    from unittest.mock import patch
    rows=pd.DataFrame([{"player_id":1,"player_name":"One","rank":1,"ranking_score":80},{"player_id":2,"player_name":"Two","rank":2,"ranking_score":70}])
    with patch.object(api,"ranked",return_value=rows):
        payload=api.rankings("batter","strict_exact_context",1,2,"ranking_score","desc","")
    assert len(payload["items"])==2 and payload["items"][0]["player_name"]=="One"

def test_player_compare_route_is_not_captured_as_player_id():
    from unittest.mock import patch
    rankings=pd.DataFrame([{"player_id":1,"player_name":"One","player_role":"batter"},{"player_id":2,"player_name":"Two","player_role":"batter"}])
    situations=pd.DataFrame(columns=["player_id","situation_id","situation_score"])
    with patch.object(api,"ranked",return_value=rankings), patch.object(api,"frame",return_value=situations):
        result=api.compare_players("1,2","strict_exact_context")
    assert {p["player_id"] for p in result["players"]}=={1,2}

def test_valid_unobserved_situation_is_empty_not_error():
    from unittest.mock import patch
    empty=pd.DataFrame(columns=["situation_id","player_id","situation_score"])
    episodes=pd.DataFrame(columns=["situation_id","episode_id"])
    with patch.object(api,"frame",side_effect=[empty,episodes,episodes]):
        result=api.situation_detail("B1","strict_exact_context")
    assert result["evidence_available"] is False

def test_unknown_scenario_is_rejected():
    from fastapi import HTTPException
    import pytest
    with pytest.raises(HTTPException) as exc:
        api.rankings("batter","other",1,50,"ranking_score","desc","")
    assert exc.value.status_code==422

def test_mapped_player_profile_remains_available_without_pressure_rating():
    from unittest.mock import patch
    master=pd.DataFrame([{"player_id":91,"player_name":"Unrated Player"}])
    situations=pd.DataFrame(columns=["player_id","situation_id","situation_score"])
    batting=pd.DataFrame([{"player_id":91,"runs":0,"matches_in_sample":1}])
    bowling=pd.DataFrame(columns=["player_id","wickets"])
    normal_bat=pd.DataFrame(columns=["player_id","innings_in_sample"])
    normal_bowl=pd.DataFrame(columns=["player_id","innings_in_sample"])
    with patch.object(api,"frame",side_effect=[master,situations,batting,bowling,normal_bat,normal_bowl]), patch.object(api,"ranked",return_value=pd.DataFrame(columns=["player_id","player_role","rank"])):
        result=api.player_profile(91,"strict_exact_context")
    assert result["player"]["player_name"]=="Unrated Player"
    assert result["player"]["ratings"]==[]
    assert result["player"]["player_type"]=="No recorded role"
    assert result["player"]["batting_rank"] is None
    assert result["player"]["bowling_rank"] is None
    assert result["batting"]["runs"]==0

def test_profile_marks_all_rounder_from_normal_role_innings_and_shows_both_ranks():
    from unittest.mock import patch
    master=pd.DataFrame([{"player_id":92,"player_name":"Balanced Player"}])
    situations=pd.DataFrame(columns=["player_id","player_role","situation_score"])
    batting=pd.DataFrame([{"player_id":92,"runs":300}]); bowling=pd.DataFrame([{"player_id":92,"wickets":12}])
    normal_bat=pd.DataFrame([{"player_id":92,"innings_in_sample":24}])
    normal_bowl=pd.DataFrame([{"player_id":92,"innings_in_sample":18}])
    ranks={"batter":pd.DataFrame([{"player_id":92,"player_role":"batter","rank":14}]),
        "bowler":pd.DataFrame([{"player_id":92,"player_role":"bowler","rank":31}])}
    with patch.object(api,"frame",side_effect=[master,situations,batting,bowling,normal_bat,normal_bowl]), \
         patch.object(api,"ranked",side_effect=lambda scenario,role:ranks[role]):
        result=api.player_profile(92,"strict_exact_context")
    assert result["player"]["player_type"]=="All-rounder"
    assert result["player"]["batting_rank"]==14
    assert result["player"]["bowling_rank"]==31


def test_josh_hazlewood_proxy_profile_has_rank_and_bowling_metrics():
    profile=api.player_profile(830, "proxy_inclusive")
    assert profile["player"]["player_name"] == "Josh Hazlewood"
    assert profile["player"]["bowling_rank"] == 2
    assert profile["bowling"]["legal_balls"] > 0
    assert profile["bowling"]["wickets"] > 0


def test_default_api_scenario_is_proxy_inclusive():
    assert api.dashboard_summary.__defaults__[0] == "proxy_inclusive"
    assert api.player_profile.__defaults__[0] == "proxy_inclusive"
    assert api.rankings.__defaults__[0] == "proxy_inclusive"
