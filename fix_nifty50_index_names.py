#!/usr/bin/env python3
"""
Script to fix NIFTY50 data with missing index_name field
"""

import pymongo
from datetime import datetime

def fix_nifty50_index_names():
    """Update NIFTY50 records to have correct index_name"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        db = client['market_hunt']
        collection = db.index_meta
        
        # Find all records that should belong to NIFTY50 but have null index_name
        # We'll identify them by looking for records with 50 total companies in the index
        # First, let's count records with null index_name
        null_count = collection.count_documents({'index_name': None})
        print(f"Found {null_count} records with null index_name")
        
        if null_count > 0:
            # Update all records with null index_name to have "NIFTY50"
            result = collection.update_many(
                {'index_name': None},
                {'$set': {'index_name': 'NIFTY50'}}
            )
            print(f"Updated {result.modified_count} records to have index_name='NIFTY50'")
        else:
            print("No records found with null index_name")
            
        # Verify the fix
        nifty50_count = collection.count_documents({'index_name': 'NIFTY50'})
        print(f"Total NIFTY50 records after fix: {nifty50_count}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"Error during fix: {e}")
        return False

if __name__ == "__main__":
    print("Starting NIFTY50 index_name fix...")
    success = fix_nifty50_index_names()
    if success:
        print("Fix completed successfully!")
    else:
        print("Fix failed!")
