"""MikroTik RouterOS API integration."""

from __future__ import annotations

import asyncio
import ssl
from dataclasses import dataclass
from typing import Any

import structlog
from librouteros import connect


class MikroTikClientError(Exception):
    """Raised when RouterOS API operation fails."""


@dataclass(slots=True)
class MikroTikClient:
    """Async wrapper over librouteros for WireGuard peer management."""

    host: str
    port: int
    username: str
    password: str
    use_tls: bool
    timeout_seconds: int = 15
    retry_attempts: int = 3
    retry_backoff_seconds: int = 2
    tls_insecure: bool = True

    def __post_init__(self) -> None:
        self._logger = structlog.get_logger(__name__).bind(host=self.host, port=self.port, tls=self.use_tls)

    async def add_wireguard_peer(
        self,
        interface: str,
        name: str,
        public_key: str,
        allowed_address: str,
        preshared_key: str | None,
        comment: str,
    ) -> bool:
        """Add peer and return True if created, False if already exists."""

        self._logger.info("Adding peer on MikroTik", interface=interface, name=name, allowed_address=allowed_address)

        if await self.peer_exists(interface=interface, public_key=public_key, allowed_address=allowed_address):
            self._logger.info(
                "Peer already exists on MikroTik",
                interface=interface,
                public_key_tail=public_key[-8:],
                allowed_address=allowed_address,
            )
            return False

        payload: dict[str, str] = {
            "interface": interface,
            "name": name,
            "public-key": public_key,
            "allowed-address": allowed_address,
            "comment": comment,
        }
        if preshared_key:
            payload["preshared-key"] = preshared_key

        await self._run_api("add_peer", **payload)
        self._logger.info("Peer added successfully", interface=interface, name=name, allowed_address=allowed_address)
        return True

    async def peer_exists(self, interface: str, public_key: str, allowed_address: str | None = None) -> bool:
        """Check existing peers by public key and optionally by allowed address."""

        peers = await self.list_wireguard_peers(interface)
        for peer in peers:
            if peer.get("public-key") == public_key:
                return True
            if allowed_address and peer.get("allowed-address") == allowed_address:
                return True
        return False

    async def remove_wireguard_peer(self, peer_id: str) -> None:
        """Remove peer by RouterOS internal ID."""

        await self._run_api("remove_peer", peer_id=peer_id)

    async def list_wireguard_peers(self, interface: str) -> list[dict[str, str]]:
        """Return peers list for selected WireGuard interface."""

        records = await self._run_api("list_peers", interface=interface)
        return [dict(item) for item in records]

    async def _run_api(self, operation: str, **params: str) -> Any:
        """Run API command with retries and timeout."""

        last_error: Exception | None = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._run_api_sync, operation, params),
                    timeout=self.timeout_seconds,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self._logger.warning("MikroTik operation failed", operation=operation, attempt=attempt, error=str(exc))
                if attempt < self.retry_attempts:
                    await asyncio.sleep(self.retry_backoff_seconds * attempt)

        raise MikroTikClientError(f"MikroTik operation failed: {operation}") from last_error

    def _build_ssl_wrapper(self):
        if not self.use_tls:
            return None

        if self.tls_insecure:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context.wrap_socket

        return ssl.create_default_context().wrap_socket

    def _run_api_sync(self, operation: str, params: dict[str, str]) -> Any:
        self._logger.info("Connecting to MikroTik")
        api = connect(
            host=self.host,
            username=self.username,
            password=self.password,
            port=self.port,
            ssl_wrapper=self._build_ssl_wrapper(),
        )

        peers_path = api.path("interface/wireguard/peers")

        try:
            if operation == "add_peer":
                peers_path.add(**params)
                return None

            if operation == "remove_peer":
                peers_path.remove(**{".id": params["peer_id"]})
                return None

            if operation == "list_peers":
                interface = params["interface"]
                return [
                    item
                    for item in peers_path.select(".id", "interface", "name", "public-key", "allowed-address", "comment")
                    if item.get("interface") == interface
                ]

            raise ValueError(f"Unsupported MikroTik operation: {operation}")
        finally:
            api.close()
