"""Service layer for MikroTik RouterOS integration."""

from dataclasses import dataclass

from app.config import Settings
from app.integrations import MikroTikClient, MikroTikClientError


@dataclass(slots=True)
class MikroTikService:
    """Service facade around MikroTik client initialized from app settings."""

    settings: Settings

    def __post_init__(self) -> None:
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
        )

    async def ensure_wireguard_peer(
        self,
        telegram_id: int,
        config_id: int,
        public_key: str,
        ip_address: str,
        preshared_key: str | None,
    ) -> bool:
        """Ensure peer exists and return True when created, False when already present."""

        peer_name = f"peer-{config_id}"
        comment = f"tg:{telegram_id} cfg:{config_id}"
        return await self._client.add_wireguard_peer(
            interface=self.settings.wg_interface_name,
            name=peer_name,
            public_key=public_key,
            allowed_address=f"{ip_address}/32",
            preshared_key=preshared_key,
            comment=comment,
        )

    async def remove_wireguard_peer(self, peer_id: str) -> None:
        """Delete peer by RouterOS internal ID."""

        await self._client.remove_wireguard_peer(peer_id)


__all__ = ["MikroTikService", "MikroTikClientError"]
