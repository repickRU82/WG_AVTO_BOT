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

    async def get_active_for_user(self, user_id: int) -> asyncpg.Record | None:
        query = """
        SELECT id, user_id, telegram_id, private_key, public_key, preshared_key, host(ip_address) AS ip_address,
               config_text, mikrotik_peer_id, is_active, created_at
        FROM wireguard_configs
        WHERE user_id = $1 AND is_active
        ORDER BY created_at DESC
        LIMIT 1
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, user_id)

    async def allocate_and_create(
        self,
        user_id: int,
        telegram_id: int,
        network_cidr: str,
        profile_builder: Callable[[str], tuple[str, str, str, str]],
        *,
        retries: int = 5,
    ) -> tuple[int, str, str, str, str]:
        """Allocate IP and persist active config for user."""

        for _ in range(retries):
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("LOCK TABLE wireguard_configs IN SHARE ROW EXCLUSIVE MODE")
                    existing = await conn.fetchrow(
                        "SELECT id, host(ip_address) AS ip_address, config_text, public_key, preshared_key "
                        "FROM wireguard_configs WHERE user_id = $1 AND is_active",
                        user_id,
                    )
                    if existing:
                        return (
                            int(existing["id"]),
                            str(existing["ip_address"]),
                            str(existing["config_text"]),
                            str(existing["public_key"]),
                            str(existing["preshared_key"]),
                        )

                    rows = await conn.fetch("SELECT host(ip_address) AS ip FROM wireguard_configs WHERE is_active")
                    used_ips = {row["ip"] for row in rows}
                    ip_address = allocate_next_ip(network_cidr, used_ips)
                    private_key, public_key, preshared_key, config_text = profile_builder(ip_address)

                    try:
                        row = await conn.fetchrow(
                            """
                            INSERT INTO wireguard_configs
                                (user_id, telegram_id, private_key, public_key, preshared_key, ip_address, config_text, is_active)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE)
                            RETURNING id
                            """,
                            user_id,
                            telegram_id,
                            private_key,
                            public_key,
                            preshared_key,
                            ip_address,
                            config_text,
                        )
                    except asyncpg.UniqueViolationError:
                        continue

                    return int(row["id"]), ip_address, config_text, public_key, preshared_key

        raise DuplicateIPAddressError("Failed to allocate unique WireGuard IP after retries")

    async def reissue_for_user(
        self,
        user_id: int,
        telegram_id: int,
        profile_builder: Callable[[str], tuple[str, str, str, str]],
    ) -> tuple[int, str, str, str, str, str | None]:
        """Reissue config preserving current IP and peer binding."""

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                current = await conn.fetchrow(
                    "SELECT id, host(ip_address) AS ip_address, mikrotik_peer_id FROM wireguard_configs WHERE user_id = $1 AND is_active",
                    user_id,
                )
                if current is None:
                    raise RuntimeError("Active config not found")

                ip_address = str(current["ip_address"])
                old_peer_id = current["mikrotik_peer_id"]
                private_key, public_key, preshared_key, config_text = profile_builder(ip_address)

                await conn.execute("UPDATE wireguard_configs SET is_active = FALSE WHERE user_id = $1 AND is_active", user_id)
                row = await conn.fetchrow(
                    """
                    INSERT INTO wireguard_configs
                        (user_id, telegram_id, private_key, public_key, preshared_key, ip_address, config_text, mikrotik_peer_id, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE)
                    RETURNING id
                    """,
                    user_id,
                    telegram_id,
                    private_key,
                    public_key,
                    preshared_key,
                    ip_address,
                    config_text,
                    old_peer_id,
                )
                return int(row["id"]), ip_address, config_text, public_key, preshared_key, old_peer_id

    async def attach_mikrotik_peer(self, config_id: int, peer_id: str | None) -> None:
        query = "UPDATE wireguard_configs SET mikrotik_peer_id = $2 WHERE id = $1"
        async with self._pool.acquire() as conn:
            await conn.execute(query, config_id, peer_id)

    async def list_for_user(self, user_id: int) -> list[asyncpg.Record]:
        query = """
        SELECT id, host(ip_address) AS ip_address, is_active, created_at
        FROM wireguard_configs
        WHERE user_id = $1
        ORDER BY created_at DESC
        """
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, user_id)
