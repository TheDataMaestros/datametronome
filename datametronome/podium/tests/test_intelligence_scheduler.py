"""Tests for intelligence Beat schedule management."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from datametronome_podium.services.intelligence_scheduler import (
    register_daily_intelligence,
    remove_daily_intelligence,
    register_prune_schedule,
)


def test_register_daily_intelligence():
    with patch("datametronome_podium.services.intelligence_scheduler.RedBeatSchedulerEntry") as mock_entry:
        mock_instance = MagicMock()
        mock_entry.return_value = mock_instance
        register_daily_intelligence("stave-1")
        mock_entry.assert_called_once()
        mock_instance.save.assert_called_once()


def test_remove_daily_intelligence():
    with patch("datametronome_podium.services.intelligence_scheduler.RedBeatSchedulerEntry") as mock_entry:
        mock_instance = MagicMock()
        mock_entry.from_key.return_value = mock_instance
        remove_daily_intelligence("stave-1")
        mock_instance.delete.assert_called_once()


def test_remove_nonexistent_schedule_is_safe():
    with patch("datametronome_podium.services.intelligence_scheduler.RedBeatSchedulerEntry") as mock_entry:
        mock_entry.from_key.side_effect = KeyError("not found")
        # Should not raise
        remove_daily_intelligence("stave-nonexistent")
