#!/usr/bin/env python3
"""
Migration script to add new status fields to existing symbol_mappings collection
"""

import asyncio
from datetime import datetime
from pymongo import MongoClient
import motor.motor_asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_symbol_mappings():
    """Add new status fields to existing symbol_mappings documents"""
    
    # Connect to MongoDB
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
    db = client.market_hunt
    collection = db.symbol_mappings
    
    try:
        logger.info("Starting migration of symbol_mappings collection...")
        
        # Get all documents that don't have the new fields
        query = {
            "$or": [
                {"is_up_to_date": {"$exists": False}},
                {"data_quality_score": {"$exists": False}},
                {"last_status_check": {"$exists": False}},
                {"last_data_update": {"$exists": False}}
            ]
        }
        
        cursor = collection.find(query)
        count = await collection.count_documents(query)
        
        logger.info(f"Found {count} documents to migrate")
        
        if count == 0:
            logger.info("No documents need migration")
            return
        
        updated_count = 0
        async for doc in cursor:
            symbol = doc.get("symbol", doc["_id"])
            
            # Set default values for new fields
            update_data = {}
            
            if "is_up_to_date" not in doc:
                update_data["is_up_to_date"] = None  # Will be calculated on first status check
            
            if "data_quality_score" not in doc:
                update_data["data_quality_score"] = None  # Will be calculated on first status check
            
            if "last_status_check" not in doc:
                update_data["last_status_check"] = None  # Never checked yet
            
            if "last_data_update" not in doc:
                update_data["last_data_update"] = None  # No data loaded yet
            
            if update_data:
                result = await collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": update_data}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    logger.info(f"Migrated {symbol}")
        
        logger.info(f"✅ Migration completed. Updated {updated_count} documents.")
        
        # Show sample of updated document
        sample = await collection.find_one({}, {"_id": 1, "symbol": 1, "is_up_to_date": 1, "data_quality_score": 1, "last_status_check": 1, "last_data_update": 1})
        if sample:
            logger.info(f"Sample migrated document: {sample}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(migrate_symbol_mappings())
