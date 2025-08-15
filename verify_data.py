#!/usr/bin/env python3
"""
MongoDB Data Verification Script
Verifies the loaded NIFTY 50 data in MongoDB
"""

import pymongo
from pymongo import MongoClient
import pandas as pd
from datetime import datetime
import json

def verify_mongodb_data():
    """Verify the loaded data in MongoDB"""
    try:
        # Connect to MongoDB
        client = MongoClient("mongodb://localhost:27017/")
        db = client.market_hunt
        collection = db.index_meta
        
        print("🔍 MongoDB Data Verification Report")
        print("=" * 50)
        
        # Get collection statistics
        total_docs = collection.count_documents({})
        nifty50_docs = collection.count_documents({"index_name": "NIFTY 50"})
        
        print(f"📊 Total documents in index_meta: {total_docs}")
        print(f"📈 NIFTY 50 documents: {nifty50_docs}")
        print()
        
        # Get sample documents
        print("📋 Sample Documents:")
        sample_docs = list(collection.find({"index_name": "NIFTY 50"}).limit(5))
        
        for i, doc in enumerate(sample_docs, 1):
            print(f"\n{i}. {doc.get('Company Name', 'N/A')} ({doc.get('Symbol', 'N/A')})")
            print(f"   Industry: {doc.get('Industry', 'N/A')}")
            print(f"   ISIN: {doc.get('ISIN Code', 'N/A')}")
        
        print("\n" + "=" * 50)
        
        # Get all unique industries
        industries = collection.distinct("Industry", {"index_name": "NIFTY 50"})
        print(f"🏭 Industries represented: {len(industries)}")
        for industry in sorted(industries):
            count = collection.count_documents({"index_name": "NIFTY 50", "Industry": industry})
            print(f"   - {industry}: {count} companies")
        
        print("\n" + "=" * 50)
        
        # Data quality check
        print("✅ Data Quality Check:")
        missing_symbols = collection.count_documents({"index_name": "NIFTY 50", "Symbol": {"$in": [None, ""]}})
        missing_companies = collection.count_documents({"index_name": "NIFTY 50", "Company Name": {"$in": [None, ""]}})
        missing_isin = collection.count_documents({"index_name": "NIFTY 50", "ISIN Code": {"$in": [None, ""]}})
        
        print(f"   Missing Symbols: {missing_symbols}")
        print(f"   Missing Company Names: {missing_companies}")
        print(f"   Missing ISIN Codes: {missing_isin}")
        
        # Show the latest data timestamp
        latest_doc = collection.find_one({"index_name": "NIFTY 50"}, sort=[("download_timestamp", -1)])
        if latest_doc and 'download_timestamp' in latest_doc:
            print(f"   Latest Data Timestamp: {latest_doc['download_timestamp']}")
        
        print("\n✅ Data verification completed successfully!")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error verifying data: {e}")

def export_to_csv():
    """Export the MongoDB data to CSV for verification"""
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client.market_hunt
        collection = db.index_meta
        
        # Get all NIFTY 50 data
        cursor = collection.find({"index_name": "NIFTY 50"})
        data = list(cursor)
        
        if data:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Remove MongoDB _id field for cleaner export
            if '_id' in df.columns:
                df = df.drop('_id', axis=1)
            
            # Export to CSV
            output_file = "/media/guru/Data/workspace/market_hunt/nifty50_verification.csv"
            df.to_csv(output_file, index=False)
            print(f"📁 Data exported to: {output_file}")
            
        client.close()
        
    except Exception as e:
        print(f"❌ Error exporting data: {e}")

if __name__ == "__main__":
    verify_mongodb_data()
    print()
    export_to_csv()
