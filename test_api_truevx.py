#!/usr/bin/env python3
"""
Test the actual API endpoint to see what's returned for TrueValueX calculation
"""

import requests
import json
from datetime import datetime

def test_api_truevx():
    """Test the TrueValueX API endpoint"""
    
    print("🔍 Testing TrueValueX API endpoint...")
    
    # Construct the API request (similar to what frontend sends)
    api_url = "http://localhost:3001/api/stock/indicators"
    
    payload = {
        "symbol": "TCS",
        "indicator_type": "truevx",
        "base_symbol": "Nifty 50",
        "period": 22,
        "price_field": "close_price",
        # Use full range - don't specify start/end dates
        "start_date": None,
        "end_date": None
    }
    
    print(f"📤 Sending request to: {api_url}")
    print(f"📋 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Success! Response summary:")
            print(f"  Symbol: {data.get('symbol')}")
            print(f"  Indicator: {data.get('indicator_type')}")
            print(f"  Total points: {data.get('total_points')}")
            print(f"  Price data points: {data.get('price_data_points')}")
            print(f"  Calculation time: {data.get('calculation_time_seconds')}s")
            
            indicator_data = data.get('data', [])
            if indicator_data:
                print(f"\n📊 Indicator Data:")
                print(f"  First result: {indicator_data[0]['date']}")
                print(f"  Last result: {indicator_data[-1]['date']}")
                
                # Check for August 26 specifically
                aug_26_results = [item for item in indicator_data if '2025-08-26' in item['date']]
                print(f"\n🎯 August 26 results: {len(aug_26_results)}")
                for item in aug_26_results:
                    print(f"  {item['date']}: truevx_score={item.get('truevx_score', 'N/A')}")
                
                # Show last 3 results
                print(f"\n📈 Last 3 results:")
                for item in indicator_data[-3:]:
                    score = item.get('truevx_score', 'N/A')
                    print(f"  {item['date']}: truevx_score={score}")
                    
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_api_truevx()
