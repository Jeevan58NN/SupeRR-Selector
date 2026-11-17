FROM node:22-alpine AS ui
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS app
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY config/ ./config/
COPY docs/ ./docs/
COPY data/ ./data/
COPY matches.csv competitions.csv teams.csv playing_eleven.csv competition_team_player_mapping.csv ./
COPY --from=ui /app/frontend/dist ./frontend/dist
ENV PYTHONPATH=/app/src SUPERR_ROOT=/app PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)" || exit 1
CMD ["uvicorn","superr_selector.api.app:app","--host","0.0.0.0","--port","8000"]
