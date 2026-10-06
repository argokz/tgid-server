"""SCRAM-SHA-256 верификатор пароля роли PostgreSQL (RFC 5802 / 7677, формат pg_authid.rolpassword).

API передаёт в БД только верификатор (tgid_auth.set_password): открытый пароль не попадает ни в текст
SQL, ни в журнал сервера. Формат: SCRAM-SHA-256$<iterations>:<salt>$<StoredKey>:<ServerKey>.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import unicodedata

DEFAULT_ITERATIONS = 4096  # как scram_iterations по умолчанию в PostgreSQL 16


def _saslprep(password: str) -> str:
    # PostgreSQL нормализует пароль SASLprep (NFKC); при ошибке нормализации берёт байты как есть
    return unicodedata.normalize("NFKC", password)


def scram_sha256_verifier(password: str, *, salt: bytes | None = None,
                          iterations: int = DEFAULT_ITERATIONS) -> str:
    if not password:
        raise ValueError("Пустой пароль")
    salt = salt or os.urandom(16)
    salted = hashlib.pbkdf2_hmac("sha256", _saslprep(password).encode("utf-8"), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    b64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731
    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored_key)}:{b64(server_key)}"
