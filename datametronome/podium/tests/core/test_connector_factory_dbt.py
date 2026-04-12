"""Tests for dbt connector factory integration."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from datametronome_podium.core.connector_factory import _build_connector


class TestBuildDbtConnector:
    """Test _build_connector with dst='dbt'."""

    def test_dispatches_to_dbt_builder(self):
        with patch("datametronome_podium.core.connector_factory._build_dbt_connector") as mock_build:
            mock_build.return_value = MagicMock()
            _build_connector("dbt", {"mode": "local", "project_path": "/tmp"}, read_only=True)
            mock_build.assert_called_once_with(
                {"mode": "local", "project_path": "/tmp"}, read_only=True
            )

    def test_dbt_read_only_false_raises(self):
        with pytest.raises(ValueError, match="read-only"):
            _build_connector("dbt", {"mode": "local", "project_path": "/tmp"}, read_only=False)

    def test_dbt_local_mode(self):
        """Verify local config keys are forwarded correctly."""
        from datametronome_podium.core.connector_factory import _build_dbt_connector

        with patch(
            "datametronome_podium.core.connector_factory.DbtReadonlyPulse",
            create=True,
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            try:
                _build_dbt_connector(
                    {"mode": "local", "project_path": "/my/dbt", "target_path": "build"},
                    read_only=True,
                )
            except ImportError:
                pytest.skip("metronome_pulse_dbt not installed")  # ty: ignore[too-many-positional-arguments]

    def test_dbt_cloud_mode(self):
        """Verify cloud config keys are forwarded correctly."""
        from datametronome_podium.core.connector_factory import _build_dbt_connector

        with patch(
            "datametronome_podium.core.connector_factory.DbtReadonlyPulse",
            create=True,
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            try:
                _build_dbt_connector(
                    {
                        "mode": "cloud",
                        "api_token": "tok",
                        "account_id": "123",
                        "job_id": "456",
                    },
                    read_only=True,
                )
            except ImportError:
                pytest.skip("metronome_pulse_dbt not installed")  # ty: ignore[too-many-positional-arguments]


class TestDbtInStaveTypes:
    """Verify 'dbt' is accepted as a valid data source type."""

    def test_model_accepts_dbt(self):
        from datametronome_podium.features.staves.model import SUPPORTED_DATA_SOURCES

        assert "dbt" in SUPPORTED_DATA_SOURCES

    def test_schema_accepts_dbt(self):
        from datametronome_podium.features.staves.schema import VALID_DATA_SOURCE_TYPES

        assert "dbt" in VALID_DATA_SOURCE_TYPES

    def test_stave_model_validates_dbt(self):
        from datametronome_podium.features.staves.model import Stave

        stave = Stave(
            name="my-dbt",
            data_source_type="dbt",
            connection_config={"mode": "local", "project_path": "/tmp"},
        )
        assert stave.data_source_type == "dbt"


class TestDbtEncryption:
    """Verify dbt sensitive fields are configured."""

    def test_dbt_sensitive_fields(self):
        from datametronome_podium.core.encryption import SENSITIVE_FIELDS

        assert "dbt" in SENSITIVE_FIELDS
        assert "api_token" in SENSITIVE_FIELDS["dbt"]
