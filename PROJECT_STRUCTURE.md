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
│  │     ├─ __init__.py
│  │     ├─ users.py
│  │     ├─ logs.py
│  │     └─ wireguard_configs.py
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
│     ├─ session.py
│     ├─ logger.py
│     └─ ip_pool.py
├─ docker/
│  └─ bot/
│     └─ Dockerfile
├─ examples/
│  └─ wg_generation_example.py
├─ .env.example
├─ docker-compose.yml
├─ pyproject.toml
└─ PROJECT_STRUCTURE.md
```

## Notes
- `app/main.py` wires aiogram Dispatcher, database, Redis session manager and repositories/services.
- `database/migrations/` is reserved for SQL migration files (or Alembic in future stages).
- `handlers/` contains command routers for `/start`, `/login`, `/menu`, `/new_connection`, `/my_connections`.
- `examples/wg_generation_example.py` demonstrates WireGuard key generation and config rendering.
