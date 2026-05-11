#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8003}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-3003}"
DOCKER_BIN="${DOCKER_BIN:-$(command -v docker || true)}"

if [ -z "$DOCKER_BIN" ] && [ -x "/Applications/Docker.app/Contents/Resources/bin/docker" ]; then
  DOCKER_BIN="/Applications/Docker.app/Contents/Resources/bin/docker"
fi

if [ -z "$DOCKER_BIN" ]; then
  echo "Docker CLI not found. Install Docker or set DOCKER_BIN."
  exit 1
fi
export PATH="$(dirname "$DOCKER_BIN"):$PATH"

mkdir -p logs
touch logs/backend.log logs/frontend.log

"$DOCKER_BIN" compose -f docker-compose.observability.yml up -d

export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export OBSERVABILITY_JSON_LOGS="${OBSERVABILITY_JSON_LOGS:-true}"
export OBSERVABILITY_TRACING_ENABLED="${OBSERVABILITY_TRACING_ENABLED:-true}"
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="${OTEL_EXPORTER_OTLP_TRACES_ENDPOINT:-http://localhost:4319/v1/traces}"
export OBSERVABILITY_PROMETHEUS_URL="${OBSERVABILITY_PROMETHEUS_URL:-http://localhost:9091}"
export OBSERVABILITY_LOKI_URL="${OBSERVABILITY_LOKI_URL:-http://localhost:3100}"

uv sync --group dev

uv run python -m uvicorn backend.app.main:app \
  --reload \
  --reload-dir backend/app \
  --host "$BACKEND_HOST" \
  --port "$BACKEND_PORT" \
  > logs/backend.log 2>&1 &
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  npm install
fi
HOST="$FRONTEND_HOST" PORT="$FRONTEND_PORT" npm start > "$ROOT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$ROOT_DIR"

echo "Observability stack: http://localhost:3004"
echo "Prometheus: http://localhost:9091"
echo "Loki: http://localhost:3100"
echo "Tempo: http://localhost:3200"
echo "Backend: http://localhost:${BACKEND_PORT}"
echo "Frontend: http://localhost:${FRONTEND_PORT}"
echo "Logs: logs/backend.log and logs/frontend.log"
echo "Press Ctrl+C to stop app processes."

stop_app() {
  echo "Stopping app processes..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  if [ "${STOP_OBSERVABILITY_ON_EXIT:-false}" = "true" ]; then
    "$DOCKER_BIN" compose -f docker-compose.observability.yml down
  fi
}

trap stop_app INT TERM EXIT
wait
