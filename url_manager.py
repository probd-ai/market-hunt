#!/usr/bin/env python3
"""
URL Manager for Index Constituent Data Sources
Manages CSV URL configurations stored in MongoDB
"""

import pymongo
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import logging
import re
from urllib.parse import urlparse
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class URLManager:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="market_hunt"):
        """Initialize URL Manager with MongoDB connection"""
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.url_collection = None
        
    def connect_to_mongodb(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.url_collection = self.db.index_meta_csv_urls
            logger.info(f"Connected to MongoDB: {self.db_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def extract_index_name_from_url(self, url):
        """Extract index name from CSV URL or filename"""
        try:
            # Parse the URL to get the filename
            parsed_url = urlparse(url)
            filename = parsed_url.path.split('/')[-1]
            
            # Remove file extension
            filename_no_ext = filename.replace('.csv', '').replace('.CSV', '')
            
            # Common patterns for index names
            patterns = [
                r'ind[_\-]nifty[_\-]?([a-zA-Z0-9]+)',  # ind_nifty50list, ind_niftymidcap50 etc.
                r'nifty[_\-]?(\d+)',  # nifty50, nifty_50, nifty-50
                r'sensex[_\-]?(\d+)?',  # sensex, sensex30
                r'bse[_\-]?(\d+)',  # bse500, bse_100
                r'(nifty|sensex|bse)',  # general match
            ]
            
            for pattern in patterns:
                match = re.search(pattern, filename_no_ext, re.IGNORECASE)
                if match:
                    if pattern.startswith(r'ind[_\-]nifty'):
                        # Special handling for ind_nifty patterns
                        full_match = match.group(0)
                        # Extract everything after 'ind_'
                        index_part = full_match.split('_', 1)[-1] if '_' in full_match else full_match.split('-', 1)[-1]
                        return index_part.upper().replace('LIST', '').replace('_', ' ').replace('-', ' ')
                    elif match.groups():
                        # If there's a captured group (like number)
                        base_name = match.group(0).upper()
                        return base_name.replace('_', ' ').replace('-', ' ')
                    else:
                        return match.group(0).upper()
            
            # If no pattern matches, use the filename
            return filename_no_ext.upper().replace('_', ' ').replace('-', ' ')
            
        except Exception as e:
            logger.error(f"Error extracting index name from URL: {e}")
            return "UNKNOWN_INDEX"
    
    def validate_url(self, url):
        """Validate if URL is accessible and returns CSV data"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.head(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Check content type or file extension
            content_type = response.headers.get('content-type', '').lower()
            if 'csv' in content_type or url.lower().endswith('.csv'):
                return True, "URL is valid and points to CSV data"
            else:
                # Try to download a small portion to verify
                response = requests.get(url, headers=headers, timeout=10, stream=True)
                chunk = next(response.iter_content(chunk_size=1024)).decode('utf-8', errors='ignore')
                if ',' in chunk or ';' in chunk:  # Basic CSV detection
                    return True, "URL appears to contain CSV data"
                else:
                    return False, "URL does not appear to contain CSV data"
                    
        except Exception as e:
            return False, f"URL validation failed: {str(e)}"
    
    def add_url(self, url, index_name=None, description="", tags=None, is_active=True):
        """Add a new URL configuration"""
        try:
            # Validate URL
            is_valid, validation_message = self.validate_url(url)
            if not is_valid:
                logger.warning(f"URL validation failed: {validation_message}")
            
            # Extract index name if not provided
            if not index_name:
                index_name = self.extract_index_name_from_url(url)
                logger.info(f"Extracted index name: {index_name}")
            
            # Check if URL already exists
            existing = self.url_collection.find_one({"url": url})
            if existing:
                logger.warning(f"URL already exists: {url}")
                return False, "URL already exists"
            
            # Create URL document
            url_doc = {
                "url": url,
                "index_name": index_name.strip(),
                "description": description,
                "tags": tags or [],
                "is_active": is_active,
                "is_valid": is_valid,
                "validation_message": validation_message,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "last_downloaded": None,
                "download_count": 0,
                "last_error": None
            }
            
            # Insert into MongoDB
            result = self.url_collection.insert_one(url_doc)
            logger.info(f"Added URL configuration: {url} -> {index_name}")
            
            return True, str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error adding URL: {e}")
            return False, str(e)
    
    def update_url(self, url_id, **kwargs):
        """Update an existing URL configuration"""
        try:
            # Prepare update document
            update_doc = {"updated_at": datetime.now()}
            
            # Add allowed fields to update
            allowed_fields = ['url', 'index_name', 'description', 'tags', 'is_active']
            for field in allowed_fields:
                if field in kwargs:
                    update_doc[field] = kwargs[field]
            
            # If URL is being updated, validate it
            if 'url' in kwargs:
                is_valid, validation_message = self.validate_url(kwargs['url'])
                update_doc['is_valid'] = is_valid
                update_doc['validation_message'] = validation_message
            
            # Update in MongoDB
            result = self.url_collection.update_one(
                {"_id": ObjectId(url_id)},
                {"$set": update_doc}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated URL configuration: {url_id}")
                return True, "URL configuration updated successfully"
            else:
                return False, "No URL configuration found with the given ID"
                
        except Exception as e:
            logger.error(f"Error updating URL: {e}")
            return False, str(e)
    
    def delete_url(self, url_id):
        """Delete a URL configuration"""
        try:            
            result = self.url_collection.delete_one({"_id": ObjectId(url_id)})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted URL configuration: {url_id}")
                return True, "URL configuration deleted successfully"
            else:
                return False, "No URL configuration found with the given ID"
                
        except Exception as e:
            logger.error(f"Error deleting URL: {e}")
            return False, str(e)
    
    def get_all_urls(self, active_only=False):
        """Get all URL configurations"""
        try:
            query = {"is_active": True} if active_only else {}
            urls = list(self.url_collection.find(query).sort("created_at", -1))
            
            # Convert ObjectId to string for JSON serialization
            for url in urls:
                url['_id'] = str(url['_id'])
            
            return urls
            
        except Exception as e:
            logger.error(f"Error getting URLs: {e}")
            return []
    
    def get_url_by_id(self, url_id):
        """Get a specific URL configuration by ID"""
        try:            
            url_doc = self.url_collection.find_one({"_id": ObjectId(url_id)})
            if url_doc:
                url_doc['_id'] = str(url_doc['_id'])
            
            return url_doc
            
        except Exception as e:
            logger.error(f"Error getting URL by ID: {e}")
            return None
    
    def mark_download_success(self, url_id):
        """Mark a successful download for a URL"""
        try:            
            self.url_collection.update_one(
                {"_id": ObjectId(url_id)},
                {
                    "$set": {
                        "last_downloaded": datetime.now(),
                        "last_error": None,
                        "updated_at": datetime.now()
                    },
                    "$inc": {"download_count": 1}
                }
            )
            
        except Exception as e:
            logger.error(f"Error marking download success: {e}")
    
    def mark_download_error(self, url_id, error_message):
        """Mark a download error for a URL"""
        try:            
            self.url_collection.update_one(
                {"_id": ObjectId(url_id)},
                {
                    "$set": {
                        "last_error": error_message,
                        "updated_at": datetime.now()
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error marking download error: {e}")
    
    def get_statistics(self):
        """Get statistics about URL configurations"""
        try:
            total_urls = self.url_collection.count_documents({})
            active_urls = self.url_collection.count_documents({"is_active": True})
            valid_urls = self.url_collection.count_documents({"is_valid": True})
            
            # Get unique index names
            index_names = self.url_collection.distinct("index_name")
            
            # Get recent downloads
            recent_downloads = list(
                self.url_collection.find(
                    {"last_downloaded": {"$ne": None}},
                    {"url": 1, "index_name": 1, "last_downloaded": 1}
                ).sort("last_downloaded", -1).limit(5)
            )
            
            return {
                "total_urls": total_urls,
                "active_urls": active_urls,
                "valid_urls": valid_urls,
                "unique_indices": len(index_names),
                "index_names": index_names,
                "recent_downloads": recent_downloads
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

def main():
    """Test function"""
    manager = URLManager()
    
    try:
        if not manager.connect_to_mongodb():
            return
        
        # Add some sample URLs
        sample_urls = [
            {
                "url": "https://niftyindices.com/IndexConstituent/ind_nifty50list.csv",
                "index_name": "NIFTY 50",
                "description": "NIFTY 50 Index Constituents",
                "tags": ["nifty", "large-cap", "equity"]
            },
            {
                "url": "https://niftyindices.com/IndexConstituent/ind_nifty100list.csv",
                "description": "NIFTY 100 Index Constituents",
                "tags": ["nifty", "large-cap", "equity"]
            }
        ]
        
        for url_data in sample_urls:
            success, message = manager.add_url(**url_data)
            print(f"Add URL: {success} - {message}")
        
        # Get statistics
        stats = manager.get_statistics()
        print(f"\nStatistics: {stats}")
        
        # List all URLs
        urls = manager.get_all_urls()
        print(f"\nTotal URLs: {len(urls)}")
        for url in urls:
            print(f"- {url['index_name']}: {url['url']}")
        
    finally:
        manager.close_connection()

if __name__ == "__main__":
    main()
