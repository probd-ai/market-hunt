#!/usr/bin/env python3
"""
Quick Performance Test - Simple validation of optimization improvements
"""

import asyncio
import time
import json
from datetime import datetime
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_endpoints():
    """Test both original and optimized simulation endpoints"""
    
    base_url = "http://localhost:3001"
    
    # Test parameters for original endpoint
    original_request = {
        "strategy_id": "strategy_1756565385890",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",  # 6 months for quick test
        "portfolio_base_value": 1000000,
        "universe": "NIFTY100",
        "max_holdings": 10,  # Reduced for faster test
        "rebalance_frequency": "monthly",
        "rebalance_date": "first",
        "rebalance_type": "equal_weight",
        "momentum_ranking": "20_day_return",
        "include_brokerage": False,
        "exchange": "NSE"
    }
    
    # Test parameters for optimized endpoint  
    optimized_request = {
        "strategy": {
            "name": "momentum_strategy",
            "description": "TrueValueX momentum-based selection"
        },
        "params": {
            "universe": "NIFTY100",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",  # 6 months for quick test
            "initial_capital": 1000000,
            "max_stocks": 10,  # Reduced for faster test
            "rebalance_frequency": "monthly",
            "rebalance_type": "equal",
            "momentum_method": "20_day_return",
            "include_brokerage": False,
            "exchange": "NSE"
        }
    }
    
    logger.info("🚀 Testing API Endpoints Performance")
    logger.info("=" * 60)
    
    # Test Original Endpoint
    logger.info("🔥 Testing Original Simulation Endpoint")
    original_start = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/api/simulation/run",
            json=original_request,
            timeout=300  # 5 minute timeout
        )
        
        original_time = time.time() - original_start
        
        if response.status_code == 200:
            original_result = response.json()
            logger.info(f"✅ Original endpoint completed in {original_time:.2f} seconds")
            logger.info(f"📈 Final value: ₹{original_result.get('final_portfolio_value', 0):,.2f}")
        else:
            logger.error(f"❌ Original endpoint failed: {response.status_code}")
            original_time = None
            original_result = None
            
    except Exception as e:
        logger.error(f"❌ Original endpoint error: {e}")
        original_time = None
        original_result = None
    
    logger.info("=" * 60)
    
    # Test Optimized Endpoint  
    logger.info("🚀 Testing Optimized Simulation Endpoint")
    optimized_start = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/api/simulation/run-optimized",
            json=optimized_request,
            timeout=300  # 5 minute timeout
        )
        
        optimized_time = time.time() - optimized_start
        
        if response.status_code == 200:
            optimized_result = response.json()
            logger.info(f"✅ Optimized endpoint completed in {optimized_time:.2f} seconds")
            logger.info(f"📈 Final value: ₹{optimized_result.get('final_portfolio_value', 0):,.2f}")
        else:
            logger.error(f"❌ Optimized endpoint failed: {response.status_code}")
            optimized_time = None
            optimized_result = None
            
    except Exception as e:
        logger.error(f"❌ Optimized endpoint error: {e}")
        optimized_time = None
        optimized_result = None
    
    logger.info("=" * 60)
    
    # Performance Comparison
    if original_time and optimized_time:
        speed_improvement = original_time / optimized_time
        time_saved = original_time - optimized_time
        
        logger.info("📊 PERFORMANCE COMPARISON")
        logger.info(f"🔥 Original: {original_time:.2f} seconds")
        logger.info(f"🚀 Optimized: {optimized_time:.2f} seconds")
        logger.info(f"⚡ Speed Improvement: {speed_improvement:.2f}x faster")
        logger.info(f"⏰ Time Saved: {time_saved:.2f} seconds")
        
        if speed_improvement >= 5.0:
            logger.info("🎉 EXCELLENT: 5x+ performance improvement achieved!")
        elif speed_improvement >= 3.0:
            logger.info("✅ GREAT: 3x+ performance improvement achieved!")
        elif speed_improvement >= 2.0:
            logger.info("👍 GOOD: 2x+ performance improvement achieved!")
        else:
            logger.info("⚠️ MODERATE: Some improvement but below target")
    
    # Accuracy Validation
    if original_result and optimized_result:
        logger.info("=" * 60)
        logger.info("🔍 ACCURACY VALIDATION")
        
        original_final = original_result.get('final_portfolio_value', 0)
        optimized_final = optimized_result.get('final_portfolio_value', 0)
        
        if original_final > 0:
            difference_percent = abs(original_final - optimized_final) / original_final * 100
            
            if difference_percent < 1.0:
                logger.info("✅ VALIDATION PASSED: Results match within 1%")
            elif difference_percent < 5.0:
                logger.info("⚠️ VALIDATION WARNING: Results differ by <5%")
            else:
                logger.info("❌ VALIDATION FAILED: Results differ significantly")
            
            logger.info(f"   Original: ₹{original_final:,.2f}")
            logger.info(f"   Optimized: ₹{optimized_final:,.2f}")
            logger.info(f"   Difference: {difference_percent:.3f}%")
    
    logger.info("=" * 60)
    logger.info("🏁 Performance Test Completed")

def check_server_status():
    """Check if the API server is running"""
    try:
        response = requests.get("http://localhost:3001/api/simulation/charge-rates", timeout=5)
        if response.status_code == 200:
            logger.info("✅ API server is running")
            return True
        else:
            logger.error("❌ API server returned error")
            return False
    except Exception as e:
        logger.error(f"❌ Cannot connect to API server: {e}")
        logger.error("💡 Make sure to start the server with: python api_server.py")
        return False

if __name__ == "__main__":
    logger.info("🚀 Market Hunt Performance Test")
    logger.info("Testing optimization improvements for strategy simulation")
    
    # Check server status first
    if check_server_status():
        test_api_endpoints()
    else:
        logger.error("❌ Server not available. Please start the API server first.")
        print("\n💡 To start the server:")
        print("   cd /media/guru/Data/workspace/market-hunt")
        print("   python api_server.py")
