# Validation report

## Completed checks

- Source audit: 180,723 deliveries, 779 covered matches, and 883 match metadata records. Source gaps and duplicate-file limitations are documented in `SOURCE_AUDIT.md` and `DATA_QUALITY_REPORT.md`.
- Both scenario pressure datasets were regenerated after correcting B10 to apply in either innings. Strict: 6,633 batting episodes, 6,141 bowling episodes, and 230,117 labeled delivery-situation rows. Proxy: 9,631 batting episodes, 10,101 bowling episodes, and 371,398 labeled rows. Each scenario has 672 B10 episodes.
- Final scoring exports: strict 1,078 role ratings, 25,221 match-situation observations, and 12,403 player-match rows; proxy 1,082 role ratings, 40,293 observations, and 14,689 player-match rows. The strict/proxy comparison contains 1,134 player-role rows.
- The final ranking model uses the harmonic mean of distinct, opponent-weighted pressure matches and normal role innings as effective evidence, a 30 effective-match prior for pressure performance and consistency, and a final mix of 50% adjusted pressure performance, 20% consistency, and 30% normal-role performance. The normal-role score uses a 10-innings prior; sensitivity compares 5, 10, and 15 innings. Pressure prior and consistency sensitivities are also retained.
- Following the normal-sample audit, the proxy batter top ten starts with Vaibhav Sooryavanshi (12 pressure matches, 30 normal innings), Priyansh Arya (9, 29), Suryakumar Yadav (61, 110), and Heinrich Klaasen (50, 44). The proxy bowler list starts with Jasprit Bumrah (49 pressure matches, 51 normal innings), Josh Hazlewood (40, 52), and Mohammed Siraj (58, 77). Virat Kohli ranks 72 in proxy batting (46 pressure matches, 87 normal innings). Batting and bowling evidence are scored independently.
- Profile API identifies all-rounders from at least 15 normal reference innings in each role and returns separate batting and bowling ranks; the UI has a role selector and displays `—` when a rank is unavailable.
- Python suite: 27 tests passed, including cricket rules, reconstruction, context exports, scoring evidence behavior, API route behavior, and synthetic trigger activation for all 31 situations.
- Vite production build passed: 28 modules transformed; 167.88 kB JavaScript and 6.76 kB CSS before gzip.
- Strict B1 has zero exact-context observations; proxy has 336. Strict missing evidence is reported as unavailable, not zero performance.
- Final ranking reconciliation: both scenarios have exactly ten rows in each top-ten CSV, matching the first ten rows of the full role ranking. No low-confidence player appears in either role's top ten in either scenario. Each scenario has 32 sensitivity variants, including normal-innings prior values of 5, 10, and 15.

## Remaining validation limits

The synthetic suite verifies activation of all 31 situations but does not independently verify every episode-ending edge case, including B13/BW15 win/tie/loss outcomes, revised/DLS targets, and ambiguous A-team inference. Automated browser/mobile interaction and live HTTP integration were not completed in this environment. Docker is unavailable here, so an image build was not run. The two alternate ball-by-ball files needed for a duplicate hash comparison were not supplied.

Ratings and confidence labels summarize the supplied records; they do not guarantee future performance. Review `METHODOLOGY.md`, `SCORING_MODEL.md`, and `DATA_QUALITY_REPORT.md` alongside the top tens. The primary ranking is strict exact context; proxy-inclusive rankings can rely on flagged lower-bound estimates. Rankings were recalculated from precomputed match-state and pressure files; the pressure detector itself was not rerun during this scoring-only update.



## Ranking evidence audit (normal prior update)

The review compared pressure matches, weighted pressure evidence, normal innings, effective evidence, above-benchmark match frequency, confidence, and opponent-tier coverage for both role lists in both scenarios. The data joins are role-correct: batter opponent is the bowling side; bowler opponent is the batting side. The configured opponent factor is applied to each context-adjusted situation contribution and to pressure evidence, while tier-specific scores remain exported for inspection. No top-ten player is supported only by A-team or lowest-tier opposition.

A real weakness was found in normal-role shrinkage: a five-innings prior allowed unusually high normal estimates from small samples to move players with only a handful of pressure matches into the top ten. The normal prior is now 10 innings. Strict top-ten low-confidence counts changed from present to zero in both roles; proxy top-ten low-confidence counts are also zero in both roles. Moderate-evidence players remain eligible, with their pressure-match and normal-innings counts shown. The normal-prior sensitivity variants are included in each scenario's `ranking_sensitivity.csv`.

The pressure trigger engine and reconstructed delivery-state files were not changed or rerun. Only scoring and ranking exports were regenerated. This preserves all existing situation definitions and backend/API structure.
