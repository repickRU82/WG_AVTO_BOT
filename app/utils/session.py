"""Redis-backed session manager."""

from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(slots=True)
class SessionManager:
    """Simple session manager storing role by Telegram user id."""

    redis: Redis
    ttl_seconds: int

    def _session_key(self, telegram_id: int) -> str:
        return f"session:{telegram_id}"

    async def create_session(self, telegram_id: int, role: str) -> None:
        """Create or refresh user session with fixed TTL."""

        await self.redis.set(self._session_key(telegram_id), role, ex=self.ttl_seconds)

    async def get_role(self, telegram_id: int) -> str | None:
        """Get active role if session exists."""

        role = await self.redis.get(self._session_key(telegram_id))
        if role is None:
            return None
        return role.decode("utf-8") if isinstance(role, bytes) else str(role)

    async def destroy_session(self, telegram_id: int) -> None:
        """Delete session key."""

        await self.redis.delete(self._session_key(telegram_id))
