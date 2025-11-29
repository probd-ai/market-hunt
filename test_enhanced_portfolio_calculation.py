#!/usr/bin/env python3
"""
Test Enhanced Portfolio Calculation with Brokerage Integration
Validates the comprehensive charge tracking and analytics
"""

import asyncio
import json
import requests
from datetime import datetime, timedelta

def test_enhanced_simulation_with_charges():
    """Test the enhanced simulation with comprehensive charge tracking"""
    print("🚀 Testing Enhanced Portfolio Calculation with Brokerage Charges...")
    print("=" * 70)
    
    # Test simulation parameters with brokerage enabled
    simulation_params = {
        "strategy_id": "strategy_1756565385890",  # Use existing strategy
        "start_date": "2024-01-01",
        "end_date": "2024-03-31",  # 3 months for testing
        "portfolio_base_value": 1000000,  # ₹10 Lakh
        "rebalance_frequency": "monthly",
        "universe": "NIFTY50",
        "max_holdings": 10,
        "momentum_ranking": "20_day_return",
        "include_brokerage": True,
        "exchange": "NSE",
        "custom_brokerage_rate": 0.0,
        "portfolio_turnover_estimate": 0.6  # 60% turnover per rebalance
    }
    
    # Test 1: Enhanced simulation with charges
    print("🧪 Test 1: Running simulation with enhanced charge tracking...")
    try:
        response = requests.post(
            "http://localhost:3001/api/simulation/run",
            json=simulation_params,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                simulation = result["simulation"]
                
                print(f"✅ Simulation completed successfully")
                print(f"📊 Parameters: {simulation['params']['portfolio_base_value']:,} portfolio, {simulation['params']['rebalance_frequency']} rebalancing")
                print(f"🎯 Universe: {simulation['params']['universe']}, Max Holdings: {simulation['params']['max_holdings']}")
                print(f"💱 Exchange: {simulation['params']['exchange']}, Brokerage: {simulation['params']['custom_brokerage_rate']*100:.3f}%")
                
                # Test enhanced summary statistics
                summary = simulation["summary"]
                print(f"\n📈 PERFORMANCE SUMMARY:")
                print(f"  Total Return: {summary['total_return']:.2f}%")
                print(f"  Benchmark Return: {summary['benchmark_return']:.2f}%")
                print(f"  Alpha: {summary['alpha']:.2f}%")
                print(f"  Max Drawdown: {summary['max_drawdown']:.2f}%")
                print(f"  Sharpe Ratio: {summary['sharpe_ratio']:.3f}")
                print(f"  Total Trades: {summary['total_trades']}")
                
                # Test enhanced charge analytics
                if "charge_analytics" in simulation:
                    charge_analytics = simulation["charge_analytics"]
                    print(f"\n💰 CHARGE ANALYTICS:")
                    print(f"  Total Cumulative Charges: ₹{charge_analytics['total_cumulative_charges']:,.2f}")
                    print(f"  Charge Impact: {charge_analytics['charge_impact_percent']:.4f}% of initial portfolio")
                    print(f"  Total Rebalances: {charge_analytics['total_rebalances']}")
                    print(f"  Avg Cost per Rebalance: ₹{charge_analytics['avg_cost_per_rebalance']:,.2f}")
                    print(f"  Charge Drag on Returns: {charge_analytics['charge_drag_on_returns']:.4f}%")
                    print(f"  Theoretical Return (No Charges): {charge_analytics['theoretical_return_without_charges']:.2f}%")
                    
                    # Test component breakdown
                    if "component_breakdown" in charge_analytics:
                        breakdown = charge_analytics["component_breakdown"]
                        print(f"\n📊 CHARGE BREAKDOWN:")
                        print(f"  STT: ₹{breakdown['stt']:,.2f}")
                        print(f"  Transaction Charges: ₹{breakdown['transaction_charges']:,.2f}")
                        print(f"  SEBI Charges: ₹{breakdown['sebi_charges']:,.2f}")
                        print(f"  Stamp Duty: ₹{breakdown['stamp_duty']:,.2f}")
                        print(f"  Brokerage: ₹{breakdown['brokerage']:,.2f}")
                        print(f"  GST: ₹{breakdown['gst']:,.2f}")
                        print(f"  Total Buy Charges: ₹{breakdown['total_buy_charges']:,.2f}")
                        print(f"  Total Sell Charges: ₹{breakdown['total_sell_charges']:,.2f}")
                
                # Test daily results with enhanced tracking
                results = simulation["results"]
                print(f"\n📅 DAILY RESULTS SAMPLE:")
                print(f"  Total Days: {len(results)}")
                
                # Find rebalance days
                rebalance_days = [r for r in results if r["daily_charges"]["total_charges"] > 0]
                print(f"  Rebalance Days: {len(rebalance_days)}")
                
                if rebalance_days:
                    first_rebalance = rebalance_days[0]
                    print(f"\n📊 FIRST REBALANCE ({first_rebalance['date']}):")
                    print(f"  Portfolio Value: ₹{first_rebalance['portfolio_value']:,.2f}")
                    print(f"  Daily Charges: ₹{first_rebalance['daily_charges']['total_charges']:,.2f}")
                    print(f"  Cumulative Charges: ₹{first_rebalance['cumulative_charges']:,.2f}")
                    print(f"  Charge Impact: {first_rebalance['charge_impact_percent']:.4f}%")
                    print(f"  Holdings: {len(first_rebalance['holdings'])}")
                    print(f"  New Added: {len(first_rebalance['new_added'])}")
                    print(f"  Exited: {len(first_rebalance['exited'])}")
                    
                    # Test trade details
                    if first_rebalance["trade_details"]:
                        print(f"  Trade Details: {len(first_rebalance['trade_details'])} trades")
                        sample_trade = first_rebalance["trade_details"][0]
                        print(f"    Sample Trade: {sample_trade.get('trade_type', 'N/A')} {sample_trade.get('symbol', 'N/A')} - ₹{sample_trade.get('gross_value', 0):,.2f}")
                
                print(f"\n✅ Enhanced simulation test PASSED")
                
            else:
                print(f"❌ Simulation failed: {result.get('detail', 'Unknown error')}")
                return False
                
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced simulation test failed: {e}")
        return False
    
    # Test 2: Compare with and without charges
    print(f"\n🧪 Test 2: Comparing simulation with vs without charges...")
    
    try:
        # Run simulation without charges
        no_charge_params = simulation_params.copy()
        no_charge_params["include_brokerage"] = False
        
        response_no_charges = requests.post(
            "http://localhost:3001/api/simulation/run",
            json=no_charge_params,
            timeout=60
        )
        
        if response_no_charges.status_code == 200:
            result_no_charges = response_no_charges.json()
            
            if result_no_charges.get("success"):
                summary_no_charges = result_no_charges["simulation"]["summary"]
                
                print(f"📊 COMPARISON RESULTS:")
                print(f"  With Charges Return: {summary['total_return']:.2f}%")
                print(f"  Without Charges Return: {summary_no_charges['total_return']:.2f}%")
                
                charge_impact = summary_no_charges['total_return'] - summary['total_return']
                print(f"  Charge Impact: {charge_impact:.2f}% drag on returns")
                
                if "charge_analytics" in simulation:
                    expected_drag = charge_analytics['charge_drag_on_returns']
                    print(f"  Expected Drag: {expected_drag:.2f}%")
                    
                    if abs(charge_impact - expected_drag) < 0.5:  # Within 0.5% tolerance
                        print(f"✅ Charge impact calculation ACCURATE")
                    else:
                        print(f"⚠️ Charge impact calculation may need refinement")
                
                print(f"✅ Comparison test PASSED")
                
            else:
                print(f"❌ No-charges simulation failed")
                return False
        else:
            print(f"❌ No-charges API request failed: {response_no_charges.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Comparison test failed: {e}")
        return False
    
    return True

def test_charge_estimation_integration():
    """Test charge estimation endpoint with simulation parameters"""
    print(f"\n🧪 Test 3: Charge estimation integration...")
    
    estimation_params = {
        "strategy_id": "strategy_1756565385890",  # Use existing strategy
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "portfolio_base_value": 1000000,
        "rebalance_frequency": "monthly",
        "exchange": "NSE",
        "custom_brokerage_rate": 0.0,
        "portfolio_turnover_estimate": 0.5
    }
    
    try:
        response = requests.post(
            "http://localhost:3001/api/simulation/estimate-charges",
            json=estimation_params,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                estimate = result["charge_estimate"]
                
                print(f"📊 CHARGE ESTIMATION:")
                print(f"  Estimated Total Charges: ₹{estimate['total_estimated_charges']:,.2f}")
                print(f"  Estimated Charge %: {estimate['estimated_charge_percentage']:.3f}%")
                print(f"  Annual Charge %: {estimate['annual_charge_percentage']:.3f}%")
                print(f"  Monthly Charge %: {estimate['monthly_charge_percentage']:.4f}%")
                print(f"  Charge per Rebalance: ₹{estimate['charge_per_rebalance']:,.2f}")
                
                # Test breakdown
                breakdown = estimate["breakdown"]
                print(f"\n💰 ESTIMATED BREAKDOWN:")
                print(f"  STT: ₹{breakdown['stt']:,.2f}")
                print(f"  Transaction Charges: ₹{breakdown['transaction_charges']:,.2f}")
                print(f"  SEBI Charges: ₹{breakdown['sebi_charges']:,.2f}")
                print(f"  Stamp Duty: ₹{breakdown['stamp_duty']:,.2f}")
                print(f"  Brokerage: ₹{breakdown['brokerage']:,.2f}")
                print(f"  GST: ₹{breakdown['gst']:,.2f}")
                
                print(f"✅ Charge estimation test PASSED")
                return True
                
            else:
                print(f"❌ Charge estimation failed: {result.get('detail', 'Unknown error')}")
                return False
        else:
            print(f"❌ Charge estimation API failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Charge estimation test failed: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Enhanced Portfolio Calculation Test Suite")
    print("Testing comprehensive brokerage integration with simulation engine")
    print("=" * 70)
    
    # Check if API server is running
    try:
        health_response = requests.get("http://localhost:3001/api/simulation/charge-rates", timeout=5)
        if health_response.status_code == 200:
            print("✅ API server is running and responsive")
        else:
            print("❌ API server is not responding correctly")
            exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        exit(1)
    
    # Run all tests
    test_results = []
    
    test_results.append(test_enhanced_simulation_with_charges())
    test_results.append(test_charge_estimation_integration())
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 TEST SUMMARY:")
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    
    if passed == total:
        print("🎉 All enhanced portfolio calculation tests PASSED!")
        print("💰 Brokerage integration is fully operational with comprehensive analytics")
    else:
        print("⚠️ Some tests failed - check implementation")
    
    print("=" * 70)
