# DataMetronome Brain Base

> **📁 DIRECTORY TYPE**: Internal Infrastructure Code  
> **🚫 NOT A PYPI PACKAGE** - This is internal code, not a public Python library

Base analytics library for DataMetronome.

## Overview

This package provides core data analysis capabilities including data profiling, anomaly detection, and statistical analysis.

## Features

- Data profiling and statistics
- Anomaly detection algorithms
- Statistical analysis tools
- Pydantic-based data models

## Installation

```bash
pip install -e .
```

## Usage

```python
from datametronome_brain_base.profiler import DataProfiler

# Create profiler instance
profiler = DataProfiler()

# Profile a DataFrame
profile = profiler.profile_dataframe(df, "my_table")

# Detect anomalies
anomalies = profiler.detect_anomalies(df, "numeric_column")
```




