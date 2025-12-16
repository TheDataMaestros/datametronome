"""
SARIMA forecasting for time-series anomaly detection.

This module provides SARIMA (Seasonal AutoRegressive Integrated Moving Average)
forecasting capabilities for detecting anomalies in time-series metrics.
"""

import logging
import warnings
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Suppress convergence warnings for cleaner output
warnings.filterwarnings("ignore", category=ConvergenceWarning)

logger = logging.getLogger(__name__)


class ForecastResult(BaseModel):
    """Result of a SARIMA forecast."""

    forecast_value: float = Field(description="Point forecast for next period")
    lower_bound: float = Field(description="Lower bound of confidence interval")
    upper_bound: float = Field(description="Upper bound of confidence interval")
    confidence_level: float = Field(
        ge=0.0, le=100.0, description="Confidence level (0-100)"
    )
    is_anomaly: bool = Field(description="Whether the observed value is anomalous")
    observed_value: Optional[float] = Field(None, description="Observed value to check")
    p_value: Optional[float] = Field(None, description="P-value for anomaly detection")
    model_info: dict[str, Any] = Field(
        default_factory=dict, description="Model information"
    )


class SarimaForecaster:
    """
    SARIMA forecaster for time-series anomaly detection.

    This class provides methods to:
    - Train SARIMA models on historical time-series data
    - Generate forecasts with confidence intervals
    - Detect anomalies by comparing observed values to forecast bounds
    """

    def __init__(
        self,
        order: tuple[int, int, int] = (1, 1, 1),
        seasonal_order: tuple[int, int, int, int] = (1, 1, 1, 12),
        trend: str = "c",
        enforce_stationarity: bool = True,
        enforce_invertibility: bool = True,
    ):
        """
        Initialize SARIMA forecaster.

        Args:
            order: (p, d, q) order of the ARIMA model
            seasonal_order: (P, D, Q, s) seasonal order of the SARIMA model
            trend: Trend component ('n', 'c', 't', 'ct')
            enforce_stationarity: Whether to enforce stationarity
            enforce_invertibility: Whether to enforce invertibility
        """
        self.order = order
        self.seasonal_order = seasonal_order
        self.trend = trend
        self.enforce_stationarity = enforce_stationarity
        self.enforce_invertibility = enforce_invertibility
        self.model: Optional[SARIMAX] = None
        self.fitted_model: Optional[Any] = None
        self.training_data: Optional[pd.Series] = None

    def train(self, data: pd.Series | list[float] | np.ndarray) -> dict[str, Any]:
        """
        Train SARIMA model on historical data.

        Args:
            data: Time-series data (pandas Series, list, or numpy array)

        Returns:
            Dictionary with training results and model information

        Raises:
            ValueError: If data is insufficient or invalid
        """
        # Convert to pandas Series if needed
        if isinstance(data, (list, np.ndarray)):
            data = pd.Series(data)
        elif not isinstance(data, pd.Series):
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Validate data
        if len(data) < max(
            self.order[0] + self.order[2],
            self.seasonal_order[0] + self.seasonal_order[2] + self.seasonal_order[3],
        ):
            raise ValueError(
                f"Insufficient data: need at least {max(self.order[0] + self.order[2], self.seasonal_order[0] + self.seasonal_order[2] + self.seasonal_order[3])} "
                f"points, got {len(data)}"
            )

        # Remove NaN values
        data = data.dropna()
        if len(data) < 10:
            raise ValueError(f"Too few non-NaN values: {len(data)}")

        self.training_data = data

        try:
            # Fit SARIMA model
            self.model = SARIMAX(
                data,
                order=self.order,
                seasonal_order=self.seasonal_order,
                trend=self.trend,
                enforce_stationarity=self.enforce_stationarity,
                enforce_invertibility=self.enforce_invertibility,
            )

            self.fitted_model = self.model.fit(disp=False)

            # Get model information
            model_info = {
                "aic": float(self.fitted_model.aic),
                "bic": float(self.fitted_model.bic),
                "llf": float(self.fitted_model.llf),
                "order": self.order,
                "seasonal_order": self.seasonal_order,
                "training_samples": len(data),
                "model_summary": str(self.fitted_model.summary()),
            }

            logger.info(
                f"SARIMA model trained successfully. AIC: {model_info['aic']:.2f}"
            )

            return {
                "success": True,
                "model_info": model_info,
            }

        except Exception as e:
            logger.error(f"Failed to train SARIMA model: {e}")
            raise ValueError(f"SARIMA model training failed: {str(e)}")

    def forecast(
        self,
        steps: int = 1,
        confidence_level: float = 95.0,
        alpha: Optional[float] = None,
    ) -> ForecastResult:
        """
        Generate forecast for future periods.

        Args:
            steps: Number of periods ahead to forecast
            confidence_level: Confidence level (0-100) for prediction intervals
            alpha: Significance level (alternative to confidence_level)

        Returns:
            ForecastResult with forecast and confidence intervals

        Raises:
            ValueError: If model is not trained
        """
        if self.fitted_model is None:
            raise ValueError("Model must be trained before forecasting")

        # Convert confidence level to alpha
        if alpha is None:
            alpha = 1.0 - (confidence_level / 100.0)

        # Generate forecast
        forecast = self.fitted_model.get_forecast(steps=steps)
        forecast_mean = forecast.predicted_mean
        forecast_ci = forecast.conf_int(alpha=alpha)

        # Extract values
        forecast_value = float(forecast_mean.iloc[-1])
        lower_bound = float(forecast_ci.iloc[-1, 0])
        upper_bound = float(forecast_ci.iloc[-1, 1])

        return ForecastResult(
            forecast_value=forecast_value,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=confidence_level,
            is_anomaly=False,  # No observed value to compare yet
            model_info={
                "steps": steps,
                "order": self.order,
                "seasonal_order": self.seasonal_order,
            },
        )

    def detect_anomaly(
        self,
        observed_value: float,
        confidence_level: float = 95.0,
        alpha: Optional[float] = None,
    ) -> ForecastResult:
        """
        Detect if an observed value is anomalous compared to forecast.

        Args:
            observed_value: The observed value to check
            confidence_level: Confidence level (0-100) for prediction intervals
            alpha: Significance level (alternative to confidence_level)

        Returns:
            ForecastResult indicating if the value is anomalous

        Raises:
            ValueError: If model is not trained
        """
        # Generate forecast
        forecast_result = self.forecast(
            steps=1, confidence_level=confidence_level, alpha=alpha
        )

        # Check if observed value is outside confidence interval
        is_anomaly = (
            observed_value < forecast_result.lower_bound
            or observed_value > forecast_result.upper_bound
        )

        # Calculate how far outside the interval (for p-value approximation)
        if is_anomaly:
            if observed_value < forecast_result.lower_bound:
                distance = forecast_result.lower_bound - observed_value
                bound_range = forecast_result.upper_bound - forecast_result.lower_bound
            else:
                distance = observed_value - forecast_result.upper_bound
                bound_range = forecast_result.upper_bound - forecast_result.lower_bound

            # Approximate p-value based on distance from bounds
            # This is a simplified approach; more sophisticated methods could be used
            normalized_distance = distance / bound_range if bound_range > 0 else 1.0
            p_value = max(
                0.0,
                min(
                    1.0, (1.0 - confidence_level / 100.0) * (1.0 - normalized_distance)
                ),
            )
        else:
            p_value = 1.0 - (confidence_level / 100.0)

        forecast_result.observed_value = observed_value
        forecast_result.is_anomaly = is_anomaly
        forecast_result.p_value = p_value

        return forecast_result

    def auto_select_order(
        self,
        data: pd.Series | list[float] | np.ndarray,
        max_p: int = 3,
        max_d: int = 2,
        max_q: int = 3,
        max_P: int = 2,
        max_D: int = 1,
        max_Q: int = 2,
        seasonal_periods: int = 12,
        information_criterion: str = "aic",
    ) -> dict[str, Any]:
        """
        Automatically select optimal SARIMA order using grid search.

        Args:
            data: Time-series data
            max_p, max_d, max_q: Maximum values for non-seasonal order
            max_P, max_D, max_Q: Maximum values for seasonal order
            seasonal_periods: Seasonal period (s)
            information_criterion: Criterion to minimize ('aic' or 'bic')

        Returns:
            Dictionary with optimal order and model information
        """
        from itertools import product

        # Convert to pandas Series if needed
        if isinstance(data, (list, np.ndarray)):
            data = pd.Series(data)
        elif not isinstance(data, pd.Series):
            raise ValueError(f"Unsupported data type: {type(data)}")

        data = data.dropna()

        best_score = float("inf")
        best_order = None
        best_seasonal_order = None
        best_model = None

        # Grid search
        p_range = range(0, max_p + 1)
        d_range = range(0, max_d + 1)
        q_range = range(0, max_q + 1)
        P_range = range(0, max_P + 1)
        D_range = range(0, max_D + 1)
        Q_range = range(0, max_Q + 1)

        total_combinations = len(
            list(product(p_range, d_range, q_range, P_range, D_range, Q_range))
        )
        logger.info(f"Testing {total_combinations} SARIMA model combinations...")

        tested = 0
        for p, d, q, P, D, Q in product(
            p_range, d_range, q_range, P_range, D_range, Q_range
        ):
            tested += 1
            if tested % 10 == 0:
                logger.debug(f"Tested {tested}/{total_combinations} combinations...")

            try:
                model = SARIMAX(
                    data,
                    order=(p, d, q),
                    seasonal_order=(P, D, Q, seasonal_periods),
                    enforce_stationarity=True,
                    enforce_invertibility=True,
                )
                fitted = model.fit(disp=False)

                score = fitted.aic if information_criterion == "aic" else fitted.bic

                if score < best_score:
                    best_score = score
                    best_order = (p, d, q)
                    best_seasonal_order = (P, D, Q, seasonal_periods)
                    best_model = fitted

            except Exception:
                # Skip invalid combinations
                continue

        if best_order is None:
            raise ValueError("Could not find valid SARIMA model")

        logger.info(
            f"Best model: order={best_order}, seasonal_order={best_seasonal_order}, {information_criterion}={best_score:.2f}"
        )

        # Update instance with best model
        self.order = best_order
        self.seasonal_order = best_seasonal_order
        self.fitted_model = best_model

        return {
            "order": best_order,
            "seasonal_order": best_seasonal_order,
            "information_criterion": information_criterion,
            "score": float(best_score),
            "model_info": {
                "aic": float(best_model.aic),
                "bic": float(best_model.bic),
                "llf": float(best_model.llf),
            },
        }


