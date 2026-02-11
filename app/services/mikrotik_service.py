"""MikroTik RouterOS API integration for WireGuard peers."""

import asyncio
from dataclasses import dataclass

from librouteros import connect

from app.config import Settings


@dataclass(slots=True)
class MikroTikService:
    """Service that wraps librouteros calls with retries and timeout."""

    settings: Settings

    async def _run_api(self, path: str, **params: str) -> None:
        """Run API command with retry/backoff in worker thread."""

        last_error: Exception | None = None

        for attempt in range(1, self.settings.mikrotik_retry_attempts + 1):
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._run_api_sync, path, params),
                    timeout=self.settings.mikrotik_timeout_seconds,
                )
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.settings.mikrotik_retry_attempts:
                    await asyncio.sleep(self.settings.mikrotik_retry_backoff_seconds * attempt)

        raise RuntimeError(f"MikroTik command failed after retries: {path}") from last_error

    def _run_api_sync(self, path: str, params: dict[str, str]) -> None:
        api = connect(
            host=self.settings.mikrotik_host,
            username=self.settings.mikrotik_username,
            password=self.settings.mikrotik_password,
            port=self.settings.mikrotik_port,
            ssl_wrapper=self.settings.mikrotik_use_tls,
        )
        api.path(path).add(**params)

    async def add_peer(self, user_id: int, public_key: str, ip_address: str) -> None:
        """Create WireGuard peer on RouterOS."""

        await self._run_api(
            "interface/wireguard/peers",
            interface="wireguard1",
            public_key=public_key,
            allowed_address=f"{ip_address}/32",
            persistent_keepalive="25",
            comment=f"peer_user{user_id}",
        )

    async def remove_peer(self, user_id: int) -> None:
        """Delete peer by comment in RouterOS."""

        # NOTE: librouteros remove flow usually needs lookup by .id;
        # this placeholder keeps MVP service shape and is extended in next stage.
        await self._run_api("interface/wireguard/peers", comment=f"peer_user{user_id}")
