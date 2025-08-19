#!/usr/bin/env python3
"""
NIFTY 50 Index Constituent Data Loader
Downloads CSV data from NIFTY indices website and loads into MongoDB
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NiftyDataLoader:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="market_hunt"):
        """Initialize the data loader with MongoDB connection"""
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.collection = None
        
    def connect_to_mongodb(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.collection = self.db.index_meta
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
                if href.endswith('.csv') and ('constituent' in href.lower() or 'nifty' in href.lower()):
                    csv_links.append(urljoin(base_url, href))
                    logger.info(f"Found CSV link via direct match: {href}")
            
            # Pattern 3: Look for download buttons or links
            for element in soup.find_all(['a', 'button'], href=True):
                if 'download' in element.get('class', []) or 'download' in str(element.get('onclick', '')):
                    href = element.get('href', '')
                    if href and (href.endswith('.csv') or 'csv' in href):
                        csv_links.append(urljoin(base_url, href))
                        logger.info(f"Found CSV link via download button: {href}")
            
            if csv_links:
                return csv_links[0]  # Return the first found link
            else:
                logger.warning("No CSV download link found. Attempting manual URL construction...")
                # Try common patterns for NIFTY CSV downloads
                possible_urls = [
                    "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
                    "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
                    "https://www1.nseindia.com/content/indices/ind_nifty50list.csv"
                ]
                return possible_urls
                
        except Exception as e:
            logger.error(f"Error finding CSV link: {e}")
            return None
    
    def download_csv_data(self, url_or_urls):
        """Download CSV data from the given URL(s)"""
        urls = url_or_urls if isinstance(url_or_urls, list) else [url_or_urls]
        
        for url in urls:
            try:
                logger.info(f"Attempting to download from: {url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Check if the response contains CSV data
                if 'text/csv' in response.headers.get('content-type', '') or url.endswith('.csv'):
                    logger.info(f"Successfully downloaded CSV data from: {url}")
                    return response.text
                else:
                    logger.warning(f"Response from {url} doesn't appear to be CSV data")
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to download from {url}: {e}")
                continue
        
        return None
    
    def parse_csv_data(self, csv_text):
        """Parse CSV text data into pandas DataFrame"""
        try:
            from io import StringIO
            df = pd.read_csv(StringIO(csv_text))
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Add metadata
            df['data_source'] = 'niftyindices.com'
            df['download_timestamp'] = datetime.now()
            df['index_name'] = 'NIFTY 50'
            
            logger.info(f"Parsed CSV data: {len(df)} rows, {len(df.columns)} columns")
            logger.info(f"Columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing CSV data: {e}")
            return None
    
    def load_to_mongodb(self, df):
        """Load DataFrame to MongoDB collection"""
        try:
            if df is None or df.empty:
                logger.error("No data to load")
                return False
            
            # Convert DataFrame to dictionary records
            records = df.to_dict('records')
            
            # Clear existing data for this index
            self.collection.delete_many({"index_name": "NIFTY 50"})
            logger.info("Cleared existing NIFTY 50 data")
            
            # Insert new data
            result = self.collection.insert_many(records)
            logger.info(f"Inserted {len(result.inserted_ids)} records into index_meta collection")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading data to MongoDB: {e}")
            return False
    
    def get_collection_stats(self):
        """Get statistics about the loaded data"""
        try:
            total_count = self.collection.count_documents({})
            nifty50_count = self.collection.count_documents({"index_name": "NIFTY 50"})
            
            logger.info(f"Total documents in index_meta: {total_count}")
            logger.info(f"NIFTY 50 documents: {nifty50_count}")
            
            # Get sample document
            sample = self.collection.find_one({"index_name": "NIFTY 50"})
            if sample:
                logger.info(f"Sample document keys: {list(sample.keys())}")
            
            return {
                "total_documents": total_count,
                "nifty50_documents": nifty50_count,
                "sample_document": sample
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return None
    
    def run(self, base_url="https://niftyindices.com/indices/equity/broad-based-indices/NIFTY--50"):
        """Main method to download and load NIFTY 50 data"""
        logger.info("Starting NIFTY 50 data loading process...")
        
        # Connect to MongoDB
        if not self.connect_to_mongodb():
            return False
        
        # Find CSV download link
        csv_url = self.find_csv_download_link(base_url)
        if not csv_url:
            logger.error("Could not find CSV download link")
            return False
        
        # Download CSV data
        csv_data = self.download_csv_data(csv_url)
        if not csv_data:
            logger.error("Could not download CSV data")
            return False
        
        # Parse CSV data
        df = self.parse_csv_data(csv_data)
        if df is None:
            logger.error("Could not parse CSV data")
            return False
        
        # Load to MongoDB
        if not self.load_to_mongodb(df):
            logger.error("Could not load data to MongoDB")
            return False
        
        # Get stats
        stats = self.get_collection_stats()
        
        logger.info("NIFTY 50 data loading completed successfully!")
        return True
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

def main():
    """Main function"""
    loader = NiftyDataLoader()
    
    try:
        success = loader.run()
        if success:
            print("✅ NIFTY 50 data loaded successfully!")
        else:
            print("❌ Failed to load NIFTY 50 data")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        loader.close_connection()

if __name__ == "__main__":
    main()
