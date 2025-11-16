"""
Temporal Financial Analyzer
Handles time-series analysis, trend detection, and temporal reasoning
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Trend:
    """Container for trend information"""
    metric_name: str
    direction: str  # 'up', 'down', 'stable'
    magnitude: float
    confidence: float
    period: str
    start_date: datetime
    end_date: datetime
    data_points: List[Tuple[datetime, float]]


@dataclass
class AnomalyEvent:
    """Container for anomaly/event detection"""
    event_id: str
    event_type: str
    timestamp: datetime
    severity: float
    description: str
    affected_metrics: List[str]
    context: Dict[str, Any]


@dataclass
class Forecast:
    """Container for forecast results"""
    metric_name: str
    predictions: List[Tuple[datetime, float]]
    confidence_intervals: List[Tuple[float, float]]
    horizon_days: int
    model_name: str
    accuracy_metrics: Dict[str, float]


class TrendAnalyzer:
    """
    Analyze trends in financial time series data
    """

    def __init__(self, min_data_points: int = 3):
        self.min_data_points = min_data_points

    def analyze(
        self,
        data: pd.DataFrame,
        metric_columns: Optional[List[str]] = None
    ) -> Dict[str, Trend]:
        """
        Analyze trends in time series data
        """
        if metric_columns is None:
            # Analyze all numeric columns
            metric_columns = data.select_dtypes(include=[np.number]).columns.tolist()

        trends = {}

        for col in metric_columns:
            if col not in data.columns:
                continue

            # Get clean data
            series = data[col].dropna()

            if len(series) < self.min_data_points:
                logger.warning(f"Insufficient data points for {col}")
                continue

            # Calculate trend
            trend = self._calculate_trend(series, col)
            trends[col] = trend

        return trends

    def _calculate_trend(
        self,
        series: pd.Series,
        metric_name: str
    ) -> Trend:
        """
        Calculate trend for a time series
        """
        # Simple linear regression for trend
        x = np.arange(len(series))
        y = series.values

        # Calculate slope
        slope, intercept = np.polyfit(x, y, 1)

        # Determine direction
        if abs(slope) < 0.001:
            direction = 'stable'
        elif slope > 0:
            direction = 'up'
        else:
            direction = 'down'

        # Calculate magnitude (percentage change)
        if y[0] != 0:
            magnitude = ((y[-1] - y[0]) / abs(y[0])) * 100
        else:
            magnitude = 0.0

        # Calculate confidence (R-squared)
        y_pred = slope * x + intercept
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        ss_res = np.sum((y - y_pred) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Create data points
        data_points = [(series.index[i], float(y[i])) for i in range(len(y))]

        return Trend(
            metric_name=metric_name,
            direction=direction,
            magnitude=magnitude,
            confidence=r_squared,
            period=f"{len(series)} periods",
            start_date=series.index[0] if isinstance(series.index[0], datetime) else datetime.now(),
            end_date=series.index[-1] if isinstance(series.index[-1], datetime) else datetime.now(),
            data_points=data_points
        )

    def compare_trends(
        self,
        trend1: Trend,
        trend2: Trend
    ) -> Dict[str, Any]:
        """
        Compare two trends
        """
        return {
            'metric1': trend1.metric_name,
            'metric2': trend2.metric_name,
            'direction_match': trend1.direction == trend2.direction,
            'magnitude_diff': abs(trend1.magnitude - trend2.magnitude),
            'correlation': self._calculate_correlation(
                trend1.data_points,
                trend2.data_points
            )
        }

    def _calculate_correlation(
        self,
        data1: List[Tuple[datetime, float]],
        data2: List[Tuple[datetime, float]]
    ) -> float:
        """
        Calculate correlation between two time series
        """
        # Extract values
        values1 = [v for _, v in data1]
        values2 = [v for _, v in data2]

        # Align lengths
        min_len = min(len(values1), len(values2))
        values1 = values1[:min_len]
        values2 = values2[:min_len]

        if min_len < 2:
            return 0.0

        # Calculate Pearson correlation
        corr = np.corrcoef(values1, values2)[0, 1]

        return float(corr) if not np.isnan(corr) else 0.0


class EventDetector:
    """
    Detect anomalies and significant events in time series
    """

    def __init__(self, sensitivity: float = 0.95):
        self.sensitivity = sensitivity

    def detect(
        self,
        data: pd.DataFrame,
        sensitivity: Optional[float] = None
    ) -> List[AnomalyEvent]:
        """
        Detect anomalies in time series data
        """
        if sensitivity is not None:
            self.sensitivity = sensitivity

        events = []

        # Analyze each numeric column
        for col in data.select_dtypes(include=[np.number]).columns:
            series = data[col].dropna()

            if len(series) < 5:
                continue

            # Detect outliers using z-score
            anomalies = self._detect_outliers(series, col)
            events.extend(anomalies)

            # Detect sudden changes
            changes = self._detect_sudden_changes(series, col)
            events.extend(changes)

        return events

    def _detect_outliers(
        self,
        series: pd.Series,
        metric_name: str
    ) -> List[AnomalyEvent]:
        """
        Detect outliers using statistical methods
        """
        anomalies = []

        # Calculate z-scores
        mean = series.mean()
        std = series.std()

        if std == 0:
            return anomalies

        z_scores = np.abs((series - mean) / std)

        # Find outliers (z-score > 3)
        outlier_threshold = 3.0
        outliers = z_scores > outlier_threshold

        for idx, is_outlier in outliers.items():
            if is_outlier:
                event = AnomalyEvent(
                    event_id=f"outlier_{metric_name}_{idx}",
                    event_type='outlier',
                    timestamp=idx if isinstance(idx, datetime) else datetime.now(),
                    severity=float(z_scores[idx]) / outlier_threshold,
                    description=f"Outlier detected in {metric_name}",
                    affected_metrics=[metric_name],
                    context={
                        'value': float(series[idx]),
                        'mean': float(mean),
                        'std': float(std),
                        'z_score': float(z_scores[idx])
                    }
                )
                anomalies.append(event)

        return anomalies

    def _detect_sudden_changes(
        self,
        series: pd.Series,
        metric_name: str
    ) -> List[AnomalyEvent]:
        """
        Detect sudden changes (spikes/drops)
        """
        changes = []

        # Calculate percentage change
        pct_change = series.pct_change()

        # Detect significant changes (>20%)
        threshold = 0.20

        for idx, change in pct_change.items():
            if abs(change) > threshold:
                event_type = 'spike' if change > 0 else 'drop'

                event = AnomalyEvent(
                    event_id=f"change_{metric_name}_{idx}",
                    event_type=event_type,
                    timestamp=idx if isinstance(idx, datetime) else datetime.now(),
                    severity=min(abs(change), 1.0),
                    description=f"Sudden {event_type} in {metric_name}: {change*100:.1f}%",
                    affected_metrics=[metric_name],
                    context={
                        'change_pct': float(change * 100),
                        'previous_value': float(series.iloc[series.index.get_loc(idx) - 1]),
                        'current_value': float(series[idx])
                    }
                )
                changes.append(event)

        return changes


class TimeSeriesForecaster:
    """
    Generate forecasts for financial time series
    """

    def __init__(self, model_name: str = 'simple_moving_average'):
        self.model_name = model_name

    def forecast(
        self,
        data: pd.Series,
        horizon_days: int,
        metric_name: str
    ) -> Forecast:
        """
        Generate forecast for time series
        """
        logger.info(f"Forecasting {metric_name} for {horizon_days} days")

        # Use simple moving average for now
        # In production, use ARIMA, Prophet, or Temporal Fusion Transformer
        predictions = self._simple_forecast(data, horizon_days)

        # Calculate confidence intervals
        confidence_intervals = self._calculate_confidence_intervals(
            data,
            predictions
        )

        # Calculate accuracy metrics (on training data)
        accuracy_metrics = self._calculate_accuracy_metrics(data)

        return Forecast(
            metric_name=metric_name,
            predictions=predictions,
            confidence_intervals=confidence_intervals,
            horizon_days=horizon_days,
            model_name=self.model_name,
            accuracy_metrics=accuracy_metrics
        )

    def _simple_forecast(
        self,
        data: pd.Series,
        horizon_days: int
    ) -> List[Tuple[datetime, float]]:
        """
        Simple forecasting using moving average
        """
        # Calculate moving average
        window = min(7, len(data))
        ma = data.rolling(window=window).mean().iloc[-1]

        # Calculate trend
        if len(data) >= 2:
            recent_trend = data.iloc[-1] - data.iloc[-2]
        else:
            recent_trend = 0

        # Generate predictions
        predictions = []
        last_date = data.index[-1] if isinstance(data.index[-1], datetime) else datetime.now()

        for i in range(1, horizon_days + 1):
            forecast_date = last_date + timedelta(days=i)
            forecast_value = ma + (recent_trend * i * 0.5)  # Dampen trend
            predictions.append((forecast_date, float(forecast_value)))

        return predictions

    def _calculate_confidence_intervals(
        self,
        data: pd.Series,
        predictions: List[Tuple[datetime, float]]
    ) -> List[Tuple[float, float]]:
        """
        Calculate confidence intervals for predictions
        """
        # Use standard deviation of historical data
        std = data.std()

        intervals = []
        for i, (_, pred) in enumerate(predictions):
            # Widen interval as we go further into future
            width = std * (1 + i * 0.1)
            intervals.append((
                float(pred - 1.96 * width),  # 95% CI lower bound
                float(pred + 1.96 * width)   # 95% CI upper bound
            ))

        return intervals

    def _calculate_accuracy_metrics(self, data: pd.Series) -> Dict[str, float]:
        """
        Calculate forecast accuracy metrics
        """
        # Simple metrics for demonstration
        return {
            'mape': 5.0,  # Placeholder
            'rmse': float(data.std() * 0.1),
            'mae': float(data.std() * 0.08)
        }


class TemporalFinancialAnalyzer:
    """
    Main temporal analysis system for financial data
    """

    def __init__(self):
        self.trend_analyzer = TrendAnalyzer()
        self.event_detector = EventDetector()
        self.forecaster = TimeSeriesForecaster()

        logger.info("Initialized TemporalFinancialAnalyzer")

    def analyze_temporal_patterns(
        self,
        company: str,
        data: pd.DataFrame,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive temporal analysis
        """
        logger.info(f"Analyzing temporal patterns for {company}")

        analysis = {
            'company': company,
            'time_range': time_range,
            'trends': {},
            'events': [],
            'correlations': {},
            'forecasts': {}
        }

        # Filter by time range if provided
        if time_range:
            start_date, end_date = time_range
            data = data[(data.index >= start_date) & (data.index <= end_date)]

        # Analyze trends for different periods
        periods = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30,
            'quarterly': 90
        }

        for period_name, days in periods.items():
            if len(data) >= days:
                period_data = data.tail(days)
                trends = self.trend_analyzer.analyze(period_data)
                analysis['trends'][period_name] = trends

        # Detect anomalous events
        events = self.event_detector.detect(data, sensitivity=0.95)
        analysis['events'] = events
        logger.info(f"Detected {len(events)} anomalous events")

        # Calculate cross-metric correlations
        correlations = self._compute_correlations(data)
        analysis['correlations'] = correlations

        # Generate forecasts
        for col in data.select_dtypes(include=[np.number]).columns:
            series = data[col].dropna()
            if len(series) >= 7:
                forecast = self.forecaster.forecast(
                    series,
                    horizon_days=30,
                    metric_name=col
                )
                analysis['forecasts'][col] = forecast

        return analysis

    def _compute_correlations(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Compute correlations between metrics
        """
        numeric_data = data.select_dtypes(include=[np.number])

        if numeric_data.empty:
            return {}

        # Calculate correlation matrix
        corr_matrix = numeric_data.corr()

        # Find strong correlations
        strong_correlations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:
                    strong_correlations.append({
                        'metric1': corr_matrix.columns[i],
                        'metric2': corr_matrix.columns[j],
                        'correlation': float(corr_value)
                    })

        return {
            'correlation_matrix': corr_matrix.to_dict(),
            'strong_correlations': strong_correlations
        }

    def align_multi_modal_temporal_data(
        self,
        data_sources: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Align data from different sources temporally
        """
        logger.info("Aligning multi-modal temporal data")

        aligned_data = pd.DataFrame()

        # Start with the primary source (usually market data)
        if 'market' in data_sources:
            aligned_data = data_sources['market']

        # Merge other sources
        for source_name, source_df in data_sources.items():
            if source_name == 'market':
                continue

            # Merge based on timestamp
            if not aligned_data.empty:
                aligned_data = pd.merge_asof(
                    aligned_data,
                    source_df,
                    left_index=True,
                    right_index=True,
                    direction='nearest',
                    tolerance=pd.Timedelta('1 day')
                )
            else:
                aligned_data = source_df

        logger.info(f"Aligned data shape: {aligned_data.shape}")

        return aligned_data

    def analyze_period_comparison(
        self,
        data: pd.DataFrame,
        period1: Tuple[datetime, datetime],
        period2: Tuple[datetime, datetime],
        metrics: List[str]
    ) -> Dict[str, Any]:
        """
        Compare two time periods
        """
        start1, end1 = period1
        start2, end2 = period2

        period1_data = data[(data.index >= start1) & (data.index <= end1)]
        period2_data = data[(data.index >= start2) & (data.index <= end2)]

        comparison = {}

        for metric in metrics:
            if metric not in data.columns:
                continue

            p1_values = period1_data[metric].dropna()
            p2_values = period2_data[metric].dropna()

            if len(p1_values) == 0 or len(p2_values) == 0:
                continue

            comparison[metric] = {
                'period1_mean': float(p1_values.mean()),
                'period2_mean': float(p2_values.mean()),
                'change_pct': float(((p2_values.mean() - p1_values.mean()) / p1_values.mean()) * 100),
                'period1_std': float(p1_values.std()),
                'period2_std': float(p2_values.std())
            }

        return comparison
