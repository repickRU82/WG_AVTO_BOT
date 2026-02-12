"""Service layer for MikroTik RouterOS integration."""

from dataclasses import dataclass, field
from typing import Any

import structlog

from app.config import Settings
from app.integrations import MikroTikClient, MikroTikClientError


@dataclass(slots=True)
class MikroTikService:
    """Service facade around MikroTik client initialized from app settings."""

    settings: Settings
    _client: MikroTikClient = field(init=False, repr=False)
    _logger: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = structlog.get_logger(__name__)
        self._client = MikroTikClient(
            host=self.settings.mikrotik_host,
            port=self.settings.mikrotik_port,
            username=self.settings.mikrotik_username,
            password=self.settings.mikrotik_password,
            use_tls=self.settings.mikrotik_use_tls,
            timeout_seconds=self.settings.mikrotik_timeout_seconds,
            retry_attempts=self.settings.mikrotik_retry_attempts,
            retry_backoff_seconds=self.settings.mikrotik_retry_backoff_seconds,
            tls_insecure=self.settings.mikrotik_tls_insecure,
            dry_run=self.settings.mikrotik_dry_run,
        )

    async def ensure_wireguard_peer(
        self,
        telegram_id: int,
        config_id: int,
        public_key: str,
        ip_address: str,
        preshared_key: str | None,
    ) -> tuple[str, str | None]:
        peer_name = f"tg-{telegram_id}"
        comment = f"tg:{telegram_id}:vpn"
        """Ensure peer exists and return action + peer id."""

        peer_name = f"peer-{config_id}"
        comment = f"tg:{telegram_id}:profile:{config_id}"
        return await self._client.add_wireguard_peer(
            interface=self.settings.wg_interface_name,
            name=peer_name,
            public_key=public_key,
            allowed_address=f"{ip_address}/32",
            preshared_key=preshared_key,
            comment=comment,
        )

    async def test_connection(self) -> tuple[str, int]:
        identity = await self._client.ping()
        peers = await self._client.list_wireguard_peers(self.settings.wg_interface_name)
        return identity, len(peers)

    async def remove_wireguard_peer(self, peer_id: str) -> None:

    async def test_connection(self) -> tuple[str, int]:
        """Return identity and peers count for diagnostics."""

        identity = await self._client.ping()
        peers = await self._client.list_wireguard_peers(self.settings.wg_interface_name)
        return identity, len(peers)

    async def remove_wireguard_peer(self, peer_id: str) -> None:
        """Delete peer by RouterOS internal ID."""

        await self._client.remove_wireguard_peer(peer_id)


__all__ = ["MikroTikService", "MikroTikClientError"]
