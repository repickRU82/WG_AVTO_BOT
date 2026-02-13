"""Repository for structured security/audit logs."""

import json

import asyncpg


class LogsRepository:
    """Data access methods for logs table."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add(self, event_type: str, details: dict, user_id: int | None = None) -> None:
        payload = json.dumps(details, ensure_ascii=False)

        query = """
        INSERT INTO logs (user_id, event_type, details)
        VALUES ($1, $2, $3::jsonb)
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, user_id, event_type, payload)
