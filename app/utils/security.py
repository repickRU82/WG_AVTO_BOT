"""Security helpers for PIN hashing and verification."""

import bcrypt


def hash_pin(pin: str, rounds: int = 12) -> str:
    """Hash a PIN with bcrypt."""

    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(pin.encode("utf-8"), salt).decode("utf-8")


def verify_pin(pin: str, pin_hash: str) -> bool:
    """Verify a PIN against bcrypt hash."""

    return bcrypt.checkpw(pin.encode("utf-8"), pin_hash.encode("utf-8"))
