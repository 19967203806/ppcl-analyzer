from src.utils.security import hash_password, verify_password, generate_token, hash_token


def test_hash_password_does_not_store_plaintext():
    hashed = hash_password("secret")

    assert hashed != "secret"
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)


def test_verify_password_keeps_legacy_plaintext_compatibility():
    assert verify_password("legacy", "legacy")
    assert not verify_password("wrong", "legacy")


def test_generate_token_is_random_and_urlsafe():
    a, b = generate_token(), generate_token()
    assert a != b
    assert len(a) >= 32
    assert all(c.isalnum() or c in "-_" for c in a)


def test_hash_token_is_stable_sha256_hex():
    token = "abc123"
    assert hash_token(token) == hash_token(token)
    assert len(hash_token(token)) == 64
    assert hash_token(token) != token
