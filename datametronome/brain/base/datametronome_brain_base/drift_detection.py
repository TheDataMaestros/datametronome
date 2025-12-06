"""
Drift detection using statistical tests.

This module provides Kolmogorov-Smirnov and other statistical tests
for detecting distribution drift in data profiles.
"""

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from scipy import stats

logger = logging.getLogger(__name__)


class DriftResult(BaseModel):
    """Result of a drift detection test."""
    
    drift_detected: bool = Field(description="Whether drift was detected")
    test_statistic: float = Field(description="Test statistic value")
    p_value: float = Field(ge=0.0, le=1.0, description="P-value of the test")
    critical_p_value: float = Field(ge=0.0, le=1.0, description="Critical p-value threshold")
    test_name: str = Field(description="Name of the statistical test used")
    baseline_size: int = Field(description="Size of baseline/reference sample")
    current_size: int = Field(description="Size of current/comparison sample")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional test information")


class DriftDetector:
    """
    Drift detector for comparing data distributions.
    
    This class provides methods to detect changes in data distributions
    using statistical tests like Kolmogorov-Smirnov.
    """
    
    def kolmogorov_smirnov_test(
        self,
        baseline: list[float] | np.ndarray | pd.Series,
        current: list[float] | np.ndarray | pd.Series,
        critical_p_value: float = 0.05,
        alternative: str = "two-sided",
    ) -> DriftResult:
        """
        Perform Kolmogorov-Smirnov test to detect distribution drift.
        
        The KS test compares the empirical distribution functions of two samples
        to determine if they come from the same distribution.
        
        Args:
            baseline: Reference/baseline distribution
            current: Current distribution to compare against baseline
            critical_p_value: P-value threshold for drift detection (default: 0.05)
            alternative: Alternative hypothesis ('two-sided', 'less', 'greater')
            
        Returns:
            DriftResult indicating if drift was detected
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Convert to numpy arrays
        baseline_array = self._to_array(baseline)
        current_array = self._to_array(current)
        
        # Remove NaN values
        baseline_array = baseline_array[~np.isnan(baseline_array)]
        current_array = current_array[~np.isnan(current_array)]
        
        # Validate inputs
        if len(baseline_array) < 2:
            raise ValueError(f"Baseline sample too small: {len(baseline_array)}")
        if len(current_array) < 2:
            raise ValueError(f"Current sample too small: {len(current_array)}")
        
        if not 0 < critical_p_value <= 1:
            raise ValueError(f"Critical p-value must be between 0 and 1, got {critical_p_value}")
        
        # Perform KS test
        try:
            statistic, p_value = stats.ks_2samp(
                baseline_array,
                current_array,
                alternative=alternative,
            )
            
            drift_detected = p_value < critical_p_value
            
            logger.info(
                f"KS test: statistic={statistic:.4f}, p_value={p_value:.4f}, "
                f"drift_detected={drift_detected}"
            )
            
            return DriftResult(
                drift_detected=drift_detected,
                test_statistic=float(statistic),
                p_value=float(p_value),
                critical_p_value=critical_p_value,
                test_name="kolmogorov_smirnov",
                baseline_size=len(baseline_array),
                current_size=len(current_array),
                metadata={
                    "alternative": alternative,
                    "baseline_mean": float(np.mean(baseline_array)),
                    "baseline_std": float(np.std(baseline_array)),
                    "current_mean": float(np.mean(current_array)),
                    "current_std": float(np.std(current_array)),
                },
            )
            
        except Exception as e:
            logger.error(f"KS test failed: {e}")
            raise ValueError(f"KS test execution failed: {str(e)}")
    
    def anderson_darling_test(
        self,
        baseline: list[float] | np.ndarray | pd.Series,
        current: list[float] | np.ndarray | pd.Series,
        critical_p_value: float = 0.05,
    ) -> DriftResult:
        """
        Perform Anderson-Darling test to detect distribution drift.
        
        The AD test is more sensitive to differences in the tails of distributions
        compared to the KS test.
        
        Args:
            baseline: Reference/baseline distribution
            current: Current distribution to compare against baseline
            critical_p_value: P-value threshold for drift detection
            
        Returns:
            DriftResult indicating if drift was detected
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Convert to numpy arrays
        baseline_array = self._to_array(baseline)
        current_array = self._to_array(current)
        
        # Remove NaN values
        baseline_array = baseline_array[~np.isnan(baseline_array)]
        current_array = current_array[~np.isnan(current_array)]
        
        # Validate inputs
        if len(baseline_array) < 2:
            raise ValueError(f"Baseline sample too small: {len(baseline_array)}")
        if len(current_array) < 2:
            raise ValueError(f"Current sample too small: {len(current_array)}")
        
        # Combine samples for AD test
        combined = np.concatenate([baseline_array, current_array])
        labels = np.concatenate([
            np.zeros(len(baseline_array)),
            np.ones(len(current_array)),
        ])
        
        # Perform Anderson-Darling test
        # Note: scipy doesn't have a direct 2-sample AD test, so we use a workaround
        # by testing if both samples come from the same distribution
        try:
            # Use k-sample AD test
            statistic, critical_values, significance_level = stats.anderson_ksamp([
                baseline_array,
                current_array,
            ])
            
            # Approximate p-value from significance level
            # Lower statistic means less evidence against null hypothesis
            p_value = max(0.0, min(1.0, significance_level / 100.0))
            
            drift_detected = p_value < critical_p_value
            
            logger.info(
                f"AD test: statistic={statistic:.4f}, p_value={p_value:.4f}, "
                f"drift_detected={drift_detected}"
            )
            
            return DriftResult(
                drift_detected=drift_detected,
                test_statistic=float(statistic),
                p_value=float(p_value),
                critical_p_value=critical_p_value,
                test_name="anderson_darling",
                baseline_size=len(baseline_array),
                current_size=len(current_array),
                metadata={
                    "critical_values": [float(cv) for cv in critical_values],
                    "significance_level": float(significance_level),
                    "baseline_mean": float(np.mean(baseline_array)),
                    "baseline_std": float(np.std(baseline_array)),
                    "current_mean": float(np.mean(current_array)),
                    "current_std": float(np.std(current_array)),
                },
            )
            
        except Exception as e:
            logger.error(f"AD test failed: {e}")
            raise ValueError(f"AD test execution failed: {str(e)}")
    
    def mann_whitney_u_test(
        self,
        baseline: list[float] | np.ndarray | pd.Series,
        current: list[float] | np.ndarray | pd.Series,
        critical_p_value: float = 0.05,
        alternative: str = "two-sided",
    ) -> DriftResult:
        """
        Perform Mann-Whitney U test (Wilcoxon rank-sum test) to detect distribution drift.
        
        This is a non-parametric test that compares medians and distributions.
        Useful when data is not normally distributed.
        
        Args:
            baseline: Reference/baseline distribution
            current: Current distribution to compare against baseline
            critical_p_value: P-value threshold for drift detection
            alternative: Alternative hypothesis ('two-sided', 'less', 'greater')
            
        Returns:
            DriftResult indicating if drift was detected
        """
        # Convert to numpy arrays
        baseline_array = self._to_array(baseline)
        current_array = self._to_array(current)
        
        # Remove NaN values
        baseline_array = baseline_array[~np.isnan(baseline_array)]
        current_array = current_array[~np.isnan(current_array)]
        
        # Validate inputs
        if len(baseline_array) < 2:
            raise ValueError(f"Baseline sample too small: {len(baseline_array)}")
        if len(current_array) < 2:
            raise ValueError(f"Current sample too small: {len(current_array)}")
        
        try:
            statistic, p_value = stats.mannwhitneyu(
                baseline_array,
                current_array,
                alternative=alternative,
            )
            
            drift_detected = p_value < critical_p_value
            
            logger.info(
                f"Mann-Whitney U test: statistic={statistic:.4f}, p_value={p_value:.4f}, "
                f"drift_detected={drift_detected}"
            )
            
            return DriftResult(
                drift_detected=drift_detected,
                test_statistic=float(statistic),
                p_value=float(p_value),
                critical_p_value=critical_p_value,
                test_name="mann_whitney_u",
                baseline_size=len(baseline_array),
                current_size=len(current_array),
                metadata={
                    "alternative": alternative,
                    "baseline_median": float(np.median(baseline_array)),
                    "current_median": float(np.median(current_array)),
                    "baseline_mean": float(np.mean(baseline_array)),
                    "current_mean": float(np.mean(current_array)),
                },
            )
            
        except Exception as e:
            logger.error(f"Mann-Whitney U test failed: {e}")
            raise ValueError(f"Mann-Whitney U test execution failed: {str(e)}")
    
    def _to_array(self, data: list[float] | np.ndarray | pd.Series) -> np.ndarray:
        """Convert various input types to numpy array."""
        if isinstance(data, pd.Series):
            return data.values
        elif isinstance(data, list):
            return np.array(data)
        elif isinstance(data, np.ndarray):
            return data
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")







