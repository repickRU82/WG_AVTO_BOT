"""Repository for wireguard_configs table."""

import asyncpg


class WireGuardConfigsRepository:
    """Data access for generated client configs."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def used_ips(self) -> set[str]:
        query = "SELECT host(ip_address) AS ip FROM wireguard_configs"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
        return {row["ip"] for row in rows}

    async def create(
        self,
        user_id: int,
        private_key: str,
        public_key: str,
        preshared_key: str,
        ip_address: str,
        config_text: str,
    ) -> int:
        query = """
        INSERT INTO wireguard_configs (user_id, private_key, public_key, preshared_key, ip_address, config_text)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                user_id,
                private_key,
                public_key,
                preshared_key,
                ip_address,
                config_text,
            )
        return int(row["id"])

    async def list_for_user(self, user_id: int) -> list[asyncpg.Record]:
        query = """
        SELECT id, ip_address, is_active, created_at
        FROM wireguard_configs
        WHERE user_id = $1
        ORDER BY created_at DESC
        """
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, user_id)
