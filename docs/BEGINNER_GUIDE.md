# Beginner guide

## What SupeRR Selector does

This project reads the supplied cricket CSV files, rebuilds innings context, finds the defined pressure episodes, scores players from match-level pressure performances, and displays results in a local dashboard. The app does not use outside player data, rankings, or team-strength lists.

## Folder map

- Root CSVs/PDF: original user-supplied inputs.
- `src/superr_selector/data`: schema checks and loading.
- `src/superr_selector/match_state`: legal balls, scores, targets, phase and innings state.
- `src/superr_selector/pressure`: B1–B15 and BW1–BW16 episode detection and overlap handling.
- `src/superr_selector/scoring`: role benchmarks, player ratings, evidence shrinkage and scenario comparisons.
- `data/processed`: cleaned deliveries and master tables.
- `data/outputs/strict_exact_context`: conservative exact-score view.
- `data/outputs/proxy_inclusive`: lower-bound estimates where the extra categories allow them.
- `frontend`: React/Vite responsive dashboard.
- `docs`: audit, formulas, outputs, situation definitions and operational guides.

## Install and run on Windows

1. Install Python 3.11+ and Node.js 20+.
2. Open PowerShell in the project folder.
3. Run `scripts/install.ps1` to create `.venv` and install Python plus frontend dependencies.
4. In `frontend`, run `npm install` once.
5. Run `scripts/run_pipeline.ps1` to rebuild datasets and rankings. This may take several minutes because every delivery and scenario is processed.
6. Run `scripts/run_backend.ps1` in one PowerShell window.
7. Run `scripts/run_frontend.ps1` in another window. Open the Vite address it prints (normally `http://127.0.0.1:5173`). Or use `scripts/run_all.ps1` to start the backend hidden and foreground the frontend.
8. `scripts/validate_installation.ps1` checks Python packages and Node/npm availability.

## How calculation works

A legal ball is not the same as a raw delivery row: wides and no-balls do not advance legal-ball count; batter balls-faced rules differ because no-balls count to the batter and wides do not. Match state preserves batter runs, team runs and bowler-conceded runs separately. Unknown extra amounts terminate exact score reliability. Proxy values are lower bounds, always scenario-labelled.

A pressure episode has a trigger event, eligible participants, evaluation deliveries, intensity history and ending reason. Players contribute only on deliveries they personally face/bowl in an active episode. Situations can overlap; the overlap table prevents similar configured conditions from contributing multiple full weights while retaining their independent records.

The performance benchmark is role- and situation-aware. Episodes in one match are first combined into one player-match observation; this prevents treating repeated deliveries or episodes as independent matches. Shrinkage pulls estimates toward a neutral peer score when there are few independent matches. Consistency is not declared from a single match. Confidence is displayed separately from the performance score.

## Safely regenerating outputs

Keep raw files in place. Run the pipeline from the project root via `scripts/run_pipeline.ps1`; it overwrites only generated files under `data/interim`, `data/processed`, and `data/outputs`. Use the same source files and config to reproduce results. To change rules, edit the configuration and formulas, update tests, then rerun the pipeline and compare scenario sensitivity outputs.

## API

FastAPI serves precomputed CSVs. The React client filters API results and does not recalculate ratings. Browse `/docs` at `http://127.0.0.1:8000/docs` to inspect endpoint schemas.

