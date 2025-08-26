#!/usr/bin/env python3
"""
Test TrueValueX Ranking Indicator with Real Market Data

This script tests the TrueValueX indicator with real TCS vs Nifty 50 data
to validate the implementation works with production data.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_data_manager import StockDataManager
from indicator_engine import IndicatorEngine


async def test_truevx_with_real_data():
    """Test TrueValueX indicator with real TCS and Nifty 50 data"""
    print("🧪 Testing TrueValueX Indicator with Real Market Data")
    print("=" * 60)
    
    try:
        async with StockDataManager() as manager:
            # Get TCS data for the last 1 year to ensure we have enough data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # 1 year
            
            print(f"📅 Date Range: {start_date.date()} to {end_date.date()}")
            print(f"📈 Target Stock: TCS")
            print(f"📊 Base Index: Nifty 50")
            print()
            
            # Fetch TCS price data
            print("🔍 Fetching TCS price data...")
            tcs_data = await manager.get_price_data(
                symbol='TCS',
                start_date=start_date,
                end_date=end_date,
                limit=5000,
                sort_order=1  # Ascending order for calculation
            )
            
            if not tcs_data:
                print("❌ No TCS data found!")
                return False
                
            print(f"✅ Retrieved {len(tcs_data)} TCS price records")
            
            # Convert to dictionary format for indicator engine
            tcs_dict_data = []
            for record in tcs_data:
                tcs_dict_data.append({
                    "date": record.date.isoformat(),
                    "open_price": record.open_price,
                    "high_price": record.high_price,
                    "low_price": record.low_price,
                    "close_price": record.close_price,
                    "volume": record.volume
                })
            
            print(f"📋 Sample TCS data point:")
            print(f"   Date: {tcs_dict_data[0]['date']}")
            print(f"   OHLC: {tcs_dict_data[0]['open_price']}, {tcs_dict_data[0]['high_price']}, {tcs_dict_data[0]['low_price']}, {tcs_dict_data[0]['close_price']}")
            print()
            
            # Initialize indicator engine
            print("⚙️ Initializing TrueValueX calculation...")
            engine = IndicatorEngine()
            
            # Calculate TrueValueX ranking with smaller lookback periods for testing
            calculation_start = datetime.now()
            
            truevx_data = await engine.calculate_truevx_ranking(
                data=tcs_dict_data,
                base_symbol="Nifty 50",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                # Use smaller lookback periods for testing
                s1=10,   # Short: 10 days instead of 22
                m2=30,   # Medium: 30 days instead of 66
                l3=60    # Long: 60 days instead of 222
            )
            
            calculation_time = (datetime.now() - calculation_start).total_seconds()
            
            print(f"✅ TrueValueX calculation completed in {calculation_time:.3f} seconds")
            print(f"📊 Generated {len(truevx_data)} TrueValueX data points")
            print()
            
            if truevx_data:
                # Check the structure of the first data point
                print("🔍 TrueValueX data structure:")
                first_point = truevx_data[0]
                print(f"   Keys: {list(first_point.keys())}")
                print(f"   Sample: {first_point}")
                print()
                
                # Show first few results (adapt to actual structure)
                print("📈 First 5 TrueValueX Rankings:")
                for i, point in enumerate(truevx_data[:5]):
                    date = point['date']
                    # Use truevx_score as the main ranking value
                    ranking = point.get('truevx_score', 'N/A')
                    structural = point.get('structural_score', 'N/A')
                    trend = point.get('trend_score', 'N/A')
                    print(f"   {i+1}. {date}: Score={ranking:.1f} (Struct={structural:.1f}, Trend={trend:.1f})")
                
                print()
                
                # Show last few results
                print("📈 Last 5 TrueValueX Rankings:")
                for i, point in enumerate(truevx_data[-5:]):
                    date = point['date']
                    ranking = point.get('truevx_score', 'N/A')
                    structural = point.get('structural_score', 'N/A')
                    trend = point.get('trend_score', 'N/A')
                    print(f"   {i+1}. {date}: Score={ranking:.1f} (Struct={structural:.1f}, Trend={trend:.1f})")
                
                print()
                
                # Statistics using truevx_score
                try:
                    rankings = [point['truevx_score'] for point in truevx_data if point.get('truevx_score') is not None]
                    
                    if rankings:
                        min_rank = min(rankings)
                        max_rank = max(rankings)
                        avg_rank = sum(rankings) / len(rankings)
                        
                        print("📊 TrueValueX Statistics:")
                        print(f"   Min Ranking: {min_rank:.2f}")
                        print(f"   Max Ranking: {max_rank:.2f}")
                        print(f"   Avg Ranking: {avg_rank:.2f}")
                        print(f"   Valid Range: {50 <= min_rank <= 100 and 50 <= max_rank <= 100}")
                        
                        # Performance analysis
                        recent_data = truevx_data[-10:]  # Last 10 days
                        recent_rankings = [point['truevx_score'] for point in recent_data if point.get('truevx_score') is not None]
                        
                        if recent_rankings:
                            recent_avg = sum(recent_rankings) / len(recent_rankings)
                            
                            print()
                            print("🎯 Performance Analysis:")
                            print(f"   Recent 10-day average: {recent_avg:.2f}")
                            
                            if recent_avg > 75:
                                print("   📈 Strong performance vs Nifty 50")
                            elif recent_avg > 60:
                                print("   📊 Moderate performance vs Nifty 50") 
                            else:
                                print("   📉 Underperforming vs Nifty 50")
                            
                            # Show trend analysis
                            structural_scores = [point.get('structural_score', 0) for point in recent_data]
                            trend_scores = [point.get('trend_score', 0) for point in recent_data]
                            
                            avg_structural = sum(structural_scores) / len(structural_scores) if structural_scores else 0
                            avg_trend = sum(trend_scores) / len(trend_scores) if trend_scores else 0
                            
                            print(f"   Recent structural component: {avg_structural:.2f}")
                            print(f"   Recent trend component: {avg_trend:.2f}")
                    else:
                        print("⚠️ No valid ranking scores found")
                        
                except Exception as e:
                    print(f"⚠️ Error calculating statistics: {e}")
                
                print()
                print("✅ TrueValueX indicator test completed successfully!")
                return True
                
            else:
                print("❌ No TrueValueX data generated!")
                return False
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🚀 Starting TrueValueX Real Data Test")
    print()
    
    success = await test_truevx_with_real_data()
    
    print()
    if success:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
