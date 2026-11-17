from pathlib import Path
import pandas as pd

def compare_scenarios(root):
    root=Path(root); strict=root/"data"/"outputs"/"strict_exact_context"; proxy=root/"data"/"outputs"/"proxy_inclusive"
    dest=root/"data"/"outputs"/"scenario_comparison"; dest.mkdir(parents=True,exist_ok=True)
    comparisons=[]
    for role in ["batter","bowler"]:
        a=pd.read_csv(strict/f"all_{role}_rankings.csv")
        b=pd.read_csv(proxy/f"all_{role}_rankings.csv")
        keep=["player_id","player_name","rank","ranking_score","pressure_matches","confidence_label"]
        a=a[keep].rename(columns={c:f"{c}_strict" for c in keep if c not in ["player_id"]})
        b=b[keep].rename(columns={c:f"{c}_proxy" for c in keep if c not in ["player_id"]})
        x=a.merge(b,on="player_id",how="outer")
        x["player_role"]=role
        x["rank_change_proxy_minus_strict"]=x.rank_proxy-x.rank_strict
        x["rating_change_proxy_minus_strict"]=x.ranking_score_proxy-x.ranking_score_strict
        x["top10_status"]=x.apply(lambda r:"entered" if pd.notna(r.rank_proxy) and r.rank_proxy<=10 and (pd.isna(r.rank_strict) or r.rank_strict>10) else ("left" if pd.notna(r.rank_strict) and r.rank_strict<=10 and (pd.isna(r.rank_proxy) or r.rank_proxy>10) else "stayed/outside"),axis=1)
        comparisons.append(x)
        x.to_csv(dest/f"scenario_{role}_comparison.csv",index=False)
    rank_changes=pd.concat(comparisons,ignore_index=True)
    rank_changes.to_csv(dest/"scenario_rank_changes.csv",index=False)
    rank_changes[["player_id","player_name_strict","player_role","ranking_score_strict","ranking_score_proxy","rating_change_proxy_minus_strict","pressure_matches_strict","pressure_matches_proxy"]].to_csv(dest/"scenario_rating_changes.csv",index=False)
    sit=[]
    for role in ["batting","bowling"]:
        file=f"{role}_situation_ratings.csv"
        a=pd.read_csv(strict/file); b=pd.read_csv(proxy/file)
        x=a.merge(b,on=["player_id","player_role","situation_id"],how="outer",suffixes=("_strict","_proxy"))
        x["situation_score_change"]=x.situation_score_proxy-x.situation_score_strict
        sit.append(x[["player_id","player_role","situation_id","situation_score_strict","situation_score_proxy","situation_score_change"]])
    pd.concat(sit,ignore_index=True).to_csv(dest/"scenario_situation_changes.csv",index=False)
    return rank_changes
