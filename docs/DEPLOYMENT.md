# Deployment notes

The local application uses a read-only API over precomputed CSV outputs. Production should package the backend and built frontend together or serve the Vite build via a reverse proxy. Set `SUPERR_ROOT` to the data/project root or mount precomputed `data/outputs`, `data/processed`, `data/interim`, and the required match/ball source files read-only. Do not publish raw source CSVs as static assets. Set trusted origins and HTTPS at the hosting proxy before public release.

## Container build

Run the pipeline before building the deployment image so the versioned outputs exist. Build with `docker build -t superr-selector .`, then run with `docker run --rm -p 8000:8000 -e SUPERR_ROOT=/app -v <read-only-data-folder>:/app/data:ro superr-selector`. Confirm `/api/health` reports `data_ready: true`. Deployment credentials and a public host are not configured in this repository; no public URL is claimed.
