#!/usr/bin/env python3
"""
Diagnostic Script for TrueValueX Calculation
Debug the early calculation periods to understand why mean values are None
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_data_manager import StockDataManager
from indicator_engine import IndicatorEngine, TrueValueXHelper


async def debug_truevx_calculation():
    """Debug TrueValueX calculation step by step"""
    print("🔍 TrueValueX Calculation Diagnostics")
    print("=" * 50)
    
    try:
        async with StockDataManager() as manager:
            # Get small sample of data for debugging
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)  # 3 months only
            
            print(f"📅 Debug Date Range: {start_date.date()} to {end_date.date()}")
            
            # Fetch TCS data
            tcs_data = await manager.get_price_data(
                symbol='TCS',
                start_date=start_date,
                end_date=end_date,
                limit=100,
                sort_order=1
            )
            
            # Fetch Nifty 50 data
            nifty_data = await manager.get_price_data(
                symbol='Nifty 50',
                start_date=start_date,
                end_date=end_date,
                limit=100,
                sort_order=1
            )
            
            print(f"📊 TCS Records: {len(tcs_data)}")
            print(f"📊 Nifty Records: {len(nifty_data)}")
            
            if not tcs_data or not nifty_data:
                print("❌ No data available for debugging")
                return
            
            # Convert to dictionary format
            tcs_dict = []
            for record in tcs_data:
                tcs_dict.append({
                    "date": record.date.isoformat(),
                    "open_price": record.open_price,
                    "high_price": record.high_price,
                    "low_price": record.low_price,
                    "close_price": record.close_price,
                    "volume": record.volume
                })
                
            nifty_dict = []
            for record in nifty_data:
                nifty_dict.append({
                    "date": record.date.isoformat(),
                    "open_price": record.open_price,
                    "high_price": record.high_price,
                    "low_price": record.low_price,
                    "close_price": record.close_price,
                    "volume": record.volume
                })
            
            # Manual calculation with debug parameters
            print("\n🧮 Manual TrueValueX Calculation Debug")
            print("=" * 40)
            
            # Use very small lookback periods for debugging
            s1, m2, l3 = 5, 10, 15  # Very small periods for debugging
            strength = 2
            
            print(f"Parameters: s1={s1}, m2={m2}, l3={l3}, strength={strength}")
            
            # Convert to DataFrames
            target_df = pd.DataFrame(tcs_dict)
            benchmark_df = pd.DataFrame(nifty_dict)
            
            # Convert dates
            target_df['date'] = pd.to_datetime(target_df['date'])
            benchmark_df['date'] = pd.to_datetime(benchmark_df['date'])
            
            # Merge on dates
            merged_df = pd.merge(target_df, benchmark_df, on='date', suffixes=('_target', '_bench'))
            merged_df = merged_df.sort_values('date')
            
            print(f"Merged Records: {len(merged_df)}")
            
            if len(merged_df) < max(s1, m2, l3):
                print(f"⚠️  Not enough data: {len(merged_df)} < {max(s1, m2, l3)}")
                return
                
            # Calculate relative prices
            c = merged_df['close_price_target'].values / merged_df['close_price_bench'].values
            o = merged_df['open_price_target'].values / merged_df['open_price_bench'].values  
            h = merged_df['high_price_target'].values / merged_df['high_price_bench'].values
            l = merged_df['low_price_target'].values / merged_df['low_price_bench'].values
            
            print(f"\n📈 Relative Price Sample (first 5):")
            for i in range(min(5, len(c))):
                print(f"   Day {i+1}: C={c[i]:.4f}, O={o[i]:.4f}, H={h[i]:.4f}, L={l[i]:.4f}")
            
            # Calculate dynamic Fibonacci levels
            print(f"\n🔢 Fibonacci Calculation Debug:")
            s23 = TrueValueXHelper.dynamic_fib(h, l, s1)
            m23 = TrueValueXHelper.dynamic_fib(h, l, m2)
            l23 = TrueValueXHelper.dynamic_fib(h, l, l3)
            
            print(f"   Short Fib (s1={s1}):")
            for i in range(min(10, len(s23))):
                val = s23[i]
                val_str = f"{val:.4f}" if not np.isnan(val) else "NaN"
                print(f"     Day {i+1}: {val_str}")
                
            print(f"   Medium Fib (m2={m2}):")
            for i in range(min(10, len(m23))):
                val = m23[i]
                val_str = f"{val:.4f}" if not np.isnan(val) else "NaN"
                print(f"     Day {i+1}: {val_str}")
            
            # Smooth fibs
            s23_smooth = TrueValueXHelper.ema(s23, 3)
            m23_smooth = TrueValueXHelper.ema(m23, 3)
            l23_smooth = TrueValueXHelper.ema(l23, 3)
            
            print(f"\n📊 Smoothed Fibonacci (first 10):")
            for i in range(min(10, len(s23_smooth))):
                s_val = s23_smooth[i] if not np.isnan(s23_smooth[i]) else None
                m_val = m23_smooth[i] if not np.isnan(m23_smooth[i]) else None
                l_val = l23_smooth[i] if not np.isnan(l23_smooth[i]) else None
                
                s_str = f"{s_val:.4f}" if s_val is not None else "None"
                m_str = f"{m_val:.4f}" if m_val is not None else "None"
                l_str = f"{l_val:.4f}" if l_val is not None else "None"
                
                print(f"   Day {i+1}: Short={s_str}, Med={m_str}, Long={l_str}")
            
            # Test the full calculation
            print(f"\n🎯 Running Full TrueValueX with Debug Parameters")
            engine = IndicatorEngine()
            
            result = await engine.calculate_truevx_ranking(
                data=tcs_dict,
                base_symbol="Nifty 50",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                s1=s1, m2=m2, l3=l3, strength=strength
            )
            
            print(f"✅ Result: {len(result)} data points")
            
            if result:
                print(f"\n📋 First 10 TrueValueX Results:")
                for i, point in enumerate(result[:10]):
                    date = point['date']
                    score = point.get('truevx_score', 'N/A')
                    struct = point.get('structural_score', 'N/A')
                    trend = point.get('trend_score', 'N/A')
                    mean_s = point.get('mean_short', 'N/A')
                    mean_m = point.get('mean_mid', 'N/A')
                    mean_l = point.get('mean_long', 'N/A')
                    
                    score_str = f"{score:.2f}" if isinstance(score, (int, float)) else "N/A"
                    struct_str = f"{struct:.2f}" if isinstance(struct, (int, float)) and struct is not None else "N/A"
                    trend_str = f"{trend:.2f}" if isinstance(trend, (int, float)) and trend is not None else "N/A"
                    mean_s_str = f"{mean_s:.2f}" if mean_s is not None and isinstance(mean_s, (int, float)) else "None"
                    mean_m_str = f"{mean_m:.2f}" if mean_m is not None and isinstance(mean_m, (int, float)) else "None"
                    mean_l_str = f"{mean_l:.2f}" if mean_l is not None and isinstance(mean_l, (int, float)) else "None"
                    
                    print(f"   {i+1:2d}. {date}: Score={score_str} | " +
                          f"Struct={struct_str} | " +
                          f"Trend={trend_str} | " +
                          f"Means: S={mean_s_str} " +
                          f"M={mean_m_str} " +
                          f"L={mean_l_str}")
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    print("🚀 Starting TrueValueX Diagnostics")
    await debug_truevx_calculation()


if __name__ == "__main__":
    asyncio.run(main())
