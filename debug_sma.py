#!/usr/bin/env python3

import requests
import json

# Test SMA calculation to understand the issue
def test_sma_calculation():
    print("Testing SMA calculation...")
    
    # Test with a known dataset
    url = "http://localhost:3001/api/stock/indicators"
    payload = {
        "symbol": "RELIANCE",
        "indicator_type": "sma",
        "period": 200,
        "start_date": "2005-01-01",
        "end_date": "2025-08-19"
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Total SMA data points returned: {len(data.get('data', []))}")
    
    # Check first few data points
    sma_data = data.get('data', [])
    if sma_data:
        print(f"\nFirst SMA point:")
        print(f"Date: {sma_data[0]['date']}")
        print(f"Value: {sma_data[0]['value']}")
        print(f"Period: {sma_data[0]['period']}")
        
        print(f"\nLast SMA point:")
        print(f"Date: {sma_data[-1]['date']}")
        print(f"Value: {sma_data[-1]['value']}")
    
    # Also check the raw price data count
    price_url = "http://localhost:3001/api/stock/data/RELIANCE"
    price_params = {
        "start_date": "2005-01-01",
        "end_date": "2025-08-19",
        "limit": 50000
    }
    
    price_response = requests.get(price_url, params=price_params)
    price_data = price_response.json()
    
    print(f"\nRaw price data points: {len(price_data)}")
    print(f"Expected SMA points: {len(price_data) - 200 + 1} = {len(price_data) - 199}")
    print(f"Actual SMA points: {len(sma_data)}")
    
    if len(sma_data) == len(price_data):
        print("\n❌ ERROR: SMA data has same length as price data!")
        print("This means the SMA calculation is not properly skipping the first 199 points.")
    else:
        print(f"\n✅ SMA data length is different from price data ({len(sma_data)} vs {len(price_data)})")

if __name__ == "__main__":
    test_sma_calculation()
