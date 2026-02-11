"""Helpers to allocate next available IP from network pool."""

from ipaddress import IPv4Address, IPv4Network


def allocate_next_ip(network_cidr: str, used_ips: set[str]) -> str:
    """Return first available host IP from network not present in used_ips."""

    network = IPv4Network(network_cidr)
    used = {IPv4Address(ip) for ip in used_ips}

    for host in network.hosts():
        if host not in used:
            return str(host)

    raise RuntimeError("No free IP addresses available in pool")
