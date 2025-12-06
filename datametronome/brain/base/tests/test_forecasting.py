"""
Unit tests for SARIMA forecasting module.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from datametronome_brain_base.forecasting import SarimaForecaster, ForecastResult


class TestSarimaForecaster:
    """Tests for SarimaForecaster class."""
    
    @pytest.fixture
    def sample_time_series(self):
        """Generate sample time-series data with trend and seasonality."""
        np.random.seed(42)
        n = 100
        dates = pd.date_range(start='2020-01-01', periods=n, freq='D')
        
        # Generate time series with trend and seasonality
        trend = np.linspace(100, 200, n)
        seasonal = 10 * np.sin(2 * np.pi * np.arange(n) / 12)  # Monthly seasonality
        noise = np.random.normal(0, 5, n)
        values = trend + seasonal + noise
        
        return pd.Series(values, index=dates)
    
    @pytest.fixture
    def forecaster(self):
        """Create a SarimaForecaster instance."""
        return SarimaForecaster(
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12),
        )
    
    def test_initialization(self):
        """Test forecaster initialization."""
        forecaster = SarimaForecaster(
            order=(2, 1, 2),
            seasonal_order=(1, 1, 1, 12),
            trend="c",
        )
        
        assert forecaster.order == (2, 1, 2)
        assert forecaster.seasonal_order == (1, 1, 1, 12)
        assert forecaster.trend == "c"
        assert forecaster.model is None
        assert forecaster.fitted_model is None
    
    def test_train_success(self, forecaster, sample_time_series):
        """Test successful model training."""
        result = forecaster.train(sample_time_series)
        
        assert result["success"] is True
        assert "model_info" in result
        assert forecaster.fitted_model is not None
        assert forecaster.training_data is not None
        assert len(forecaster.training_data) == len(sample_time_series)
    
    def test_train_with_list(self, forecaster):
        """Test training with list input."""
        data = [100 + i + np.random.normal(0, 5) for i in range(50)]
        result = forecaster.train(data)
        
        assert result["success"] is True
        assert forecaster.fitted_model is not None
    
    def test_train_with_numpy_array(self, forecaster):
        """Test training with numpy array input."""
        data = np.array([100 + i + np.random.normal(0, 5) for i in range(50)])
        result = forecaster.train(data)
        
        assert result["success"] is True
        assert forecaster.fitted_model is not None
    
    def test_train_insufficient_data(self, forecaster):
        """Test training with insufficient data."""
        data = [1, 2, 3]  # Too few points
        
        with pytest.raises(ValueError, match="Insufficient data"):
            forecaster.train(data)
    
    def test_train_with_nans(self, forecaster):
        """Test training with NaN values (should be removed)."""
        data = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0, np.nan, 7.0, 8.0, 9.0, 10.0] * 5)
        result = forecaster.train(data)
        
        assert result["success"] is True
        assert forecaster.fitted_model is not None
    
    def test_forecast_before_training(self, forecaster):
        """Test that forecast fails before training."""
        with pytest.raises(ValueError, match="Model must be trained"):
            forecaster.forecast()
    
    def test_forecast_success(self, forecaster, sample_time_series):
        """Test successful forecast generation."""
        forecaster.train(sample_time_series)
        result = forecaster.forecast(steps=1, confidence_level=95.0)
        
        assert isinstance(result, ForecastResult)
        assert result.forecast_value is not None
        assert result.lower_bound < result.forecast_value
        assert result.upper_bound > result.forecast_value
        assert result.confidence_level == 95.0
        assert result.is_anomaly is False  # No observed value
        assert result.observed_value is None
    
    def test_forecast_multiple_steps(self, forecaster, sample_time_series):
        """Test forecasting multiple steps ahead."""
        forecaster.train(sample_time_series)
        result = forecaster.forecast(steps=5, confidence_level=90.0)
        
        assert isinstance(result, ForecastResult)
        assert result.confidence_level == 90.0
    
    def test_detect_anomaly_before_training(self, forecaster):
        """Test that anomaly detection fails before training."""
        with pytest.raises(ValueError, match="Model must be trained"):
            forecaster.detect_anomaly(100.0)
    
    def test_detect_anomaly_normal_value(self, forecaster, sample_time_series):
        """Test anomaly detection with normal (non-anomalous) value."""
        forecaster.train(sample_time_series)
        
        # Get forecast first to see the expected range
        forecast = forecaster.forecast(confidence_level=95.0)
        normal_value = forecast.forecast_value  # Use forecast as normal value
        
        result = forecaster.detect_anomaly(normal_value, confidence_level=95.0)
        
        assert isinstance(result, ForecastResult)
        assert result.observed_value == normal_value
        assert result.is_anomaly is False
        assert result.p_value is not None
    
    def test_detect_anomaly_outlier_value(self, forecaster, sample_time_series):
        """Test anomaly detection with anomalous (outlier) value."""
        forecaster.train(sample_time_series)
        
        # Use an extreme value that should be outside confidence interval
        extreme_value = 1000.0
        
        result = forecaster.detect_anomaly(extreme_value, confidence_level=95.0)
        
        assert isinstance(result, ForecastResult)
        assert result.observed_value == extreme_value
        assert result.is_anomaly is True
        assert result.p_value is not None
    
    def test_auto_select_order(self, forecaster, sample_time_series):
        """Test automatic order selection."""
        result = forecaster.auto_select_order(
            sample_time_series,
            max_p=2,
            max_d=1,
            max_q=2,
            max_P=1,
            max_D=1,
            max_Q=1,
            seasonal_periods=12,
        )
        
        assert "order" in result
        assert "seasonal_order" in result
        assert "score" in result
        assert forecaster.fitted_model is not None
        assert forecaster.order == result["order"]
        assert forecaster.seasonal_order == result["seasonal_order"]
    
    def test_auto_select_order_insufficient_data(self, forecaster):
        """Test auto order selection with insufficient data."""
        data = [1, 2, 3, 4, 5]
        
        with pytest.raises(ValueError):
            forecaster.auto_select_order(data)
    
    def test_different_confidence_levels(self, forecaster, sample_time_series):
        """Test forecasting with different confidence levels."""
        forecaster.train(sample_time_series)
        
        result_90 = forecaster.forecast(confidence_level=90.0)
        result_95 = forecaster.forecast(confidence_level=95.0)
        result_99 = forecaster.forecast(confidence_level=99.0)
        
        # Higher confidence should have wider intervals
        interval_90 = result_90.upper_bound - result_90.lower_bound
        interval_95 = result_95.upper_bound - result_95.lower_bound
        interval_99 = result_99.upper_bound - result_99.lower_bound
        
        assert interval_90 < interval_95 < interval_99







