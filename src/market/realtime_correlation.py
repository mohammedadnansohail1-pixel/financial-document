"""
Real-Time Market Correlation Analysis
Live correlation tracking between assets, sectors, and market factors
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from collections import deque
from threading import Lock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CorrelationPair:
    """Correlation between two assets"""
    asset1: str
    asset2: str
    correlation: float  # -1 to 1
    rolling_correlation: List[float]
    timestamp: datetime
    significance: float  # p-value
    sample_size: int


@dataclass
class MarketRegime:
    """Current market regime"""
    regime_type: str  # bull, bear, volatile, stable
    confidence: float
    duration_days: int
    characteristics: Dict[str, Any]
    detected_at: datetime


class RollingCorrelationCalculator:
    """
    Calculate rolling correlations efficiently
    """

    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.data_buffers: Dict[str, deque] = {}
        self.lock = Lock()

    def update(self, asset: str, value: float, timestamp: datetime):
        """
        Update data buffer for an asset

        Args:
            asset: Asset identifier
            value: Asset value (price, return, etc.)
            timestamp: Timestamp
        """
        with self.lock:
            if asset not in self.data_buffers:
                self.data_buffers[asset] = deque(maxlen=self.window_size)

            self.data_buffers[asset].append((timestamp, value))

    def calculate_correlation(
        self,
        asset1: str,
        asset2: str
    ) -> Optional[float]:
        """
        Calculate correlation between two assets

        Args:
            asset1: First asset
            asset2: Second asset
        """
        with self.lock:
            if asset1 not in self.data_buffers or asset2 not in self.data_buffers:
                return None

            buffer1 = self.data_buffers[asset1]
            buffer2 = self.data_buffers[asset2]

            if len(buffer1) < 10 or len(buffer2) < 10:
                return None

            # Extract values (align timestamps)
            values1 = [v for _, v in buffer1]
            values2 = [v for _, v in buffer2]

            # Calculate correlation
            corr = np.corrcoef(values1, values2)[0, 1]

            return float(corr) if not np.isnan(corr) else None

    def calculate_all_correlations(self) -> Dict[Tuple[str, str], float]:
        """
        Calculate correlations for all asset pairs
        """
        correlations = {}
        assets = list(self.data_buffers.keys())

        for i, asset1 in enumerate(assets):
            for asset2 in assets[i + 1:]:
                corr = self.calculate_correlation(asset1, asset2)
                if corr is not None:
                    correlations[(asset1, asset2)] = corr

        return correlations


class RealTimeCorrelationTracker:
    """
    Track correlations in real-time with live updates
    """

    def __init__(
        self,
        update_interval: int = 60,  # seconds
        window_size: int = 30  # days
    ):
        self.update_interval = update_interval
        self.window_size = window_size

        self.calculator = RollingCorrelationCalculator(window_size=window_size)
        self.correlation_history: Dict[Tuple[str, str], List[CorrelationPair]] = {}
        self.last_update = datetime.now()

        logger.info(f"RealTimeCorrelationTracker initialized (window={window_size} days)")

    def ingest_market_data(
        self,
        market_data: Dict[str, float],
        timestamp: Optional[datetime] = None
    ):
        """
        Ingest real-time market data

        Args:
            market_data: Dict of asset -> price/return
            timestamp: Data timestamp
        """
        timestamp = timestamp or datetime.now()

        # Update all assets
        for asset, value in market_data.items():
            self.calculator.update(asset, value, timestamp)

        # Check if we should update correlations
        if (timestamp - self.last_update).seconds >= self.update_interval:
            self._update_correlations(timestamp)
            self.last_update = timestamp

    def _update_correlations(self, timestamp: datetime):
        """Update correlation calculations"""
        correlations = self.calculator.calculate_all_correlations()

        for (asset1, asset2), corr in correlations.items():
            pair_key = (asset1, asset2)

            # Create correlation pair object
            corr_pair = CorrelationPair(
                asset1=asset1,
                asset2=asset2,
                correlation=corr,
                rolling_correlation=[corr],  # Would track history in production
                timestamp=timestamp,
                significance=self._calculate_significance(corr, self.window_size),
                sample_size=self.window_size
            )

            # Store in history
            if pair_key not in self.correlation_history:
                self.correlation_history[pair_key] = []

            self.correlation_history[pair_key].append(corr_pair)

    def _calculate_significance(self, correlation: float, n: int) -> float:
        """
        Calculate statistical significance (p-value) of correlation

        Args:
            correlation: Correlation coefficient
            n: Sample size
        """
        # Fisher's Z-transformation
        if abs(correlation) >= 1.0:
            return 0.0

        z = 0.5 * np.log((1 + correlation) / (1 - correlation))
        se = 1.0 / np.sqrt(n - 3)

        # Two-tailed p-value (simplified)
        z_score = abs(z / se)
        p_value = 2 * (1 - self._normal_cdf(z_score))

        return p_value

    def _normal_cdf(self, x: float) -> float:
        """Standard normal CDF (approximation)"""
        return 0.5 * (1 + np.tanh(x / np.sqrt(2)))

    def get_current_correlations(
        self,
        min_significance: float = 0.05
    ) -> List[CorrelationPair]:
        """
        Get current correlations above significance threshold

        Args:
            min_significance: Minimum significance level (p-value threshold)
        """
        current_correlations = []

        for pair_history in self.correlation_history.values():
            if pair_history:
                latest = pair_history[-1]
                if latest.significance < min_significance:
                    current_correlations.append(latest)

        # Sort by absolute correlation strength
        current_correlations.sort(key=lambda x: abs(x.correlation), reverse=True)

        return current_correlations

    def get_highly_correlated_assets(
        self,
        threshold: float = 0.7
    ) -> List[Tuple[str, str, float]]:
        """
        Get asset pairs with high correlation

        Args:
            threshold: Minimum correlation threshold
        """
        correlations = []

        for (asset1, asset2), history in self.correlation_history.items():
            if history:
                latest_corr = history[-1].correlation

                if abs(latest_corr) >= threshold:
                    correlations.append((asset1, asset2, latest_corr))

        correlations.sort(key=lambda x: abs(x[2]), reverse=True)

        return correlations


class MarketRegimeDetector:
    """
    Detect market regimes using statistical methods
    """

    def __init__(self):
        self.regime_history: List[MarketRegime] = []
        self.current_regime: Optional[MarketRegime] = None

    def detect_regime(
        self,
        market_returns: List[float],
        volatility: List[float]
    ) -> MarketRegime:
        """
        Detect current market regime

        Args:
            market_returns: Recent market returns
            volatility: Recent volatility measures
        """
        if len(market_returns) < 20:
            return MarketRegime(
                regime_type='unknown',
                confidence=0.0,
                duration_days=0,
                characteristics={},
                detected_at=datetime.now()
            )

        # Calculate regime characteristics
        avg_return = np.mean(market_returns[-20:])
        avg_volatility = np.mean(volatility[-20:])
        trend = np.polyfit(range(len(market_returns[-20:])), market_returns[-20:], 1)[0]

        # Determine regime
        if avg_return > 0.001 and avg_volatility < 0.015:
            regime_type = 'bull_stable'
            confidence = 0.85
        elif avg_return > 0.001 and avg_volatility >= 0.015:
            regime_type = 'bull_volatile'
            confidence = 0.75
        elif avg_return <= 0.001 and avg_volatility >= 0.02:
            regime_type = 'bear_volatile'
            confidence = 0.80
        elif avg_return <= 0.001 and avg_volatility < 0.02:
            regime_type = 'bear_stable'
            confidence = 0.70
        else:
            regime_type = 'transitional'
            confidence = 0.60

        # Calculate duration
        duration = 0
        if self.current_regime and self.current_regime.regime_type == regime_type:
            duration = (datetime.now() - self.current_regime.detected_at).days
        else:
            duration = 0

        regime = MarketRegime(
            regime_type=regime_type,
            confidence=confidence,
            duration_days=duration,
            characteristics={
                'avg_return': avg_return,
                'avg_volatility': avg_volatility,
                'trend': 'upward' if trend > 0 else 'downward'
            },
            detected_at=datetime.now()
        )

        if not self.current_regime or self.current_regime.regime_type != regime_type:
            self.regime_history.append(regime)
            self.current_regime = regime
            logger.info(f"Market regime changed to: {regime_type}")

        return regime


class SectorCorrelationAnalyzer:
    """
    Analyze correlations at sector level
    """

    def __init__(self):
        self.sector_map: Dict[str, str] = {}  # asset -> sector
        self.sector_returns: Dict[str, List[float]] = {}

    def map_asset_to_sector(self, asset: str, sector: str):
        """Map asset to sector"""
        self.sector_map[asset] = sector

    def calculate_sector_correlations(
        self,
        asset_returns: Dict[str, List[float]]
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate inter-sector correlations

        Args:
            asset_returns: Dict of asset -> returns list
        """
        # Aggregate returns by sector
        sector_aggregated = {}

        for asset, returns in asset_returns.items():
            sector = self.sector_map.get(asset, 'Unknown')

            if sector not in sector_aggregated:
                sector_aggregated[sector] = []

            sector_aggregated[sector].append(returns)

        # Calculate sector-level returns (equal-weighted)
        sector_returns = {}
        for sector, returns_list in sector_aggregated.items():
            # Average across all assets in sector
            sector_returns[sector] = np.mean(returns_list, axis=0)

        # Calculate inter-sector correlations
        correlations = {}
        sectors = list(sector_returns.keys())

        for i, sector1 in enumerate(sectors):
            for sector2 in sectors[i + 1:]:
                corr = np.corrcoef(
                    sector_returns[sector1],
                    sector_returns[sector2]
                )[0, 1]

                if not np.isnan(corr):
                    correlations[(sector1, sector2)] = float(corr)

        return correlations


class RealTimeMarketCorrelationEngine:
    """
    Main real-time market correlation engine
    """

    def __init__(
        self,
        update_interval: int = 60,
        correlation_window: int = 30
    ):
        self.correlation_tracker = RealTimeCorrelationTracker(
            update_interval=update_interval,
            window_size=correlation_window
        )
        self.regime_detector = MarketRegimeDetector()
        self.sector_analyzer = SectorCorrelationAnalyzer()

        self.market_data_history: deque = deque(maxlen=1000)

        logger.info("RealTimeMarketCorrelationEngine initialized")

    def ingest_live_data(
        self,
        market_data: Dict[str, float],
        timestamp: Optional[datetime] = None
    ):
        """
        Ingest live market data

        Args:
            market_data: Dict of asset_id -> current_price
            timestamp: Data timestamp
        """
        timestamp = timestamp or datetime.now()

        # Store in history
        self.market_data_history.append({
            'timestamp': timestamp,
            'data': market_data
        })

        # Update correlation tracker
        self.correlation_tracker.ingest_market_data(market_data, timestamp)

    def get_correlation_matrix(
        self,
        assets: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get correlation matrix for specified assets

        Args:
            assets: List of assets (None for all)
        """
        current_correlations = self.correlation_tracker.get_current_correlations()

        # Build correlation matrix
        if not current_correlations:
            return pd.DataFrame()

        # Get unique assets
        all_assets = set()
        for corr in current_correlations:
            all_assets.add(corr.asset1)
            all_assets.add(corr.asset2)

        if assets:
            all_assets = all_assets.intersection(set(assets))

        assets_list = sorted(list(all_assets))

        # Initialize matrix
        matrix = np.identity(len(assets_list))

        # Fill matrix
        asset_index = {asset: i for i, asset in enumerate(assets_list)}

        for corr in current_correlations:
            if corr.asset1 in asset_index and corr.asset2 in asset_index:
                i = asset_index[corr.asset1]
                j = asset_index[corr.asset2]

                matrix[i, j] = corr.correlation
                matrix[j, i] = corr.correlation

        return pd.DataFrame(matrix, index=assets_list, columns=assets_list)

    def detect_market_regime(self) -> MarketRegime:
        """
        Detect current market regime
        """
        if len(self.market_data_history) < 20:
            return MarketRegime(
                regime_type='unknown',
                confidence=0.0,
                duration_days=0,
                characteristics={},
                detected_at=datetime.now()
            )

        # Calculate returns from price history
        returns = []
        volatility = []

        for i in range(1, min(len(self.market_data_history), 100)):
            prev_data = self.market_data_history[i - 1]['data']
            curr_data = self.market_data_history[i]['data']

            # Calculate average market return
            common_assets = set(prev_data.keys()) & set(curr_data.keys())

            if common_assets:
                period_returns = [
                    (curr_data[asset] - prev_data[asset]) / prev_data[asset]
                    for asset in common_assets
                    if prev_data[asset] != 0
                ]

                if period_returns:
                    avg_return = np.mean(period_returns)
                    returns.append(avg_return)
                    volatility.append(np.std(period_returns))

        return self.regime_detector.detect_regime(returns, volatility)

    def find_correlation_opportunities(
        self,
        strategy: str = 'pairs_trading'
    ) -> List[Dict[str, Any]]:
        """
        Find trading opportunities based on correlations

        Args:
            strategy: Trading strategy type
        """
        opportunities = []

        if strategy == 'pairs_trading':
            # Find highly correlated pairs
            high_corr_pairs = self.correlation_tracker.get_highly_correlated_assets(
                threshold=0.85
            )

            for asset1, asset2, corr in high_corr_pairs:
                opportunities.append({
                    'strategy': 'pairs_trading',
                    'asset1': asset1,
                    'asset2': asset2,
                    'correlation': corr,
                    'confidence': 'high' if abs(corr) > 0.9 else 'medium',
                    'action': 'monitor_for_divergence'
                })

        elif strategy == 'diversification':
            # Find low/negative correlations for diversification
            all_corrs = self.correlation_tracker.get_current_correlations()

            low_corr_pairs = [
                (corr.asset1, corr.asset2, corr.correlation)
                for corr in all_corrs
                if abs(corr.correlation) < 0.3
            ]

            for asset1, asset2, corr in low_corr_pairs[:10]:
                opportunities.append({
                    'strategy': 'diversification',
                    'asset1': asset1,
                    'asset2': asset2,
                    'correlation': corr,
                    'confidence': 'high' if abs(corr) < 0.1 else 'medium',
                    'action': 'consider_for_portfolio_diversification'
                })

        return opportunities

    def get_analytics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics summary
        """
        current_regime = self.detect_market_regime()
        correlation_matrix = self.get_correlation_matrix()

        # Calculate average correlation
        if not correlation_matrix.empty:
            # Get upper triangle (excluding diagonal)
            upper_triangle = correlation_matrix.where(
                np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
            )
            avg_correlation = upper_triangle.stack().mean()
        else:
            avg_correlation = 0.0

        return {
            'current_regime': {
                'type': current_regime.regime_type,
                'confidence': current_regime.confidence,
                'duration_days': current_regime.duration_days
            },
            'correlation_stats': {
                'average_correlation': avg_correlation,
                'num_assets_tracked': len(correlation_matrix) if not correlation_matrix.empty else 0,
                'high_correlation_pairs': len(
                    self.correlation_tracker.get_highly_correlated_assets(0.7)
                )
            },
            'data_coverage': {
                'data_points': len(self.market_data_history),
                'last_update': self.correlation_tracker.last_update.isoformat()
            }
        }


# Example usage
async def main():
    """Example real-time correlation tracking"""
    engine = RealTimeMarketCorrelationEngine(
        update_interval=10,  # 10 seconds
        correlation_window=30
    )

    # Simulate real-time data ingestion
    assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']

    # Simulate 100 time periods
    for t in range(100):
        # Generate correlated prices
        base_return = np.random.normal(0.001, 0.02)

        market_data = {}
        for asset in assets:
            # Add some correlation
            asset_return = base_return + np.random.normal(0, 0.01)
            price = 100 * (1 + asset_return) ** t

            market_data[asset] = price

        # Ingest data
        timestamp = datetime.now() + timedelta(seconds=t * 10)
        engine.ingest_live_data(market_data, timestamp)

    # Get correlations
    corr_matrix = engine.get_correlation_matrix()
    print("Correlation Matrix:")
    print(corr_matrix)

    # Detect regime
    regime = engine.detect_market_regime()
    print(f"\nCurrent Regime: {regime.regime_type} (confidence: {regime.confidence:.2%})")

    # Find opportunities
    opportunities = engine.find_correlation_opportunities('pairs_trading')
    print(f"\nFound {len(opportunities)} trading opportunities")

    # Get summary
    summary = engine.get_analytics_summary()
    print(f"\nAnalytics Summary:")
    print(f"Average Correlation: {summary['correlation_stats']['average_correlation']:.3f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
