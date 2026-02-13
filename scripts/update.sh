#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="wg-avto-bot"
ENV_FILE="$APP_DIR/.env"
BACKUP="/root/wg_avto_bot_env_backup_$(date +%F_%H%M%S).env"

cd "$APP_DIR"

log() { echo "[update] $*"; }

if ! command -v python3.11 >/dev/null 2>&1; then
  log "ERROR: python3.11 not found. Install: apt install -y python3.11 python3.11-venv python3.11-dev"
  exit 2
fi
PYTHON_BIN="python3.11"

if [[ -f "$ENV_FILE" ]]; then
  cp "$ENV_FILE" "$BACKUP"
  log ".env backup: $BACKUP"
fi

PREV_COMMIT="$(git rev-parse HEAD)"
log "previous commit: $PREV_COMMIT"

rollback() {
  local code="${1:-1}"
  log "rollback to $PREV_COMMIT ..."
  git reset --hard "$PREV_COMMIT" || true

  if [[ ! -f "$ENV_FILE" && -f "$BACKUP" ]]; then
    cp "$BACKUP" "$ENV_FILE"
    log ".env restored from backup"
  fi

  if [[ -d ".venv" ]]; then
    rm -rf .venv
  fi
  "$PYTHON_BIN" -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install -U pip setuptools wheel
  pip install -e .

  sudo systemctl restart "$SERVICE" || true
  sudo systemctl --no-pager status "$SERVICE" -n 50 || true
  exit "$code"
}

trap 'rollback 1' ERR

log "pulling..."
git fetch origin
git reset --hard origin/main
log "updated to: $(git rev-parse HEAD)"

if [[ ! -f "$ENV_FILE" && -f "$BACKUP" ]]; then
  cp "$BACKUP" "$ENV_FILE"
  log ".env restored from backup"
fi

NEED_VENV_RECREATE=0
if [[ -x ".venv/bin/python" ]]; then
  VENV_VER="$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  [[ "$VENV_VER" != "3.11" ]] && NEED_VENV_RECREATE=1
else
  NEED_VENV_RECREATE=1
fi

if [[ "$NEED_VENV_RECREATE" -eq 1 ]]; then
  log "venv python: recreating .venv with $($PYTHON_BIN -V)"
  rm -rf .venv
  "$PYTHON_BIN" -m venv .venv
else
  log "venv python: $(.venv/bin/python -V)"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

log "installing deps..."
python -m pip install -U pip setuptools wheel
pip install -e .

log "running checks..."
./scripts/ci_check.sh

log "db init/migration..."
python - <<'PY'
import asyncio
from app.config import get_settings
from app.database.connection import Database

async def main():
    s = get_settings()
    db = Database(s.database_dsn)
    await db.connect()
    await db.init_schema()
    await db.disconnect()

asyncio.run(main())
print('db migration ok')
PY

log "restarting service..."
sudo systemctl restart "$SERVICE"

if ! sudo systemctl is-active --quiet "$SERVICE"; then
  log "service is NOT active, dumping logs"
  sudo journalctl -u "$SERVICE" -n 80 --no-pager || true
  exit 3
fi

sudo systemctl --no-pager status "$SERVICE" -n 30

log "redis check/import check..."
python - <<'PY'
import asyncio

from app.config import get_settings
from redis.asyncio import Redis

async def main():
    s = get_settings()
    r = Redis.from_url(s.redis_dsn)
    pong = await r.ping()
    await r.aclose()
    print('redis ok', pong)

asyncio.run(main())
print('import ok')
PY

trap - ERR
log "DONE"
