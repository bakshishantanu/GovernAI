from __future__ import annotations

import json

from cryptography.fernet import Fernet

from app.config import settings

#: Fixed dev-only key so local/test runs never need a real secret configured.
#: See the CONNECTIONS_ENCRYPTION_KEY comment in config.py -- a deployed
#: server must override this via the environment.
_DEV_FALLBACK_KEY = "PQQX3vdXy6pjWhiFZXdTF95aZ2TwwJMv08dlSNhWb-8="


def _fernet() -> Fernet:
    key = settings.CONNECTIONS_ENCRYPTION_KEY or _DEV_FALLBACK_KEY
    return Fernet(key.encode())


def encrypt_secret(fields: dict[str, str]) -> str:
    """Encrypts a requirement's field values as one opaque token. Only ever
    called with values a user just submitted (see ConnectionService) -- never
    store a value here that wasn't explicitly typed into a connection form."""
    return _fernet().encrypt(json.dumps(fields).encode()).decode()


def decrypt_secret(token: str) -> dict[str, str]:
    return json.loads(_fernet().decrypt(token.encode()).decode())
