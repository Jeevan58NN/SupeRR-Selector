# Data dictionary

| Field | Meaning | Reliability notes |
|---|---|---|
| `match_id`, `innings`, `delivery_id` | Stable match/innings/delivery identifiers. | Delivery IDs are generated from match, innings and row order where absent. |
| `striker_id`, `non_striker_id`, `bowler_id` | Player IDs at the delivery. | Player joins use IDs, not names. |
| `runs` / `batter_runs` | Batter-credited runs. | Kept distinct from team totals and bowler runs. |
| `extras1_runs` / `extra_code` | Extra category code. | Codes 1–7 are categories, not numeric extra amounts. |
| `team_runs_proxy_delivery` | Known batter runs plus defensible minimum extra runs. | Lower-bound estimate, not scorecard total. |
| `bowler_runs_exact_delivery` | Bowler runs when exact value is supported by the source semantics. | Null when an extra prevents exact per-delivery bowler total. |
| `bowler_runs_proxy_delivery` | Bowler runs with minimum known wide/no-ball penalty. | Proxy scenario only; lower bound. |
| `is_legal_ball` | Whether the delivery advances legal-ball count. | Wide/no-ball are illegal; other rows are treated as legal under supplied categories. |
| `is_ball_faced` | Whether a delivery counts against the batter. | Wide excluded, no-ball included. |
| `team_score_before_exact`, `team_score_before_proxy` | Running score before delivery. | Exact becomes unavailable after uncertain extras; proxy remains a lower bound. |
| `is_score_exact_before`, `is_score_exact_after` | Exact running-score reliability flags. | Do not infer exact score when false. |
| `target_exact`, `target_proxy_lower_bound` | Chase target from verified metadata or reconstructed innings. | Target exact requires verified target/first-innings completion without unresolved revision. |
| `crr_before_exact`, `crr_before_proxy` | Current run rate before delivery. | Team runs × 6 / legal balls used. |
| `rrr_before_exact`, `rrr_before_proxy` | Required run rate before delivery. | Chase only; target minus score, divided by legal balls remaining, ×6. |
| `team_wickets_before`, `wickets_in_hand_before` | Team wickets and remaining wickets. | Includes all recorded dismissals; bowler wickets are calculated separately. |
| `partnership_runs_before_exact`, `partnership_runs_before_proxy` | Current stand runs before delivery. | Exact/proxy are kept separate. |
| `is_powerplay`, `is_middle`, `is_death` | Innings phase flags. | Based on allocated legal balls, not observed rows or decimal-over arithmetic. |
| `pressure_intensity` | State-derived pressure from 0 to 1 on an active episode. | Not a player-performance score. |
| `severity_weight`, `shared_contribution_factor` | Situation priority and duplicate-overlap adjustment. | Applied separately from intensity; overlap audit retains all situation tags. |
| `scenario`, `score_quality`, `is_incomplete_innings` | Analysis view and data quality. | Strict/proxy never silently mix; incomplete innings are not treated as complete. |
| `rank`, `ranking_score`, `final_rating` | Role-specific player order and 0–100 rating. | Ranking uses match-level evidence; `confidence_label` reports evidence strength. |

See `METHODOLOGY.md` for source columns, formulas, units and missing-data rules.
