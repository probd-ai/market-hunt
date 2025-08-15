#!/usr/bin/env python3
"""
Generic Index Data Loader
Downloads CSV data from multiple configured URLs and loads into MongoDB
"""

import requests
import pandas as pd
import pymongo
from pymongo import MongoClient
from datetime import datetime
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
from io import StringIO
from url_manager import URLManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GenericIndexDataLoader:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="market_hunt"):
        """Initialize the generic data loader with MongoDB connection"""
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.collection = None
        self.url_manager = URLManager(mongo_uri, db_name)
        
    def connect_to_mongodb(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.collection = self.db.index_meta
            
            # Also connect URL manager
            if not self.url_manager.connect_to_mongodb():
                return False
                
            logger.info(f"Connected to MongoDB: {self.db_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def find_csv_download_link(self, base_url):
        """Find the CSV download link for Index Constituent data"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(base_url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for links containing "Index Constituent" or CSV download patterns
            csv_links = []
            
            # Pattern 1: Look for text containing "Index Constituent"
            for link in soup.find_all('a', href=True):
                link_text = link.get_text(strip=True).lower()
                if 'index constituent' in link_text or 'constituent' in link_text:
                    href = link['href']
                    if href.endswith('.csv') or 'csv' in href.lower():
                        csv_links.append(urljoin(base_url, href))
                        logger.info(f"Found CSV link via text match: {href}")
            
            # Pattern 2: Look for direct CSV links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.csv') and ('constituent' in href.lower() or 'nifty' in href.lower() or 'sensex' in href.lower()):
                    csv_links.append(urljoin(base_url, href))
                    logger.info(f"Found CSV link via direct match: {href}")
            
            if csv_links:
                return csv_links[0]  # Return the first found link
            else:
                # If no CSV link found, try the URL directly
                logger.warning("No CSV download link found. Trying URL directly...")
                return base_url
                
        except Exception as e:
            logger.error(f"Error finding CSV link: {e}")
            return base_url  # Try the original URL as fallback
    
    def download_csv_data(self, url):
        """Download CSV data from the given URL"""
        try:
            logger.info(f"Attempting to download from: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Check if the response contains CSV data
            content_type = response.headers.get('content-type', '').lower()
            if 'text/csv' in content_type or url.endswith('.csv') or ',' in response.text[:1000]:
                logger.info(f"Successfully downloaded CSV data from: {url}")
                return response.text
            else:
                logger.warning(f"Response from {url} doesn't appear to be CSV data")
                return None
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download from {url}: {e}")
            return None
    
    def parse_csv_data(self, csv_text, index_name, data_source_url):
        """Parse CSV text data into pandas DataFrame"""
        try:
            df = pd.read_csv(StringIO(csv_text))
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Add metadata
            df['data_source'] = data_source_url
            df['download_timestamp'] = datetime.now()
            df['index_name'] = index_name
            
            logger.info(f"Parsed CSV data for {index_name}: {len(df)} rows, {len(df.columns)} columns")
            logger.info(f"Columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing CSV data for {index_name}: {e}")
            return None
    
    def load_to_mongodb(self, df, index_name):
        """Load DataFrame to MongoDB collection"""
        try:
            if df is None or df.empty:
                logger.error(f"No data to load for {index_name}")
                return False
            
            # Convert DataFrame to dictionary records
            records = df.to_dict('records')
            
            # Clear existing data for this index
            delete_result = self.collection.delete_many({"index_name": index_name})
            logger.info(f"Cleared {delete_result.deleted_count} existing {index_name} records")
            
            # Insert new data
            result = self.collection.insert_many(records)
            logger.info(f"Inserted {len(result.inserted_ids)} records for {index_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading data to MongoDB for {index_name}: {e}")
            return False
    
    def process_single_url(self, url_config):
        """Process a single URL configuration"""
        url_id = url_config['_id']
        url = url_config['url']
        index_name = url_config['index_name']
        
        logger.info(f"Processing {index_name}: {url}")
        
        try:
            # Check if URL needs CSV link discovery
            if not url.endswith('.csv'):
                csv_url = self.find_csv_download_link(url)
                if csv_url != url:
                    logger.info(f"Found CSV URL: {csv_url}")
                    url = csv_url
            
            # Download CSV data
            csv_data = self.download_csv_data(url)
            if not csv_data:
                error_msg = f"Failed to download CSV data from {url}"
                logger.error(error_msg)
                self.url_manager.mark_download_error(url_id, error_msg)
                return False
            
            # Parse CSV data
            df = self.parse_csv_data(csv_data, index_name, url)
            if df is None:
                error_msg = f"Failed to parse CSV data for {index_name}"
                logger.error(error_msg)
                self.url_manager.mark_download_error(url_id, error_msg)
                return False
            
            # Load to MongoDB
            if not self.load_to_mongodb(df, index_name):
                error_msg = f"Failed to load data to MongoDB for {index_name}"
                logger.error(error_msg)
                self.url_manager.mark_download_error(url_id, error_msg)
                return False
            
            # Mark success
            self.url_manager.mark_download_success(url_id)
            logger.info(f"Successfully processed {index_name}")
            return True
            
        except Exception as e:
            error_msg = f"Unexpected error processing {index_name}: {str(e)}"
            logger.error(error_msg)
            self.url_manager.mark_download_error(url_id, error_msg)
            return False
    
    def process_all_active_urls(self):
        """Process all active URL configurations"""
        try:
            url_configs = self.url_manager.get_all_urls(active_only=True)
            
            if not url_configs:
                logger.warning("No active URL configurations found")
                return False
            
            logger.info(f"Found {len(url_configs)} active URL configurations")
            
            success_count = 0
            for url_config in url_configs:
                if self.process_single_url(url_config):
                    success_count += 1
            
            logger.info(f"Successfully processed {success_count}/{len(url_configs)} URL configurations")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error processing URLs: {e}")
            return False
    
    def process_specific_urls(self, url_ids):
        """Process specific URL configurations by their IDs"""
        try:
            success_count = 0
            results = []
            
            for url_id in url_ids:
                url_config = self.url_manager.get_url_by_id(url_id)
                if not url_config:
                    logger.error(f"URL configuration not found: {url_id}")
                    results.append({
                        "url_id": url_id,
                        "success": False,
                        "error": "URL configuration not found"
                    })
                    continue
                
                if self.process_single_url(url_config):
                    success_count += 1
                    # Get the count of documents loaded for this index
                    doc_count = self.collection.count_documents({"index_name": url_config['index_name']})
                    results.append({
                        "url_id": url_id,
                        "success": True,
                        "index_name": url_config['index_name'],
                        "url": url_config['url'],
                        "documents_loaded": doc_count,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    results.append({
                        "url_id": url_id,
                        "success": False,
                        "index_name": url_config['index_name'],
                        "url": url_config['url'],
                        "error": "Failed to process URL"
                    })
            
            logger.info(f"Successfully processed {success_count}/{len(url_ids)} specified URLs")
            
            return {
                "success": success_count > 0,
                "processed_count": success_count,
                "total_count": len(url_ids),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error processing specific URLs: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "total_count": len(url_ids) if url_ids else 0
            }
    
    def get_collection_stats(self):
        """Get statistics about the loaded data"""
        try:
            total_count = self.collection.count_documents({})
            
            # Get stats by index
            pipeline = [
                {"$group": {
                    "_id": "$index_name",
                    "count": {"$sum": 1},
                    "last_update": {"$max": "$download_timestamp"}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            index_stats = list(self.collection.aggregate(pipeline))
            
            logger.info(f"Total documents in index_meta: {total_count}")
            for stat in index_stats:
                logger.info(f"{stat['_id']}: {stat['count']} documents (last update: {stat['last_update']})")
            
            return {
                "total_documents": total_count,
                "index_stats": index_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return None
    
    def run_all(self):
        """Main method to process all active URLs"""
        logger.info("Starting generic index data loading process...")
        
        # Connect to MongoDB
        if not self.connect_to_mongodb():
            return False
        
        # Process all active URLs
        if not self.process_all_active_urls():
            logger.error("Failed to process URLs")
            return False
        
        # Get stats
        stats = self.get_collection_stats()
        
        logger.info("Generic index data loading completed!")
        return True
    
    def run_specific(self, url_ids):
        """Run for specific URL IDs"""
        logger.info(f"Starting data loading for specific URLs: {url_ids}")
        
        # Connect to MongoDB
        if not self.connect_to_mongodb():
            return False
        
        # Process specific URLs
        if not self.process_specific_urls(url_ids):
            logger.error("Failed to process specified URLs")
            return False
        
        # Get stats
        stats = self.get_collection_stats()
        
        logger.info("Specific URL data loading completed!")
        return True
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
        if self.url_manager:
            self.url_manager.close_connection()
        logger.info("MongoDB connections closed")

def main():
    """Main function"""
    import sys
    
    loader = GenericIndexDataLoader()
    
    try:
        if len(sys.argv) > 1:
            # Run for specific URL IDs
            url_ids = sys.argv[1:]
            success = loader.run_specific(url_ids)
        else:
            # Run for all active URLs
            success = loader.run_all()
        
        if success:
            print("✅ Index data loading completed successfully!")
        else:
            print("❌ Failed to load index data")
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Error: {e}")
    finally:
        loader.close_connection()

if __name__ == "__main__":
    main()
