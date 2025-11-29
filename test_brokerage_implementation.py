#!/usr/bin/env python3
"""
Test script for brokerage charges implementation
Tests the new charge estimation API endpoints and functionality
"""

import requests
import json
from datetime import datetime, timedelta

# API base URL
BASE_URL = "http://localhost:3001"

def test_charge_rates_endpoint():
    """Test the charge rates information endpoint"""
    print("🧪 Testing charge rates endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/simulation/charge-rates")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Charge rates endpoint working")
            print(f"📊 STT Rate: {data['charge_rates']['stt_rate']*100}%")
            print(f"📊 NSE Transaction Charges: {data['charge_rates']['nse_transaction_rate']*100}%")
            print(f"📊 Example Buy ₹1L on NSE: ₹{data['examples']['buy_1_lakh_nse']['total_charges']:.2f}")
            print(f"📊 Example Sell ₹1L on NSE: ₹{data['examples']['sell_1_lakh_nse']['total_charges']:.2f}")
            return True
        else:
            print(f"❌ Charge rates endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing charge rates: {e}")
        return False

def test_charge_estimation_endpoint():
    """Test the charge estimation endpoint"""
    print("\n🧪 Testing charge estimation endpoint...")
    
    # Sample simulation parameters
    params = {
        "strategy_id": "test_strategy",
        "portfolio_base_value": 1000000,  # ₹10 lakhs
        "rebalance_frequency": "monthly",
        "rebalance_date": "first",
        "universe": "NIFTY50",
        "max_holdings": 15,
        "momentum_ranking": "20_day_return",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "include_brokerage": True,
        "exchange": "NSE",
        "custom_brokerage_rate": 0.0,
        "portfolio_turnover_estimate": 0.5
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/simulation/estimate-charges",
            json=params,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Charge estimation endpoint working")
            print(f"📊 Portfolio: ₹{data['simulation_params']['portfolio_value']:,}")
            print(f"📊 Simulation Period: {data['simulation_params']['simulation_days']} days")
            print(f"📊 Estimated Total Charges: ₹{data['charge_estimate']['total_estimated_charges']:,.2f}")
            print(f"📊 Charge Impact: {data['charge_estimate']['estimated_charge_percentage']:.3f}% of portfolio")
            print(f"📊 Annual Charge Rate: {data['charge_estimate']['annual_charge_percentage']:.3f}%")
            
            # Breakdown
            breakdown = data['charge_estimate']['breakdown']
            print("💰 Charge Breakdown:")
            print(f"  - STT: ₹{breakdown['stt']:,.2f}")
            print(f"  - Transaction Charges: ₹{breakdown['transaction_charges']:,.2f}")
            print(f"  - SEBI Charges: ₹{breakdown['sebi_charges']:,.2f}")
            print(f"  - Stamp Duty: ₹{breakdown['stamp_duty']:,.2f}")
            print(f"  - GST: ₹{breakdown['gst']:,.2f}")
            
            return True
        else:
            print(f"❌ Charge estimation endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing charge estimation: {e}")
        return False

def test_brokerage_calculator_directly():
    """Test the brokerage calculator directly"""
    print("\n🧪 Testing brokerage calculator directly...")
    
    try:
        from brokerage_calculator import BrokerageCalculator, calculate_single_trade_charges, estimate_portfolio_charges
        
        # Test single trade
        charges = calculate_single_trade_charges(100000, "BUY", "NSE")
        print(f"✅ Single trade test: Buy ₹1L = ₹{charges['total_charges']:.2f} charges")
        
        # Test portfolio estimation
        impact = estimate_portfolio_charges(1000000, "monthly", 0.5)
        print(f"✅ Portfolio estimation: {impact['impact_metrics']['annual_charge_percentage']:.2f}% annual impact")
        
        # Test different scenarios
        scenarios = [
            {"portfolio": 500000, "frequency": "monthly", "churn": 0.3, "name": "Conservative ₹5L"},
            {"portfolio": 1000000, "frequency": "weekly", "churn": 0.5, "name": "Active ₹10L"},
            {"portfolio": 2000000, "frequency": "monthly", "churn": 0.7, "name": "Aggressive ₹20L"}
        ]
        
        print("\n📊 Charge Impact Scenarios:")
        for scenario in scenarios:
            impact = estimate_portfolio_charges(
                scenario["portfolio"], 
                scenario["frequency"], 
                scenario["churn"]
            )
            print(f"  {scenario['name']}: {impact['impact_metrics']['annual_charge_percentage']:.2f}% annually")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing calculator directly: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting brokerage charges implementation tests...")
    print("=" * 60)
    
    results = []
    
    # Test direct calculator
    results.append(test_brokerage_calculator_directly())
    
    # Test API endpoints (only if server is running)
    print("\n🌐 Testing API endpoints (requires running server)...")
    results.append(test_charge_rates_endpoint())
    results.append(test_charge_estimation_endpoint())
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("🎉 All tests passed! Brokerage implementation is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
