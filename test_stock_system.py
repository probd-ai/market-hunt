#!/usr/bin/env python3
"""
Test Stock Data Management System

This script tests the NSE client and stock data manager functionality
to ensure the stock data management system works correctly.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nse_data_client import NSEDataClient
from stock_data_manager import StockDataManager


async def test_nse_client():
    """Test NSE client functionality"""
    print("🧪 Testing NSE Data Client")
    print("=" * 50)
    
    try:
        async with NSEDataClient() as client:
            # Test 1: Fetch equity masters
            print("📊 Test 1: Fetching equity masters...")
            masters = await client.fetch_equity_masters()
            print(f"✅ Fetched {len(masters)} equity master records")
            
            if masters:
                # Show sample records
                print("📋 Sample master records:")
                for i, master in enumerate(masters[:5]):
                    print(f"   {i+1}. {master}")
                
                # Test 2: Historical data for NIFTY 50
                print(f"\n📈 Test 2: Fetching historical data for NIFTY 50...")
                nifty_master = None
                for master in masters:
                    if master.get('scrip_code') == 26000 or 'NIFTY' in str(master.get('name', '')).upper():
                        nifty_master = master
                        break
                
                if nifty_master:
                    historical = await client.fetch_historical_data(
                        scrip_code=nifty_master['scrip_code'],
                        symbol=nifty_master['symbol'],
                        start_date=datetime.now() - timedelta(days=10),  # Last 10 days
                        end_date=datetime.now()
                    )
                    print(f"✅ Fetched {len(historical)} historical records for {nifty_master['symbol']}")
                    
                    if historical:
                        print("📋 Sample historical records:")
                        for i, record in enumerate(historical[:3]):
                            print(f"   {i+1}. Date: {record.date}, Close: {record.close_price}")
                else:
                    print("⚠️ NIFTY 50 master record not found")
            
            return True
            
    except Exception as e:
        print(f"❌ NSE Client test failed: {e}")
        return False


async def test_stock_data_manager():
    """Test stock data manager functionality"""
    print("\n🧪 Testing Stock Data Manager")
    print("=" * 50)
    
    try:
        async with StockDataManager() as manager:
            # Test 1: Get current statistics
            print("📊 Test 1: Getting data statistics...")
            stats = await manager.get_data_statistics()
            print(f"✅ Current statistics: {stats['total_records']} records, {stats['unique_symbols_count']} symbols")
            
            # Test 2: Refresh symbol mappings
            print(f"\n🔄 Test 2: Refreshing symbol mappings...")
            mapping_result = await manager.refresh_symbol_mappings_from_index_meta()
            print(f"✅ Symbol mapping result: {mapping_result}")
            
            # Test 3: Get mappings
            print(f"\n📋 Test 3: Getting symbol mappings...")
            mappings = await manager.get_symbol_mappings(mapped_only=True)
            print(f"✅ Found {len(mappings)} mapped symbols")
            
            if mappings:
                # Show sample mappings
                print("📋 Sample mappings:")
                for i, mapping in enumerate(mappings[:5]):
                    print(f"   {i+1}. {mapping.symbol} -> {mapping.nse_scrip_code} (confidence: {mapping.match_confidence})")
                
                # Test 4: Download data for a single symbol (if available)
                test_symbol = mappings[0].symbol
                print(f"\n📈 Test 4: Testing download for symbol: {test_symbol}")
                
                download_result = await manager.download_historical_data_for_symbol(
                    symbol=test_symbol,
                    start_date=datetime.now() - timedelta(days=7),  # Last 7 days
                    end_date=datetime.now()
                )
                print(f"✅ Download result for {test_symbol}: {download_result}")
                
                # Test 5: Retrieve stored data
                if download_result.get('records_fetched', 0) > 0:
                    print(f"\n📋 Test 5: Retrieving stored data for {test_symbol}...")
                    price_data = await manager.get_price_data(
                        symbol=test_symbol,
                        limit=5
                    )
                    print(f"✅ Retrieved {len(price_data)} price records")
                    
                    if price_data:
                        print("📋 Sample price records:")
                        for i, record in enumerate(price_data[:3]):
                            print(f"   {i+1}. {record.date.date()}: O={record.open_price}, H={record.high_price}, L={record.low_price}, C={record.close_price}")
            
            # Test 6: Updated statistics
            print(f"\n📊 Test 6: Getting updated statistics...")
            updated_stats = await manager.get_data_statistics()
            print(f"✅ Updated statistics: {updated_stats['total_records']} records, {updated_stats['unique_symbols_count']} symbols")
            
            return True
            
    except Exception as e:
        print(f"❌ Stock Data Manager test failed: {e}")
        return False


async def test_api_endpoints():
    """Test API endpoints (requires running server)"""
    print("\n🧪 Testing API Endpoints")
    print("=" * 50)
    
    try:
        import aiohttp
        
        base_url = "http://localhost:3001/api"
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Health check
            print("🏥 Test 1: Health check...")
            async with session.get(f"{base_url}/../health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ Health check: {health_data['status']}")
                else:
                    print(f"⚠️ Health check failed: {response.status}")
            
            # Test 2: Get symbol mappings
            print(f"\n📋 Test 2: Get symbol mappings...")
            async with session.get(f"{base_url}/stock/mappings?mapped_only=true") as response:
                if response.status == 200:
                    mappings_data = await response.json()
                    print(f"✅ Mappings: {mappings_data['total_mappings']} total, {mappings_data['mapped_count']} mapped")
                else:
                    print(f"⚠️ Mappings failed: {response.status}")
            
            # Test 3: Get stock statistics
            print(f"\n📊 Test 3: Get stock statistics...")
            async with session.get(f"{base_url}/stock/statistics") as response:
                if response.status == 200:
                    stats_data = await response.json()
                    print(f"✅ Statistics: {stats_data.get('total_records', 0)} records")
                else:
                    print(f"⚠️ Statistics failed: {response.status}")
            
            return True
            
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        print("   Note: Make sure the API server is running on port 3001")
        return False


async def main():
    """Main test function"""
    print("🚀 Stock Data Management System Test Suite")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: NSE Client
    nse_result = await test_nse_client()
    test_results.append(("NSE Client", nse_result))
    
    # Test 2: Stock Data Manager
    manager_result = await test_stock_data_manager()
    test_results.append(("Stock Data Manager", manager_result))
    
    # Test 3: API Endpoints (optional)
    api_result = await test_api_endpoints()
    test_results.append(("API Endpoints", api_result))
    
    # Summary
    print("\n\n📊 TEST SUMMARY")
    print("=" * 40)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Stock data management system is ready!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please check the logs above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
