#!/usr/bin/env bash
# Beendet Backend und Oberfläche, die start.sh gestartet hat.
set -uo pipefail
WURZEL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WURZEL"
[ -f .env ] && { set -a; . ./.env; set +a; }

beende_port() {  # beendet, was noch auf dem Port lauscht (auch Kindprozesse von uv und npm)
  local pids
  pids="$(lsof -nP -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null || true)"
  [ -n "$pids" ] && kill $pids 2>/dev/null
}

for teil in backend frontend; do
  datei=".run/$teil.pid"
  if [ -f "$datei" ]; then
    kill "$(cat "$datei")" 2>/dev/null && echo "$teil beendet"
    rm -f "$datei"
  fi
done
beende_port "${FAEHRE_BACKEND_PORT:-8490}"
beende_port "${FAEHRE_FRONTEND_PORT:-5490}"
exit 0
