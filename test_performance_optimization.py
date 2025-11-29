#!/usr/bin/env python3
"""
Performance Test Script for Optimized Strategy Simulation

This script compares the performance of the original simulation engine
with the optimized version to validate the 10x speed improvement.
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, Any
import motor.motor_asyncio

# Import existing modules
from api_server import run_strategy_simulation as original_simulation
from performance_optimizations import run_optimized_strategy_simulation
from stock_data_manager import StockDataManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceTestParams:
    """Test parameters class matching the original API structure"""
    def __init__(self):
        self.universe = "NIFTY100"
        self.start_date = datetime(2023, 1, 1)
        self.end_date = datetime(2024, 12, 31)
        self.initial_capital = 1000000
        self.max_stocks = 20
        self.rebalance_frequency = "monthly"
        self.rebalance_type = "equal"
        self.momentum_method = "20_day_return"
        self.include_brokerage = True
        self.exchange = "NSE"
        self.custom_brokerage_rate = None

async def run_performance_comparison():
    """
    Run both simulation engines and compare performance
    """
    logger.info("🚀 Starting Performance Comparison Test")
    logger.info("=" * 80)
    
    # Initialize database connection
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
    db = client.market_hunt
    
    # Initialize stock data manager
    async with StockDataManager() as stock_manager:
        
        # Create test parameters
        params = PerformanceTestParams()
        
        logger.info(f"📊 Test Parameters:")
        logger.info(f"   Universe: {params.universe}")
        logger.info(f"   Period: {params.start_date.date()} to {params.end_date.date()}")
        logger.info(f"   Capital: ₹{params.initial_capital:,}")
        logger.info(f"   Max Stocks: {params.max_stocks}")
        logger.info(f"   Rebalancing: {params.rebalance_frequency}")
        logger.info("=" * 80)
        
        # Test 1: Original Simulation Engine
        logger.info("🔥 Testing Original Simulation Engine")
        original_start_time = time.time()
        
        try:
            original_results = await original_simulation(params)
            original_execution_time = time.time() - original_start_time
            
            logger.info(f"✅ Original simulation completed")
            logger.info(f"⏱️  Execution time: {original_execution_time:.2f} seconds")
            logger.info(f"📈 Final portfolio value: ₹{original_results.get('final_portfolio_value', 0):,.2f}")
            
        except Exception as e:
            logger.error(f"❌ Original simulation failed: {e}")
            original_execution_time = None
            original_results = None
        
        logger.info("=" * 80)
        
        # Test 2: Optimized Simulation Engine
        logger.info("🚀 Testing Optimized Simulation Engine")
        optimized_start_time = time.time()
        
        try:
            optimized_results = await run_optimized_strategy_simulation(params, db, stock_manager)
            optimized_execution_time = time.time() - optimized_start_time
            
            logger.info(f"✅ Optimized simulation completed")
            logger.info(f"⏱️  Execution time: {optimized_execution_time:.2f} seconds")
            logger.info(f"📈 Final portfolio value: ₹{optimized_results.get('final_portfolio_value', 0):,.2f}")
            
        except Exception as e:
            logger.error(f"❌ Optimized simulation failed: {e}")
            optimized_execution_time = None
            optimized_results = None
        
        logger.info("=" * 80)
        
        # Performance Analysis
        if original_execution_time and optimized_execution_time:
            speed_improvement = original_execution_time / optimized_execution_time
            time_saved = original_execution_time - optimized_execution_time
            
            logger.info("📊 PERFORMANCE ANALYSIS RESULTS")
            logger.info(f"🔥 Original Engine: {original_execution_time:.2f} seconds")
            logger.info(f"🚀 Optimized Engine: {optimized_execution_time:.2f} seconds")
            logger.info(f"⚡ Speed Improvement: {speed_improvement:.2f}x faster")
            logger.info(f"⏰ Time Saved: {time_saved:.2f} seconds ({time_saved/60:.2f} minutes)")
            
            if speed_improvement >= 5.0:
                logger.info("🎉 SUCCESS: Achieved 5x+ performance improvement!")
            elif speed_improvement >= 3.0:
                logger.info("✅ GOOD: Achieved 3x+ performance improvement")
            elif speed_improvement >= 2.0:
                logger.info("⚠️  MODERATE: Achieved 2x+ performance improvement")
            else:
                logger.info("❌ INSUFFICIENT: Performance improvement below expectations")
        
        # Results Validation
        if original_results and optimized_results:
            logger.info("=" * 80)
            logger.info("🔍 RESULTS VALIDATION")
            
            original_final = original_results.get('final_portfolio_value', 0)
            optimized_final = optimized_results.get('final_portfolio_value', 0)
            
            if abs(original_final - optimized_final) / original_final < 0.01:  # 1% tolerance
                logger.info("✅ VALIDATION PASSED: Portfolio values match within 1%")
                logger.info(f"   Original: ₹{original_final:,.2f}")
                logger.info(f"   Optimized: ₹{optimized_final:,.2f}")
                logger.info(f"   Difference: {abs(original_final - optimized_final)/original_final*100:.3f}%")
            else:
                logger.warning("⚠️  VALIDATION WARNING: Portfolio values differ significantly")
                logger.warning(f"   Original: ₹{original_final:,.2f}")
                logger.warning(f"   Optimized: ₹{optimized_final:,.2f}")
                logger.warning(f"   Difference: {abs(original_final - optimized_final)/original_final*100:.3f}%")
        
        logger.info("=" * 80)
        logger.info("🏁 Performance Comparison Test Completed")
    
    # Close database connection
    client.close()

async def run_memory_usage_test():
    """
    Test memory usage optimization
    """
    logger.info("🧠 Starting Memory Usage Test")
    
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        logger.info(f"📊 Baseline memory usage: {baseline_memory:.2f} MB")
        
        # Initialize database and run optimized simulation
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
        db = client.market_hunt
        
        async with StockDataManager() as stock_manager:
            from performance_optimizations import OptimizedSimulationEngine
            
            params = PerformanceTestParams()
            optimizer = OptimizedSimulationEngine(db, stock_manager)
            
            # Memory during data loading
            universe_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]  # Sample
            
            memory_before_preload = process.memory_info().rss / 1024 / 1024
            logger.info(f"📊 Memory before data preload: {memory_before_preload:.2f} MB")
            
            optimized_data = await optimizer.preload_simulation_data(
                universe_symbols=universe_symbols,
                start_date=params.start_date,
                end_date=params.end_date
            )
            
            memory_after_preload = process.memory_info().rss / 1024 / 1024
            logger.info(f"📊 Memory after data preload: {memory_after_preload:.2f} MB")
            logger.info(f"📊 Memory increase for data: {memory_after_preload - memory_before_preload:.2f} MB")
            
            # Memory efficiency metrics
            data_stats = optimized_data.get("data_statistics", {})
            logger.info(f"📊 Data loaded: {data_stats.get('total_symbols', 0)} symbols")
            logger.info(f"📊 Trading days: {data_stats.get('total_trading_days', 0)} days")
            
            memory_per_symbol = (memory_after_preload - memory_before_preload) / len(universe_symbols)
            logger.info(f"📊 Memory per symbol: {memory_per_symbol:.2f} MB")
        
        client.close()
        
    except ImportError:
        logger.warning("⚠️  psutil not available, skipping memory test")
    except Exception as e:
        logger.error(f"❌ Memory test failed: {e}")

async def run_data_loading_benchmark():
    """
    Benchmark the data loading performance specifically
    """
    logger.info("🔄 Starting Data Loading Benchmark")
    
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
    db = client.market_hunt
    
    async with StockDataManager() as stock_manager:
        from performance_optimizations import OptimizedSimulationEngine
        
        # Test with different symbol counts
        test_cases = [
            {"symbols": 10, "name": "Small (10 symbols)"},
            {"symbols": 50, "name": "Medium (50 symbols)"},
            {"symbols": 100, "name": "Large (100 symbols)"}
        ]
        
        optimizer = OptimizedSimulationEngine(db, stock_manager)
        
        # Get sample symbols from database
        collection = db.truevx_momentum_20d
        all_symbols = await collection.distinct("symbol")
        
        for test_case in test_cases:
            symbol_count = min(test_case["symbols"], len(all_symbols))
            test_symbols = all_symbols[:symbol_count]
            
            logger.info(f"🔄 Testing {test_case['name']} - {symbol_count} symbols")
            
            start_time = time.time()
            
            optimized_data = await optimizer.preload_simulation_data(
                universe_symbols=test_symbols,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 3, 31),  # 3 months for benchmark
                required_indicators=["momentum_20d"]
            )
            
            load_time = time.time() - start_time
            
            stats = optimized_data.get("data_statistics", {})
            logger.info(f"   ✅ Loaded in {load_time:.2f} seconds")
            logger.info(f"   📊 Trading days: {stats.get('total_trading_days', 0)}")
            logger.info(f"   ⚡ Load rate: {symbol_count / load_time:.1f} symbols/second")
    
    client.close()

if __name__ == "__main__":
    async def main():
        """Run all performance tests"""
        logger.info("🚀 Starting Comprehensive Performance Testing Suite")
        logger.info("=" * 100)
        
        # Test 1: Performance Comparison
        await run_performance_comparison()
        
        print("\n" + "=" * 100 + "\n")
        
        # Test 2: Memory Usage
        await run_memory_usage_test()
        
        print("\n" + "=" * 100 + "\n")
        
        # Test 3: Data Loading Benchmark
        await run_data_loading_benchmark()
        
        logger.info("🏁 All Performance Tests Completed")
    
    # Run the test suite
    asyncio.run(main())
