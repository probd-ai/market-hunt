#!/usr/bin/env python3
"""
Script to manually clean up orphaned NIFTY 50 data
"""

import pymongo
from datetime import datetime

def cleanup_nifty50_data():
    """Remove orphaned NIFTY 50 data"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        db = client['market_hunt']
        
        # Check how many NIFTY 50 records exist
        collection = db.index_meta
        count_before = collection.count_documents({'index_name': 'NIFTY 50'})
        print(f"Found {count_before} NIFTY 50 records")
        
        if count_before > 0:
            # Delete all NIFTY 50 records
            result = collection.delete_many({'index_name': 'NIFTY 50'})
            print(f"Deleted {result.deleted_count} NIFTY 50 records")
        else:
            print("No NIFTY 50 records found")
            
        # Verify cleanup
        count_after = collection.count_documents({'index_name': 'NIFTY 50'})
        print(f"NIFTY 50 records remaining: {count_after}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return False

if __name__ == "__main__":
    print("Starting NIFTY 50 data cleanup...")
    success = cleanup_nifty50_data()
    if success:
        print("Cleanup completed successfully!")
    else:
        print("Cleanup failed!")
