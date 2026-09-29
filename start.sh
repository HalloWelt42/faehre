#!/usr/bin/env bash
# Startet Backend und Oberfläche im Hintergrund und öffnet den Browser.
# PIDs und Protokolle liegen unter .run/. Beenden mit ./stop.sh
set -uo pipefail
WURZEL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WURZEL"

LAUF="$WURZEL/.run"
mkdir -p "$LAUF"

if [ ! -f .env ] || [ ! -d backend/.venv ] || [ ! -d frontend/node_modules ]; then
  echo "Erster Start - Einrichtung läuft ..."
  bash tools/einrichten.sh || exit 1
fi
set -a
. ./.env
set +a
BACKEND_PORT="${FAEHRE_BACKEND_PORT:-8490}"
FRONTEND_PORT="${FAEHRE_FRONTEND_PORT:-5490}"

warte() {  # warte <name> <adresse>
  printf "   warte auf %s " "$1"
  for _ in $(seq 1 60); do
    if curl -fsS -o /dev/null "$2" 2>/dev/null; then echo " bereit."; return 0; fi
    printf "."; sleep 1
  done
  echo " Zeitüberschreitung - siehe .run/*.log"; return 1
}

bash "$WURZEL/stop.sh" >/dev/null 2>&1
adb start-server >/dev/null 2>&1 || true

echo "== Fähre startet =="
echo "[1/2] Backend (Port $BACKEND_PORT)"
( cd backend && nohup uv run uvicorn faehre.main:app --app-dir src --host 127.0.0.1 --port "$BACKEND_PORT" \
    >"$LAUF/backend.log" 2>&1 & echo $! >"$LAUF/backend.pid" )
warte "Backend" "http://127.0.0.1:$BACKEND_PORT/api/status"

echo "[2/2] Oberfläche (Port $FRONTEND_PORT)"
( cd frontend && nohup npm run dev -- --port "$FRONTEND_PORT" --strictPort \
    >"$LAUF/frontend.log" 2>&1 & echo $! >"$LAUF/frontend.pid" )
warte "Oberfläche" "http://localhost:$FRONTEND_PORT/"

echo "Fähre läuft: http://localhost:$FRONTEND_PORT"
open "http://localhost:$FRONTEND_PORT" 2>/dev/null || true
