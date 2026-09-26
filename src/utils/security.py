import hashlib
import secrets


PASSWORD_PREFIX = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_PREFIX}${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_password: str) -> bool:
    if not stored_password.startswith(f"{PASSWORD_PREFIX}$"):
        return secrets.compare_digest(password, stored_password)

    try:
        _, iterations, salt, digest = stored_password.split("$", 3)
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
    except Exception:
        return False
    return secrets.compare_digest(candidate, digest)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
