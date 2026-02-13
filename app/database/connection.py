"""Asyncpg pool and schema bootstrap helpers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg


class Database:
    """Thin asyncpg wrapper used across repositories."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return self._pool

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=10)

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def init_schema(self) -> None:
        """Create tables and perform lightweight migrations."""

        schema_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            pin_hash TEXT NOT NULL,
            access_status TEXT NOT NULL DEFAULT 'pending',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS wireguard_configs (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            telegram_id BIGINT,
            private_key TEXT NOT NULL,
            public_key TEXT NOT NULL,
            preshared_key TEXT NOT NULL,
            ip_address INET NOT NULL,
            config_text TEXT NOT NULL,
            mikrotik_peer_id TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            plan_name TEXT NOT NULL DEFAULT 'basic',
            starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            auto_renew BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS logs (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            event_type TEXT NOT NULL,
            details JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """

        alter_sql = """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS access_status TEXT NOT NULL DEFAULT 'pending';
        ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS mikrotik_peer_id TEXT;
        ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS telegram_id BIGINT;

        UPDATE wireguard_configs cfg
        SET telegram_id = u.telegram_id
        FROM users u
        WHERE cfg.user_id = u.id AND cfg.telegram_id IS NULL;

        WITH ranked_active AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY ip_address ORDER BY created_at DESC, id DESC) AS row_num
            FROM wireguard_configs
            WHERE is_active
        )
        UPDATE wireguard_configs AS cfg
        SET is_active = FALSE
        FROM ranked_active AS ra
        WHERE cfg.id = ra.id
          AND ra.row_num > 1;

        WITH ranked_user AS (
            SELECT id, user_id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC, id DESC) AS row_num
            FROM wireguard_configs
            WHERE is_active
        )
        UPDATE wireguard_configs AS cfg
        SET is_active = FALSE
        FROM ranked_user AS ru
        WHERE cfg.id = ru.id
          AND ru.row_num > 1;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_wireguard_configs_ip_active
            ON wireguard_configs (ip_address)
            WHERE is_active;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_wireguard_configs_user_active
            ON wireguard_configs (user_id)
            WHERE is_active;
        """

        async with self.pool.acquire() as conn:
            await conn.execute(schema_sql)
            await conn.execute(alter_sql)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        """Yield pooled connection."""

        async with self.pool.acquire() as connection:
            yield connection
