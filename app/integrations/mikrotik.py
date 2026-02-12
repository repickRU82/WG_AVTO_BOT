"""MikroTik RouterOS API integration."""

from __future__ import annotations

import asyncio
import ssl
from dataclasses import dataclass, field
from ipaddress import IPv4Address
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
    dry_run: bool = False
    _logger: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = structlog.get_logger(__name__).bind(
            host=self.host,
            port=self.port,
            tls=self.use_tls,
            dry_run=self.dry_run,
        )

    async def add_wireguard_peer(
        self,
        interface: str,
        name: str,
        public_key: str,
        allowed_address: str,
        preshared_key: str | None,
        comment: str,
    ) -> tuple[str, str | None]:
        """Ensure peer exists and return action + peer id."""

        IPv4Address(allowed_address.split("/")[0])

        payload: dict[str, str] = {
            "interface": interface,
            "name": name,
            "public-key": public_key,
            "allowed-address": allowed_address,
            "comment": comment,
        }
        if preshared_key:
            payload["preshared-key"] = preshared_key

        self._logger.info("Adding peer on MikroTik", interface=interface, name=name, allowed_address=allowed_address)

        existing = await self.find_peer(interface=interface, comment=comment)
        if existing is not None:
            await self._update_peer_if_needed(existing=existing, payload=payload)
            return "updated", existing.get(".id")

        duplicate = await self.find_peer(interface=interface, public_key=public_key, allowed_address=allowed_address)
        if duplicate is not None:
            self._logger.info(
                "Peer already exists on MikroTik",
                interface=interface,
                peer_id=duplicate.get(".id"),
                allowed_address=duplicate.get("allowed-address"),
            )
            return "exists", duplicate.get(".id")

        if self.dry_run:
            self._logger.info("Dry-run enabled: skip peer creation", payload=payload)
            return "dry_run", None

        await self._run_api("add_peer", **payload)
        created = await self.find_peer(interface=interface, comment=comment)
        peer_id = created.get(".id") if created else None
        self._logger.info("Peer added successfully", interface=interface, peer_id=peer_id, allowed_address=allowed_address)
        return "created", peer_id

    async def find_peer(
        self,
        interface: str,
        comment: str | None = None,
        public_key: str | None = None,
        allowed_address: str | None = None,
    ) -> dict[str, str] | None:
        """Find single peer by comment/public key/allowed address."""

        peers = await self.list_wireguard_peers(interface)
        for peer in peers:
            if comment and peer.get("comment") == comment:
                return peer
            if public_key and peer.get("public-key") == public_key:
                return peer
            if allowed_address and peer.get("allowed-address") == allowed_address:
                return peer
        return None

    async def remove_wireguard_peer(self, peer_id: str) -> None:
        """Remove peer by RouterOS internal ID."""

        if self.dry_run:
            self._logger.info("Dry-run enabled: skip peer remove", peer_id=peer_id)
            return
        await self._run_api("remove_peer", peer_id=peer_id)

    async def list_wireguard_peers(self, interface: str) -> list[dict[str, str]]:
        """Return peers list for selected WireGuard interface."""

        records = await self._run_api("list_peers", interface=interface)
        return [dict(item) for item in records]

    async def ping(self) -> str:
        """Return RouterOS identity to verify API connectivity."""

        identity = await self._run_api("identity")
        return str(identity)

    async def _update_peer_if_needed(self, existing: dict[str, str], payload: dict[str, str]) -> None:
        needs_update = (
            existing.get("allowed-address") != payload["allowed-address"]
            or existing.get("public-key") != payload["public-key"]
            or (payload.get("preshared-key") and existing.get("preshared-key") != payload.get("preshared-key"))
            or existing.get("name") != payload["name"]
        )

        if not needs_update:
            self._logger.info("Peer already up to date", peer_id=existing.get(".id"), comment=payload["comment"])
            return

        if self.dry_run:
            self._logger.info("Dry-run enabled: skip peer update", peer_id=existing.get(".id"), payload=payload)
            return

        update_payload = {
            "peer_id": existing[".id"],
            "name": payload["name"],
            "public-key": payload["public-key"],
            "allowed-address": payload["allowed-address"],
            "comment": payload["comment"],
        }
        if payload.get("preshared-key"):
            update_payload["preshared-key"] = payload["preshared-key"]

        await self._run_api("set_peer", **update_payload)
        self._logger.info("Peer updated successfully", peer_id=existing.get(".id"), comment=payload["comment"])

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
        self._logger.info("Connected to MikroTik")

        peers_path = api.path("interface/wireguard/peers")

        try:
            if operation == "add_peer":
                peers_path.add(**params)
                return None

            if operation == "set_peer":
                peer_id = params.pop("peer_id")
                peers_path.set(**{".id": peer_id, **params})
                return None

            if operation == "remove_peer":
                peers_path.remove(**{".id": params["peer_id"]})
                return None

            if operation == "list_peers":
                interface = params["interface"]
                return [
                    item
                    for item in peers_path.select(
                        ".id",
                        "interface",
                        "name",
                        "public-key",
                        "allowed-address",
                        "preshared-key",
                        "comment",
                    )
                    if item.get("interface") == interface
                ]

            if operation == "identity":
                identities = list(api.path("system/identity").select("name"))
                return identities[0].get("name", "unknown") if identities else "unknown"

            raise ValueError(f"Unsupported MikroTik operation: {operation}")
        finally:
            api.close()
