"""
DataMetronome Brain Base - Basic analytics library.

This package provides fundamental analytics capabilities for data profiling,
statistical analysis, and basic anomaly detection.
"""

__version__ = "0.1.0"
__author__ = "DataMetronome Team"
__email__ = "team@datametronome.dev"

from .profiler import DataProfiler, ColumnProfile, TableProfile, AnomalyResult
from .forecasting import SarimaForecaster, ForecastResult
from .drift_detection import DriftDetector, DriftResult

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
