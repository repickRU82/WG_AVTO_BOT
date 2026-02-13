"""Authentication and session workflows."""

from dataclasses import dataclass

from app.database.repositories import LogsRepository, User, UsersRepository
from app.utils.security import hash_pin
from app.utils.session import SessionManager


@dataclass(slots=True)
class AuthService:
    """Service for user registration/login using global PIN and Redis sessions."""

    users_repo: UsersRepository
    logs_repo: LogsRepository
    sessions: SessionManager
    pin_bcrypt_rounds: int
    admin_ids: set[int]
    superadmin_ids: set[int]
    global_pin: str

    def resolve_role(self, telegram_id: int) -> str:
        if telegram_id in self.superadmin_ids:
            return "superadmin"
        if telegram_id in self.admin_ids:
            return "admin"
        return "user"

    async def register_if_absent(self, telegram_id: int, username: str | None, full_name: str | None) -> User:
        user = await self.users_repo.get_by_telegram_id(telegram_id)
        if user is not None:
            return user

        role = self.resolve_role(telegram_id)
        access_status = "approved" if role in {"admin", "superadmin"} else "pending"
        user = await self.users_repo.create(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=role,
            pin_hash=hash_pin(self.global_pin, rounds=self.pin_bcrypt_rounds),
            access_status=access_status,
        )
        await self.logs_repo.add("register_success", {"telegram_id": telegram_id, "role": role}, user.id)
        return user

    async def sync_user_role(self, user: User) -> User:
        expected_role = self.resolve_role(user.telegram_id)
        if expected_role != user.role:
            await self.users_repo.set_role(user.telegram_id, expected_role)
            await self.logs_repo.add(
                "role_synced",
                {"telegram_id": user.telegram_id, "old_role": user.role, "new_role": expected_role},
                user.id,
            )
            refreshed = await self.users_repo.get_by_telegram_id(user.telegram_id)
            if refreshed is not None:
                return refreshed
        return user

    async def check_pin(self, telegram_id: int, pin: str) -> tuple[bool, User | None]:
        user = await self.users_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return False, None
        ok = pin == self.global_pin
        await self.logs_repo.add("pin_check", {"telegram_id": telegram_id, "ok": ok}, user.id)
        return ok, user

    async def login_approved(self, user: User) -> None:
        await self.users_repo.mark_pin_verified(user.telegram_id, True)
        await self.users_repo.touch_last_seen(user.telegram_id)
        await self.sessions.create_session(telegram_id=user.telegram_id, role=user.role)
        await self.logs_repo.add("login_success", {"telegram_id": user.telegram_id, "role": user.role}, user.id)
