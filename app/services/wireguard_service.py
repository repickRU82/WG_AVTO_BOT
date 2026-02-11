"""WireGuard key generation and client config rendering."""

import base64
import secrets
from dataclasses import dataclass
from typing import Protocol

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey


class WireGuardSettings(Protocol):
    """Protocol for settings used by WireGuard service."""

    wg_server_public_key: str
    wg_endpoint_host: str
    wg_endpoint_port: int
    wg_dns_servers: str
    wg_allowed_ips: str
    wg_persistent_keepalive: int
    wg_junk_packet_count: int
    wg_junk_packet_min_size: int
    wg_junk_packet_max_size: int
    wg_init_packet_junk_size: int
    wg_response_packet_junk_size: int
    wg_underload_packet_junk_size: int
    wg_transport_packet_magic: int
    wg_network_cidr: str


@dataclass(slots=True)
class WireGuardCredentials:
    """Generated keys and assigned IP for client profile."""

    private_key: str
    public_key: str
    preshared_key: str
    ip_address: str


class WireGuardService:
    """Generates WireGuard material and renders AmneziaWG config template."""

    def __init__(self, settings: WireGuardSettings) -> None:
        self.settings = settings

    @staticmethod
    def _to_wg_base64(raw: bytes) -> str:
        return base64.b64encode(raw).decode("ascii")

    def generate_keys(self) -> tuple[str, str, str]:
        """Generate private/public/preshared keys in WireGuard-compatible format."""

        private_key = X25519PrivateKey.generate()
        private_raw = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_raw = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        preshared_raw = secrets.token_bytes(32)

        return (
            self._to_wg_base64(private_raw),
            self._to_wg_base64(public_raw),
            self._to_wg_base64(preshared_raw),
        )

    def generate_profile(self, ip_address: str) -> WireGuardCredentials:
        """Generate full credentials bundle for one user profile."""

        private_key, public_key, preshared_key = self.generate_keys()
        return WireGuardCredentials(
            private_key=private_key,
            public_key=public_key,
            preshared_key=preshared_key,
            ip_address=ip_address,
        )

    def render_config(self, credentials: WireGuardCredentials) -> str:
        """Render WireGuard INI config including AmneziaWG obfuscation values."""

        return (
            "[Interface]\n"
            f"PrivateKey = {credentials.private_key}\n"
            f"Address = {credentials.ip_address}/32\n"
            f"DNS = {self.settings.wg_dns_servers}\n"
            "JunkPacketCount = {junk_count}\n"
            "JunkPacketMinSize = {junk_min}\n"
            "JunkPacketMaxSize = {junk_max}\n"
            "InitPacketJunkSize = {init_junk}\n"
            "ResponsePacketJunkSize = {resp_junk}\n"
            "UnderloadPacketJunkSize = {underload_junk}\n"
            "TransportPacketMagic = {magic}\n\n"
            "[Peer]\n"
            f"PublicKey = {self.settings.wg_server_public_key}\n"
            f"PresharedKey = {credentials.preshared_key}\n"
            f"Endpoint = {self.settings.wg_endpoint_host}:{self.settings.wg_endpoint_port}\n"
            f"AllowedIPs = {self.settings.wg_allowed_ips}\n"
            f"PersistentKeepalive = {self.settings.wg_persistent_keepalive}\n"
        ).format(
            junk_count=self.settings.wg_junk_packet_count,
            junk_min=self.settings.wg_junk_packet_min_size,
            junk_max=self.settings.wg_junk_packet_max_size,
            init_junk=self.settings.wg_init_packet_junk_size,
            resp_junk=self.settings.wg_response_packet_junk_size,
            underload_junk=self.settings.wg_underload_packet_junk_size,
            magic=self.settings.wg_transport_packet_magic,
        )
