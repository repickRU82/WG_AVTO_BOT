import asyncio
from dataclasses import dataclass

from app.services.auth_service import AuthService
from app.utils.security import hash_pin


@dataclass
class DummyUser:
    id: int
    telegram_id: int
    username: str | None
    full_name: str | None
    role: str
    pin_hash: str
    is_active: bool


class FakeUsersRepo:
    async def get_by_telegram_id(self, telegram_id: int):
        return DummyUser(
            id=10,
            telegram_id=telegram_id,
            username="u",
            full_name="User",
            role="user",
            pin_hash=hash_pin("1234", rounds=12),
            is_active=True,
        )


class FakeLogsRepo:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict, int | None]] = []

    async def add(self, event_type: str, details: dict, user_id: int | None = None) -> None:
        self.events.append((event_type, details, user_id))


class FakeSessionManager:
    def __init__(self) -> None:
        self.created: list[tuple[int, str]] = []

    async def create_session(self, telegram_id: int, role: str) -> None:
        self.created.append((telegram_id, role))


def test_login_success_creates_event_without_crash() -> None:
    users = FakeUsersRepo()
    logs = FakeLogsRepo()
    sessions = FakeSessionManager()

    service = AuthService(
        users_repo=users,  # type: ignore[arg-type]
        logs_repo=logs,  # type: ignore[arg-type]
        sessions=sessions,  # type: ignore[arg-type]
        pin_bcrypt_rounds=12,
        admin_ids=set(),
    )

    success, role = asyncio.run(service.login(telegram_id=123, pin="1234"))

    assert success is True
    assert role == "user"
    assert sessions.created == [(123, "user")]
    assert any(event[0] == "login_success" for event in logs.events)
