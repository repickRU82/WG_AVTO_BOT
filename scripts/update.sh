#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/WG_AVTO_BOT"
SERVICE="wg-avto-bot"
ENV_FILE="$APP_DIR/.env"
BACKUP="/root/wg_avto_bot_env_backup_$(date +%F_%H%M%S).env"

cd "$APP_DIR"

if [[ -f "$ENV_FILE" ]]; then
  cp "$ENV_FILE" "$BACKUP"
  echo "[update] .env backup: $BACKUP"
fi

git fetch origin
git reset --hard origin/main

if [[ ! -f "$ENV_FILE" && -f "$BACKUP" ]]; then
  cp "$BACKUP" "$ENV_FILE"
  echo "[update] .env restored from backup"
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e .

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

sudo systemctl restart "$SERVICE"
sudo systemctl --no-pager status "$SERVICE" -n 50

python - <<'PY'
from app.config import get_settings
from redis.asyncio import Redis
import asyncio

async def main():
    s = get_settings()
    r = Redis.from_url(s.redis_dsn)
    pong = await r.ping()
    await r.close()
    print('redis ok', pong)

asyncio.run(main())
print('import ok')
PY
