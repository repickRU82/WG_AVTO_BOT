"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global settings container."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True

    bot_token: str = Field(..., min_length=20)
    bot_parse_mode: str = "HTML"
    admin_telegram_ids: str = ""
    superadmin_telegram_ids: str = ""
    global_pin: str = "1234"
    rate_limit_reissue_seconds: int = 300

    database_dsn: str = "postgresql://wg_bot:wg_bot_password@127.0.0.1:5432/wg_bot"
    redis_dsn: str = "redis://127.0.0.1:6379/0"

    session_ttl_seconds: int = 2592000
    pin_bcrypt_rounds: int = 12

    wg_interface_name: str = "wireguard1"
    wg_server_public_key: str = ""
    wg_endpoint_host: str = "vpn.example.com"
    wg_endpoint_port: int = 51820
    wg_dns_servers: str = "1.1.1.1,1.0.0.1"
    wg_network_cidr: str = "10.0.0.0/24"
    wg_allowed_ips: str = "0.0.0.0/0,::/0"
    wg_persistent_keepalive: int = 25

    wg_junk_packet_count: int = 5
    wg_junk_packet_min_size: int = 90
    wg_junk_packet_max_size: int = 220
    wg_init_packet_junk_size: int = 40
    wg_response_packet_junk_size: int = 120
    wg_underload_packet_junk_size: int = 80
    wg_transport_packet_magic: int = 666

    mikrotik_enabled: bool = True
    mikrotik_dry_run: bool = False
    mikrotik_host: str = "192.168.88.1"
    mikrotik_port: int = 8729
    mikrotik_use_tls: bool = True
    mikrotik_tls_insecure: bool = True
    mikrotik_username: str = "api_user"
    mikrotik_password: str = "api_password"
    mikrotik_timeout_seconds: int = 15
    mikrotik_retry_attempts: int = 3
    mikrotik_retry_backoff_seconds: int = 2

    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "json"
    log_file_path: str = ""

    @field_validator("database_dsn", mode="before")
    @classmethod
    def normalize_database_dsn(cls, value: str) -> str:
        raw = str(value).strip()
        double_prefix = "DATABASE_DSN="
        if raw.upper().startswith(double_prefix):
            return raw[len(double_prefix) :]
        return raw

    @property
    def admin_ids(self) -> set[int]:
        """Return parsed admin Telegram IDs set."""

        if not self.admin_telegram_ids.strip():
            return set()
        return {int(raw.strip()) for raw in self.admin_telegram_ids.split(",") if raw.strip()}

    @property
    def superadmin_ids(self) -> set[int]:
        """Return parsed superadmin Telegram IDs set."""

        if not self.superadmin_telegram_ids.strip():
            return set()
        return {int(raw.strip()) for raw in self.superadmin_telegram_ids.split(",") if raw.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
