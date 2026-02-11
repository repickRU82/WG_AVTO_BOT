"""Example: generate WireGuard keys and render client config from template."""

from types import SimpleNamespace

from app.services.wireguard_service import WireGuardService


def main() -> None:
    settings = Settings(
        bot_token="123456:TEST_TOKEN_FOR_LOCAL_EXAMPLE_ONLY",
        wg_server_public_key="SERVER_PUBLIC_KEY_BASE64",
    settings = SimpleNamespace(
        wg_server_public_key="SERVER_PUBLIC_KEY_BASE64",
        wg_endpoint_host="vpn.example.com",
        wg_endpoint_port=51820,
        wg_dns_servers="1.1.1.1,1.0.0.1",
        wg_allowed_ips="0.0.0.0/0,::/0",
        wg_persistent_keepalive=25,
        wg_junk_packet_count=5,
        wg_junk_packet_min_size=90,
        wg_junk_packet_max_size=220,
        wg_init_packet_junk_size=40,
        wg_response_packet_junk_size=120,
        wg_underload_packet_junk_size=80,
        wg_transport_packet_magic=666,
        wg_network_cidr="10.0.0.0/24",
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
