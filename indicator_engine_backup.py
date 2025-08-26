#!/usr/bin/env python3
"""
Indicator Engine for Market Hunt
Calculates custom technical indicators for stock price data
Starting fresh with clean architecture for custom indicators
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
        """Simple example of price change calculation"""
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
    
    def calculate_sma(self, data: List[Dict], period: int = 20, price_field: str = 'close_price') -> List[Dict]:
        """
        Calculate Simple Moving Average (SMA) - Optimized with NumPy
        
        Args:
            data: List of price data dictionaries with date and price fields
            period: Period for SMA calculation (default: 20)
            price_field: Field to use for calculation (default: 'close_price')
            
        Returns:
            List of dictionaries with date and SMA values
        """
        try:
            if not data or len(data) < period:
                logger.warning(f"Insufficient data for SMA calculation. Need at least {period} records, got {len(data) if data else 0}")
                return []
            
            # Convert to numpy arrays for faster calculation
            dates = []
            prices = []
            
            # Sort data by date first
            sorted_data = sorted(data, key=lambda x: x['date'])
            
            for item in sorted_data:
                if price_field in item and item[price_field] is not None:
                    dates.append(item['date'])
                    prices.append(float(item[price_field]))
            
            if len(prices) < period:
                logger.warning(f"Insufficient valid price data for SMA calculation. Need {period}, got {len(prices)}")
                return []
            
            # Use numpy for fast rolling calculation
            prices_array = np.array(prices)
            sma_values = np.convolve(prices_array, np.ones(period)/period, mode='valid')
            
            # Prepare result with proper date alignment
            sma_data = []
            start_idx = period - 1  # Skip first (period-1) points as they don't have enough data
            
            for i, sma_value in enumerate(sma_values):
                date_idx = start_idx + i
                if date_idx < len(dates):
                    sma_data.append({
                        'date': dates[date_idx],
                        'value': float(sma_value),
                        'indicator': 'sma',
                        'period': period,
                        'price_field': price_field
                    })
            
            logger.info(f"Calculated SMA({period}) for {len(sma_data)} data points using NumPy optimization")
            return sma_data
            
        except Exception as e:
            logger.error(f"Error calculating SMA: {e}")
            raise
    
    def calculate_ema(self, data: List[Dict], period: int = 20, price_field: str = 'close_price') -> List[Dict]:
        """
        Calculate Exponential Moving Average (EMA)
        
        Args:
            data: List of price data dictionaries
            period: Period for EMA calculation (default: 20)
            price_field: Field to use for calculation (default: 'close_price')
            
        Returns:
            List of dictionaries with date and EMA values
        """
        try:
            if not data or len(data) < period:
                logger.warning(f"Insufficient data for EMA calculation. Need at least {period} records, got {len(data) if data else 0}")
                return []
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Calculate EMA
            df[f'ema_{period}'] = df[price_field].ewm(span=period, adjust=False).mean()
            
            # Prepare result (EMA starts from first value, unlike SMA)
            ema_data = []
            for _, row in df.iterrows():
                if not pd.isna(row[f'ema_{period}']):
                    ema_data.append({
                        'date': row['date'].isoformat(),
                        'value': float(row[f'ema_{period}']),
                        'indicator': 'ema',
                        'period': period,
                        'price_field': price_field
                    })
            
            logger.info(f"Calculated EMA({period}) for {len(ema_data)} data points")
            return ema_data
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            raise
    
    def calculate_rsi(self, data: List[Dict], period: int = 14, price_field: str = 'close_price') -> List[Dict]:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            data: List of price data dictionaries
            period: Period for RSI calculation (default: 14)
            price_field: Field to use for calculation (default: 'close_price')
            
        Returns:
            List of dictionaries with date and RSI values
        """
        try:
            if not data or len(data) < period + 1:
                logger.warning(f"Insufficient data for RSI calculation. Need at least {period + 1} records, got {len(data) if data else 0}")
                return []
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Calculate price changes
            df['price_change'] = df[price_field].diff()
            
            # Separate gains and losses
            df['gain'] = df['price_change'].where(df['price_change'] > 0, 0)
            df['loss'] = -df['price_change'].where(df['price_change'] < 0, 0)
            
            # Calculate moving averages of gains and losses
            df['avg_gain'] = df['gain'].rolling(window=period, min_periods=period).mean()
            df['avg_loss'] = df['loss'].rolling(window=period, min_periods=period).mean()
            
            # Calculate RSI
            df['rs'] = df['avg_gain'] / df['avg_loss']
            df[f'rsi_{period}'] = 100 - (100 / (1 + df['rs']))
            
            # Prepare result
            rsi_data = []
            for _, row in df.iterrows():
                if not pd.isna(row[f'rsi_{period}']):
                    rsi_data.append({
                        'date': row['date'].isoformat(),
                        'value': float(row[f'rsi_{period}']),
                        'indicator': 'rsi',
                        'period': period,
                        'price_field': price_field
                    })
            
            logger.info(f"Calculated RSI({period}) for {len(rsi_data)} data points")
            return rsi_data
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            raise
    
    def calculate_macd(self, data: List[Dict], fast_period: int = 12, slow_period: int = 26, 
                      signal_period: int = 9, price_field: str = 'close_price') -> List[Dict]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            data: List of price data dictionaries
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line EMA period (default: 9)
            price_field: Field to use for calculation (default: 'close_price')
            
        Returns:
            List of dictionaries with date, MACD, signal, and histogram values
        """
        try:
            if not data or len(data) < slow_period + signal_period:
                logger.warning(f"Insufficient data for MACD calculation. Need at least {slow_period + signal_period} records, got {len(data) if data else 0}")
                return []
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Calculate fast and slow EMAs
            df['ema_fast'] = df[price_field].ewm(span=fast_period, adjust=False).mean()
            df['ema_slow'] = df[price_field].ewm(span=slow_period, adjust=False).mean()
            
            # Calculate MACD line
            df['macd'] = df['ema_fast'] - df['ema_slow']
            
            # Calculate signal line
            df['signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
            
            # Calculate histogram
            df['histogram'] = df['macd'] - df['signal']
            
            # Prepare result
            macd_data = []
            for _, row in df.iterrows():
                if not pd.isna(row['signal']):  # Wait for signal line to be available
                    macd_data.append({
                        'date': row['date'].isoformat(),
                        'macd': float(row['macd']),
                        'signal': float(row['signal']),
                        'histogram': float(row['histogram']),
                        'indicator': 'macd',
                        'fast_period': fast_period,
                        'slow_period': slow_period,
                        'signal_period': signal_period,
                        'price_field': price_field
                    })
            
            logger.info(f"Calculated MACD({fast_period},{slow_period},{signal_period}) for {len(macd_data)} data points")
            return macd_data
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            raise
    
    def calculate_bollinger_bands(self, data: List[Dict], period: int = 20, std_dev: float = 2.0, 
                                 price_field: str = 'close_price') -> List[Dict]:
        """
        Calculate Bollinger Bands
        
        Args:
            data: List of price data dictionaries
            period: Period for moving average and standard deviation (default: 20)
            std_dev: Number of standard deviations for bands (default: 2.0)
            price_field: Field to use for calculation (default: 'close_price')
            
        Returns:
            List of dictionaries with date, middle band (SMA), upper band, and lower band values
        """
        try:
            if not data or len(data) < period:
                logger.warning(f"Insufficient data for Bollinger Bands calculation. Need at least {period} records, got {len(data) if data else 0}")
                return []
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Calculate middle band (SMA)
            df['middle_band'] = df[price_field].rolling(window=period, min_periods=period).mean()
            
            # Calculate standard deviation
            df['std'] = df[price_field].rolling(window=period, min_periods=period).std()
            
            # Calculate upper and lower bands
            df['upper_band'] = df['middle_band'] + (df['std'] * std_dev)
            df['lower_band'] = df['middle_band'] - (df['std'] * std_dev)
            
            # Prepare result
            bb_data = []
            for _, row in df.iterrows():
                if not pd.isna(row['middle_band']):
                    bb_data.append({
                        'date': row['date'].isoformat(),
                        'upper_band': float(row['upper_band']),
                        'middle_band': float(row['middle_band']),
                        'lower_band': float(row['lower_band']),
                        'indicator': 'bollinger',
                        'period': period,
                        'std_dev': std_dev,
                        'price_field': price_field
                    })
            
            logger.info(f"Calculated Bollinger Bands({period},{std_dev}) for {len(bb_data)} data points")
            return bb_data
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            raise
    
    async def calculate_crs(self, data: List[Dict], base_symbol: str = "Nifty 500", 
                           start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Calculate Comparative Relative Strength (CRS)
        
        Args:
            data: List of stock price data dictionaries (target symbol)
            base_symbol: Base symbol for comparison (default: "Nifty 500")
            start_date: Start date for base data retrieval
            end_date: End date for base data retrieval
            
        Returns:
            List of dictionaries with date and CRS OHLC values
        """
        try:
            if not data:
                logger.warning("No data provided for CRS calculation")
                return []
            
            # Import here to avoid circular imports
            from stock_data_manager import StockDataManager
            
            # Get base symbol data
            async with StockDataManager() as manager:
                # Parse date range from target data if not provided
                if not start_date:
                    start_date = min(item['date'] for item in data)
                if not end_date:
                    end_date = max(item['date'] for item in data)
                
                # Convert string dates to datetime objects
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_date.replace('T', ' ').split('.')[0]) if isinstance(start_date, str) else start_date
                end_dt = datetime.fromisoformat(end_date.replace('T', ' ').split('.')[0]) if isinstance(end_date, str) else end_date
                
                # Get base symbol data (Nifty 500)
                base_data = await manager.get_price_data(
                    symbol=base_symbol,
                    start_date=start_dt,
                    end_date=end_dt,
                    sort_order=1  # Ascending order
                )
                
                if not base_data:
                    logger.error(f"No base data found for symbol {base_symbol}")
                    return []
            
            # Convert base data to dictionary keyed by date for fast lookup
            base_dict = {}
            for record in base_data:
                date_key = record.date.strftime('%Y-%m-%d')
                base_dict[date_key] = {
                    'open_price': record.open_price,
                    'high_price': record.high_price,
                    'low_price': record.low_price,
                    'close_price': record.close_price
                }
            
            # Calculate CRS for each data point
            crs_data = []
            for item in sorted(data, key=lambda x: x['date']):
                # Extract date from target data
                target_date = item['date']
                if isinstance(target_date, str):
                    target_date = target_date.split('T')[0]  # Extract date part
                
                # Find matching base data
                if target_date in base_dict:
                    base_record = base_dict[target_date]
                    
                    # Calculate CRS for OHLC
                    crs_record = {
                        'date': item['date'],
                        'crs_open': item.get('open_price', 0) / base_record['open_price'] if base_record['open_price'] != 0 else 0,
                        'crs_high': item.get('high_price', 0) / base_record['high_price'] if base_record['high_price'] != 0 else 0,
                        'crs_low': item.get('low_price', 0) / base_record['low_price'] if base_record['low_price'] != 0 else 0,
                        'crs_close': item.get('close_price', 0) / base_record['close_price'] if base_record['close_price'] != 0 else 0,
                        'indicator': 'crs',
                        'base_symbol': base_symbol
                    }
                    crs_data.append(crs_record)
            
            logger.info(f"Calculated CRS for {len(crs_data)} data points against {base_symbol}")
            return crs_data
            
        except Exception as e:
            logger.error(f"Error calculating CRS: {e}")
            raise
    
    def calculate_dynamic_fib(self, data: List[Dict], lookback: List[int] = None, **kwargs) -> List[Dict]:
        """
        Calculate Dynamic Fibonacci 23.6% retracement level with trend direction for multiple periods
        
        Args:
            data: List of stock price data dictionaries (can be price data or CRS data with OHLC)
            lookback: List of lookback periods. Default: [22, 66, 222]
            
        Returns:
            List of dictionaries with date, fib_23 values for each period, trend direction, and color
        """
        try:
            if lookback is None:
                lookback = [22, 66, 222]
            
            if not data:
                logger.warning("No data provided for Dynamic Fibonacci calculation")
                return []
            
            # Check minimum data requirement (largest lookback period)
            max_lookback = max(lookback)
            if len(data) < max_lookback:
                logger.warning(f"Insufficient data for Dynamic Fibonacci calculation. Need at least {max_lookback} records, got {len(data)}")
                return []
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Determine OHLC field names based on data type
            # For CRS data, use crs_open, crs_high, crs_low, crs_close
            # For price data, use open_price, high_price, low_price, close_price
            if 'crs_high' in df.columns and 'crs_low' in df.columns:
                # CRS data
                high_field = 'crs_high'
                low_field = 'crs_low'
                open_field = 'crs_open'
                close_field = 'crs_close'
                data_type = 'crs'
            elif 'high_price' in df.columns and 'low_price' in df.columns:
                # Price data
                high_field = 'high_price'
                low_field = 'low_price'
                open_field = 'open_price'
                close_field = 'close_price'
                data_type = 'price'
            else:
                logger.error("Data must contain either OHLC price fields (high_price, low_price) or CRS fields (crs_high, crs_low)")
                return []
            
            # Prepare result list
            fib_data = []
            
            # Calculate for each lookback period
            for period in lookback:
                if len(data) < period:
                    logger.warning(f"Insufficient data for lookback period {period}. Skipping.")
                    continue
                
                # Calculate rolling highest high and lowest low for this period
                trend_hh_col = f'trend_hh_{period}'
                trend_ll_col = f'trend_ll_{period}'
                fib_23_col = f'fib_23_{period}'
                
                df[trend_hh_col] = df[high_field].rolling(window=period, min_periods=period).max()
                df[trend_ll_col] = df[low_field].rolling(window=period, min_periods=period).min()
                
                # Calculate 23.6% Fibonacci retracement level
                df[fib_23_col] = df[trend_ll_col] + (df[trend_hh_col] - df[trend_ll_col]) * 0.236
                
                # Calculate trend direction (rising/falling for last 2 periods)
                fib_rising_col = f'fib_rising_{period}'
                fib_falling_col = f'fib_falling_{period}'
                trend_rising_col = f'trend_rising_{period}'
                trend_falling_col = f'trend_falling_{period}'
                color_col = f'color_{period}'
                
                df[fib_rising_col] = df[fib_23_col].diff(1) > 0
                df[fib_falling_col] = df[fib_23_col].diff(1) < 0
                
                # Initialize trend columns
                df[trend_rising_col] = False
                df[trend_falling_col] = False
                
                # Apply trend logic similar to Pine Script
                for i in range(2, len(df)):
                    current_rising = df.iloc[i][fib_rising_col]
                    current_falling = df.iloc[i][fib_falling_col]
                    prev_fib_rising = df.iloc[i-1][fib_rising_col] if i > 1 else False
                    prev_fib_falling = df.iloc[i-1][fib_falling_col] if i > 1 else False
                    
                    # Rising trend logic: if per_r or (per_r[1] and not per_f)
                    if current_rising or (prev_fib_rising and not current_falling):
                        df.iloc[i, df.columns.get_loc(trend_rising_col)] = True
                        
                    # Falling trend logic: if per_f or (per_f[1] and not per_r)
                    if current_falling or (prev_fib_falling and not current_rising):
                        df.iloc[i, df.columns.get_loc(trend_falling_col)] = True
                
                # Determine color based on trend
                def get_color(rising, falling):
                    if rising:
                        return 'green'
                    elif falling:
                        return 'red'
                    else:
                        return 'neutral'
                
                df[color_col] = df.apply(lambda row: get_color(row[trend_rising_col], row[trend_falling_col]), axis=1)
            
            # Prepare combined result for all periods
            for _, row in df.iterrows():
                # Check if we have valid data for at least one period
                has_valid_data = False
                row_data = {
                    'date': row['date'].isoformat(),
                    'indicator': 'dynamic_fib',
                    'data_type': data_type,
                    'lookback_periods': lookback
                }
                
                # Add data for each period
                for period in lookback:
                    fib_23_col = f'fib_23_{period}'
                    if fib_23_col in row and not pd.isna(row[fib_23_col]):
                        has_valid_data = True
                        row_data[f'fib_23_{period}'] = float(row[fib_23_col])
                        row_data[f'trend_hh_{period}'] = float(row[f'trend_hh_{period}'])
                        row_data[f'trend_ll_{period}'] = float(row[f'trend_ll_{period}'])
                        row_data[f'trend_rising_{period}'] = bool(row[f'trend_rising_{period}'])
                        row_data[f'trend_falling_{period}'] = bool(row[f'trend_falling_{period}'])
                        row_data[f'color_{period}'] = row[f'color_{period}']
                
                if has_valid_data:
                    fib_data.append(row_data)
            
            logger.info(f"Calculated Dynamic Fibonacci for periods {lookback} on {data_type} data: {len(fib_data)} data points")
            return fib_data
            
        except Exception as e:
            logger.error(f"Error calculating Dynamic Fibonacci: {e}")
            raise

    def calculate_indicator(self, indicator_type: str, data: List[Dict], **kwargs) -> List[Dict]:
        """
        Generic method to calculate any supported indicator with caching
        
        Args:
            indicator_type: Type of indicator ('sma', 'ema', 'rsi', 'macd', 'bollinger')
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

# Usage example and testing
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
        {'date': '2024-01-10', 'close_price': 109.0},
        {'date': '2024-01-11', 'close_price': 111.0},
        {'date': '2024-01-12', 'close_price': 110.0},
        {'date': '2024-01-13', 'close_price': 112.0},
        {'date': '2024-01-14', 'close_price': 114.0},
        {'date': '2024-01-15', 'close_price': 113.0},
        {'date': '2024-01-16', 'close_price': 115.0},
        {'date': '2024-01-17', 'close_price': 117.0},
        {'date': '2024-01-18', 'close_price': 116.0},
        {'date': '2024-01-19', 'close_price': 118.0},
        {'date': '2024-01-20', 'close_price': 120.0},
    ]
    
    engine = IndicatorEngine()
    
    # Test SMA calculation
    sma_result = engine.calculate_sma(sample_data, period=5)
    print(f"SMA(5) calculated for {len(sma_result)} points")
    if sma_result:
        print(f"Last SMA value: {sma_result[-1]}")
    
    # Test EMA calculation
    ema_result = engine.calculate_ema(sample_data, period=5)
    print(f"EMA(5) calculated for {len(ema_result)} points")
    if ema_result:
        print(f"Last EMA value: {ema_result[-1]}")
