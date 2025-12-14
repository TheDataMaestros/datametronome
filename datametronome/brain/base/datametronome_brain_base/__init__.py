"""
DataMetronome Brain Base - Basic analytics library.

This package provides fundamental analytics capabilities for data profiling,
statistical analysis, and basic anomaly detection.
"""

__version__ = "0.1.0"
__author__ = "DataMetronome Team"
__email__ = "team@datametronome.dev"

from .drift_detection import DriftDetector, DriftResult
from .forecasting import ForecastResult, SarimaForecaster
from .profiler import AnomalyResult, ColumnProfile, DataProfiler, TableProfile

__all__ = [
    "DataProfiler",
    "ColumnProfile",
    "TableProfile",
    "AnomalyResult",
    "SarimaForecaster",
    "ForecastResult",
    "DriftDetector",
    "DriftResult",
]
