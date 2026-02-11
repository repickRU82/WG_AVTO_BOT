"""MikroTik RouterOS API integration for WireGuard peers."""

import asyncio
from dataclasses import dataclass
from typing import Any

from librouteros import connect

from app.config import Settings


@dataclass(slots=True)
class MikroTikService:
    """Service that wraps librouteros calls with retries and timeout."""

    settings: Settings

    async def _run_api(self, operation: str, **params: str) -> Any:
        """Run API command with retry/backoff in worker thread."""

        last_error: Exception | None = None

        for attempt in range(1, self.settings.mikrotik_retry_attempts + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._run_api_sync, operation, params),
                    timeout=self.settings.mikrotik_timeout_seconds,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.settings.mikrotik_retry_attempts:
                    await asyncio.sleep(self.settings.mikrotik_retry_backoff_seconds * attempt)

        raise RuntimeError(f"MikroTik operation failed after retries: {operation}") from last_error

    def _connect(self):
        return connect(
            host=self.settings.mikrotik_host,
            username=self.settings.mikrotik_username,
            password=self.settings.mikrotik_password,
            port=self.settings.mikrotik_port,
            ssl_wrapper=self.settings.mikrotik_use_tls,
        )

    def _run_api_sync(self, operation: str, params: dict[str, str]) -> Any:
        api = self._connect()
        peers_path = api.path("interface/wireguard/peers")

        if operation == "add_peer":
            peers_path.add(**params)
            return None

        if operation == "remove_peer":
            comment = params["comment"]
            peer_ids = [item[".id"] for item in peers_path.select(".id", "comment") if item.get("comment") == comment]
            for peer_id in peer_ids:
                peers_path.remove(**{".id": peer_id})
            return len(peer_ids)

        raise ValueError(f"Unsupported MikroTik operation: {operation}")

    async def add_peer(self, user_id: int, public_key: str, ip_address: str) -> None:
        """Create WireGuard peer on RouterOS."""

        await self._run_api(
            "add_peer",
            interface="wireguard1",
            public_key=public_key,
            allowed_address=f"{ip_address}/32",
            persistent_keepalive="25",
            comment=f"peer_user{user_id}",
        )

    async def remove_peer(self, user_id: int) -> int:
        """Delete peer by comment in RouterOS and return number of removed records."""

        removed = await self._run_api("remove_peer", comment=f"peer_user{user_id}")
        return int(removed)
