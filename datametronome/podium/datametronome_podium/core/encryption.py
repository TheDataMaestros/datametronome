"""
Field-level encryption for sensitive stave connection credentials.

Uses Fernet symmetric encryption. Encrypted values are prefixed with ``enc::``
so legacy plaintext values pass through transparently (backward compat).
"""

import base64
import hashlib
import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet

# ---------------------------------------------------------------------------
# Sensitive-field registry
# ---------------------------------------------------------------------------

# Per data-source-type overrides
SENSITIVE_FIELDS: dict[str, list[str]] = {
    "postgres": ["password"],
    "mysql": ["password"],
    "redis": ["password"],
    "mongodb": ["password"],
    "snowflake": ["password", "private_key"],
    "bigquery": ["credentials_json"],
}

# Fallback for unknown / future types
_DEFAULT_SENSITIVE_FIELDS: list[str] = [
    "password",
    "api_key",
    "credentials_json",
    "secret",
    "token",
    "private_key",
]

MASKED_VALUE = "\u25cf\u25cf\u25cf\u25cf\u25cf\u25cf"  # "●●●●●●"

_ENC_PREFIX = "enc::"


# ---------------------------------------------------------------------------
# Fernet helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Return a cached Fernet instance derived from settings."""
    from datametronome_podium.core.config import get_settings

    settings = get_settings()
    raw_key = settings.encryption_key or settings.secret_key
    # Derive a 32-byte key via SHA-256 and base64-encode for Fernet
    digest = hashlib.sha256(raw_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string, returning ``enc::<token>``."""
    token = _get_fernet().encrypt(plaintext.encode())
    return _ENC_PREFIX + token.decode()


def decrypt_value(value: str) -> str:
    """Decrypt an ``enc::``-prefixed value.  Plaintext passes through."""
    if not value.startswith(_ENC_PREFIX):
        return value  # legacy / plaintext
    token = value[len(_ENC_PREFIX) :]
    return _get_fernet().decrypt(token.encode()).decode()


# ---------------------------------------------------------------------------
# Config-level helpers
# ---------------------------------------------------------------------------


def _sensitive_keys(data_source_type: str | None) -> list[str]:
    """Return the list of sensitive field names for the given type."""
    if data_source_type and data_source_type.lower() in SENSITIVE_FIELDS:
        return SENSITIVE_FIELDS[data_source_type.lower()]
    return _DEFAULT_SENSITIVE_FIELDS


def encrypt_sensitive_fields(
    config: dict[str, Any],
    data_source_type: str | None = None,
) -> dict[str, Any]:
    """Return a *new* dict with sensitive values encrypted."""
    keys = _sensitive_keys(data_source_type)
    out = dict(config)
    for k in keys:
        if k not in out:
            continue
        val = out[k]
        if isinstance(val, dict):
            val = json.dumps(val)
        if isinstance(val, str) and val.startswith(_ENC_PREFIX):
            continue  # already encrypted
        out[k] = encrypt_value(str(val))
    return out


def decrypt_sensitive_fields(
    config: dict[str, Any],
    data_source_type: str | None = None,
) -> dict[str, Any]:
    """Return a *new* dict with ``enc::``-prefixed values decrypted."""
    keys = _sensitive_keys(data_source_type)
    out = dict(config)
    for k in keys:
        if k not in out:
            continue
        val = out[k]
        if not isinstance(val, str) or not val.startswith(_ENC_PREFIX):
            continue  # plaintext / non-string — pass through
        decrypted = decrypt_value(val)
        # Restore dict types (e.g. credentials_json)
        if decrypted.startswith("{"):
            try:
                out[k] = json.loads(decrypted)
                continue
            except json.JSONDecodeError:
                pass
        out[k] = decrypted
    return out


def mask_sensitive_fields(
    config: dict[str, Any],
    data_source_type: str | None = None,
) -> dict[str, Any]:
    """Return a *new* dict with sensitive values replaced by ``MASKED_VALUE``."""
    keys = _sensitive_keys(data_source_type)
    out = dict(config)
    for k in keys:
        if k in out:
            out[k] = MASKED_VALUE
    return out
