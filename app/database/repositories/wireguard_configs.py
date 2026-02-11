"""Repository for wireguard_configs table."""

from collections.abc import Callable

import asyncpg

from app.utils.ip_pool import allocate_next_ip


class DuplicateIPAddressError(Exception):
    """Raised when IP allocation conflicts with another concurrent request."""


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

    async def allocate_and_create(
        self,
        user_id: int,
        network_cidr: str,
        profile_builder: Callable[[str], tuple[str, str, str, str]],
        *,
        retries: int = 5,
    ) -> tuple[int, str, str]:
        """Allocate IP and persist config with DB lock + retry for concurrent requests."""

        for _ in range(retries):
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("LOCK TABLE wireguard_configs IN SHARE ROW EXCLUSIVE MODE")
                    rows = await conn.fetch(
                        "SELECT host(ip_address) AS ip FROM wireguard_configs WHERE is_active"
                    )
                    used_ips = {row["ip"] for row in rows}
                    ip_address = allocate_next_ip(network_cidr, used_ips)
                    private_key, public_key, preshared_key, config_text = profile_builder(ip_address)

                    try:
                        row = await conn.fetchrow(
                            """
                            INSERT INTO wireguard_configs
                                (user_id, private_key, public_key, preshared_key, ip_address, config_text)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            RETURNING id
                            """,
                            user_id,
                            private_key,
                            public_key,
                            preshared_key,
                            ip_address,
                            config_text,
                        )
                    except asyncpg.UniqueViolationError:
                        continue

                    return int(row["id"]), ip_address, config_text

        raise DuplicateIPAddressError("Failed to allocate unique WireGuard IP after retries")

    async def list_for_user(self, user_id: int) -> list[asyncpg.Record]:
        query = """
        SELECT id, ip_address, is_active, created_at
        FROM wireguard_configs
        WHERE user_id = $1
        ORDER BY created_at DESC
        """
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, user_id)
