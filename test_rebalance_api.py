"""
Test script to verify rebalance date selection works via API
"""
import requests
import json
from datetime import datetime

def test_rebalance_dates_via_api():
    """Test rebalance date selection with actual simulation API"""
    
    base_url = "http://localhost:3001"
    
    # Test parameters - short date range for quick testing
    test_params = {
        "strategy_id": "strategy_1756565385890",
        "portfolio_base_value": 100000,
        "rebalance_frequency": "monthly",
        "universe": "NIFTY50",
        "benchmark_symbol": "Nifty 50",
        "max_holdings": 10,
        "momentum_ranking": "20_day_return",
        "start_date": "2024-01-01",
        "end_date": "2024-03-31",  # Just 3 months for quick test
        "include_brokerage": False,
        "rebalance_type": "equal_weight"
    }
    
    print("=" * 70)
    print("TESTING REBALANCE DATE SELECTION VIA API")
    print("=" * 70)
    print(f"\nTest Period: {test_params['start_date']} to {test_params['end_date']}")
    print(f"Frequency: {test_params['rebalance_frequency']}")
    print()
    
    # Test 1: First available date
    print("=" * 70)
    print("TEST 1: FIRST AVAILABLE DATE")
    print("=" * 70)
    test_params["rebalance_date"] = "first"
    
    try:
        response = requests.post(f"{base_url}/api/simulation/run", json=test_params)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                results = data["simulation"]["results"]
                rebalance_days = [r for r in results if r.get("new_added") or r.get("exited")]
                
                print(f"✅ API Call Successful")
                print(f"📅 Rebalance Events Found: {len(rebalance_days)}")
                print("\nRebalance Dates:")
                for r in rebalance_days[:5]:  # Show first 5
                    date = r["date"]
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    print(f"   {date} (Day of month: {date_obj.day})")
            else:
                print(f"❌ API returned error: {data.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text[:500])
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print()
    
    # Test 2: Mid period date
    print("=" * 70)
    print("TEST 2: MID PERIOD DATE")
    print("=" * 70)
    test_params["rebalance_date"] = "mid"
    
    try:
        response = requests.post(f"{base_url}/api/simulation/run", json=test_params)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                results = data["simulation"]["results"]
                rebalance_days = [r for r in results if r.get("new_added") or r.get("exited")]
                
                print(f"✅ API Call Successful")
                print(f"📅 Rebalance Events Found: {len(rebalance_days)}")
                print("\nRebalance Dates:")
                for r in rebalance_days[:5]:  # Show first 5
                    date = r["date"]
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    print(f"   {date} (Day of month: {date_obj.day})")
            else:
                print(f"❌ API returned error: {data.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text[:500])
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print()
    
    # Test 3: Last available date
    print("=" * 70)
    print("TEST 3: LAST AVAILABLE DATE")
    print("=" * 70)
    test_params["rebalance_date"] = "last"
    
    try:
        response = requests.post(f"{base_url}/api/simulation/run", json=test_params)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                results = data["simulation"]["results"]
                rebalance_days = [r for r in results if r.get("new_added") or r.get("exited")]
                
                print(f"✅ API Call Successful")
                print(f"📅 Rebalance Events Found: {len(rebalance_days)}")
                print("\nRebalance Dates:")
                for r in rebalance_days[:5]:  # Show first 5
                    date = r["date"]
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    print(f"   {date} (Day of month: {date_obj.day})")
                    
                print("\n" + "=" * 70)
                print("✅ ALL TESTS COMPLETED")
                print("=" * 70)
                print("\n💡 Check the 'Day of month' values:")
                print("   - FIRST should show early days (1-5)")
                print("   - MID should show middle days (10-20)")
                print("   - LAST should show late days (25-31)")
            else:
                print(f"❌ API returned error: {data.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text[:500])
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_rebalance_dates_via_api()
