# Pressure situation definitions

The engine gives each pressure occurrence a situation ID, trigger and response window. Full trigger logic is implemented in `src/superr_selector/pressure/detect.py`; thresholds below mirror the supplied project specification. The evaluation window begins after any trigger-only sequence where explicitly required.

## Batting situations

| ID | Trigger |
|---|---|
| B1 | Final allotted over of a chase with RRR ≥ 12 at over start. |
| B2 | No team boundary in first three completed overs; response starts after over three. |
| B3 | Batter faces four consecutive batter-dot balls; assess next scoring ball/dismissal, max ten subsequent balls faced. |
| B4 | Batter has faced ≥10 balls and strike rate <100; both current batters participate until trigger batter is dismissed. |
| B5 | Third Powerplay wicket; assess remaining innings. |
| B6 | Score below 35 at end of Powerplay; assess remainder. |
| B7 | Fifth wicket within first ten overs; assess remainder. |
| B8 | Three wickets within rolling twelve legal balls; assess until next partnership reaches 20. |
| B9 | Final five overs of chase while RRR >12.5. |
| B10 | Three or fewer wickets in hand during final five overs. |
| B11 | Eighteen legal balls without batter-credited boundary; response until four boundaries. |
| B12 | Three consecutive completed overs each scoring below seven runs; response until CRR ≥10. |
| B13 | Final legal ball of chase with 1–7 runs required before ball; outcome is win/tie/loss. |
| B14 | Over five or six starts with CRR <8; evaluate that over using start-of-over CRR. |
| B15 | Knockout match context; supporting rating/tie-break only, not an artificial delivery pressure window. |

## Bowling situations

| ID | Trigger |
|---|---|
| BW1 | Same bowler concedes three consecutive boundaries within one over (wides excluded from sequence). |
| BW2 | Same bowler delivers three consecutive wides/no-balls with no legal ball between; assess remaining over. |
| BW3 | Applicable free-hit deliveries following no-ball/overstep; illegal deliveries carry state forward. |
| BW4 | Powerplay from third over onward; pre-over batting CRR >12. |
| BW5 | Team reaches 70 without losing a wicket; assess until third team wicket or innings end. |
| BW6 | Partnership reaches 60; assess bowlers until partnership breaks. |
| BW7 | Final five overs of chase with RRR <8; difficult defensive situation. |
| BW8 | At final-over start in chase, 1–12 runs required; assess full final over. |
| BW9 | From fixed 16th over onward with at least eight opposition wickets in hand. |
| BW10 | Bowler delivers to a batter already on 100; assess that batter until dismissal/innings end. |
| BW11 | Fixed 19th over, with start-of-over RRR <12; evaluate that over. |
| BW12 | Opposition reaches 100 within first ten overs; assess subsequent bowling. |
| BW13 | After ten completed overs with zero or one wicket lost; assess subsequent bowling. |
| BW14 | After bowler concedes ≥15 in an over; assess next bowler’s over and original bowler’s next over separately. |
| BW15 | Final legal ball of chase with one or two runs required; classify defended/tied/conceded win. |
| BW16 | Second innings target below 150 × first-innings allocated balls /120. |

## Data limits

Score-dependent triggers require exact score in strict mode. Proxy mode retains eligible records only with lower-bound flags. Target-dependent triggers require a verified target. Incomplete innings and Super Overs are flagged/excluded from full-match chase conclusions. An unavailable situation observation is missing evidence, never a zero score.
