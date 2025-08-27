"""
Data profiling and basic analytics for DataMetronome Brain.
"""

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    """Profile data for a single column."""
    
    column_name: str
    data_type: str
    total_count: int = Field(ge=0)
    null_count: int = Field(ge=0)
    null_percentage: float = Field(ge=0.0, le=100.0)
    unique_count: int = Field(ge=0)
    unique_percentage: float = Field(ge=0.0, le=100.0)
    
    # Numeric statistics
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    median_value: float | None = None
    std_value: float | None = None
    q25_value: float | None = None
    q75_value: float | None = None
    iqr_value: float | None = None
    skewness: float | None = None
    kurtosis: float | None = None
    
    # Categorical statistics
    top_values: dict[str, int] | None = None
    top_value: str | None = None
    top_value_count: int | None = None
    top_value_percentage: float | None = None
    
    # Datetime statistics
    min_date: str | None = None
    max_date: str | None = None
    date_range_days: int | None = None
    most_common_year: int | None = None
    most_common_month: int | None = None
    most_common_day_of_week: int | None = None


class TableProfile(BaseModel):
    """Profile data for an entire table."""
    
    table_name: str
    total_rows: int = Field(ge=0)
    total_columns: int = Field(ge=0)
    memory_usage_mb: float = Field(ge=0.0)
    columns: dict[str, ColumnProfile]
    summary: dict[str, Any]


class AnomalyResult(BaseModel):
    """Result of anomaly detection."""
    
    anomalies: list[int]
    anomaly_count: int = Field(ge=0)
    method: str
    thresholds: dict[str, float]
    note: str | None = None


class DataProfiler:
    """Basic data profiling and analytics."""
    
    def profile_column(self, data: pd.Series) -> ColumnProfile:
        """Generate a comprehensive profile for a single column.
        
        Args:
            data: Pandas Series to profile.
            
        Returns:
            ColumnProfile containing comprehensive column statistics.
        """
        profile = ColumnProfile(
            column_name=data.name or "unnamed",
            data_type=str(data.dtype),
            total_count=len(data),
            null_count=data.isnull().sum(),
            null_percentage=(data.isnull().sum() / len(data)) * 100,
            unique_count=data.nunique(),
            unique_percentage=(data.nunique() / len(data)) * 100,
        )
        
        # Add type-specific statistics
        if np.issubdtype(data.dtype, np.number):
            self._add_numeric_stats(profile, data)
        elif data.dtype == 'object' or data.dtype == 'category':
            self._add_categorical_stats(profile, data)
        elif pd.api.types.is_datetime64_any_dtype(data):
            self._add_datetime_stats(profile, data)
        
        return profile
    
    def _add_numeric_stats(self, profile: ColumnProfile, data: pd.Series) -> None:
        """Add numeric statistics to profile.
        
        Args:
            profile: Profile to update.
            data: Numeric data series.
        """
        clean_data = data.dropna()
        
        if len(clean_data) == 0:
            return
        
        profile.min_value = float(clean_data.min())
        profile.max_value = float(clean_data.max())
        profile.mean_value = float(clean_data.mean())
        profile.median_value = float(clean_data.median())
        profile.std_value = float(clean_data.std())
        profile.q25_value = float(clean_data.quantile(0.25))
        profile.q75_value = float(clean_data.quantile(0.75))
        profile.iqr_value = profile.q75_value - profile.q25_value
        profile.skewness = float(clean_data.skew())
        profile.kurtosis = float(clean_data.kurtosis())
    
    def _add_categorical_stats(self, profile: ColumnProfile, data: pd.Series) -> None:
        """Add categorical statistics to profile.
        
        Args:
            profile: Profile to update.
            data: Categorical data series.
        """
        clean_data = data.dropna()
        
        if len(clean_data) == 0:
            return
        
        value_counts = clean_data.value_counts()
        
        profile.top_values = value_counts.head(10).to_dict()
        profile.top_value = value_counts.index[0] if len(value_counts) > 0 else None
        profile.top_value_count = int(value_counts.iloc[0]) if len(value_counts) > 0 else None
        profile.top_value_percentage = (value_counts.iloc[0] / len(clean_data)) * 100 if len(value_counts) > 0 else None
    
    def _add_datetime_stats(self, profile: ColumnProfile, data: pd.Series) -> None:
        """Add datetime statistics to profile.
        
        Args:
            profile: Profile to update.
            data: Datetime data series.
        """
        clean_data = data.dropna()
        
        if len(clean_data) == 0:
            return
        
        profile.min_date = clean_data.min().isoformat()
        profile.max_date = clean_data.max().isoformat()
        profile.date_range_days = (clean_data.max() - clean_data.min()).days
        profile.most_common_year = int(clean_data.dt.year.mode().iloc[0]) if len(clean_data.dt.year.mode()) > 0 else None
        profile.most_common_month = int(clean_data.dt.month.mode().iloc[0]) if len(clean_data.dt.month.mode()) > 0 else None
        profile.most_common_day_of_week = int(clean_data.dt.dayofweek.mode().iloc[0]) if len(clean_data.dt.dayofweek.mode()) > 0 else None
    
    def profile_table(self, data: pd.DataFrame) -> TableProfile:
        """Generate a comprehensive profile for an entire table.
        
        Args:
            data: Pandas DataFrame to profile.
            
        Returns:
            TableProfile containing comprehensive table statistics.
        """
        columns = {}
        for column in data.columns:
            columns[column] = self.profile_column(data[column])
        
        summary = self._generate_table_summary(data, columns)
        
        return TableProfile(
            table_name="unknown",
            total_rows=len(data),
            total_columns=len(data.columns),
            memory_usage_mb=data.memory_usage(deep=True).sum() / 1024 / 1024,
            columns=columns,
            summary=summary
        )
    
    def _generate_table_summary(self, data: pd.DataFrame, column_profiles: dict[str, ColumnProfile]) -> dict[str, Any]:
        """Generate summary statistics for the entire table.
        
        Args:
            data: DataFrame being profiled.
            column_profiles: Dictionary of column profiles.
            
        Returns:
            Summary statistics dictionary.
        """
        numeric_columns = []
        categorical_columns = []
        datetime_columns = []
        
        for col_name, profile in column_profiles.items():
            if profile.data_type.startswith(('int', 'float')):
                numeric_columns.append(col_name)
            elif profile.data_type in ('object', 'category'):
                categorical_columns.append(col_name)
            elif profile.data_type.startswith('datetime'):
                datetime_columns.append(col_name)
        
        return {
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "datetime_columns": datetime_columns,
            "high_cardinality_columns": [
                col for col, profile in column_profiles.items()
                if profile.unique_percentage > 80
            ],
            "high_null_columns": [
                col for col, profile in column_profiles.items()
                if profile.null_percentage > 20
            ],
        }
    
    def detect_anomalies(self, data: pd.Series, method: str = "iqr") -> AnomalyResult:
        """Detect anomalies in a data series using various methods.
        
        Args:
            data: Data series to analyze.
            method: Anomaly detection method.
            
        Returns:
            AnomalyResult containing detection results.
            
        Raises:
            ValueError: If method is not supported.
        """
        if method == "iqr":
            return self._detect_anomalies_iqr(data)
        elif method == "zscore":
            return self._detect_anomalies_zscore(data)
        elif method == "isolation_forest":
            return self._detect_anomalies_isolation_forest(data)
        else:
            raise ValueError(f"Unknown anomaly detection method: {method}")
    
    def _detect_anomalies_iqr(self, data: pd.Series) -> AnomalyResult:
        """Detect anomalies using the Interquartile Range method.
        
        Args:
            data: Data series to analyze.
            
        Returns:
            AnomalyResult with IQR-based detection.
        """
        clean_data = data.dropna()
        
        if len(clean_data) < 4:
            return AnomalyResult(
                anomalies=[],
                method="iqr",
                thresholds={}
            )
        
        q1 = clean_data.quantile(0.25)
        q3 = clean_data.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        anomalies = clean_data[(clean_data < lower_bound) | (clean_data > upper_bound)]
        
        return AnomalyResult(
            anomalies=anomalies.index.tolist(),
            anomaly_count=len(anomalies),
            method="iqr",
            thresholds={
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "q1": float(q1),
                "q3": float(q3),
                "iqr": float(iqr)
            }
        )
    
    def _detect_anomalies_zscore(self, data: pd.Series, threshold: float = 3.0) -> AnomalyResult:
        """Detect anomalies using the Z-score method.
        
        Args:
            data: Data series to analyze.
            threshold: Z-score threshold for anomaly detection.
            
        Returns:
            AnomalyResult with Z-score-based detection.
        """
        clean_data = data.dropna()
        
        if len(clean_data) < 2:
            return AnomalyResult(
                anomalies=[],
                method="zscore",
                thresholds={}
            )
        
        z_scores = np.abs((clean_data - clean_data.mean()) / clean_data.std())
        anomalies = clean_data[z_scores > threshold]
        
        return AnomalyResult(
            anomalies=anomalies.index.tolist(),
            anomaly_count=len(anomalies),
            method="zscore",
            thresholds={
                "z_score_threshold": threshold,
                "mean": float(clean_data.mean()),
                "std": float(clean_data.std())
            }
        )
    
    def _detect_anomalies_isolation_forest(self, data: pd.Series) -> AnomalyResult:
        """Detect anomalies using Isolation Forest (placeholder for future implementation).
        
        Args:
            data: Data series to analyze.
            
        Returns:
            AnomalyResult with placeholder note.
        """
        return AnomalyResult(
            anomalies=[],
            method="isolation_forest",
            thresholds={},
            note="Isolation Forest detection not yet implemented"
        )
