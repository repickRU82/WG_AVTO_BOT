# MVP Project Structure (Stage 1)

```text
WG_AVTO_BOT/
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ config.py
│  ├─ database/
│  │  ├─ __init__.py
│  │  ├─ connection.py
│  │  ├─ migrations/
│  │  └─ repositories/
│  ├─ handlers/
│  │  ├─ __init__.py
│  │  ├─ start.py
│  │  ├─ auth.py
│  │  ├─ menu.py
│  │  └─ connections.py
│  ├─ services/
│  │  ├─ __init__.py
│  │  ├─ auth_service.py
│  │  ├─ wireguard_service.py
│  │  └─ mikrotik_service.py
│  └─ utils/
│     ├─ __init__.py
│     ├─ security.py
│     ├─ logger.py
│     └─ ip_pool.py
├─ docker/
│  └─ bot/
│     └─ Dockerfile
├─ scripts/
│  ├─ run_bot.sh
│  └─ wait_for_postgres.sh
├─ .env.example
├─ docker-compose.yml
├─ pyproject.toml
└─ README.md
```

## Notes
- `app/` is the runtime package for bot logic.
- `database/migrations/` is reserved for SQL migration files (or Alembic in future stages).
- `repositories/` will contain typed asyncpg access layer.
- `docker/bot/Dockerfile` is planned for bot container image in next block.
