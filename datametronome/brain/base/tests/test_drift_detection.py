"""
Unit tests for drift detection module.
"""

import numpy as np
import pandas as pd
import pytest
from datametronome_brain_base.drift_detection import DriftDetector, DriftResult


class TestDriftDetector:
    """Tests for DriftDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a DriftDetector instance."""
        return DriftDetector()

    @pytest.fixture
    def baseline_data(self):
        """Generate baseline/reference data."""
        np.random.seed(42)
        return np.random.normal(100, 10, 1000)

    @pytest.fixture
    def similar_data(self):
        """Generate data similar to baseline (no drift)."""
        np.random.seed(43)
        return np.random.normal(100, 10, 1000)

    @pytest.fixture
    def drifted_data(self):
        """Generate data with drift (different distribution)."""
        np.random.seed(44)
        return np.random.normal(120, 15, 1000)  # Different mean and std

    def test_kolmogorov_smirnov_no_drift(self, detector, baseline_data, similar_data):
        """Test KS test with no drift (similar distributions)."""
        result = detector.kolmogorov_smirnov_test(
            baseline_data,
            similar_data,
            critical_p_value=0.05,
        )

        assert isinstance(result, DriftResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert result.drift_detected is False  # Should not detect drift
        assert 0.0 <= result.p_value <= 1.0
        assert result.test_statistic >= 0.0
        assert result.baseline_size == len(baseline_data)
        assert result.current_size == len(similar_data)
        assert "baseline_mean" in result.metadata

    def test_kolmogorov_smirnov_with_drift(self, detector, baseline_data, drifted_data):
        """Test KS test with drift (different distributions)."""
        result = detector.kolmogorov_smirnov_test(
            baseline_data,
            drifted_data,
            critical_p_value=0.05,
        )

        assert isinstance(result, DriftResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert result.drift_detected is True  # Should detect drift
        assert result.p_value < 0.05
        assert result.test_statistic > 0.0

    def test_kolmogorov_smirnov_with_list(self, detector, baseline_data):
        """Test KS test with list input."""
        current = list(baseline_data + np.random.normal(0, 1, len(baseline_data)))
        result = detector.kolmogorov_smirnov_test(
            list(baseline_data),
            current,
        )

        assert isinstance(result, DriftResult)
        assert result.drift_detected is False  # Similar data

    def test_kolmogorov_smirnov_with_series(self, detector, baseline_data):
        """Test KS test with pandas Series input."""
        baseline_series = pd.Series(baseline_data)
        current_series = pd.Series(
            baseline_data + np.random.normal(0, 1, len(baseline_data))
        )

        result = detector.kolmogorov_smirnov_test(
            baseline_series,
            current_series,
        )

        assert isinstance(result, DriftResult)

    def test_kolmogorov_smirnov_with_nans(self, detector, baseline_data):
        """Test KS test with NaN values (should be removed)."""
        current = baseline_data.copy()
        current[::10] = np.nan  # Add some NaNs

        result = detector.kolmogorov_smirnov_test(
            baseline_data,
            current,
        )

        assert isinstance(result, DriftResult)
        assert result.current_size < len(current)  # NaNs removed

    def test_kolmogorov_smirnov_insufficient_data(self, detector):
        """Test KS test with insufficient data."""
        baseline = [1.0]
        current = [2.0]

        with pytest.raises(ValueError, match="too small"):
            detector.kolmogorov_smirnov_test(baseline, current)

    def test_kolmogorov_smirnov_different_critical_values(
        self, detector, baseline_data, drifted_data
    ):
        """Test KS test with different critical p-values."""
        result_01 = detector.kolmogorov_smirnov_test(
            baseline_data,
            drifted_data,
            critical_p_value=0.01,
        )

        result_05 = detector.kolmogorov_smirnov_test(
            baseline_data,
            drifted_data,
            critical_p_value=0.05,
        )

        result_10 = detector.kolmogorov_smirnov_test(
            baseline_data,
            drifted_data,
            critical_p_value=0.10,
        )

        # All should detect drift (p-value is very small)
        assert result_01.drift_detected is True
        assert result_05.drift_detected is True
        assert result_10.drift_detected is True

    def test_kolmogorov_smirnov_alternatives(
        self, detector, baseline_data, drifted_data
    ):
        """Test KS test with different alternative hypotheses."""
        result_two_sided = detector.kolmogorov_smirnov_test(
            baseline_data,
            drifted_data,
            alternative="two-sided",
        )

        result_less = detector.kolmogorov_smirnov_test(
            baseline_data,
            drifted_data,
            alternative="less",
        )

        result_greater = detector.kolmogorov_smirnov_test(
            baseline_data,
            drifted_data,
            alternative="greater",
        )

        assert result_two_sided.test_statistic >= 0.0
        assert result_less.test_statistic >= 0.0
        assert result_greater.test_statistic >= 0.0

    def test_anderson_darling_test(self, detector, baseline_data, similar_data):
        """Test Anderson-Darling test."""
        result = detector.anderson_darling_test(
            baseline_data,
            similar_data,
            critical_p_value=0.05,
        )

        assert isinstance(result, DriftResult)
        assert result.test_name == "anderson_darling"
        assert 0.0 <= result.p_value <= 1.0
        assert result.test_statistic >= 0.0
        assert "critical_values" in result.metadata

    def test_anderson_darling_with_drift(self, detector, baseline_data, drifted_data):
        """Test AD test with drift."""
        result = detector.anderson_darling_test(
            baseline_data,
            drifted_data,
            critical_p_value=0.05,
        )

        assert isinstance(result, DriftResult)
        assert result.drift_detected is True

    def test_mann_whitney_u_test(self, detector, baseline_data, similar_data):
        """Test Mann-Whitney U test."""
        result = detector.mann_whitney_u_test(
            baseline_data,
            similar_data,
            critical_p_value=0.05,
        )

        assert isinstance(result, DriftResult)
        assert result.test_name == "mann_whitney_u"
        assert 0.0 <= result.p_value <= 1.0
        assert result.test_statistic >= 0.0
        assert "baseline_median" in result.metadata

    def test_mann_whitney_u_with_drift(self, detector, baseline_data, drifted_data):
        """Test Mann-Whitney U test with drift."""
        result = detector.mann_whitney_u_test(
            baseline_data,
            drifted_data,
            critical_p_value=0.05,
        )

        assert isinstance(result, DriftResult)
        assert result.drift_detected is True

    def test_mann_whitney_u_alternatives(self, detector, baseline_data, drifted_data):
        """Test Mann-Whitney U test with different alternatives."""
        result_two_sided = detector.mann_whitney_u_test(
            baseline_data,
            drifted_data,
            alternative="two-sided",
        )

        result_less = detector.mann_whitney_u_test(
            baseline_data,
            drifted_data,
            alternative="less",
        )

        result_greater = detector.mann_whitney_u_test(
            baseline_data,
            drifted_data,
            alternative="greater",
        )

        assert result_two_sided.test_statistic >= 0.0
        assert result_less.test_statistic >= 0.0
        assert result_greater.test_statistic >= 0.0

    def test_invalid_critical_p_value(self, detector, baseline_data, similar_data):
        """Test with invalid critical p-value."""
        with pytest.raises(ValueError, match="Critical p-value"):
            detector.kolmogorov_smirnov_test(
                baseline_data,
                similar_data,
                critical_p_value=1.5,  # Invalid
            )

    def test_invalid_data_type(self, detector):
        """Test with invalid data type."""
        with pytest.raises(ValueError, match="Unsupported data type"):
            detector.kolmogorov_smirnov_test(
                "not a list",
                [1, 2, 3],
            )
