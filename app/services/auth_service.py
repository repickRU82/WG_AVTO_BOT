"""Authentication and session workflows."""

from dataclasses import dataclass

from app.database.repositories import LogsRepository, User, UsersRepository
from app.utils.security import hash_pin, verify_pin
from app.utils.session import SessionManager


@dataclass(slots=True)
class AuthService:
    """Service for user registration/login using PIN and Redis sessions."""

    users_repo: UsersRepository
    logs_repo: LogsRepository
    sessions: SessionManager
    pin_bcrypt_rounds: int
    admin_ids: set[int]

    async def register_if_absent(self, telegram_id: int, username: str | None, full_name: str | None, pin: str) -> User:
        """Create new user with hashed PIN if not existing."""

        user = await self.users_repo.get_by_telegram_id(telegram_id)
        if user is not None:
            return user

        role = "admin" if telegram_id in self.admin_ids else "user"
        user = await self.users_repo.create(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=role,
            pin_hash=hash_pin(pin, rounds=self.pin_bcrypt_rounds),
        )
        await self.logs_repo.add("register_success", {"telegram_id": telegram_id, "role": role}, user.id)
        return user

    async def login(self, telegram_id: int, pin: str) -> tuple[bool, str | None]:
        """Validate PIN and create session. Returns (success, role)."""

        user = await self.users_repo.get_by_telegram_id(telegram_id)
        if user is None:
            await self.logs_repo.add("login_failed", {"reason": "user_not_found", "telegram_id": telegram_id})
            return False, None

        if not verify_pin(pin, user.pin_hash):
            await self.logs_repo.add("login_failed", {"reason": "invalid_pin", "telegram_id": telegram_id}, user.id)
            return False, None

        await self.sessions.create_session(telegram_id=telegram_id, role=user.role)
        await self.logs_repo.add("login_success", {"telegram_id": telegram_id, "role": user.role}, user.id)
        return True, user.role
