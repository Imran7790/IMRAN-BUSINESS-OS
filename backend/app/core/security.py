import hashlib
import hmac
import os


def hash_password(password: str) -> str:
    salt = os.urandom(16)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120000
    )

    return (
        salt.hex()
        + "$"
        + derived.hex()
    )


def verify_password(
    password: str,
    stored: str
) -> bool:

    try:
        salt_hex, hash_hex = stored.split("$", 1)

        salt = bytes.fromhex(salt_hex)

        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            120000
        )

        return hmac.compare_digest(
            derived.hex(),
            hash_hex
        )

    except Exception:
        return False
