"""Repository for users table."""

from dataclasses import dataclass

import asyncpg


@dataclass(slots=True)
class User:
    id: int
    telegram_id: int
    username: str | None
    full_name: str | None
    role: str
    pin_hash: str
    pin_verified: bool
    is_active: bool
    access_status: str


class UsersRepository:
    """Data access methods for users."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        query = """
        SELECT id, telegram_id, username, full_name, role, pin_hash, pin_verified, is_active, access_status
        FROM users
        WHERE telegram_id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, telegram_id)
        if row is None:
            return None
        return User(**dict(row))

    async def create(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
        role: str,
        pin_hash: str,
        access_status: str,
        pin_verified: bool = False,
    ) -> User:
        query = """
        INSERT INTO users (telegram_id, username, full_name, role, pin_hash, pin_verified, access_status)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, telegram_id, username, full_name, role, pin_hash, pin_verified, is_active, access_status
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, telegram_id, username, full_name, role, pin_hash, pin_verified, access_status)
        return User(**dict(row))

    async def mark_pin_verified(self, telegram_id: int, verified: bool = True) -> None:
        query = "UPDATE users SET pin_verified = $2, updated_at = NOW(), last_seen = NOW() WHERE telegram_id = $1"
        async with self._pool.acquire() as conn:
            await conn.execute(query, telegram_id, verified)

    async def touch_last_seen(self, telegram_id: int) -> None:
        query = "UPDATE users SET last_seen = NOW(), updated_at = NOW() WHERE telegram_id = $1"
        async with self._pool.acquire() as conn:
            await conn.execute(query, telegram_id)

    async def set_role(self, telegram_id: int, role: str) -> None:
        query = "UPDATE users SET role = $2, updated_at = NOW() WHERE telegram_id = $1"
        async with self._pool.acquire() as conn:
            await conn.execute(query, telegram_id, role)

    async def set_access_status(self, telegram_id: int, access_status: str) -> None:
        query = "UPDATE users SET access_status = $2, updated_at = NOW() WHERE telegram_id = $1"
        async with self._pool.acquire() as conn:
            await conn.execute(query, telegram_id, access_status)

    async def list_pending(self) -> list[asyncpg.Record]:
        query = """
        SELECT telegram_id, username, full_name, created_at
        FROM users
        WHERE access_status = 'pending'
        ORDER BY created_at DESC
        """
        async with self._pool.acquire() as conn:
            return await conn.fetch(query)
