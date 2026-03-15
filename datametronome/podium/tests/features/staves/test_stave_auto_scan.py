"""Test that stave creation triggers auto-scan."""
from unittest.mock import patch


def test_dispatch_auto_scan_calls_delay():
    """Verify _dispatch_auto_scan calls run_auto_scan.delay."""
    with patch("datametronome_podium.tasks.intelligence_tasks.run_auto_scan") as mock_scan:
        from datametronome_podium.features.staves.router import _dispatch_auto_scan
        _dispatch_auto_scan("stave-123")
        mock_scan.delay.assert_called_once_with("stave-123")


def test_dispatch_auto_scan_swallows_errors():
    """If Celery is not available, dispatch should log and not raise."""
    with patch("datametronome_podium.tasks.intelligence_tasks.run_auto_scan") as mock_scan:
        mock_scan.delay.side_effect = Exception("Celery not available")
        from datametronome_podium.features.staves.router import _dispatch_auto_scan
        # Should not raise
        _dispatch_auto_scan("stave-456")
