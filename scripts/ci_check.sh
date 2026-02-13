#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

log() { echo "[check] $*"; }

log "python: $(python -V)"

log "compileall app/"
python -m compileall -q app

log "pip check"
python -m pip check

log "import smoke"
python - <<'PY'
import app
import app.main
print("imports ok")
PY

log "OK"
