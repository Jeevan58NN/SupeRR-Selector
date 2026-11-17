# Data quality report

## Coverage from supplied files

- Ball-by-ball: 180,723 rows, 33 columns, 779 distinct matches, 0 exact duplicate rows.
- Match metadata: 883 records, leaving 104 with no delivery records.
- Player-team-competition mapping: 6,413 rows; observed player IDs in deliveries map to the supplied player mapping.
- Playing XI: 28,381 rows across 880 distinct matches. Appearance is a distinct match where `is_played` is true OR `is_impact` is 1.
- Competitions: 141 records; 134 T20I and 7 T20 records. The T20 pool includes IPL and two other T20 competitions.
- Knockouts: 31 metadata matches, of which 25 have delivery coverage.
- Five covered matches have innings numbered 3 or 4, treated as Super Over innings and excluded from the main pressure rankings.
- Match 46249 has an innings-2 segment starting part way into its match record, with no observed innings 1. It is incomplete and excluded from complete-chase interpretation.

## Source semantics and join issues

`extras1_runs` stores a category code, not numeric extra runs: 1 overstep/no-ball, 2 wide, 3 leg-bye, 4 bye, 5 other, 6 no extra, 7 penalty. Only 35 rows have a nonzero `extras_2_runs`. Unknown extras therefore affect running score reliability. Strict values become unavailable downstream of an uncertain score event; proxy values use only justified lower bounds and are separately flagged.

There are 20 differences between `is_four` and `runs == 4`, and 2 differences between `is_six` and `runs == 6`; the supplied flags are retained. Forty repeated match/team/player XI keys have differing batting-order values. IDs are used for joins; player master selects a deterministic available mapping and preserves the ID.

Only `ball_by_ball.csv` was supplied in the active project folder. Expected alternate names `ball_by_ball(1).csv` and `ball_by_ball_repaired(1).csv` are absent, so a byte/hash equality comparison cannot be performed. The duplicate report records that limitation; the canonical file is not appended to any other file.

## Scenario counts

| Scenario | Batting episodes | Bowling episodes | Unique episodes | Labeled delivery-situation rows | Player-role ratings |
|---|---:|---:|---:|---:|---:|
| Strict exact context | 6,633 | 6,141 | 12,774 | 230,117 | 1,078 |
| Proxy inclusive | 9,631 | 10,101 | 19,732 | 371,398 | 1,082 |

The latest detector fix applies B10 (three or fewer wickets in hand in the final five overs) to both innings, as specified. Each scenario has 672 B10 episodes in the supplied data.

Strict has no exact-context B1 ratings in these supplied records; proxy has 336 B1 player-situation rows. That difference is shown as unavailable strict evidence, not a zero score.

## Limits

The dataset spans the input-reported 2022–2026 period, but availability is determined by the supplied file and may not represent complete seasons or official scorecards. DLS/revised targets are used only when source metadata supports them. Proxy run values are estimates/lower bounds, never exact scorecard values. Refer to `SOURCE_AUDIT.md`, `METHODOLOGY.md`, and the per-scenario quality flags for detailed provenance.
