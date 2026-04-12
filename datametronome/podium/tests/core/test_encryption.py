"""Tests for field-level encryption of stave connection credentials."""

import json

from datametronome_podium.core.encryption import (
    MASKED_VALUE,
    SENSITIVE_FIELDS,
    _DEFAULT_SENSITIVE_FIELDS,
    decrypt_sensitive_fields,
    decrypt_value,
    encrypt_sensitive_fields,
    encrypt_value,
    mask_sensitive_fields,
)


class TestEncryptDecryptValue:
    """Roundtrip encrypt/decrypt for individual values."""

    def test_roundtrip_string(self):
        encrypted = encrypt_value("my_secret_password")
        assert encrypted.startswith("enc::")
        assert decrypt_value(encrypted) == "my_secret_password"

    def test_roundtrip_json_dict(self):
        original = json.dumps({"project_id": "x", "private_key": "abc"})
        encrypted = encrypt_value(original)
        assert encrypted.startswith("enc::")
        assert decrypt_value(encrypted) == original

    def test_plaintext_passthrough(self):
        assert decrypt_value("plain_password") == "plain_password"

    def test_empty_string(self):
        encrypted = encrypt_value("")
        assert encrypted.startswith("enc::")
        assert decrypt_value(encrypted) == ""


class TestEncryptSensitiveFields:
    """Encrypt only sensitive fields in a config dict."""

    def test_postgres_encrypts_password(self):
        config = {"host": "localhost", "port": 5432, "user": "admin", "password": "secret"}
        result = encrypt_sensitive_fields(config, "postgres")
        assert result["host"] == "localhost"
        assert result["port"] == 5432
        assert result["user"] == "admin"
        assert result["password"].startswith("enc::")

    def test_bigquery_encrypts_credentials_json(self):
        creds = {"project_id": "my-project", "private_key": "-----BEGIN-----"}
        config = {"project": "my-project", "credentials_json": creds}
        result = encrypt_sensitive_fields(config, "bigquery")
        assert result["project"] == "my-project"
        assert result["credentials_json"].startswith("enc::")

    def test_sqlite_no_sensitive_fields(self):
        config = {"path": "/data/analytics.db"}
        result = encrypt_sensitive_fields(config, "sqlite")
        assert result == config  # nothing to encrypt

    def test_unknown_type_uses_defaults(self):
        config = {"host": "h", "password": "pw", "api_key": "ak", "database": "db"}
        result = encrypt_sensitive_fields(config, "some_future_db")
        assert result["host"] == "h"
        assert result["database"] == "db"
        assert result["password"].startswith("enc::")
        assert result["api_key"].startswith("enc::")

    def test_already_encrypted_not_double_encrypted(self):
        config = {"host": "h", "password": encrypt_value("secret")}
        result = encrypt_sensitive_fields(config, "postgres")
        assert result["password"] == config["password"]  # unchanged


class TestDecryptSensitiveFields:
    """Decrypt enc::-prefixed fields; pass through plaintext."""

    def test_roundtrip_postgres(self):
        original = {"host": "localhost", "password": "secret", "port": 5432}
        encrypted = encrypt_sensitive_fields(original, "postgres")
        decrypted = decrypt_sensitive_fields(encrypted, "postgres")
        assert decrypted == original

    def test_legacy_plaintext_passthrough(self):
        config = {"host": "localhost", "password": "plain_old_password"}
        result = decrypt_sensitive_fields(config, "postgres")
        assert result["password"] == "plain_old_password"

    def test_bigquery_credentials_json_restored_as_dict(self):
        creds = {"project_id": "x", "private_key": "pk"}
        config = {"credentials_json": creds}
        encrypted = encrypt_sensitive_fields(config, "bigquery")
        decrypted = decrypt_sensitive_fields(encrypted, "bigquery")
        assert decrypted["credentials_json"] == creds
        assert isinstance(decrypted["credentials_json"], dict)

    def test_non_sensitive_fields_unchanged(self):
        config = {"host": "h", "port": 5432, "database": "db", "password": "pw"}
        encrypted = encrypt_sensitive_fields(config, "postgres")
        decrypted = decrypt_sensitive_fields(encrypted, "postgres")
        assert decrypted["host"] == "h"
        assert decrypted["port"] == 5432
        assert decrypted["database"] == "db"


class TestMaskSensitiveFields:
    """Mask sensitive fields with MASKED_VALUE."""

    def test_postgres_mask(self):
        config = {"host": "h", "port": 5432, "password": "secret"}
        result = mask_sensitive_fields(config, "postgres")
        assert result["host"] == "h"
        assert result["port"] == 5432
        assert result["password"] == MASKED_VALUE

    def test_bigquery_mask(self):
        config = {"project": "p", "credentials_json": {"key": "value"}}
        result = mask_sensitive_fields(config, "bigquery")
        assert result["project"] == "p"
        assert result["credentials_json"] == MASKED_VALUE

    def test_unknown_type_masks_defaults(self):
        config = {"host": "h", "password": "pw", "token": "tk"}
        result = mask_sensitive_fields(config, "unknown_db")
        assert result["host"] == "h"
        assert result["password"] == MASKED_VALUE
        assert result["token"] == MASKED_VALUE

    def test_missing_sensitive_field_no_error(self):
        config = {"host": "h", "port": 5432}  # no password
        result = mask_sensitive_fields(config, "postgres")
        assert result == config


class TestSensitiveFieldsRegistry:
    """Verify the registry and defaults are reasonable."""

    def test_postgres_fields(self):
        assert SENSITIVE_FIELDS["postgres"] == ["password"]

    def test_bigquery_fields(self):
        assert "credentials_json" in SENSITIVE_FIELDS["bigquery"]

    def test_defaults_cover_common_secrets(self):
        for field in ["password", "api_key", "credentials_json", "secret", "token"]:
            assert field in _DEFAULT_SENSITIVE_FIELDS
