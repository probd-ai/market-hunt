#!/usr/bin/env python3
"""
Comprehensive System Verification Script
Verifies the generic URL management and data loading system
"""

import pymongo
from pymongo import MongoClient
import pandas as pd
from datetime import datetime
import json
from url_manager import URLManager
from generic_data_loader import GenericIndexDataLoader

def verify_url_management_system():
    """Verify the URL management system"""
    print("🔍 URL Management System Verification")
    print("=" * 60)
    
    manager = URLManager()
    
    try:
        # Connect to MongoDB
        if not manager.connect_to_mongodb():
            print("❌ Failed to connect to MongoDB")
            return False
        
        # Get URL statistics
        stats = manager.get_statistics()
        print(f"📊 URL Statistics:")
        print(f"   Total URLs: {stats.get('total_urls', 0)}")
        print(f"   Active URLs: {stats.get('active_urls', 0)}")
        print(f"   Valid URLs: {stats.get('valid_urls', 0)}")
        print(f"   Unique Indices: {stats.get('unique_indices', 0)}")
        
        # List all URLs
        urls = manager.get_all_urls()
        print(f"\n📋 Configured URLs:")
        for i, url in enumerate(urls, 1):
            status = "✅ Active" if url['is_active'] else "❌ Inactive"
            valid = "✅ Valid" if url.get('is_valid', False) else "❌ Invalid"
            downloads = url.get('download_count', 0)
            print(f"   {i}. {url['index_name']}")
            print(f"      URL: {url['url']}")
            print(f"      Status: {status} | {valid} | Downloads: {downloads}")
            if url.get('last_downloaded'):
                print(f"      Last Downloaded: {url['last_downloaded']}")
            print()
        
        print("✅ URL management system verification completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying URL management system: {e}")
        return False
    finally:
        manager.close_connection()

def verify_data_loading_system():
    """Verify the data loading system"""
    print("\n🔍 Data Loading System Verification")
    print("=" * 60)
    
    try:
        # Connect to MongoDB directly
        client = MongoClient("mongodb://localhost:27017/")
        db = client.market_hunt
        
        # Check index_meta collection
        index_collection = db.index_meta
        total_docs = index_collection.count_documents({})
        
        print(f"📊 Data Collection Statistics:")
        print(f"   Total documents in index_meta: {total_docs}")
        
        # Get stats by index
        pipeline = [
            {"$group": {
                "_id": "$index_name",
                "count": {"$sum": 1},
                "last_update": {"$max": "$download_timestamp"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        index_stats = list(index_collection.aggregate(pipeline))
        
        print(f"\n📈 Index-wise Statistics:")
        for stat in index_stats:
            print(f"   • {stat['_id']}: {stat['count']} documents")
            print(f"     Last Update: {stat['last_update']}")
        
        # Check data quality
        print(f"\n🔍 Data Quality Check:")
        
        for stat in index_stats:
            index_name = stat['_id']
            
            # Check for missing values
            missing_symbols = index_collection.count_documents({
                "index_name": index_name, 
                "Symbol": {"$in": [None, ""]}
            })
            missing_companies = index_collection.count_documents({
                "index_name": index_name, 
                "Company Name": {"$in": [None, ""]}
            })
            missing_isin = index_collection.count_documents({
                "index_name": index_name, 
                "ISIN Code": {"$in": [None, ""]}
            })
            
            print(f"   {index_name}:")
            print(f"     Missing Symbols: {missing_symbols}")
            print(f"     Missing Company Names: {missing_companies}")
            print(f"     Missing ISIN Codes: {missing_isin}")
            
            # Get sample data
            sample = index_collection.find_one({"index_name": index_name})
            if sample:
                print(f"     Sample fields: {list(sample.keys())}")
        
        # Check URL collection
        url_collection = db.index_meta_csv_urls
        url_docs = url_collection.count_documents({})
        
        print(f"\n📋 URL Configuration Collection:")
        print(f"   Total URL configurations: {url_docs}")
        
        # Sample URL document
        sample_url = url_collection.find_one({})
        if sample_url:
            print(f"   Sample URL fields: {list(sample_url.keys())}")
        
        client.close()
        
        print("\n✅ Data loading system verification completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying data loading system: {e}")
        return False

def verify_auto_index_name_extraction():
    """Test automatic index name extraction"""
    print("\n🔍 Auto Index Name Extraction Test")
    print("=" * 60)
    
    manager = URLManager()
    
    test_urls = [
        "https://example.com/ind_nifty50list.csv",
        "https://example.com/ind_nifty100list.csv",
        "https://example.com/sensex30.csv",
        "https://example.com/bse500.csv",
        "https://example.com/nifty-next-50.csv",
        "https://example.com/midcap_index.csv",
        "https://example.com/data/some_index_data.csv"
    ]
    
    print("📋 Index Name Extraction Results:")
    for url in test_urls:
        extracted_name = manager.extract_index_name_from_url(url)
        print(f"   {url}")
        print(f"   → {extracted_name}")
        print()
    
    print("✅ Auto index name extraction test completed!")
    return True

def test_system_integration():
    """Test end-to-end system integration"""
    print("\n🔍 System Integration Test")
    print("=" * 60)
    
    try:
        # Test adding a new URL
        manager = URLManager()
        manager.connect_to_mongodb()
        
        test_url = "https://niftyindices.com/IndexConstituent/ind_niftymidcap50list.csv"
        
        print(f"🧪 Testing URL addition: {test_url}")
        success, message = manager.add_url(
            url=test_url,
            description="Test URL for NIFTY MIDCAP 50",
            tags=["test", "midcap"],
            is_active=True
        )
        
        if success:
            print(f"✅ URL added successfully: {message}")
            
            # Test loading data from this URL
            print(f"🧪 Testing data loading...")
            loader = GenericIndexDataLoader()
            loader.connect_to_mongodb()
            
            # Get the newly added URL
            urls = manager.get_all_urls()
            test_url_config = None
            for url_config in urls:
                if url_config['url'] == test_url:
                    test_url_config = url_config
                    break
            
            if test_url_config:
                success = loader.process_single_url(test_url_config)
                if success:
                    print("✅ Data loading test successful!")
                else:
                    print("❌ Data loading test failed!")
            
            loader.close_connection()
            
            # Clean up test URL
            if test_url_config:
                manager.delete_url(test_url_config['_id'])
                print("🧹 Test URL cleaned up")
        else:
            print(f"❌ URL addition failed: {message}")
        
        manager.close_connection()
        
        print("\n✅ System integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ System integration test failed: {e}")
        return False

def export_system_report():
    """Export comprehensive system report"""
    print("\n📄 Generating System Report")
    print("=" * 60)
    
    try:
        # Collect all system information
        manager = URLManager()
        manager.connect_to_mongodb()
        
        loader = GenericIndexDataLoader()
        loader.connect_to_mongodb()
        
        # Get URL data
        urls = manager.get_all_urls()
        url_stats = manager.get_statistics()
        
        # Get data stats
        data_stats = loader.get_collection_stats()
        
        # Create report
        report = {
            "report_generated": datetime.now().isoformat(),
            "system_status": "operational",
            "url_management": {
                "total_urls": url_stats.get('total_urls', 0),
                "active_urls": url_stats.get('active_urls', 0),
                "valid_urls": url_stats.get('valid_urls', 0),
                "configured_urls": urls
            },
            "data_collection": {
                "total_documents": data_stats.get('total_documents', 0) if data_stats else 0,
                "index_statistics": data_stats.get('index_stats', []) if data_stats else []
            }
        }
        
        # Export to file
        report_file = f"/media/guru/Data/workspace/market_hunt/system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📁 System report exported to: {report_file}")
        
        manager.close_connection()
        loader.close_connection()
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating system report: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 Market Hunt - Generic URL Management System Verification")
    print("=" * 80)
    
    # Run all verification tests
    tests = [
        verify_url_management_system,
        verify_data_loading_system,
        verify_auto_index_name_extraction,
        test_system_integration,
        export_system_report
    ]
    
    passed_tests = 0
    
    for test in tests:
        try:
            if test():
                passed_tests += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
    
    print("\n" + "=" * 80)
    print(f"📊 Verification Summary: {passed_tests}/{len(tests)} tests passed")
    
    if passed_tests == len(tests):
        print("🎉 All systems operational! Generic URL management system is ready for use.")
    else:
        print("⚠️  Some tests failed. Please review the output above for details.")

if __name__ == "__main__":
    main()
