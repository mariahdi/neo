#!/usr/bin/env bash
# Launch the Neo reviewer web app for a demo.
#
#   ./run-reviewer.sh            # start on http://127.0.0.1:8000
#   ./run-reviewer.sh 8001       # start on a different port
#
# Frees the port first if a previous run is still holding it, so you never
# hit "Address already in use". With no NEO_* credentials set, the app runs
# in demo mode (sample data). Set the keys to go live. Ctrl+C to stop.

set -euo pipefail
cd "$(dirname "$0")"

PORT="${1:-8000}"

# Free the port if something is still listening (e.g. a crashed reloader).
if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is in use — stopping the old server..."
  lsof -tiTCP:"$PORT" -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
  sleep 1
fi

echo "Starting Neo reviewer on http://127.0.0.1:$PORT"
echo "Open that address in your browser. Press Ctrl+C to stop."
exec uvicorn reviewer.main:app --port "$PORT"
