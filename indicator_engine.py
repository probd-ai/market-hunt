#!/usr/bin/env python3
"""
Indicator Engine for Market Hunt
Calculates custom technical indicators for stock price data
Production-ready architecture for custom indicators

EXPECTED DATA FORMAT:
    Input data should be a list of dictionaries with the following structure:
    [
        {
            'date': '2024-01-01',        # Date string (YYYY-MM-DD format)
            'open_price': 100.0,         # Opening price (float)
            'high_price': 105.0,         # High price (float) 
            'low_price': 98.0,           # Low price (float)
            'close_price': 102.0,        # Closing price (float)
            'volume': 1000000           # Volume (optional, int)
        },
        ...
    ]

INDICATOR OUTPUT FORMAT (Its Not fixed just an example)
    Depending on the indicator, it should return a list of dictionaries:
    [
        {
            'date': '2024-01-01',
            'value': 102.5,              # Primary indicator value
            'indicator': 'sma',          # Indicator name
            'period': 20,                # Parameters used (optional)
            # ... additional indicator-specific fields
        },
        ...
    ]
    or
    [
        {
            'date': '2024-01-01',
            'indicator_open': 0.5,
            'indicator_high': 0.6,
            'indicator_low': 0.4,
            'indicator_close': 0.5,'
            'period': 14,                # Parameters used (optional)
            # ... additional indicator-specific fields
        },
        ...
    ]
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

class IndicatorEngine:
    """
    Technical indicator calculation engine with caching
    Clean architecture for custom indicator development
    """
    
    def __init__(self):
        # Initialize with empty supported indicators - we'll add custom ones
        self.supported_indicators = {}
        
        # Simple in-memory cache for indicators
        self.cache = {}
        self.cache_max_size = 100  # Maximum number of cached results
    
    def _generate_cache_key(self, indicator_type: str, data_hash: str, **params) -> str:
        """Generate a cache key for indicator calculation"""
        key_data = {
            'indicator': indicator_type,
            'data_hash': data_hash,
            'params': params
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def _hash_data(self, data: List[Dict]) -> str:
        """Generate hash for price data to use in caching"""
        # Use first and last few records + length for hash
        if len(data) <= 10:
            data_sample = data
        else:
            data_sample = data[:5] + data[-5:] + [{'length': len(data)}]
        
        return hashlib.md5(json.dumps(data_sample, sort_keys=True).encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Get result from cache if available"""
        return self.cache.get(cache_key)
    
    def _store_in_cache(self, cache_key: str, result: List[Dict]) -> None:
        """Store result in cache with size management"""
        # Simple LRU implementation - remove oldest if cache is full
        if len(self.cache) >= self.cache_max_size:
            # Remove first (oldest) entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = result
        logger.debug(f"Cached indicator result with key: {cache_key[:8]}...")
    
    def register_indicator(self, name: str, calculation_func):
        """
        Register a new custom indicator
        
        Args:
            name: Name of the indicator (will be used as key)
            calculation_func: Function that calculates the indicator
        """
        self.supported_indicators[name] = calculation_func
        logger.info(f"Registered custom indicator: {name}")
    
    def calculate_indicator(self, indicator_type: str, data: List[Dict], **kwargs) -> List[Dict]:
        """
        Generic method to calculate any supported indicator with caching
        
        Args:
            indicator_type: Type of indicator
            data: List of price data dictionaries
            **kwargs: Additional parameters for specific indicators
            
        Returns:
            List of dictionaries with indicator values
        """
        if indicator_type not in self.supported_indicators:
            raise ValueError(f"Unsupported indicator type: {indicator_type}. Supported: {list(self.supported_indicators.keys())}")
        
        # Generate cache key
        data_hash = self._hash_data(data)
        cache_key = self._generate_cache_key(indicator_type, data_hash, **kwargs)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            logger.info(f"Cache hit for {indicator_type} calculation ({len(cached_result)} points)")
            return cached_result
        
        # Calculate indicator
        start_time = datetime.now()
        result = self.supported_indicators[indicator_type](data, **kwargs)
        calculation_time = (datetime.now() - start_time).total_seconds()
        
        # Store in cache
        self._store_in_cache(cache_key, result)
        
        logger.info(f"Calculated {indicator_type} in {calculation_time:.3f}s ({len(result)} points)")
        return result
    
    def get_supported_indicators(self) -> List[str]:
        """Get list of supported indicator types"""
        return list(self.supported_indicators.keys())
    
    def clear_cache(self):
        """Clear the indicator cache"""
        self.cache.clear()
        logger.info("Indicator cache cleared")
    
    async def calculate_truevx_ranking(self, data: List[Dict], base_symbol: str = "Nifty 50", 
                                     start_date: str = None, end_date: str = None, **kwargs) -> List[Dict]:
        """
        Calculate TrueValueX Ranking indicator with benchmark comparison
        
        Args:
            data: Target stock OHLC data
            base_symbol: Benchmark symbol (default: "Nifty 50")
            start_date: Start date for benchmark data
            end_date: End date for benchmark data
            **kwargs: Additional parameters for TrueValueX calculation
            
        Returns:
            List of dictionaries with TrueValueX ranking scores
        """
        # Import here to avoid circular imports
        from stock_data_manager import StockDataManager
        from datetime import datetime
        
        # Get benchmark data
        async with StockDataManager() as manager:
            # Parse date range from target data if not provided
            if not start_date:
                start_date = min(item['date'] for item in data)
            if not end_date:
                end_date = max(item['date'] for item in data)
            
            # Convert string dates to datetime objects if needed
            if isinstance(start_date, str):
                start_dt = datetime.fromisoformat(start_date.replace('T', ' ').split('.')[0])
            else:
                start_dt = start_date
                
            if isinstance(end_date, str):
                end_dt = datetime.fromisoformat(end_date.replace('T', ' ').split('.')[0])
            else:
                end_dt = end_date
            
            # Get benchmark data
            benchmark_records = await manager.get_price_data(
                symbol=base_symbol,
                start_date=start_dt,
                end_date=end_dt,
                sort_order=1  # Ascending order
            )
            
            if not benchmark_records:
                logger.error(f"No benchmark data found for symbol {base_symbol}")
                return []
            
            # Convert benchmark data to dictionary format
            benchmark_data = []
            for record in benchmark_records:
                benchmark_data.append({
                    "date": record.date.isoformat(),
                    "open_price": record.open_price,
                    "high_price": record.high_price,
                    "low_price": record.low_price,
                    "close_price": record.close_price,
                    "volume": record.volume
                })
            
            # Call the standalone TrueValueX function
            return calculate_truevx_ranking(data, benchmark_data, **kwargs)


# ============================================================================
# CUSTOM INDICATORS IMPLEMENTATION
# ============================================================================

class TrueValueXHelper:
    """
    Helper class for TrueValueX Ranking indicator calculations
    Implements Pine Script logic in Python
    """
    
    @staticmethod
    def dynamic_fib(high_data: np.ndarray, low_data: np.ndarray, lookback: int) -> np.ndarray:
        """
        Calculate dynamic Fibonacci 23.6% level
        
        Args:
            high_data: Array of high prices
            low_data: Array of low prices  
            lookback: Lookback period
            
        Returns:
            Array of dynamic Fibonacci levels
        """
        if len(high_data) < lookback:
            return np.full(len(high_data), np.nan)
            
        result = np.full(len(high_data), np.nan)
        
        for i in range(lookback - 1, len(high_data)):
            start_idx = i - lookback + 1
            window_high = high_data[start_idx:i+1]
            window_low = low_data[start_idx:i+1]
            
            trend_hh = np.max(window_high)
            trend_ll = np.min(window_low)
            
            # 23% Fibonacci retracement (Pine Script: * 0.23)
            result[i] = trend_ll + (trend_hh - trend_ll) * 0.23
            
        return result
    
    @staticmethod
    def ema(data: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate Exponential Moving Average
        
        Args:
            data: Input data array
            period: EMA period
            
        Returns:
            EMA values
        """
        if len(data) == 0:
            return np.array([])
            
        alpha = 2.0 / (period + 1)
        result = np.full(len(data), np.nan)
        result[0] = data[0]
        
        for i in range(1, len(data)):
            if not np.isnan(data[i]) and not np.isnan(result[i-1]):
                result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
            else:
                result[i] = data[i] if not np.isnan(data[i]) else result[i-1]
                
        return result
    
    @staticmethod
    def sma(data: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate Simple Moving Average
        
        Args:
            data: Input data array
            period: SMA period
            
        Returns:
            SMA values
        """
        if len(data) < period:
            return np.full(len(data), np.nan)
            
        result = np.full(len(data), np.nan)
        
        for i in range(period - 1, len(data)):
            start_idx = i - period + 1
            result[i] = np.mean(data[start_idx:i+1])
            
        return result
    
    @staticmethod
    def is_rising(data: np.ndarray, strength: int) -> np.ndarray:
        """
        Check if data is rising for 'strength' consecutive periods
        
        Args:
            data: Input data array
            strength: Number of consecutive rising periods required
            
        Returns:
            Boolean array indicating rising periods
        """
        if len(data) < strength:
            return np.full(len(data), False)
            
        result = np.full(len(data), False)
        
        for i in range(strength, len(data)):
            is_rising = True
            for j in range(1, strength + 1):
                if data[i - j + 1] <= data[i - j]:
                    is_rising = False
                    break
            result[i] = is_rising
            
        return result
    
    @staticmethod
    def is_falling(data: np.ndarray, strength: int) -> np.ndarray:
        """
        Check if data is falling for 'strength' consecutive periods
        
        Args:
            data: Input data array
            strength: Number of consecutive falling periods required
            
        Returns:
            Boolean array indicating falling periods
        """
        if len(data) < strength:
            return np.full(len(data), False)
            
        result = np.full(len(data), False)
        
        for i in range(strength, len(data)):
            is_falling = True
            for j in range(1, strength + 1):
                if data[i - j + 1] >= data[i - j]:
                    is_falling = False
                    break
            result[i] = is_falling
            
        return result
    
    @staticmethod
    def get_trend_color(data: np.ndarray, strength: int) -> np.ndarray:
        """
        Get trend color based on rising/falling logic (mimics Pine Script col_fun)
        
        Args:
            data: Input data array
            strength: Trend strength parameter
            
        Returns:
            Array with trend values: 1 (green/rising), -1 (red/falling), 0 (neutral)
        """
        rising = TrueValueXHelper.is_rising(data, strength)
        falling = TrueValueXHelper.is_falling(data, strength)
        
        result = np.full(len(data), 0)
        
        for i in range(1, len(data)):
            per_r = rising[i]
            per_f = falling[i]
            
            # Pine Script logic: if per_r or (per_r[1] and not per_f)
            if per_r or (rising[i-1] and not per_f):
                per_r = True
                
            # Pine Script logic: if per_f or (per_f[1] and not per_r)  
            if per_f or (falling[i-1] and not per_r):
                per_f = True
                
            if per_r:
                result[i] = 1  # Green
            elif per_f:
                result[i] = -1  # Red
            else:
                result[i] = 0  # Neutral
                
        return result
    
    @staticmethod
    def vote_scaled(current: np.ndarray, level: np.ndarray, deadband: np.ndarray) -> np.ndarray:
        """
        Calculate continuous scaled vote using tanh formula
        
        Args:
            current: Current price values
            level: Reference level values  
            deadband: Deadband values
            
        Returns:
            Scaled vote values between -1 and 1
        """
        result = np.full(len(current), 0.0)
        
        for i in range(len(current)):
            if not (np.isnan(current[i]) or np.isnan(level[i]) or np.isnan(deadband[i])):
                db_safe = max(deadband[i], 1e-10)
                x = (current[i] - level[i]) / db_safe
                # Manual tanh: (exp(2x) - 1) / (exp(2x) + 1)
                exp_2x = np.exp(2 * x)
                result[i] = (exp_2x - 1) / (exp_2x + 1)
                
        return result


def calculate_truevx_ranking(target_data: List[Dict], benchmark_data: List[Dict], **kwargs) -> List[Dict]:
    """
    Calculate TrueValueX Ranking indicator (converted from Pine Script)
    
    Args:
        target_data: Target stock OHLC data
        benchmark_data: Benchmark (comparative) OHLC data  
        **kwargs: Parameters including:
            - s1: Alpha (short lookback), default=22
            - m2: Beta (mid lookback), default=66  
            - l3: Gamma (long lookback), default=222
            - strength: Trend strength (bars), default=2
            - w_long: Weight Long, default=1.5
            - w_mid: Weight Mid, default=1.0
            - w_short: Weight Short, default=0.5
            - deadband_frac: Deadband fraction, default=0.02
            - min_deadband: Minimum deadband, default=0.001
            
    Returns:
        List of dictionaries with TrueValueX ranking scores
    """
    
    # Extract parameters with defaults
    s1 = kwargs.get('s1', 22)
    m2 = kwargs.get('m2', 66) 
    l3 = kwargs.get('l3', 222)
    strength = kwargs.get('strength', 2)
    w_long = kwargs.get('w_long', 1.5)
    w_mid = kwargs.get('w_mid', 1.0)
    w_short = kwargs.get('w_short', 0.5)
    deadband_frac = kwargs.get('deadband_frac', 0.02)
    min_deadband = kwargs.get('min_deadband', 0.001)
    
    if not target_data or not benchmark_data:
        logger.warning("Insufficient data for TrueValueX calculation")
        return []
    
    # Convert to DataFrames for easier manipulation
    target_df = pd.DataFrame(target_data)
    benchmark_df = pd.DataFrame(benchmark_data)
    
    # Ensure date columns are datetime
    target_df['date'] = pd.to_datetime(target_df['date'])
    benchmark_df['date'] = pd.to_datetime(benchmark_df['date'])
    
    # Merge on dates (inner join to get common dates)
    merged_df = pd.merge(target_df, benchmark_df, on='date', suffixes=('_target', '_bench'))
    
    if len(merged_df) < max(s1, m2, l3):
        logger.warning(f"Insufficient aligned data for TrueValueX calculation. Need at least {max(s1, m2, l3)} records")
        return []
    
    # Sort by date
    merged_df = merged_df.sort_values('date')
    
    # Calculate relative prices (target/benchmark)
    c = merged_df['close_price_target'].values / merged_df['close_price_bench'].values
    o = merged_df['open_price_target'].values / merged_df['open_price_bench'].values  
    h = merged_df['high_price_target'].values / merged_df['high_price_bench'].values
    l = merged_df['low_price_target'].values / merged_df['low_price_bench'].values
    
    # Calculate dynamic Fibonacci levels (exactly as Pine Script)
    s23 = TrueValueXHelper.dynamic_fib(h, l, s1)
    m23 = TrueValueXHelper.dynamic_fib(h, l, m2)
    l23 = TrueValueXHelper.dynamic_fib(h, l, l3)
    
    # Smooth dynamic Fibs to reduce spikes (Pine Script: ta.ema(s23, 3))
    s23_smooth = TrueValueXHelper.ema(s23, 3)
    m23_smooth = TrueValueXHelper.ema(m23, 3)
    l23_smooth = TrueValueXHelper.ema(l23, 3)
    
    # Calculate ranges for deadbands
    def get_range(high_vals, low_vals, length):
        result = np.full(len(high_vals), np.nan)
        for i in range(length - 1, len(high_vals)):
            start_idx = i - length + 1
            window_high = high_vals[start_idx:i+1]
            window_low = low_vals[start_idx:i+1]
            result[i] = np.max(window_high) - np.min(window_low)
        return result
    
    rng_s = get_range(h, l, s1)
    rng_m = get_range(h, l, m2)  
    rng_l = get_range(h, l, l3)
    
    # Calculate deadbands
    db_s = np.maximum(deadband_frac * rng_s, min_deadband)
    db_m = np.maximum(deadband_frac * rng_m, min_deadband)
    db_l = np.maximum(deadband_frac * rng_l, min_deadband)
    
    # Calculate scaled votes (structural scores)
    vs = TrueValueXHelper.vote_scaled(c, s23_smooth, db_s)
    vm = TrueValueXHelper.vote_scaled(c, m23_smooth, db_m)
    vl = TrueValueXHelper.vote_scaled(c, l23_smooth, db_l)
    
    # Normalize weights to sum = 3
    sum_w = w_long + w_mid + w_short
    if sum_w != 0:
        scale_w = 3.0 / sum_w
        w_long *= scale_w
        w_mid *= scale_w  
        w_short *= scale_w
    
    # Calculate structural score [-3, +3]
    struct_score_raw = w_short * vs + w_mid * vm + w_long * vl
    
    # Smooth structural score
    struct_score = TrueValueXHelper.ema(struct_score_raw, 2)
    
    # Calculate trend bias scores
    trend_s = TrueValueXHelper.get_trend_color(s23_smooth, strength)
    trend_m = TrueValueXHelper.get_trend_color(m23_smooth, strength)  
    trend_l = TrueValueXHelper.get_trend_color(l23_smooth, strength)
    
    trend_score = w_short * trend_s + w_mid * trend_m + w_long * trend_l
    
    # Calculate composite score [-6, +6]
    composite_score = struct_score + trend_score
    
    # Normalize to 0-100 scale
    composite_norm = (composite_score + 6) * 100 / 12
    
    # Calculate mean scores
    mean_score_s1 = TrueValueXHelper.sma(composite_norm, s1)
    mean_score_m2 = TrueValueXHelper.sma(composite_norm, m2)
    mean_score_l3 = TrueValueXHelper.sma(composite_norm, l3)
    
    # Prepare result
    result = []
    for i, date in enumerate(merged_df['date']):
        if not np.isnan(composite_norm[i]):
            result.append({
                'date': date.strftime('%Y-%m-%d'),
                'truevx_score': round(float(composite_norm[i]), 4),
                'mean_short': round(float(mean_score_s1[i]), 4) if not np.isnan(mean_score_s1[i]) else None,
                'mean_mid': round(float(mean_score_m2[i]), 4) if not np.isnan(mean_score_m2[i]) else None,
                'mean_long': round(float(mean_score_l3[i]), 4) if not np.isnan(mean_score_l3[i]) else None,
                'structural_score': round(float(struct_score[i]), 4) if not np.isnan(struct_score[i]) else None,
                'trend_score': round(float(trend_score[i]), 4) if not np.isnan(trend_score[i]) else None,
                'indicator': 'truevx_ranking',
                'parameters': {
                    's1': s1, 'm2': m2, 'l3': l3, 'strength': strength,
                    'w_long': kwargs.get('w_long', 1.5), 'w_mid': kwargs.get('w_mid', 1.0), 'w_short': kwargs.get('w_short', 0.5)
                }
            })
    
    logger.info(f"Calculated TrueValueX Ranking for {len(result)} data points")
    return result


# ============================================================================
# DEVELOPMENT AND TESTING SECTION
# ============================================================================
# Uncomment the section below for development/testing purposes

"""
# Usage example for custom indicator development
if __name__ == "__main__":
    # Sample price data for testing
    sample_data = [
        {'date': '2024-01-01', 'close_price': 100.0},
        {'date': '2024-01-02', 'close_price': 102.0},
        {'date': '2024-01-03', 'close_price': 101.0},
        {'date': '2024-01-04', 'close_price': 103.0},
        {'date': '2024-01-05', 'close_price': 105.0},
        {'date': '2024-01-06', 'close_price': 104.0},
        {'date': '2024-01-07', 'close_price': 106.0},
        {'date': '2024-01-08', 'close_price': 108.0},
        {'date': '2024-01-09', 'close_price': 107.0},
        {'date': '2024-01-10', 'close_price': 109.0}
    ]
    
    engine = IndicatorEngine()
    print(f"Indicator Engine initialized")
    print(f"Supported indicators: {engine.get_supported_indicators()}")
    print("Ready for custom indicator development!")
    
    # Example of how to register a custom indicator
    def simple_price_change(data: List[Dict], **kwargs) -> List[Dict]:
        \"\"\"Simple example of price change calculation\"\"\"
        if len(data) < 2:
            return []
        
        sorted_data = sorted(data, key=lambda x: x['date'])
        result = []
        
        for i in range(1, len(sorted_data)):
            current = sorted_data[i]
            previous = sorted_data[i-1]
            
            change = current['close_price'] - previous['close_price']
            change_pct = (change / previous['close_price']) * 100
            
            result.append({
                'date': current['date'],
                'price_change': round(change, 4),
                'price_change_pct': round(change_pct, 4)
            })
        
        return result
    
    # Register the custom indicator
    engine.register_indicator('price_change', simple_price_change)
    
    print(f"After registration: {engine.get_supported_indicators()}")
    
    # Test the custom indicator
    result = engine.calculate_indicator('price_change', sample_data)
    print(f"Price change calculation completed: {len(result)} points")
    if result:
        print(f"Last result: {result[-1]}")
"""
