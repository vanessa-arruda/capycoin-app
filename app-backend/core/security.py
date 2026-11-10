import hashlib
import secrets
from functools import cache

from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()


def hash_secret(secret: str) -> str:
    """Slow Argon2 hash, for passwords and one-time codes."""
    return _hasher.hash(secret)


def verify_secret(secret: str, secret_hash: str) -> bool:
    return _hasher.verify(secret, secret_hash)


@cache
def _dummy_hash() -> str:
    return _hasher.hash(secrets.token_urlsafe())


def spend_verify_time() -> None:
    """Take as long as a real check, so failures don't reveal which accounts exist."""
    _hasher.verify("not-a-password", _dummy_hash())


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Fast hash for random high-entropy tokens (sessions, invitations)."""
    return hashlib.sha256(token.encode()).hexdigest()


def new_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"
