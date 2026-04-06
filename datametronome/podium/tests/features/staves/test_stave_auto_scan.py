"""Test that stave creation triggers auto-scan."""
from unittest.mock import patch


def test_dispatch_auto_scan_calls_apply_async():
    """Verify _dispatch_auto_scan calls run_auto_scan.apply_async with countdown=0."""
    with patch("datametronome_podium.tasks.intelligence_tasks.run_auto_scan") as mock_scan:
        from datametronome_podium.features.staves.router import _dispatch_auto_scan
        _dispatch_auto_scan("stave-123")
        mock_scan.apply_async.assert_called_once_with(args=["stave-123"], countdown=0)


def test_dispatch_auto_scan_swallows_errors():
    """If Celery is not available, dispatch should log a retry and not raise."""
    with patch("datametronome_podium.tasks.intelligence_tasks.run_auto_scan") as mock_scan:
        mock_scan.apply_async.side_effect = Exception("Celery not available")
        from datametronome_podium.features.staves.router import _dispatch_auto_scan
        # Should not raise even if both dispatch attempts fail
        _dispatch_auto_scan("stave-456")
