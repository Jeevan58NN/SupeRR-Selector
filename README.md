# SupeRR Selector 2.0

An auditable cricket pressure analytics platform built exclusively from the supplied datasets. Source files are retained at the project root and are not overwritten.

## Local run on Windows

1. Install Python 3.11+ and Node.js 20+.
2. Run `scripts/install.ps1` in PowerShell.
3. Run `scripts/run_pipeline.ps1` once to rebuild the scenario outputs.
4. Run `scripts/run_all.ps1`, or start `scripts/run_backend.ps1` and `scripts/run_frontend.ps1` in separate PowerShell windows.
5. Open `http://127.0.0.1:5173`. The API docs are at `http://127.0.0.1:8000/docs`.

## What is available

- Strict exact-context and proxy-inclusive state reconstruction and pressure outputs.
- Batting situations B1–B15 and bowling situations BW1–BW16.
- Dynamic intensity, episode membership, overlap records, normal/pressure performance, role-aware 0–100 ratings, match-level shrinkage, confidence intervals, top tens, full rankings and sensitivity outputs.
- FastAPI endpoints over precomputed CSVs and a responsive React/Vite dashboard with paginated/searchable full role rankings, mapped-player profiles, context breakdowns, comparison, situations, episodes, delivery-level match explorer, normal-vs-pressure view, data-quality view, and methodology.

## Documentation

- [Source audit](docs/SOURCE_AUDIT.md)
- [Data quality](docs/DATA_QUALITY_REPORT.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)
- [Methodology](docs/METHODOLOGY.md)
- [Scoring model](docs/SCORING_MODEL.md)
- [Pressure situations](docs/PRESSURE_SITUATIONS.md)
- [CSV output guide](docs/OUTPUT_FILE_GUIDE.md)
- [Ranking snapshot](docs/RANKING_SUMMARY.md)
- [Validation report](docs/VALIDATION_REPORT.md)
- [Beginner guide](docs/BEGINNER_GUIDE.md)
- [Deployment guide](docs/DEPLOYMENT.md)

Strict exact context is the conservative primary view. Proxy-inclusive outputs are sensitivity analysis and may contain lower-bound estimates. Review the evidence labels and confidence intervals alongside any ranking.

