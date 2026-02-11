"""Example: generate WireGuard keys and render client config from template."""

from app.config import Settings
from app.services.wireguard_service import WireGuardService


def main() -> None:
    settings = Settings(
        bot_token="123456:TEST_TOKEN_FOR_LOCAL_EXAMPLE_ONLY",
        wg_server_public_key="SERVER_PUBLIC_KEY_BASE64",
    )
    service = WireGuardService(settings)

    creds = service.generate_profile(ip_address="10.0.0.10")
    config_text = service.render_config(creds)

    print("Private key:", creds.private_key)
    print("Public key:", creds.public_key)
    print("Preshared key:", creds.preshared_key)
    print("\nGenerated config:\n")
    print(config_text)


if __name__ == "__main__":
    main()
