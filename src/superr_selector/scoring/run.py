import argparse
from pathlib import Path
from superr_selector.scoring.rating import score_scenario
from superr_selector.scoring.compare import compare_scenarios

def main():
    p=argparse.ArgumentParser(description="Calculate ratings from precomputed pressure outputs.")
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--scenario",choices=["strict_exact_context","proxy_inclusive"])
    a=p.parse_args()
    scenarios=[a.scenario] if a.scenario else ["strict_exact_context","proxy_inclusive"]
    for scenario in scenarios:
        ranks,obs,matches=score_scenario(a.root,scenario)
        print(f"{scenario}: {len(ranks)} player-role ratings, {len(obs)} match-situation observations, {len(matches)} player-match records")
    if not a.scenario:
        comp=compare_scenarios(a.root)
        print(f"Scenario comparison: {len(comp)} player-role rows")

if __name__=="__main__": main()
