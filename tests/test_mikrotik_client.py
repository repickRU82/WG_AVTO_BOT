from app.integrations.mikrotik import MikroTikClient


def test_mikrotik_client_post_init_sets_logger() -> None:
    client = MikroTikClient(
        host="127.0.0.1",
        port=8728,
        username="u",
        password="p",
        use_tls=False,
    )
    assert client._logger is not None
