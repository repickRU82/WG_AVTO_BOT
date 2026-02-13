import asyncio
from dataclasses import dataclass

from app.services.auth_service import AuthService


@dataclass
class DummyUser:
    id: int
    telegram_id: int
    username: str | None
    full_name: str | None
    role: str
    pin_hash: str
    pin_verified: bool
    is_active: bool
    access_status: str


class FakeUsersRepo:
    def __init__(self) -> None:
        self.user = DummyUser(
            id=10,
            telegram_id=123,
            username="u",
            full_name="User",
            role="user",
            pin_hash="ignored",
            pin_verified=False,
            is_active=True,
            access_status="approved",
        )
        self.verified_calls: list[tuple[int, bool]] = []
        self.touch_calls: list[int] = []

    async def get_by_telegram_id(self, telegram_id: int):
        return self.user

    async def mark_pin_verified(self, telegram_id: int, verified: bool = True) -> None:
        self.verified_calls.append((telegram_id, verified))

    async def touch_last_seen(self, telegram_id: int) -> None:
        self.touch_calls.append(telegram_id)

    async def set_role(self, telegram_id: int, role: str) -> None:
        self.user.role = role


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


def test_pin_and_login_success() -> None:
    users = FakeUsersRepo()
    logs = FakeLogsRepo()
    sessions = FakeSessionManager()

    service = AuthService(
        users_repo=users,  # type: ignore[arg-type]
        logs_repo=logs,  # type: ignore[arg-type]
        sessions=sessions,  # type: ignore[arg-type]
        pin_bcrypt_rounds=12,
        admin_ids={55},
        superadmin_ids={77},
        global_pin="1234",
    )

    ok, user = asyncio.run(service.check_pin(telegram_id=123, pin="1234"))
    assert ok is True
    assert user is not None

    asyncio.run(service.login_approved(user))
    assert sessions.created == [(123, "user")]
    assert users.verified_calls == [(123, True)]
    assert users.touch_calls == [123]
    assert any(event[0] == "login_success" for event in logs.events)


def test_resolve_role_superadmin_priority() -> None:
    service = AuthService(
        users_repo=FakeUsersRepo(),  # type: ignore[arg-type]
        logs_repo=FakeLogsRepo(),  # type: ignore[arg-type]
        sessions=FakeSessionManager(),  # type: ignore[arg-type]
        pin_bcrypt_rounds=12,
        admin_ids={1, 2},
        superadmin_ids={2, 3},
        global_pin="1234",
    )

    assert service.resolve_role(2) == "superadmin"
    assert service.resolve_role(1) == "admin"
    assert service.resolve_role(100) == "user"
