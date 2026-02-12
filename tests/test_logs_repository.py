import asyncio
import json

from app.database.repositories.logs import LogsRepository


class FakeConn:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None, str, str]] = []

    async def execute(self, query: str, user_id: int | None, event_type: str, payload: str) -> None:
        if not isinstance(payload, str):
            raise TypeError("expected str")
        self.calls.append((query, user_id, event_type, payload))


class FakeAcquire:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> FakeConn:
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakePool:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self._conn)


def test_logs_repository_serializes_details_to_json_string() -> None:
    conn = FakeConn()
    repo = LogsRepository(FakePool(conn))  # type: ignore[arg-type]

    details = {"telegram_id": 123, "message": "успех"}
    asyncio.run(repo.add("login_success", details, user_id=1))

    assert len(conn.calls) == 1
    _, user_id, event_type, payload = conn.calls[0]
    assert user_id == 1
    assert event_type == "login_success"
    assert json.loads(payload) == details
