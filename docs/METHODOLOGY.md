# SupeRR Selector — calculation and output guide

## Scope and inputs

The pipeline uses `ball_by_ball.csv`, `matches.csv`, `competitions.csv`, `playing_eleven.csv`, `competition_team_player_mapping.csv`, and `teams.csv` from the project root. The PDF is recorded in the audit manifest. Original files are treated as inputs and never overwritten. The current ball file has 180,723 rows and 779 covered matches; the metadata has 883 matches. See `SOURCE_AUDIT.md` for hashes, schema, quality findings and uncovered matches.

## Match state

A wide (category 2) and overstep/no-ball (category 1) do not advance legal balls. A wide is not a batter ball faced; a no-ball is. Other deliveries count as legal unless the source marks the category as wide/no-ball. Batter runs, team runs and bowler-conceded runs remain separate. The extra category field is not an extra-run amount. Strict score reconstruction stops at the first extra whose exact amount is unknown. Proxy totals use only defensible minimum values and remain flagged. CRR is runs × 6 / legal balls. RRR is (verified target − score) × 6 / legal balls remaining, only in a chase. Powerplay is ceil(30% of allocated legal balls); death is the final ceil(25% of overs).

## Pressure and ratings

Episodes keep trigger and evaluation windows separate. The strict/proxy detector files preserve each situation, player participation, delivery labels, overlap resolution and intensity history. Intensity reflects match state and is distinct from performance. Delivery tags at intensity 0.20 or lower remain pressure-tagged and may contribute to normal references; higher intensity deliveries are excluded from the normal reference.

Player observations are normalized against robust median/MAD peer benchmarks with role/situation/phase/competition/opponent fallbacks. Batting evaluates strike rate and batter dots (45%), pressure runs contributed (15%), boundary rate (20%), and chase RRR reduction (20%). Bowling evaluates economy and dot control (45%), credited wicket rate (30%), boundary prevention (15%), and increasing chase RRR (10%). Missing chase-only evidence is excluded and available weights are renormalized. For each component, groups with fewer than five players fall back to a broader same-role benchmark. A batter's bowling output never enters the batting ranking.

The user-configured opponent factor scales performance above or below neutral and weights pressure evidence; weaker opponent pools contribute less effective evidence. Normal performance is calculated separately for each role, standardized against the player's primary batting-position or bowling-phase group, adjusted by average opponent tier, and shrunk toward neutral using a 10-normal-innings prior. Sensitivity outputs compare normal priors of 5, 10, and 15 innings to identify players whose ranks depend on very small ordinary-performance samples. Pressure match evidence and normal innings are combined using their harmonic mean, so neither sample can substitute for a very small other sample. Pressure performance and consistency are shrunk toward 50 with `k=30`; sensitivity outputs cover `k=3, 5, 8, 12, 20, 30, 40`. The final rating is 50% adjusted pressure performance, 20% match consistency, and 30% normal-role performance. No minimum match cutoff is used. A capped knockout adjustment can operate only within 0.50 points. Confidence intervals resample matches, not deliveries. See `SCORING_MODEL.md` for the formulas and sensitivity details.

## Main data paths

| File | Location | Meaning |
|---|---|---|
| `source_file_manifest.csv` | `data/interim/` | Input size and SHA-256 provenance. |
| `schema_validation.csv` | `data/interim/` | Required columns and schema checks. |
| `data_quality_summary.csv` | `data/interim/` | Rows, columns, duplicate rows and missing cells by input. |
| `player_master.csv`, `team_master.csv`, `match_master.csv`, `playing_appearances.csv` | `data/processed/` | ID-based master and appearance joins. Appearance is XI played OR impact. |
| `cleaned_deliveries.csv` | `data/processed/` | Canonical delivery records with source provenance and parsed cricket rules. |
| `delivery_match_state.csv` | `data/outputs/{scenario}/` | Delivery state and exact/proxy score fields. |
| `innings_summary.csv`, `score_reconstruction.csv` | `data/outputs/{scenario}/` | Innings totals, target and completion/quality flags. |
| `batting_pressure_episodes.csv`, `bowling_pressure_episodes.csv` | Scenario folder | Trigger, start/end, severity, quality and completion per episode. |
| `batting_pressure_membership.csv`, `bowling_pressure_membership.csv` | Scenario folder | Player delivery participation in each episode. |
| `delivery_pressure_labels.csv` | Scenario folder | Situation and episode labels, trigger/stage and intensity. |
| `pressure_intensity_history.csv` | Scenario folder | State-derived intensity on active episode deliveries. |
| `overlap_resolution_log.csv` | Scenario folder | Selected shared contribution for configured overlapping situations. |
| `batting_normal_performance.csv`, `bowling_normal_performance.csv` | Scenario folder | Role-specific reference performance, including faded pressure. |
| `batting_pressure_performance.csv`, `bowling_pressure_performance.csv` | Scenario folder | Player metrics on high-intensity pressure deliveries. |
| `situation_observations.csv` | Scenario folder | Player × match × situation aggregate before peer comparison. |
| `situation_ratings.csv`, `batting_situation_ratings.csv`, `bowling_situation_ratings.csv` | Scenario folder | Context-adjusted situation scores plus evidence counts. |
| `player_episode_scores.csv` | Scenario folder | Descriptive episode outcomes; episodes are not independent matches. |
| `player_match_scores.csv` | Scenario folder | Independent player-match evidence used for shrinkage and consistency. |
| `player_reliability.csv` | Scenario folder | Match, episode, delivery, exact/proxy coverage and CI. |
| `all_player_rankings.csv`, `all_batter_rankings.csv`, `all_bowler_rankings.csv` | Scenario folder | Full ranking outputs with 0–100 score, rank, CI, evidence and role. |
| `top10_batters.csv`, `top10_bowlers.csv` | Scenario folder | First ten rows of respective full rankings. |
| `ranking_sensitivity.csv` | Scenario folder | Prior/consistency sensitivity and unweighted-opponent comparison. |
| `pressure_vs_normal_comparison.csv` | Scenario folder | Rating and normal reference side by side. |
| `player_opponent_tier_performance.csv` | Scenario folder | Player pressure performance by opponent pool/tier. |
| `scenario_rank_changes.csv`, `scenario_rating_changes.csv`, `scenario_situation_changes.csv` | `data/outputs/scenario_comparison/` | Strict/proxy differences and entry/exit status. |

Rate denominators use batter balls faced for batters and legal balls for bowling. Missing metrics remain blank. Source metadata matches with no delivery data can contribute to appearance counts only; no player delivery statistics are imputed. Super Overs are excluded from standard pressure situations. The supplied data does not include a repaired duplicate ball file, so no duplicate-hash comparison was possible.

## Additional context exports

The `data/processed` folder contains first-observed batter entries, partnership windows, bowler-over spells, legal-ball phase allocations, and batting/bowling summaries by phase and over plus batting position. Exact and proxy runs are separate. Entry score, wickets, remaining legal balls, CRR, RRR, partnership, and phase are attached when available. Bowling exact economy is missing where any delivery's bowler-conceded runs cannot be verified. Detailed explanations and source fields are in `OUTPUT_FILE_GUIDE.md` and `DATA_DICTIONARY.md`.
