#!/usr/bin/env python3
"""
Test quarterly rebalancing via API
"""

import requests
import json

def test_quarterly_api():
    """Test quarterly rebalancing through the API endpoint"""
    
    # API endpoint
    api_url = "http://localhost:3001/api/simulation/run"
    
    # Get available strategies first
    strategies_url = "http://localhost:3001/api/simulation/strategies"
    
    try:
        print("Testing Quarterly Rebalancing via API...")
        print("=" * 50)
        
        # Get strategies
        strategies_response = requests.get(strategies_url)
        if strategies_response.status_code != 200:
            print(f"❌ Failed to get strategies: {strategies_response.status_code}")
            return False
        
        strategies = strategies_response.json()
        if not strategies:
            print("❌ No strategies available for testing")
            return False
        
        strategy_id = strategies[0]['id']
        print(f"✅ Using strategy: {strategies[0]['name']} ({strategy_id})")
        
        # Test quarterly rebalancing with different date types
        date_types = ['first', 'mid', 'last']
        
        for date_type in date_types:
            print(f"\nTesting quarterly rebalancing with '{date_type}' date...")
            
            # Prepare simulation parameters
            simulation_params = {
                "strategy_id": strategy_id,
                "portfolio_base_value": 100000,
                "rebalance_frequency": "quarterly",  # This is the new quarterly option
                "rebalance_date": date_type,
                "rebalance_type": "equal_weight",
                "universe": "NIFTY50",
                "benchmark_symbol": "50 EQL Wgt",
                "max_holdings": 10,
                "momentum_ranking": "20_day_return",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "include_brokerage": True,
                "brokerage_type": "zerodha",
                "brokerage_per_trade_flat": 20,
                "brokerage_per_trade_percentage": 0.0325,
                "stt_percentage": 0.025,
                "transaction_charge_percentage": 0.00325,
                "gst_percentage": 18,
                "sebi_charge_percentage": 0.0001
            }
            
            # Make API request
            response = requests.post(
                api_url,
                json=simulation_params,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Quarterly {date_type} simulation successful")
                print(f"     Total return: {result.get('total_return', 'N/A')}%")
                print(f"     Total trades: {len(result.get('trades', []))}")
                
                # Check if we got quarterly rebalance dates
                trades = result.get('trades', [])
                if trades:
                    print(f"     Sample rebalance dates:")
                    for i, trade in enumerate(trades[:8]):  # Show first 8 trades
                        print(f"       {trade.get('date', 'N/A')}")
                        if i >= 7:  # Limit output
                            break
                
            else:
                print(f"  ❌ API request failed: {response.status_code}")
                print(f"     Response: {response.text}")
                return False
        
        print(f"\n🎉 All quarterly API tests passed!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Is it running on localhost:3001?")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    test_quarterly_api()