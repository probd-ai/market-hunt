#!/usr/bin/env python3
"""
Database Cleanup Script
Cleans up the entire market_hunt database and keeps only the URL configurations

This script will:
1. Remove all data collections (index_meta, symbol_mappings, stock_gap_status, prices_*, stock_metadata, data_processing_logs)
2. Keep only index_meta_csv_urls collection (URL configurations)
3. Show before/after statistics

Usage:
python cleanup_database.py [--confirm]

Use --confirm flag to actually perform the cleanup, otherwise it will show what would be deleted.
"""

import argparse
import pymongo
from pymongo import MongoClient
import sys
from datetime import datetime

class DatabaseCleanup:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['market_hunt']
    
    def get_database_stats(self):
        """Get current database statistics"""
        stats = {}
        collections = self.db.list_collection_names()
        
        for collection_name in collections:
            collection = self.db[collection_name]
            count = collection.count_documents({})
            stats[collection_name] = count
            
        return stats
    
    def show_cleanup_plan(self):
        """Show what will be cleaned up"""
        stats = self.get_database_stats()
        
        print("=== DATABASE CLEANUP PLAN ===")
        print(f"Database: market_hunt")
        print(f"Total collections: {len(stats)}")
        print()
        
        # Collections to keep
        keep_collections = ['index_meta_csv_urls']
        # Collections to remove (anything not in keep list)
        remove_collections = [name for name in stats.keys() if name not in keep_collections]
        
        print("📋 COLLECTIONS TO KEEP:")
        for collection in keep_collections:
            count = stats.get(collection, 0)
            print(f"  ✅ {collection}: {count:,} documents")
        
        print("\n🗑️  COLLECTIONS TO REMOVE:")
        total_documents_to_remove = 0
        for collection in remove_collections:
            count = stats[collection]
            total_documents_to_remove += count
            print(f"  ❌ {collection}: {count:,} documents")
        
        print(f"\n📊 SUMMARY:")
        print(f"  • Total documents to remove: {total_documents_to_remove:,}")
        print(f"  • Collections to remove: {len(remove_collections)}")
        
        return remove_collections, total_documents_to_remove
    
    def perform_cleanup(self, remove_collections):
        """Perform the actual cleanup"""
        print("\n🧹 PERFORMING CLEANUP...")
        
        removed_collections = 0
        removed_documents = 0
        
        for collection_name in remove_collections:
            try:
                collection = self.db[collection_name]
                doc_count = collection.count_documents({})
                
                # Drop the entire collection
                collection.drop()
                
                print(f"  ✅ Removed collection '{collection_name}' ({doc_count:,} documents)")
                removed_collections += 1
                removed_documents += doc_count
                
            except Exception as e:
                print(f"  ❌ Error removing collection '{collection_name}': {e}")
        
        print(f"\n✨ CLEANUP COMPLETED!")
        print(f"  • Removed {removed_collections} collections")
        print(f"  • Removed {removed_documents:,} documents")
        
        return removed_collections, removed_documents
    
    def verify_cleanup(self):
        """Verify the cleanup was successful"""
        print("\n🔍 VERIFYING CLEANUP...")
        stats = self.get_database_stats()
        
        print("📋 REMAINING COLLECTIONS:")
        for collection_name, count in stats.items():
            print(f"  ✅ {collection_name}: {count:,} documents")
        
        if len(stats) == 1 and 'index_meta_csv_urls' in stats:
            print("\n🎉 CLEANUP VERIFICATION: SUCCESS!")
            print("   Only index_meta_csv_urls collection remains as expected.")
        else:
            print("\n⚠️  CLEANUP VERIFICATION: WARNING!")
            print("   Unexpected collections remain or expected collection missing.")
    
    def close(self):
        """Close database connection"""
        self.client.close()

def main():
    parser = argparse.ArgumentParser(description='Clean up market_hunt database')
    parser.add_argument('--confirm', action='store_true', 
                       help='Actually perform the cleanup (without this flag, only shows what would be done)')
    
    args = parser.parse_args()
    
    print("🗄️  Market Hunt Database Cleanup Tool")
    print("=" * 50)
    
    cleanup = DatabaseCleanup()
    
    try:
        # Show what will be cleaned up
        remove_collections, total_docs = cleanup.show_cleanup_plan()
        
        if not args.confirm:
            print("\n⚠️  DRY RUN MODE")
            print("   No changes were made. Use --confirm flag to perform actual cleanup.")
            print(f"   Command: python {sys.argv[0]} --confirm")
            return
        
        # Confirm before proceeding
        print(f"\n⚠️  WARNING: This will permanently delete {total_docs:,} documents!")
        response = input("Are you sure you want to proceed? (type 'YES' to confirm): ")
        
        if response != 'YES':
            print("❌ Cleanup cancelled.")
            return
        
        # Perform cleanup
        cleanup.perform_cleanup(remove_collections)
        
        # Verify cleanup
        cleanup.verify_cleanup()
        
        print(f"\n📝 Cleanup completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n🚀 Next steps:")
        print("   1. Use IndexManagement.py to reprocess URLs and rebuild index_meta")
        print("   2. Use DataLoadManagement.py to refresh symbol mappings")
        print("   3. Download stock data as needed")
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        sys.exit(1)
    
    finally:
        cleanup.close()

if __name__ == "__main__":
    main()
