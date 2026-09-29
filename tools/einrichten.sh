#!/usr/bin/env bash
# Richtet Fähre auf einem Mac ein - auch auf einem frisch installierten.
# Jeder Schritt prüft zuerst, ob er schon erledigt ist, und überspringt sich dann.
# Das Skript lässt sich deshalb beliebig oft ausführen.
#
#   1. Homebrew (Paketverwaltung)
#   2. adb (android-platform-tools), uv (Python), Node.js
#   3. Python-Umgebung des Backends
#   4. Pakete der Oberfläche
#   5. .env mit freien Ports
#   6. Git-Haken für die Versionierung
#   7. Prüfung, ob ein Telefon erreichbar ist
set -euo pipefail

WURZEL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WURZEL"

schritt() { printf "\n\033[1m[%s] %s\033[0m\n" "$1" "$2"; }
ok() { printf "   \033[32mok\033[0m  %s\n" "$1"; }
hinweis() { printf "   \033[33m!\033[0m   %s\n" "$1"; }

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Fähre ist für macOS gebaut. Abbruch."
  exit 1
fi

# --- 1. Homebrew --------------------------------------------------------------
schritt 1/7 "Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  for kandidat in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -x "$kandidat" ] && eval "$("$kandidat" shellenv)"
  done
fi
if command -v brew >/dev/null 2>&1; then
  ok "vorhanden ($(brew --version | head -1))"
else
  hinweis "nicht gefunden - wird installiert (fragt nach dem Mac-Passwort)"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
  ok "installiert"
fi

# --- 2. Werkzeuge -------------------------------------------------------------
schritt 2/7 "Werkzeuge: adb, uv, Node.js"
installiere_formel() {  # installiere_formel <befehl> <formel>
  if command -v "$1" >/dev/null 2>&1; then
    ok "$1 vorhanden"
  else
    brew install "$2"
    ok "$1 installiert"
  fi
}
if command -v adb >/dev/null 2>&1; then
  ok "adb vorhanden ($(adb version | sed -n 2p))"
else
  brew install --cask android-platform-tools
  ok "adb installiert"
fi
installiere_formel uv uv
installiere_formel node node

# --- 3. Backend ---------------------------------------------------------------
schritt 3/7 "Python-Umgebung des Backends"
(cd backend && uv sync --quiet)
ok "backend/.venv ist aktuell"

# --- 4. Oberfläche ------------------------------------------------------------
schritt 4/7 "Pakete der Oberfläche"
(cd frontend && npm install --no-audit --no-fund --silent)
ok "frontend/node_modules ist aktuell"

# --- 5. Umgebung --------------------------------------------------------------
schritt 5/7 ".env mit freien Ports"
port_belegt() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
freier_port() { local p="$1"; while port_belegt "$p"; do p=$((p + 1)); done; echo "$p"; }
if [ -f .env ]; then
  ok ".env vorhanden - bleibt unverändert (zum Neuerzeugen löschen)"
else
  cat > .env <<EOF
# Erzeugt von tools/einrichten.sh - nicht einchecken.
FAEHRE_BACKEND_PORT=$(freier_port 8490)
FAEHRE_FRONTEND_PORT=$(freier_port 5490)
EOF
  ok ".env angelegt"
fi

# --- 6. Git-Haken -------------------------------------------------------------
schritt 6/7 "Git-Haken für die Versionierung"
if [ -d .git ]; then
  git config core.hooksPath tools/git-hooks
  ok "Versionszwang vor jedem Commit aktiv"
else
  hinweis "kein Git-Archiv - übersprungen"
fi

# --- 7. Telefon ---------------------------------------------------------------
schritt 7/7 "Telefon"
adb start-server >/dev/null 2>&1 || true
geraete="$(adb devices | sed 1d | grep -v '^$' || true)"
if echo "$geraete" | grep -q "device$"; then
  ok "Telefon bereit: $(echo "$geraete" | grep "device$" | awk '{print $1}' | paste -sd ' ' -)"
elif echo "$geraete" | grep -q "unauthorized"; then
  hinweis "Telefon wartet auf Freigabe: am Telefon \"USB-Debugging zulassen\" bestätigen."
else
  hinweis "kein Telefon gefunden. Am Telefon einmalig einrichten:"
  hinweis "  Einstellungen > Über das Telefon > 7-mal auf \"Build-Nummer\" tippen"
  hinweis "  Einstellungen > System > Entwickleroptionen > \"USB-Debugging\" einschalten"
  hinweis "  Kabel direkt am Mac anstecken und die Abfrage am Telefon bestätigen"
fi

printf "\nFertig. Starten mit ./start.sh\n"
