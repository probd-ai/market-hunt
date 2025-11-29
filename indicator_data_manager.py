#!/usr/bin/env python3
"""
Indicator Data Management System for Market Hunt
Handles pre-calculation, storage, and retrieval of technical indicators
"""

import asyncio
import pymongo
from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IndicatorCalculationJob:
    """Data class for tracking indicator calculation jobs"""
    job_id: str
    indicator_type: str
    symbol: str
    base_symbol: str
    parameters: Dict[str, Any]
    status: str  # 'pending', 'running', 'completed', 'failed'
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    total_points: Optional[int] = None

class IndicatorDataManager:
    """
    Manages pre-calculated indicator data storage and retrieval
    """
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017", database_name: str = "market_hunt"):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client = None
        self.db = None
        
        # Collection names
        self.indicators_collection = "indicators"
        self.jobs_collection = "indicator_jobs"
        self.metadata_collection = "indicator_metadata"
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """Establish database connection"""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Create indexes for performance
            await self._create_indexes()
            
            logger.info(f"✅ Connected to MongoDB: {self.database_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            # Indicators collection indexes
            indicators_coll = self.db[self.indicators_collection]
            indicators_coll.create_index([
                ("symbol", 1),
                ("indicator_type", 1),
                ("base_symbol", 1),
                ("date", 1)
            ], unique=True)
            
            indicators_coll.create_index([("symbol", 1), ("indicator_type", 1)])
            indicators_coll.create_index([("date", 1)])
            
            # Jobs collection indexes
            jobs_coll = self.db[self.jobs_collection]
            jobs_coll.create_index([("job_id", 1)], unique=True)
            jobs_coll.create_index([("status", 1)])
            jobs_coll.create_index([("created_at", 1)])
            
            # Metadata collection indexes
            metadata_coll = self.db[self.metadata_collection]
            metadata_coll.create_index([
                ("symbol", 1),
                ("indicator_type", 1),
                ("base_symbol", 1)
            ], unique=True)
            
            logger.info("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
    
    async def store_indicator_data(self, symbol: str, indicator_type: str, base_symbol: str, 
                                 data: List[Dict], parameters: Dict[str, Any]) -> bool:
        """
        Store calculated indicator data in MongoDB
        
        Args:
            symbol: Stock symbol
            indicator_type: Type of indicator (e.g., 'truevx')
            base_symbol: Base symbol for comparison
            data: List of indicator data points
            parameters: Calculation parameters used
            
        Returns:
            bool: Success status
        """
        try:
            indicators_coll = self.db[self.indicators_collection]
            metadata_coll = self.db[self.metadata_collection]
            
            # Prepare documents for bulk insert
            documents = []
            for point in data:
                doc = {
                    "symbol": symbol,
                    "indicator_type": indicator_type,
                    "base_symbol": base_symbol,
                    "date": datetime.strptime(point["date"], "%Y-%m-%d"),
                    "data": point,
                    "parameters": parameters,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                documents.append(doc)
            
            # Delete existing data for this combination
            await self._delete_existing_data(symbol, indicator_type, base_symbol)
            
            # Insert new data
            if documents:
                result = indicators_coll.insert_many(documents)
                logger.info(f"✅ Stored {len(result.inserted_ids)} indicator points for {symbol}")
            
            # Update metadata
            metadata = {
                "symbol": symbol,
                "indicator_type": indicator_type,
                "base_symbol": base_symbol,
                "parameters": parameters,
                "total_points": len(data),
                "date_range": {
                    "start": data[0]["date"] if data else None,
                    "end": data[-1]["date"] if data else None
                },
                "last_updated": datetime.now(),
                "status": "completed"
            }
            
            metadata_coll.replace_one(
                {
                    "symbol": symbol,
                    "indicator_type": indicator_type,
                    "base_symbol": base_symbol
                },
                metadata,
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store indicator data for {symbol}: {e}")
            return False
    
    async def _delete_existing_data(self, symbol: str, indicator_type: str, base_symbol: str):
        """Delete existing indicator data"""
        indicators_coll = self.db[self.indicators_collection]
        result = indicators_coll.delete_many({
            "symbol": symbol,
            "indicator_type": indicator_type,
            "base_symbol": base_symbol
        })
        if result.deleted_count > 0:
            logger.info(f"🗑️  Deleted {result.deleted_count} existing records for {symbol}")
    
    async def get_indicator_data(self, symbol: str, indicator_type: str, base_symbol: str,
                               start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        Retrieve stored indicator data
        
        Args:
            symbol: Stock symbol
            indicator_type: Type of indicator
            base_symbol: Base symbol for comparison
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            List of indicator data points
        """
        try:
            indicators_coll = self.db[self.indicators_collection]
            
            # Build query
            query = {
                "symbol": symbol,
                "indicator_type": indicator_type,
                "base_symbol": base_symbol
            }
            
            # Add date range filter if provided
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = datetime.strptime(start_date, "%Y-%m-%d")
                if end_date:
                    date_filter["$lte"] = datetime.strptime(end_date, "%Y-%m-%d")
                query["date"] = date_filter
            
            # Retrieve data
            cursor = indicators_coll.find(query).sort("date", 1)
            results = []
            
            for doc in cursor:
                results.append(doc["data"])
            
            logger.info(f"📊 Retrieved {len(results)} indicator points for {symbol}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve indicator data for {symbol}: {e}")
            return []
    
    async def count_indicator_data(self, symbol: str, indicator_type: str, base_symbol: str) -> int:
        """
        Count the number of indicator data records for a symbol efficiently
        
        Args:
            symbol: Stock symbol
            indicator_type: Type of indicator
            base_symbol: Base symbol used for calculation
            
        Returns:
            Count of records
        """
        try:
            query = {
                "symbol": symbol,
                "indicator_type": indicator_type,
                "base_symbol": base_symbol
            }
            
            count = await self.indicator_data_collection.count_documents(query)
            return count
            
        except Exception as e:
            logger.error(f"❌ Failed to count indicator data for {symbol}: {e}")
            return 0
    
    async def get_available_indicators(self) -> List[Dict]:
        """
        Get list of all available pre-calculated indicators with latest values
        
        Returns:
            List of indicator metadata with latest indicator values
        """
        try:
            metadata_coll = self.db[self.metadata_collection]
            indicators_coll = self.db[self.indicators_collection]
            
            cursor = metadata_coll.find({}).sort([
                ("symbol", 1),
                ("indicator_type", 1),
                ("base_symbol", 1)
            ])
            
            results = []
            for doc in cursor:
                # Convert ObjectId to string and datetime to string
                doc["_id"] = str(doc["_id"])
                if "last_updated" in doc:
                    doc["last_updated"] = doc["last_updated"].isoformat()
                if "date_range" in doc:
                    if doc["date_range"]["start"]:
                        doc["date_range"]["start"] = doc["date_range"]["start"]
                    if doc["date_range"]["end"]:
                        doc["date_range"]["end"] = doc["date_range"]["end"]
                
                # Get latest indicator values
                latest_data = indicators_coll.find_one(
                    {
                        "symbol": doc["symbol"],
                        "indicator_type": doc["indicator_type"],
                        "base_symbol": doc["base_symbol"]
                    },
                    sort=[("date", -1)]  # Get most recent data point
                )
                
                if latest_data and "data" in latest_data:
                    latest_values = latest_data["data"]
                    doc["latest_values"] = {
                        "date": latest_values.get("date"),
                        "truevx_score": latest_values.get("truevx_score"),
                        "mean_short": latest_values.get("mean_short"),
                        "mean_mid": latest_values.get("mean_mid"),
                        "mean_long": latest_values.get("mean_long"),
                        "structural_score": latest_values.get("structural_score"),
                        "trend_score": latest_values.get("trend_score")
                    }
                
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to get available indicators: {e}")
            return []
    
    async def create_calculation_job(self, job: IndicatorCalculationJob) -> bool:
        """Create a new calculation job"""
        try:
            jobs_coll = self.db[self.jobs_collection]
            
            job_doc = {
                "job_id": job.job_id,
                "indicator_type": job.indicator_type,
                "symbol": job.symbol,
                "base_symbol": job.base_symbol,
                "parameters": job.parameters,
                "status": job.status,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
                "total_points": job.total_points
            }
            
            jobs_coll.insert_one(job_doc)
            logger.info(f"✅ Created calculation job: {job.job_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create calculation job: {e}")
            return False
    
    async def update_job_status(self, job_id: str, status: str, **updates) -> bool:
        """Update job status and other fields"""
        try:
            jobs_coll = self.db[self.jobs_collection]
            
            update_doc = {"status": status}
            update_doc.update(updates)
            
            result = jobs_coll.update_one(
                {"job_id": job_id},
                {"$set": update_doc}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to update job status: {e}")
            return False
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status and details"""
        try:
            jobs_coll = self.db[self.jobs_collection]
            job = jobs_coll.find_one({"job_id": job_id})
            
            if job:
                # Convert ObjectId and datetime fields
                job["_id"] = str(job["_id"])
                for date_field in ["created_at", "started_at", "completed_at"]:
                    if job.get(date_field):
                        job[date_field] = job[date_field].isoformat()
            
            return job
            
        except Exception as e:
            logger.error(f"❌ Failed to get job status: {e}")
            return None
    
    async def get_recent_jobs(self, limit: int = 50) -> List[Dict]:
        """Get recent calculation jobs"""
        try:
            jobs_coll = self.db[self.jobs_collection]
            
            cursor = jobs_coll.find({}).sort("created_at", -1).limit(limit)
            results = []
            
            for job in cursor:
                job["_id"] = str(job["_id"])
                for date_field in ["created_at", "started_at", "completed_at"]:
                    if job.get(date_field):
                        job[date_field] = job[date_field].isoformat()
                results.append(job)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent jobs: {e}")
            return []

# Usage example and testing
if __name__ == "__main__":
    async def test_indicator_data_manager():
        async with IndicatorDataManager() as manager:
            # Test storing sample data
            sample_data = [
                {
                    "date": "2024-01-01",
                    "truevx_score": 50.0,
                    "mean_short": 48.5,
                    "mean_mid": 49.2,
                    "mean_long": 50.8,
                    "indicator": "truevx_ranking"
                }
            ]
            
            await manager.store_indicator_data(
                symbol="TEST",
                indicator_type="truevx",
                base_symbol="Nifty 50",
                data=sample_data,
                parameters={"s1": 22, "m2": 66, "l3": 222}
            )
            
            # Test retrieving data
            retrieved = await manager.get_indicator_data(
                symbol="TEST",
                indicator_type="truevx",
                base_symbol="Nifty 50"
            )
            
            print(f"Retrieved {len(retrieved)} data points")
    
    # Run test
    asyncio.run(test_indicator_data_manager())
