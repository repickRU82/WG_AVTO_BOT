"""Repositories package exports."""

from app.database.repositories.logs import LogsRepository
from app.database.repositories.users import User, UsersRepository
from app.database.repositories.wireguard_configs import WireGuardConfigsRepository

__all__ = [
    "User",
    "UsersRepository",
    "LogsRepository",
    "WireGuardConfigsRepository",
]
