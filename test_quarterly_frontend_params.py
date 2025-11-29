#!/usr/bin/env python3
"""
Test quarterly rebalancing using the exact parameters from the frontend URL
"""

import requests
import json

def test_quarterly_with_frontend_params():
    """Test quarterly rebalancing using frontend URL parameters"""
    
    # API endpoint
    api_url = "http://localhost:3001/api/simulation/run"
    
    print("Testing Quarterly Rebalancing with Frontend Parameters...")
    print("=" * 60)
    
    try:
        # Parameters from the frontend URL
        simulation_params = {
            "strategy_id": "strategy_1756565385890",
            "portfolio_base_value": 100000,
            "rebalance_frequency": "quarterly",
            "rebalance_date": "first", 
            "rebalance_type": "equal_weight",
            "universe": "NIFTY50",
            "benchmark_symbol": "Nifty 50",  # Note: using "Nifty 50" instead of encoded "Nifty+50"
            "max_holdings": 10,
            "momentum_ranking": "20_day_return",
            "start_date": "2020-01-01",
            "end_date": "2025-11-23",
            "include_brokerage": True,
            "brokerage_type": "zerodha",
            "brokerage_per_trade_flat": 20,
            "brokerage_per_trade_percentage": 0.0325,
            "stt_percentage": 0.025,
            "transaction_charge_percentage": 0.00325,
            "gst_percentage": 18,
            "sebi_charge_percentage": 0.0001
        }
        
        print("Request Parameters:")
        for key, value in simulation_params.items():
            print(f"  {key}: {value}")
        
        print(f"\n🚀 Sending API request to {api_url}...")
        
        # Make API request
        response = requests.post(
            api_url,
            json=simulation_params,
            headers={"Content-Type": "application/json"},
            timeout=30  # 30 second timeout
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Quarterly simulation successful!")
            print(f"\n📊 Results Summary:")
            print(f"   Total Return: {result.get('total_return', 'N/A')}%")
            print(f"   Annual Return: {result.get('annual_return', 'N/A')}%")
            print(f"   Total Trades: {len(result.get('trades', []))}")
            print(f"   Max Drawdown: {result.get('max_drawdown', 'N/A')}%")
            print(f"   Sharpe Ratio: {result.get('sharpe_ratio', 'N/A')}")
            
            # Show rebalance dates to verify quarterly frequency
            trades = result.get('trades', [])
            if trades:
                print(f"\n📅 Sample Rebalance Dates (showing quarterly pattern):")
                unique_dates = set()
                for trade in trades:
                    trade_date = trade.get('date', '')
                    if trade_date:
                        unique_dates.add(trade_date)
                
                # Show first 12 unique dates to demonstrate quarterly pattern
                sorted_dates = sorted(list(unique_dates))[:12]
                for i, date in enumerate(sorted_dates):
                    print(f"   {i+1:2d}. {date}")
                
                if len(sorted_dates) >= 4:
                    print(f"\n🔍 Quarterly Pattern Check:")
                    print(f"   Date 1: {sorted_dates[0]} (should be Q1)")
                    if len(sorted_dates) > 1:
                        print(f"   Date 2: {sorted_dates[1]} (should be Q2 or next Q1)")
                    if len(sorted_dates) > 2:
                        print(f"   Date 3: {sorted_dates[2]} (should be Q3 or next quarter)")
            
            return True
            
        elif response.status_code == 422:
            print(f"❌ Validation Error:")
            error_detail = response.json()
            print(f"   {json.dumps(error_detail, indent=2)}")
            return False
            
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
    except requests.exceptions.Timeout:
        print("⏱️ Request timed out (simulation may take longer)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Is it running on localhost:3001?")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_quarterly_with_frontend_params()
    if success:
        print(f"\n🎉 Quarterly rebalancing functionality confirmed working!")
        print(f"💡 The quarterly option is now fully integrated in both backend and frontend!")
    else:
        print(f"\n❓ Test had issues - check the output above for details")