# DataMetronome Brain Base

> **📁 DIRECTORY TYPE**: Internal Infrastructure Code  
> **🚫 NOT A PYPI PACKAGE** - This is internal code, not a public Python library

Base analytics library for DataMetronome.

## Overview

This package provides core data analysis capabilities including data profiling, anomaly detection, statistical analysis, time-series forecasting, and distribution drift detection.

## Features

- **Data Profiling**: Comprehensive column and table profiling with statistics
- **Anomaly Detection**: IQR, Z-score, and Isolation Forest methods
- **SARIMA Forecasting**: Time-series forecasting for anomaly detection (Level 2 checks)
- **Drift Detection**: Kolmogorov-Smirnov, Anderson-Darling, and Mann-Whitney U tests
- **Statistical Utilities**: Time-series and distribution analysis tools
- **Pydantic-based Models**: Type-safe data models for all results

## Installation

```bash
cd datametronome/brain/base
pip install -e .
```

## Dependencies

- pandas>=2.0.0
- numpy>=1.24.0
- scipy>=1.10.0
- scikit-learn>=1.3.0
- statsmodels>=0.14.0 (for SARIMA)
- matplotlib>=3.7.0
- seaborn>=0.12.0

## Usage

### Data Profiling

```python
from datametronome_brain_base.profiler import DataProfiler
import pandas as pd

# Create profiler instance
profiler = DataProfiler()

# Profile a DataFrame
df = pd.DataFrame({"col1": [1, 2, 3, 4, 5], "col2": ["a", "b", "c", "d", "e"]})
profile = profiler.profile_table(df)

# Detect anomalies
anomalies = profiler.detect_anomalies(df["col1"], method="iqr")
```

### SARIMA Forecasting (Level 2 Checks)

```python
from datametronome_brain_base.forecasting import SarimaForecaster
import pandas as pd
import numpy as np

# Create forecaster
forecaster = SarimaForecaster(
    order=(1, 1, 1),
    seasonal_order=(1, 1, 1, 12),  # Monthly seasonality
)

# Train on historical data
historical_data = pd.Series([100 + i + np.random.normal(0, 5) for i in range(100)])
forecaster.train(historical_data)

# Generate forecast
forecast = forecaster.forecast(steps=1, confidence_level=95.0)
print(f"Forecast: {forecast.forecast_value}")
print(f"Confidence interval: [{forecast.lower_bound}, {forecast.upper_bound}]")

# Detect anomaly
result = forecaster.detect_anomaly(observed_value=150.0, confidence_level=95.0)
if result.is_anomaly:
    print(f"Anomaly detected! Value {result.observed_value} is outside forecast bounds")
```

### Drift Detection (Level 2 Checks)

```python
from datametronome_brain_base.drift_detection import DriftDetector
import numpy as np

# Create detector
detector = DriftDetector()

# Baseline/reference distribution
baseline = np.random.normal(100, 10, 1000)

# Current distribution to compare
current = np.random.normal(120, 15, 1000)  # Different distribution

# Perform Kolmogorov-Smirnov test
result = detector.kolmogorov_smirnov_test(
    baseline,
    current,
    critical_p_value=0.05,
)

if result.drift_detected:
    print(f"Drift detected! p-value: {result.p_value:.4f}")
    print(f"Test statistic: {result.test_statistic:.4f}")
```

### Auto Model Selection

```python
# Automatically select optimal SARIMA parameters
forecaster = SarimaForecaster()
optimal = forecaster.auto_select_order(
    historical_data,
    max_p=3,
    max_d=2,
    max_q=3,
    seasonal_periods=12,
)
print(f"Optimal order: {optimal['order']}")
print(f"Optimal seasonal order: {optimal['seasonal_order']}")
```

## Module Structure

- **`profiler.py`**: Data profiling and basic anomaly detection
- **`forecasting.py`**: SARIMA time-series forecasting for anomaly detection
- **`drift_detection.py`**: Statistical tests for distribution drift detection

## Integration with Level 2 Checks

This library is used by the Podium's Level 2 check handlers:

- **`forecast` check**: Uses `SarimaForecaster` to detect anomalies in time-series metrics
- **`data_profile_drift` check**: Uses `DriftDetector` to detect distribution changes

## Testing

```bash
cd datametronome/brain/base
pytest tests/ -v
```

## License

Internal use only - part of DataMetronome project.




