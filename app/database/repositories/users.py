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
    is_active: bool


class UsersRepository:
    """Data access methods for users."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        query = """
        SELECT id, telegram_id, username, full_name, role, pin_hash, is_active
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
    ) -> User:
        query = """
        INSERT INTO users (telegram_id, username, full_name, role, pin_hash)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, telegram_id, username, full_name, role, pin_hash, is_active
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, telegram_id, username, full_name, role, pin_hash)
        return User(**dict(row))
