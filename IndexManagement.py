#!/usr/bin/env python3
"""
IndexManagement CLI Tool
Command Line Interface for managing market index constituent data URLs and processing

This tool manages CSV URLs that contain index constituent data (companies within market indices)
along with their industry categorization. The data is processed and stored in MongoDB collections.

Database Collections Used:
- index_meta_csv_urls: Stores URL configurations for CSV data sources
- index_meta: Stores the actual index constituent data with company details

Data Flow:
URL Config → CSV Download → Data Parsing → MongoDB Storage
"""

import argparse
import sys
from datetime import datetime
from url_manager import URLManager
from generic_data_loader import GenericIndexDataLoader

class IndexManagement:
    def __init__(self):
        """
        Initialize IndexManagement CLI tool for market index constituent data management
        
        This tool manages:
        - CSV URLs containing index constituent data (companies in indices)
        - Processing of CSV data into structured format
        - Storage in MongoDB collections for index metadata and constituent data
        """
        self.url_manager = URLManager()
        self.data_loader = GenericIndexDataLoader()
        
    def connect(self):
        """Connect to MongoDB"""
        if not self.url_manager.connect_to_mongodb():
            print("❌ Failed to connect to MongoDB")
            return False
        if not self.data_loader.connect_to_mongodb():
            print("❌ Failed to connect data loader to MongoDB")
            return False
        return True
    
    def add_url(self, url, index_name=None, description="", tags=None, is_active=True):
        """Add a new URL to the database"""
        print(f"🔗 Adding URL: {url}")
        
        # Convert tags string to list if provided
        if tags and isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(',')]
        
        success, message = self.url_manager.add_url(
            url=url,
            index_name=index_name,
            description=description,
            tags=tags or [],
            is_active=is_active
        )
        
        if success:
            print(f"✅ URL added successfully!")
            print(f"   URL ID: {message}")
            if not index_name:
                # Get the extracted index name
                extracted_name = self.url_manager.extract_index_name_from_url(url)
                print(f"   Extracted Index Name: {extracted_name}")
        else:
            print(f"❌ Failed to add URL: {message}")
        
        return success
    
    def edit_url(self, url_id, url=None, index_name=None, description=None, tags=None, is_active=None):
        """Edit an existing URL in the database"""
        print(f"✏️  Editing URL ID: {url_id}")
        
        # Convert tags string to list if provided
        if tags and isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(',')]
        
        # Prepare update parameters
        update_params = {}
        if url is not None:
            update_params['url'] = url
        if index_name is not None:
            update_params['index_name'] = index_name
        if description is not None:
            update_params['description'] = description
        if tags is not None:
            update_params['tags'] = tags
        if is_active is not None:
            update_params['is_active'] = is_active
        
        if not update_params:
            print("❌ No parameters provided for update")
            return False
        
        success, message = self.url_manager.update_url(url_id, **update_params)
        
        if success:
            print(f"✅ URL updated successfully!")
            print(f"   {message}")
        else:
            print(f"❌ Failed to update URL: {message}")
        
        return success
    
    def delete_url(self, url_id):
        """Delete a URL from the database"""
        print(f"🗑️  Deleting URL ID: {url_id}")
        
        success, message = self.url_manager.delete_url(url_id)
        
        if success:
            print(f"✅ URL deleted successfully!")
            print(f"   {message}")
        else:
            print(f"❌ Failed to delete URL: {message}")
        
        return success
    
    def list_urls(self, active_only=False):
        """List all URLs in the database with collection context"""
        print(f"📋 Listing Index CSV URLs {'(active only)' if active_only else '(all)'}")
        print("    Data stored in: index_meta_csv_urls collection")
        print("=" * 60)
        
        try:
            urls = self.url_manager.get_all_urls(active_only=active_only)
            
            if not urls:
                print("   No URLs found")
                return True
            
            print(f"   Found {len(urls)} URL(s):")
            print()
            
            for url in urls:
                status = "🟢 ACTIVE" if url.get('is_active') else "🔴 INACTIVE"
                valid = "✅ VALID" if url.get('is_valid') else "❌ INVALID"
                
                print(f"   ID: {url['_id']}")
                print(f"   URL: {url['url']}")
                print(f"   Index: {url['index_name']}")
                print(f"   Description: {url.get('description', 'N/A')}")
                print(f"   Tags: {', '.join(url.get('tags', []))}")
                print(f"   Status: {status} | {valid}")
                print(f"   Created: {url.get('created_at', 'N/A')}")
                print("-" * 50)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to list URLs: {e}")
            return False
    
    def process_all_active(self):
        """Process all active URLs in the database"""
        print("🔄 Processing all active index URLs...")
        print("    Reading URLs from: index_meta_csv_urls collection")
        print("    Storing data to: index_meta collection")
        print("=" * 60)
        
        try:
            # Get active URLs first to show what will be processed
            active_urls = self.url_manager.get_all_urls(active_only=True)
            
            if not active_urls:
                print("   No active URLs found")
                return True
            
            print(f"   Found {len(active_urls)} active URL(s) to process:")
            for url in active_urls:
                print(f"   • {url['index_name']}: {url['url']}")
            print()
            
            # Process all active URLs
            success = self.data_loader.process_all_active_urls()
            
            if success:
                print("✅ All active URLs processed successfully!")
                print("   Index constituent data updated in: index_meta collection")
                
                # Show statistics
                stats = self.data_loader.get_collection_stats()
                if stats:
                    self._display_stats(stats)
            else:
                print("❌ Failed to process some or all URLs. Check logs for details.")
            
            return success
            
        except Exception as e:
            print(f"❌ Failed to process URLs: {e}")
            return False
    
    def process_specific(self, url_ids):
        """Process specific URLs by their IDs"""
        print(f"🔄 Processing {len(url_ids)} specific URL(s)...")
        
        try:
            # Show which URLs will be processed
            print("   URLs to process:")
            for url_id in url_ids:
                url = self.url_manager.get_url_by_id(url_id)
                if url:
                    print(f"   • {url['index_name']}: {url['url']}")
                else:
                    print(f"   • {url_id}: URL not found")
            print()
            
            # Process specific URLs
            results = self.data_loader.process_specific_urls(url_ids)
            
            if results.get("success", False):
                processed = results.get("processed_count", 0)
                total = results.get("total_count", 0)
                print(f"✅ Successfully processed {processed}/{total} URLs!")
                
                # Show detailed results
                if results.get("results"):
                    print("\n📋 Processing Details:")
                    for result in results["results"]:
                        if result.get("success"):
                            docs = result.get("documents_loaded", "N/A")
                            print(f"   ✅ {result['index_name']}: {docs} documents loaded")
                        else:
                            error = result.get("error", "Unknown error")
                            print(f"   ❌ {result.get('index_name', 'Unknown')}: {error}")
                
                # Show overall statistics
                stats = self.data_loader.get_collection_stats()
                if stats:
                    print()
                    self._display_stats(stats)
            else:
                error = results.get("error", "Unknown error occurred")
                processed = results.get("processed_count", 0)
                total = results.get("total_count", 0)
                print(f"❌ Processed {processed}/{total} URLs with errors: {error}")
            
            return results.get("success", False)
            
        except Exception as e:
            print(f"❌ Failed to process specific URLs: {e}")
            return False
    
    def _display_stats(self, stats):
        """Display collection statistics"""
        total_docs = stats.get('total_documents', 0)
        index_stats = stats.get('index_stats', [])
        
        print(f"📊 Database Statistics:")
        print(f"   Total documents: {total_docs}")
        
        if index_stats:
            print("   Index breakdown:")
            for stat in index_stats:
                index_name = stat['_id']
                doc_count = stat['count']
                last_update = stat.get('last_update', 'Unknown')
                print(f"   • {index_name}: {doc_count} documents (last update: {last_update})")
    
    def show_stats(self):
        """Show database statistics"""
        print("📊 Database Statistics - Index Constituent Data")
        print("=" * 60)
        
        try:
            stats = self.data_loader.get_collection_stats()
            
            if stats:
                self._display_stats(stats)
                
                # Show collection schema information
                print("\n📋 Collection Information:")
                print("   • index_meta_csv_urls: URL configurations for CSV data sources")
                print("   • index_meta: Processed index constituent data")
                
                # Show sample document from index_meta if available
                self._show_collection_snippet()
            else:
                print("   No statistics available")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to get statistics: {e}")
            return False
    
    def _show_collection_snippet(self):
        """Show a sample document from index_meta collection for AI understanding"""
        try:
            # Get a sample document from index_meta
            sample_doc = self.data_loader.collection.find_one({}, {
                "_id": 0,  # Exclude _id for cleaner output
                "Company Name": 1,
                "Industry": 1,
                "Symbol": 1,
                "Series": 1,
                "ISIN Code": 1,
                "index_name": 1,
                "data_source": 1,
                "download_timestamp": 1
            })
            
            if sample_doc:
                print("\n📄 Sample Document Structure (index_meta collection):")
                print("   {")
                for key, value in sample_doc.items():
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:47] + "..."
                    print(f'     "{key}": "{value}",')
                print("   }")
                print("\n   This shows how CSV data is structured after processing:")
                print("   - Company details from CSV (Name, Industry, Symbol, etc.)")
                print("   - Metadata added during processing (index_name, data_source, timestamp)")
            
            # Show sample URL config
            url_sample = self.url_manager.url_collection.find_one({}, {
                "_id": 0,
                "url": 1,
                "index_name": 1,
                "description": 1,
                "is_active": 1,
                "is_valid": 1,
                "created_at": 1
            })
            
            if url_sample:
                print("\n📄 Sample URL Configuration (index_meta_csv_urls collection):")
                print("   {")
                for key, value in url_sample.items():
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:47] + "..."
                    print(f'     "{key}": "{value}",')
                print("   }")
                print("\n   This shows how CSV URLs are configured and managed")
                
        except Exception as e:
            print(f"   Note: Could not retrieve collection samples: {e}")
    
    def close(self):
        """Close database connections"""
        if self.url_manager:
            self.url_manager.close_connection()
        if self.data_loader:
            self.data_loader.close_connection()

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="IndexManagement CLI Tool for market index constituent data management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Database Collections:
  index_meta_csv_urls - Stores URL configurations for CSV data sources
  index_meta          - Stores processed index constituent data with company details

Examples:
  # Add a simple URL (index name will be auto-extracted)
  python IndexManagement.py add-url "https://niftyindices.com/IndexConstituent/ind_nifty50list.csv"
  
  # Add URL with custom index name and description
  python IndexManagement.py add-url "https://example.com/data.csv" --index-name "CUSTOM INDEX" --description "My custom data source"
  
  # Add URL with tags and set as inactive
  python IndexManagement.py add-url "https://example.com/data.csv" --tags "test,demo" --inactive
  
  # List all URLs (stored in index_meta_csv_urls collection)
  python IndexManagement.py list-urls
  
  # List only active URLs
  python IndexManagement.py list-urls --active-only
  
  # Edit URL description and tags
  python IndexManagement.py edit-url URL_ID --description "Updated description" --tags "new,tags"
  
  # Edit URL status
  python IndexManagement.py edit-url URL_ID --inactive
  
  # Delete a URL
  python IndexManagement.py delete-url URL_ID
  
  # Process all active URLs (downloads CSV data into index_meta collection)
  python IndexManagement.py process-all
  
  # Process specific URLs by ID
  python IndexManagement.py process-urls URL_ID1 URL_ID2 URL_ID3
  
  # Show database statistics (from index_meta collection)
  python IndexManagement.py show-stats
        """
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add URL command
    add_parser = subparsers.add_parser('add-url', help='Add a new URL to the database')
    add_parser.add_argument('url', help='CSV URL to add')
    add_parser.add_argument('--index-name', help='Index name (auto-extracted if not provided)')
    add_parser.add_argument('--description', default='', help='Description of the data source')
    add_parser.add_argument('--tags', help='Comma-separated tags')
    add_parser.add_argument('--inactive', action='store_true', help='Add URL as inactive (default is active)')
    
    # Edit URL command
    edit_parser = subparsers.add_parser('edit-url', help='Edit an existing URL in the database')
    edit_parser.add_argument('url_id', help='URL ID to edit')
    edit_parser.add_argument('--url', help='New URL')
    edit_parser.add_argument('--index-name', help='New index name')
    edit_parser.add_argument('--description', help='New description')
    edit_parser.add_argument('--tags', help='New comma-separated tags')
    edit_parser.add_argument('--active', action='store_true', help='Set URL as active')
    edit_parser.add_argument('--inactive', action='store_true', help='Set URL as inactive')
    
    # Delete URL command
    delete_parser = subparsers.add_parser('delete-url', help='Delete a URL from the database')
    delete_parser.add_argument('url_id', help='URL ID to delete')
    
    # List URLs command
    list_parser = subparsers.add_parser('list-urls', help='List all URLs in the database')
    list_parser.add_argument('--active-only', action='store_true', help='List only active URLs')
    
    # Process all active URLs command
    process_all_parser = subparsers.add_parser('process-all', help='Process all active URLs and download data')
    
    # Process specific URLs command
    process_specific_parser = subparsers.add_parser('process-urls', help='Process specific URLs by their IDs')
    process_specific_parser.add_argument('url_ids', nargs='+', help='One or more URL IDs to process')
    
    # Show statistics command
    stats_parser = subparsers.add_parser('show-stats', help='Show database statistics')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show help if no command provided
    if not args.command:
        parser.print_help()
        return
    
    # Initialize IndexManagement
    im = IndexManagement()
    
    try:
        # Connect to database
        if not im.connect():
            sys.exit(1)
        
        # Execute command
        if args.command == 'add-url':
            success = im.add_url(
                url=args.url,
                index_name=args.index_name,
                description=args.description,
                tags=args.tags,
                is_active=not args.inactive  # Invert inactive flag
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'edit-url':
            # Handle active/inactive flags
            is_active = None
            if args.active and args.inactive:
                print("❌ Cannot specify both --active and --inactive")
                sys.exit(1)
            elif args.active:
                is_active = True
            elif args.inactive:
                is_active = False
            
            success = im.edit_url(
                url_id=args.url_id,
                url=args.url,
                index_name=args.index_name,
                description=args.description,
                tags=args.tags,
                is_active=is_active
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'delete-url':
            success = im.delete_url(args.url_id)
            sys.exit(0 if success else 1)
            
        elif args.command == 'list-urls':
            success = im.list_urls(active_only=args.active_only)
            sys.exit(0 if success else 1)
            
        elif args.command == 'process-all':
            success = im.process_all_active()
            sys.exit(0 if success else 1)
            
        elif args.command == 'process-urls':
            success = im.process_specific(args.url_ids)
            sys.exit(0 if success else 1)
            
        elif args.command == 'show-stats':
            success = im.show_stats()
            sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        im.close()

if __name__ == "__main__":
    main()
