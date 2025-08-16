#!/usr/bin/env python3
"""
Stock Data Manager - Handles stock price data with 5-year partitioning

Manages historical price data storage and retrieval with MongoDB collections
partitioned by 5-year periods for horizontal scalability and performance.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, BulkWriteError
from pymongo.operations import ReplaceOne
import motor.motor_asyncio
from bson import ObjectId

from nse_data_client import NSEDataClient, PriceData, SymbolMapping

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockDataManager:
    """
    Manages stock price data with 5-year partitioning for scalability
    """
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", database_name: str = "market_hunt"):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client = None
        self.db = None
        self.nse_client = None
        
        # Collection naming pattern: prices_YYYY_YYYY (5-year partitions)
        self.partition_years = 5
        
    async def __aenter__(self):
        """Async context manager entry"""
        # MongoDB async client
        self.client = motor.motor_asyncio.AsyncIOMotorClient(self.connection_string)
        self.db = self.client[self.database_name]
        
        # NSE client
        self.nse_client = NSEDataClient()
        await self.nse_client.__aenter__()
        
        # Initialize collections and indexes
        await self._initialize_collections()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.nse_client:
            await self.nse_client.__aexit__(exc_type, exc_val, exc_tb)
        if self.client:
            self.client.close()
    
    async def _initialize_collections(self):
        """Initialize MongoDB collections and indexes"""
        logger.info("🔧 Initializing stock data collections and indexes...")
        
        # Create symbol mappings collection with indexes
        symbol_mappings = self.db.symbol_mappings
        await symbol_mappings.create_index([("symbol", ASCENDING)], unique=True)
        await symbol_mappings.create_index([("nse_scrip_code", ASCENDING)])
        await symbol_mappings.create_index([("index_name", ASCENDING)])
        await symbol_mappings.create_index([("industry", ASCENDING)])
        
        # Create stock metadata collection
        stock_metadata = self.db.stock_metadata
        await stock_metadata.create_index([("symbol", ASCENDING)], unique=True)
        await stock_metadata.create_index([("nse_scrip_code", ASCENDING)], unique=True)
        await stock_metadata.create_index([("last_updated", DESCENDING)])
        
        # Create data processing logs collection
        processing_logs = self.db.data_processing_logs
        await processing_logs.create_index([("timestamp", DESCENDING)])
        await processing_logs.create_index([("status", ASCENDING)])
        await processing_logs.create_index([("symbol", ASCENDING)])
        
        logger.info("✅ Collections and indexes initialized")
    
    def _get_partition_collection_name(self, year: int) -> str:
        """Get collection name for a given year's partition"""
        # 5-year partitions: 2005-2009, 2010-2014, 2015-2019, 2020-2024, 2025-2029, etc.
        start_year = (year // self.partition_years) * self.partition_years
        # Adjust for partitioning starting from 2005
        if start_year < 2005:
            start_year = 2005
        end_year = start_year + self.partition_years - 1
        
        return f"prices_{start_year}_{end_year}"
    
    async def _get_price_collection(self, year: int) -> Collection:
        """Get price collection for a specific year"""
        collection_name = self._get_partition_collection_name(year)
        collection = self.db[collection_name]
        
        # Create indexes if collection is new
        try:
            await collection.create_index([("scrip_code", ASCENDING), ("date", ASCENDING)], unique=True)
            await collection.create_index([("symbol", ASCENDING), ("date", DESCENDING)])
            await collection.create_index([("date", DESCENDING)])
            await collection.create_index([("year_partition", ASCENDING)])
        except Exception as e:
            # Indexes might already exist
            pass
        
        return collection
    
    async def get_all_price_collections(self) -> List[str]:
        """Get all existing price collection names"""
        collections = await self.db.list_collection_names()
        price_collections = [c for c in collections if c.startswith("prices_")]
        return sorted(price_collections)
    
    async def store_symbol_mappings(self, mappings: List[SymbolMapping]) -> Dict[str, int]:
        """Store symbol mappings in the database, preserving existing status fields"""
        logger.info(f"💾 Storing {len(mappings)} symbol mappings...")
        
        collection = self.db.symbol_mappings
        results = {"inserted": 0, "updated": 0, "errors": 0}
        
        for mapping in mappings:
            try:
                # Get existing document to preserve status fields
                existing_doc = await collection.find_one({"_id": mapping.symbol})
                
                mapping_doc = asdict(mapping)
                mapping_doc['_id'] = mapping.symbol  # Use symbol as primary key
                
                # Preserve existing status fields if they exist
                if existing_doc:
                    status_fields = [
                        'is_up_to_date', 'data_quality_score', 'last_status_check', 
                        'last_data_update'
                    ]
                    for field in status_fields:
                        if field in existing_doc and existing_doc[field] is not None:
                            mapping_doc[field] = existing_doc[field]
                            mapping_doc[field] = existing_doc[field]
                
                await collection.replace_one(
                    {"_id": mapping.symbol},
                    mapping_doc,
                    upsert=True
                )
                
                if existing_doc:
                    results["updated"] += 1
                else:
                    results["inserted"] += 1
                
            except Exception as e:
                logger.error(f"❌ Error storing mapping for {mapping.symbol}: {e}")
                results["errors"] += 1
        
        logger.info(f"✅ Symbol mappings stored: {results}")
        return results
    
    async def get_symbol_mappings(
        self, 
        symbols: List[str] = None, 
        index_name: str = None,
        industry: str = None,
        symbol_search: str = None,
        mapped_only: bool = False
    ) -> List[SymbolMapping]:
        """Retrieve symbol mappings with optional filters"""
        collection = self.db.symbol_mappings
        
        # Build query
        query = {}
        if symbols:
            query["symbol"] = {"$in": symbols}
        if index_name:
            query["index_names"] = index_name  # Search in array field
        if industry:
            query["industry"] = industry
        if symbol_search:
            # Case-insensitive search in symbol or company_name
            query["$or"] = [
                {"symbol": {"$regex": symbol_search, "$options": "i"}},
                {"company_name": {"$regex": symbol_search, "$options": "i"}}
            ]
        if mapped_only:
            query["nse_scrip_code"] = {"$ne": None}
        
        cursor = collection.find(query)
        documents = await cursor.to_list(length=None)
        
        # Convert to SymbolMapping objects
        mappings = []
        for doc in documents:
            doc.pop('_id', None)  # Remove MongoDB _id
            # Handle backward compatibility for old records
            if 'index_name' in doc and 'index_names' not in doc:
                doc['index_names'] = [doc.pop('index_name')]
            mappings.append(SymbolMapping(**doc))
        
        return mappings
    
    async def store_price_data(self, price_data: List[PriceData]) -> Dict[str, int]:
        """Store price data with automatic partitioning"""
        if not price_data:
            return {"inserted": 0, "updated": 0, "errors": 0}
        
        logger.info(f"💾 Storing {len(price_data)} price records...")
        
        # Group data by year for partitioning
        partitioned_data = {}
        for record in price_data:
            year = record.year_partition
            if year not in partitioned_data:
                partitioned_data[year] = []
            partitioned_data[year].append(record)
        
        total_results = {"inserted": 0, "updated": 0, "errors": 0}
        
        # Store data in appropriate partitions
        for year, records in partitioned_data.items():
            collection = await self._get_price_collection(year)
            
            # Prepare documents
            documents = []
            for record in records:
                doc = asdict(record)
                # Create unique identifier
                doc['_id'] = f"{record.scrip_code}_{record.date.strftime('%Y%m%d')}"
                documents.append(doc)
            
            # Bulk upsert with better counting
            try:
                # First, check which records already exist
                existing_ids = set()
                if documents:
                    doc_ids = [doc["_id"] for doc in documents]
                    cursor = collection.find({"_id": {"$in": doc_ids}}, {"_id": 1})
                    existing_ids = {doc["_id"] async for doc in cursor}
                
                operations = []
                for doc in documents:
                    operations.append(
                        ReplaceOne(
                            {"_id": doc["_id"]},
                            doc,
                            upsert=True
                        )
                    )
                
                if operations:
                    result = await collection.bulk_write(operations, ordered=False)
                    
                    # Count actual new records (upserted)
                    actual_inserted = result.upserted_count
                    
                    # Count actual updates (only count if record existed before)
                    total_processed = len(documents)
                    existing_count = len(existing_ids)
                    actual_updated = min(result.modified_count, existing_count)
                    
                    total_results["inserted"] += actual_inserted
                    total_results["updated"] += actual_updated
                    
                    logger.info(f"✅ Stored {total_processed} records in partition {year} (New: {actual_inserted}, Updated: {actual_updated}, Existing: {existing_count})")
                    
            except BulkWriteError as e:
                logger.error(f"❌ Bulk write error for year {year}: {e}")
                total_results["errors"] += len(e.details.get("writeErrors", []))
            except Exception as e:
                logger.error(f"❌ Error storing price data for year {year}: {e}")
                total_results["errors"] += len(documents)
        
        logger.info(f"✅ Price data storage complete: {total_results}")
        return total_results
    
    async def get_price_data(
        self,
        symbol: str = None,
        scrip_code: int = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = None
    ) -> List[PriceData]:
        """Retrieve price data with filters"""
        if not symbol and not scrip_code:
            raise ValueError("Either symbol or scrip_code must be provided")
        
        # Build query
        query = {}
        if symbol:
            query["symbol"] = symbol
        if scrip_code:
            query["scrip_code"] = scrip_code
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["date"] = date_query
        
        # Determine which partitions to query
        if start_date and end_date:
            start_year = start_date.year
            end_year = end_date.year
        elif start_date:
            start_year = start_date.year
            end_year = datetime.now().year
        elif end_date:
            start_year = 2005  # Our earliest data
            end_year = end_date.year
        else:
            # Query all partitions
            collections = await self.get_all_price_collections()
            start_year = 2005
            end_year = datetime.now().year
        
        # Query relevant partitions
        all_records = []
        
        # Get unique partition names to avoid querying same partition multiple times
        if start_date and end_date:
            # Get partitions that cover the date range
            partition_names = set()
            for year in range(start_date.year, end_date.year + 1):
                partition_name = self._get_partition_collection_name(year)
                partition_names.add(partition_name)
        else:
            # Query all partitions
            partition_names = set(await self.get_all_price_collections())
        
        # Query each unique partition once
        for partition_name in sorted(partition_names):
            try:
                collection = self.db[partition_name]
                
                cursor = collection.find(query).sort("date", DESCENDING)
                if limit and len(all_records) >= limit:
                    break
                    
                if limit:
                    remaining = limit - len(all_records)
                    if remaining > 0:
                        cursor = cursor.limit(remaining)
                    else:
                        break
                
                documents = await cursor.to_list(length=None)
                
                # Convert to PriceData objects
                for doc in documents:
                    doc.pop('_id', None)
                    all_records.append(PriceData(**doc))
                    
            except Exception as e:
                logger.warning(f"⚠️ Error querying partition {partition_name}: {e}")
                continue
        
        # Sort by date (most recent first) and apply limit
        all_records.sort(key=lambda x: x.date, reverse=True)
        if limit:
            all_records = all_records[:limit]
        
        return all_records
    
    async def refresh_symbol_mappings_from_index_meta(self) -> Dict[str, int]:
        """Refresh symbol mappings by fetching data from index_meta collection"""
        logger.info("🔄 Refreshing symbol mappings from index_meta...")
        
        # Fetch symbols from index_meta
        index_meta_collection = self.db.index_meta
        cursor = index_meta_collection.find({}, {
            "Company Name": 1,
            "Symbol": 1, 
            "Industry": 1,
            "index_name": 1
        })
        
        symbols = await cursor.to_list(length=None)
        logger.info(f"📋 Found {len(symbols)} symbols in index_meta")
        
        # Fetch NSE masters
        masters = await self.nse_client.fetch_equity_masters()
        
        # Create mappings
        mappings = self.nse_client.match_symbols_with_masters(symbols, masters)
        
        # Store mappings
        result = await self.store_symbol_mappings(mappings)
        
        return result
    
    async def _get_earliest_missing_year(self, symbol: str) -> int:
        """Find the earliest year with missing data for smart loading"""
        try:
            # Start from 2005 (our earliest data year)
            current_year = datetime.now().year
            
            for year in range(2005, current_year + 1):
                # Check if we have any data for this year
                year_start = datetime(year, 1, 1)
                year_end = datetime(year, 12, 31)
                
                existing_data = await self.get_price_data(
                    symbol=symbol,
                    start_date=year_start,
                    end_date=year_end,
                    limit=1  # Just check if any data exists
                )
                
                if not existing_data:
                    # Found the first year with no data
                    logger.info(f"📊 Earliest missing year for {symbol}: {year}")
                    return year
            
            # If we reach here, all years have some data, check for gaps in current year
            logger.info(f"📊 All years have data for {symbol}, checking current year gaps")
            return current_year
            
        except Exception as e:
            logger.error(f"Error finding earliest missing year for {symbol}: {e}")
            return 2005  # Default fallback
    
    async def _delete_symbol_data(self, symbol: str, start_date: datetime, end_date: datetime):
        """Delete existing data for a symbol in the given date range"""
        try:
            # Get year range for partitioned collections
            start_year = start_date.year
            end_year = end_date.year
            
            deleted_count = 0
            
            for year in range(start_year, end_year + 1):
                collection_name = self._get_partition_collection_name(year)
                collection = self.db[collection_name]
                
                # Delete data for this symbol in this year
                result = await collection.delete_many({
                    "symbol": symbol,
                    "date": {
                        "$gte": datetime(year, 1, 1),
                        "$lte": datetime(year, 12, 31)
                    }
                })
                
                deleted_count += result.deleted_count
                
            logger.info(f"🗑️ Deleted {deleted_count} existing records for {symbol}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting data for {symbol}: {e}")
            return 0
    
    async def download_historical_data_for_symbol(
        self,
        symbol: str,
        start_date: datetime = None,
        end_date: datetime = None,
        force_refresh: bool = False,
        smart_load: bool = False
    ) -> Dict[str, Any]:
        """Download historical data for a single symbol"""
        
        processing_start_time = datetime.now()
        
        # Get symbol mapping
        mappings = await self.get_symbol_mappings([symbol], mapped_only=True)
        if not mappings:
            return {"error": f"No NSE mapping found for symbol {symbol}"}
        
        mapping = mappings[0]
        scrip_code = mapping.nse_scrip_code
        
        logger.info(f"📈 Downloading historical data for {symbol} (scrip: {scrip_code})")
        
        # Handle smart_load: find earliest missing year and start from there
        if smart_load:
            earliest_missing_year = await self._get_earliest_missing_year(symbol)
            smart_start_date = datetime(earliest_missing_year, 1, 1)
            
            if smart_start_date > start_date:
                start_date = smart_start_date
                logger.info(f"🎯 Smart load: Starting from earliest missing year {earliest_missing_year}")
        
        # Set default date range if not provided
        if not start_date:
            start_date = datetime(2005, 1, 1)
        if not end_date:
            end_date = datetime.now()
        
        # For refresh mode: delete existing data first
        if force_refresh:
            logger.info(f"🔄 Refresh mode: Deleting existing data for {symbol}")
            await self._delete_symbol_data(symbol, start_date, end_date)
        
        # Check if we already have recent data (unless force refresh)
        elif not force_refresh:
            # For sync mode, check for gaps in the requested range
            existing_data = await self.get_price_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=None  # Get all data to check for gaps
            )
            
            if existing_data:
                # Check if we have complete data using intelligent gap detection
                existing_dates = {record.date.date() for record in existing_data}
                
                # Use existing data coverage to determine if we have comprehensive data
                # If we have good coverage (>95%), trust that we have complete data
                business_days = self._generate_business_days(start_date, end_date)
                coverage_ratio = len(existing_dates) / len(business_days) if business_days else 0
                
                # Indian stock market typically has ~85-90% of business days as trading days
                # If we have >95% of business days, consider data complete
                if coverage_ratio >= 0.85:
                    logger.info(f"✅ Comprehensive data exists for {symbol} ({coverage_ratio:.2%} coverage)")
                    return {
                        "message": f"Comprehensive data exists for {symbol} ({coverage_ratio:.2%} coverage)", 
                        "date_range": f"{start_date.date()} to {end_date.date()}",
                        "total_records": len(existing_data)
                    }
                else:
                    # Low coverage, need to download more data
                    logger.info(f"📊 Low coverage ({coverage_ratio:.2%}) for {symbol}, proceeding with download")
            else:
                logger.info(f"📊 No existing data for {symbol}, downloading full range")
        
        # Download from NSE
        historical_data = await self.nse_client.fetch_historical_data(
            scrip_code=scrip_code,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if not historical_data:
            return {"error": f"No historical data fetched for {symbol}"}
        
        # Store in database
        storage_result = await self.store_price_data(historical_data)
        
        # Update metadata
        await self._update_stock_metadata(symbol, scrip_code, len(historical_data))
        
        # Log processing
        await self._log_processing_activity(
            symbol=symbol,
            scrip_code=scrip_code,
            status="success",
            records_processed=len(historical_data),
            start_date=start_date,
            end_date=end_date
        )
        
        
        processing_time = (datetime.now() - processing_start_time).total_seconds()
        
        # Calculate skipped records correctly
        records_fetched = len(historical_data)
        records_added = storage_result.get("inserted", 0)
        records_updated = storage_result.get("updated", 0)
        records_errors = storage_result.get("errors", 0)
        records_skipped = records_fetched - records_added - records_updated - records_errors
        
        return {
            "symbol": symbol,
            "scrip_code": scrip_code,
            "records_fetched": records_fetched,
            "records_added": records_added,
            "records_updated": records_updated,
            "records_skipped": records_skipped,
            "records_errors": records_errors,
            "total_records": records_added + records_updated,
            "storage_result": storage_result,
            "start_date": start_date.date().isoformat() if start_date else None,
            "end_date": end_date.date().isoformat() if end_date else None,
            "processing_time": f"{processing_time:.2f}s"
        }
    
    async def download_historical_data_for_index(
        self,
        index_name: str,
        start_date: datetime = None,
        end_date: datetime = None,
        force_refresh: bool = False,
        smart_load: bool = False
    ) -> Dict[str, Any]:
        """Download historical data for all symbols in an index"""
        
        logger.info(f"📊 Downloading historical data for index: {index_name}")
        
        # Get all symbols for the index
        mappings = await self.get_symbol_mappings(index_name=index_name, mapped_only=True)
        
        if not mappings:
            return {"error": f"No mapped symbols found for index {index_name}"}
        
        results = []
        errors = []
        
        for mapping in mappings:
            try:
                result = await self.download_historical_data_for_symbol(
                    symbol=mapping.symbol,
                    start_date=start_date,
                    end_date=end_date,
                    force_refresh=force_refresh,
                    smart_load=smart_load
                )
                results.append(result)
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                error_msg = f"Error downloading data for {mapping.symbol}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
        
        return {
            "index_name": index_name,
            "total_symbols": len(mappings),
            "successful_downloads": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors
        }
    
    async def download_historical_data_for_industry(
        self,
        industry_name: str,
        start_date: datetime = None,
        end_date: datetime = None,
        force_refresh: bool = False,
        smart_load: bool = False
    ) -> Dict[str, Any]:
        """Download historical data for all symbols in an industry"""
        
        logger.info(f"🏭 Downloading historical data for industry: {industry_name}")
        
        # Get all symbols for the industry
        mappings = await self.get_symbol_mappings(industry=industry_name, mapped_only=True)
        
        if not mappings:
            return {"error": f"No mapped symbols found for industry {industry_name}"}
        
        results = []
        errors = []
        
        for mapping in mappings:
            try:
                result = await self.download_historical_data_for_symbol(
                    symbol=mapping.symbol,
                    start_date=start_date,
                    end_date=end_date,
                    force_refresh=force_refresh,
                    smart_load=smart_load
                )
                results.append(result)
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                error_msg = f"Error downloading data for {mapping.symbol}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
        
        return {
            "industry_name": industry_name,
            "total_symbols": len(mappings),
            "successful_downloads": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors
        }
    
    async def _update_stock_metadata(self, symbol: str, scrip_code: int, records_count: int):
        """Update stock metadata after data download"""
        collection = self.db.stock_metadata
        
        metadata = {
            "symbol": symbol,
            "nse_scrip_code": scrip_code,
            "last_updated": datetime.now(),
            "total_records": records_count,
            "last_download_status": "success"
        }
        
        await collection.replace_one(
            {"symbol": symbol},
            metadata,
            upsert=True
        )
    
    async def _log_processing_activity(
        self,
        symbol: str,
        scrip_code: int,
        status: str,
        records_processed: int = 0,
        start_date: datetime = None,
        end_date: datetime = None,
        error_message: str = None
    ):
        """Log data processing activity"""
        collection = self.db.data_processing_logs
        
        log_entry = {
            "timestamp": datetime.now(),
            "symbol": symbol,
            "scrip_code": scrip_code,
            "status": status,
            "records_processed": records_processed,
            "start_date": start_date,
            "end_date": end_date,
            "error_message": error_message
        }
        
        await collection.insert_one(log_entry)
    
    async def get_data_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored price data"""
        stats = {
            "collections": {},
            "total_records": 0,
            "symbols_with_data": set(),
            "date_range": {"earliest": None, "latest": None}
        }
        
        # Get all price collections
        collections = await self.get_all_price_collections()
        
        for collection_name in collections:
            collection = self.db[collection_name]
            
            # Count records
            count = await collection.count_documents({})
            stats["collections"][collection_name] = {"record_count": count}
            stats["total_records"] += count
            
            if count > 0:
                # Get symbols
                symbols = await collection.distinct("symbol")
                stats["symbols_with_data"].update(symbols)
                
                # Get date range
                earliest = await collection.find({}).sort("date", ASCENDING).limit(1).to_list(1)
                latest = await collection.find({}).sort("date", DESCENDING).limit(1).to_list(1)
                
                if earliest:
                    earliest_date = earliest[0]["date"]
                    if stats["date_range"]["earliest"] is None or earliest_date < stats["date_range"]["earliest"]:
                        stats["date_range"]["earliest"] = earliest_date
                
                if latest:
                    latest_date = latest[0]["date"]
                    if stats["date_range"]["latest"] is None or latest_date > stats["date_range"]["latest"]:
                        stats["date_range"]["latest"] = latest_date
        
        stats["unique_symbols_count"] = len(stats["symbols_with_data"])
        stats["symbols_with_data"] = list(stats["symbols_with_data"])  # Convert set to list for JSON serialization
        
        return stats

    async def get_index_symbols(self, index_name: str) -> List[str]:
        """Get all symbols for a given index"""
        try:
            mappings = await self.get_symbol_mappings()
            index_symbols = [
                mapping.symbol for mapping in mappings 
                if index_name in mapping.index_names
            ]
            return index_symbols
        except Exception as e:
            logger.error(f"Error getting index symbols for {index_name}: {e}")
            return []

    async def get_industry_symbols(self, industry_name: str) -> List[str]:
        """Get all symbols for a given industry"""
        try:
            mappings = await self.get_symbol_mappings()
            industry_symbols = [
                mapping.symbol for mapping in mappings 
                if mapping.industry == industry_name
            ]
            return industry_symbols
        except Exception as e:
            logger.error(f"Error getting industry symbols for {industry_name}: {e}")
            return []

    async def analyze_data_gaps(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        auto_download: bool = True,
        full_historical_analysis: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze data gaps for a symbol within a date range
        
        Args:
            symbol: Stock symbol to analyze
            start_date: Start date for analysis (ignored if full_historical_analysis=True)
            end_date: End date for analysis (ignored if full_historical_analysis=True)
            auto_download: Whether to attempt downloading missing data first
            full_historical_analysis: If True, discovers and analyzes the complete NSE historical range for this symbol
        
        Returns:
            Dict containing gap analysis with missing dates, total gaps, etc.
        """
        try:
            # For complete historical analysis, discover the full NSE range for this symbol
            if full_historical_analysis:
                logger.info(f"🔍 COMPLETE HISTORICAL ANALYSIS for {symbol}: Discovering full NSE range...")
                
                # Get symbol mapping
                mappings = await self.get_symbol_mappings([symbol], mapped_only=True)
                if not mappings:
                    return {"error": f"No NSE mapping found for symbol {symbol}"}
                
                mapping = mappings[0]
                scrip_code = mapping.nse_scrip_code
                
                # Discover the complete NSE historical range for this symbol
                # Start from a very early date and fetch recent data to determine actual range
                discovery_start = datetime(2000, 1, 1)  # Start early for discovery
                discovery_end = datetime.now()
                
                logger.info(f"📡 Fetching sample NSE data to discover {symbol}'s complete trading history...")
                
                try:
                    # Fetch a broad sample to determine actual NSE range
                    sample_data = await self.nse_client.fetch_historical_data(
                        scrip_code=scrip_code,
                        symbol=symbol,
                        start_date=discovery_start,
                        end_date=discovery_end
                    )
                    
                    if not sample_data:
                        return {
                            "total_expected_days": 0,
                            "total_actual_days": 0,
                            "total_missing_days": 0,
                            "gap_percentage": 0.0,
                            "has_data": False,
                            "message": f"No NSE historical data found for {symbol}",
                            "full_historical_analysis": True,
                            "nse_discovery_attempted": True
                        }
                    
                    # Determine the actual NSE historical range
                    nse_dates = [record.date.date() for record in sample_data]
                    nse_start_date = min(nse_dates)
                    nse_end_date = max(nse_dates)
                    
                    # Override analysis dates with discovered NSE range
                    start_date = datetime.combine(nse_start_date, datetime.min.time())
                    end_date = datetime.combine(nse_end_date, datetime.min.time())
                    
                    logger.info(f"✅ Discovered {symbol}'s complete NSE range: {nse_start_date} to {nse_end_date} ({len(sample_data)} sample records)")
                    logger.info(f"📊 Now analyzing gaps across {symbol}'s COMPLETE {(nse_end_date - nse_start_date).days} day history...")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to discover NSE range for {symbol}: {e}")
                    return {
                        "error": f"Failed to discover NSE historical range for {symbol}: {str(e)}",
                        "full_historical_analysis": True,
                        "nse_discovery_attempted": True
                    }
            # Get existing data for the symbol
            existing_data = await self.get_price_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=None  # Get all records
            )
            
            # Check if we have very little data and should download first
            total_expected_trading_days = self._estimate_trading_days(start_date, end_date)
            existing_count = len(existing_data) if existing_data else 0
            
            # If we have less than 10% of expected trading data, try to download first
            should_download = (
                auto_download and 
                (existing_count == 0 or existing_count < (total_expected_trading_days * 0.1))
            )
            
            if should_download:
                logger.info(f"Gap analysis for {symbol}: Only {existing_count} records exist out of {total_expected_trading_days} expected. Downloading data first...")
                
                # Attempt to download data for this symbol
                try:
                    download_result = await self.download_historical_data_for_symbol(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        force_refresh=False  # Don't refresh existing data, just fill gaps
                    )
                    
                    # Get data again after download
                    existing_data = await self.get_price_data(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        limit=None
                    )
                    logger.info(f"After download attempt: {len(existing_data) if existing_data else 0} records for {symbol}")
                    
                    # If download shows NSE API returned no data, symbol might not trade in this period
                    if isinstance(download_result, dict) and download_result.get("records_fetched", 0) == 0:
                        logger.info(f"NSE returned no data for {symbol} in period {start_date.date()} to {end_date.date()} - symbol may not have been trading")
                        # If no data was fetched from NSE, this symbol wasn't trading in this period
                        return {
                            "total_expected_days": 0,
                            "total_actual_days": 0,
                            "total_missing_days": 0,
                            "gap_percentage": 0.0,
                            "has_data": False,
                            "date_range": {
                                "start": start_date.date().isoformat(),
                                "end": end_date.date().isoformat()
                            },
                            "gaps": [],
                            "download_attempted": True,
                            "yearly_breakdown": [],
                            "message": f"Symbol {symbol} was not trading in the requested period {start_date.date()} to {end_date.date()}",
                            "nse_data_available": False
                        }
                    
                except Exception as download_error:
                    logger.warning(f"Failed to download data for {symbol}: {download_error}")
                    # Continue with gap analysis using existing data
            
            if not existing_data:
                # No data exists at all (even after download attempt)
                return {
                    "total_expected_days": 0,
                    "total_actual_days": 0,
                    "total_missing_days": 0,
                    "gap_percentage": 0.0,
                    "has_data": False,
                    "date_range": {
                        "start": start_date.date().isoformat(),
                        "end": end_date.date().isoformat()
                    },
                    "gaps": [],
                    "download_attempted": should_download,
                    "yearly_breakdown": [],
                    "message": f"No data available for {symbol} in the requested period. Symbol may not have been trading during this time.",
                    "actual_trading_period": None
                }
            
            # Convert to date set for easier processing
            existing_dates = {record.date.date() for record in existing_data}
            
            # Key Fix: Determine the actual NSE trading period for this symbol
            # We need to understand what period NSE actually has data for, not just what we have in DB
            logger.info(f"🔍 Determining actual NSE trading period for {symbol}...")
            
            # Try to get a broader range of data from NSE to understand the true trading period
            nse_data_check = await self._get_nse_trading_period(symbol, start_date, end_date)
            
            if nse_data_check and nse_data_check.get("has_data"):
                # Use NSE's actual trading period
                actual_start_date = nse_data_check["start_date"]
                actual_end_date = nse_data_check["end_date"]
                logger.info(f"📅 NSE trading period for {symbol}: {actual_start_date} to {actual_end_date}")
            else:
                # Fallback: use existing data range if NSE check fails
                if existing_dates:
                    actual_start_date = min(existing_dates)
                    actual_end_date = max(existing_dates)
                    logger.info(f"📅 Using existing data range for {symbol}: {actual_start_date} to {actual_end_date}")
                else:
                    # No data available anywhere
                    return {
                        "total_expected_days": 0,
                        "total_actual_days": 0,
                        "total_missing_days": 0,
                        "gap_percentage": 0.0,
                        "has_data": False,
                        "date_range": {
                            "start": start_date.date().isoformat(),
                            "end": end_date.date().isoformat()
                        },
                        "gaps": [],
                        "yearly_breakdown": [],
                        "message": f"No NSE data available for {symbol} in any period",
                        "actual_trading_period": None
                    }
            
            # Key Fix: Only analyze the period where the symbol actually has data
            # Don't try to analyze periods before the symbol started trading
            analysis_start = actual_start_date
            analysis_end = actual_end_date
            
            # If user requested a more recent period, respect that
            if start_date.date() > actual_start_date:
                analysis_start = start_date.date()
            if end_date.date() < actual_end_date:
                analysis_end = end_date.date()
            
            # If the adjusted period is invalid
            if analysis_start > analysis_end:
                return {
                    "total_expected_days": 0,
                    "total_actual_days": 0,
                    "total_missing_days": 0,
                    "gap_percentage": 0.0,
                    "has_data": True,
                    "date_range": {
                        "start": start_date.date().isoformat(),
                        "end": end_date.date().isoformat()
                    },
                    "actual_trading_period": {
                        "start": actual_start_date.isoformat(),
                        "end": actual_end_date.isoformat()
                    },
                    "gaps": [],
                    "yearly_breakdown": [],
                    "message": f"No overlap between requested period and actual trading period. Actual trading: {actual_start_date} to {actual_end_date}",
                    "calendar_method": "symbol_specific"
                }
            
            # Get real trading calendar only for the actual trading period
            logger.info(f"📅 Analyzing gaps for {symbol} from {analysis_start} to {analysis_end} (actual trading period)")
            
            # Strategy: Use the symbol's own data pattern to identify legitimate trading days
            # If we have substantial data coverage (>80%), trust the symbol's data pattern
            analysis_start_dt = datetime.combine(analysis_start, datetime.min.time())
            analysis_end_dt = datetime.combine(analysis_end, datetime.min.time())
            
            # Calculate expected trading days in the ACTUAL trading period only
            estimated_trading_days = self._estimate_trading_days(analysis_start_dt, analysis_end_dt)
            existing_count = len([d for d in existing_dates if analysis_start <= d <= analysis_end])
            coverage_ratio = existing_count / estimated_trading_days if estimated_trading_days > 0 else 0
            
            logger.info(f"📊 {symbol} has {existing_count} records out of {estimated_trading_days} estimated trading days ({coverage_ratio:.2%} coverage)")
            
            # If we have >95% of estimated trading days, consider data comprehensive
            if coverage_ratio >= 0.95:  
                # Use symbol's own data - we have comprehensive coverage
                real_trading_days = sorted(list(existing_dates))
                logger.info(f"📈 Using {symbol}'s own data pattern (excellent coverage: {coverage_ratio:.2%})")
                
                # For excellent coverage, report minimal gaps
                total_expected = len(real_trading_days)
                total_actual = len(existing_dates)
                total_missing = 0  # Consider data complete
                gap_percentage = 0.0
                missing_dates = []
                
            elif coverage_ratio >= 0.85:
                # Good coverage - use symbol's own data pattern
                real_trading_days = sorted(list(existing_dates))
                logger.info(f"📈 Using {symbol}'s own data pattern (good coverage: {coverage_ratio:.2%})")
                
                # Calculate minimal gaps for display only
                business_days = self._count_business_days(analysis_start_dt, analysis_end_dt)
                expected_trading_days = []
                current = analysis_start_dt
                while current.date() <= analysis_end:
                    if current.weekday() < 5:  # Monday = 0, Friday = 4
                        expected_trading_days.append(current.date())
                    current += timedelta(days=1)
                
                # Find actual missing dates (but these are likely holidays)
                missing_dates = [day for day in expected_trading_days if day not in existing_dates]
                total_expected = estimated_trading_days
                total_actual = len(existing_dates)
                total_missing = max(0, total_expected - total_actual)  # Use realistic expectation
                gap_percentage = (total_missing / total_expected * 100) if total_expected > 0 else 0
            else:
                # Low coverage - need more data, but still use realistic expectations
                logger.info(f"⚠️ Low coverage ({coverage_ratio:.2%}): Analyzing with estimated trading calendar")
                
                # Use estimated trading days as baseline
                total_expected = estimated_trading_days
                total_actual = existing_count
                total_missing = max(0, total_expected - total_actual)
                gap_percentage = (total_missing / total_expected * 100) if total_expected > 0 else 0
                missing_dates = []  # Don't calculate specific dates for low coverage
            
            # Group consecutive missing dates into gaps (only if we have missing dates)
            gaps = self._group_consecutive_dates(missing_dates) if missing_dates else []
            
            # Yearly breakdown
            yearly_breakdown = self._analyze_yearly_gaps(real_trading_days, existing_dates)
            
            logger.info(f"📊 Final gap analysis for {symbol}: {total_actual}/{total_expected} days ({gap_percentage:.2f}% gaps)")
            
            return {
                "total_expected_days": total_expected,
                "total_actual_days": total_actual,
                "total_missing_days": total_missing,
                "gap_percentage": round(gap_percentage, 2),
                "has_data": total_actual > 0,
                "date_range": {
                    "start": start_date.date().isoformat(),
                    "end": end_date.date().isoformat()
                },
                "actual_trading_period": {
                    "start": actual_start_date.isoformat(),
                    "end": actual_end_date.isoformat()
                },
                "analysis_period": {
                    "start": analysis_start.isoformat(),
                    "end": analysis_end.isoformat()
                },
                "gaps": [{"start": gap[0].isoformat(), "end": gap[-1].isoformat(), "days": len(gap)} for gap in gaps],
                "yearly_breakdown": yearly_breakdown,
                "calendar_method": "high_coverage_trust" if coverage_ratio >= 0.80 else "multi_symbol_reference",
                "coverage_ratio": round(coverage_ratio, 4),
                "calendar_symbols_analyzed": 1 if coverage_ratio >= 0.80 else len(await self._get_symbols_for_calendar_analysis(analysis_start_dt, analysis_end_dt)),
                "message": f"Trusted {symbol}'s data completeness (coverage: {coverage_ratio:.2%})" if coverage_ratio >= 0.80 else f"Low coverage analysis for {symbol}"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing gaps for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _get_nse_trading_period(self, symbol: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Check NSE to determine the actual trading period for a symbol
        This helps us understand when the symbol was actually available for trading
        """
        try:
            # Get symbol mapping
            mappings = await self.get_symbol_mappings([symbol], mapped_only=True)
            if not mappings:
                logger.warning(f"No NSE mapping found for {symbol}")
                return {"has_data": False}
            
            mapping = mappings[0]
            scrip_code = mapping.nse_scrip_code
            
            # Try to fetch a small sample of data to check availability
            # Start with the requested period, but extend if needed
            test_start = start_date
            test_end = end_date
            
            logger.info(f"🔍 Checking NSE data availability for {symbol} (scrip: {scrip_code})")
            
            # Try to fetch data for the requested period
            historical_data = await self.nse_client.fetch_historical_data(
                scrip_code=scrip_code,
                symbol=symbol,
                start_date=test_start,
                end_date=test_end
            )
            
            if not historical_data:
                # No data in requested period, symbol might not be trading in this period
                logger.info(f"No NSE data found for {symbol} in period {test_start.date()} to {test_end.date()}")
                return {"has_data": False}
            
            # Found data - determine the actual range
            nse_dates = [record.date.date() for record in historical_data]
            nse_start = min(nse_dates)
            nse_end = max(nse_dates)
            
            logger.info(f"📊 NSE has data for {symbol} from {nse_start} to {nse_end} ({len(historical_data)} records)")
            
            return {
                "has_data": True,
                "start_date": nse_start,
                "end_date": nse_end,
                "sample_records": len(historical_data)
            }
            
        except Exception as e:
            logger.error(f"Error checking NSE trading period for {symbol}: {e}")
            return {"has_data": False}

    def _count_business_days(self, start_date: datetime, end_date: datetime) -> int:
        """Count business days between two dates"""
        from datetime import timedelta
        current = start_date.date()
        end = end_date.date()
        count = 0
        while current <= end:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                count += 1
            current += timedelta(days=1)
        return count
    
    def _estimate_trading_days(self, start_date: datetime, end_date: datetime) -> int:
        """
        Estimate actual trading days for Indian stock market
        Indian market typically has ~15-20 holidays per year (85-90% of business days)
        """
        business_days = self._count_business_days(start_date, end_date)
        
        # Calculate years in the range
        years = (end_date.year - start_date.year) + 1
        
        # Estimate holidays: ~17 holidays per year on average
        estimated_holidays = years * 17
        
        # Trading days = business days - holidays
        estimated_trading_days = max(0, business_days - estimated_holidays)
        
        return estimated_trading_days
    
    async def _get_supplementary_trading_calendar(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        primary_symbol: str,
        primary_symbol_dates: set
    ) -> List[datetime.date]:
        """
        Get supplementary trading calendar from other symbols to enhance gap detection.
        Only includes dates that are business days and reasonable for the primary symbol.
        
        Args:
            start_date: Start date for calendar extraction
            end_date: End date for calendar extraction
            primary_symbol: The symbol we're analyzing
            primary_symbol_dates: Set of dates where primary symbol has data
            
        Returns:
            List of additional trading dates based on other symbols
        """
        try:
            # Get a few reliable symbols for calendar reference
            symbols_for_analysis = await self._get_symbols_for_calendar_analysis(start_date, end_date)
            
            if len(symbols_for_analysis) < 2:
                logger.warning("Insufficient symbols for supplementary calendar")
                return []
            
            # Use top 3 symbols (excluding primary symbol) for supplementary calendar
            reference_symbols = [s for s in symbols_for_analysis[:5] if s != primary_symbol][:3]
            
            if not reference_symbols:
                return []
            
            # Collect dates from reference symbols
            supplementary_dates = set()
            
            for symbol in reference_symbols:
                try:
                    symbol_data = await self.get_price_data(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        limit=None
                    )
                    
                    for record in symbol_data:
                        trading_date = record.date.date()
                        # Only include business days that fall within a reasonable range
                        if (trading_date.weekday() < 5 and 
                            start_date.date() <= trading_date <= end_date.date()):
                            supplementary_dates.add(trading_date)
                            
                except Exception as e:
                    logger.warning(f"Could not analyze {symbol} for supplementary calendar: {e}")
                    continue
            
            # Return only dates that are not already in primary symbol's data
            # These represent potential missing trading days
            additional_dates = [date for date in supplementary_dates if date not in primary_symbol_dates]
            
            logger.info(f"📊 Supplementary calendar: found {len(additional_dates)} additional potential trading days")
            
            return sorted(additional_dates)
            
        except Exception as e:
            logger.error(f"Error getting supplementary trading calendar: {e}")
            return []

    async def _get_real_trading_calendar(self, start_date: datetime, end_date: datetime, min_symbols: int = 5) -> List[datetime.date]:
        """
        Extract real trading calendar by analyzing actual trading data from multiple symbols.
        This is more accurate than guessing holidays.
        
        Args:
            start_date: Start date for calendar extraction
            end_date: End date for calendar extraction  
            min_symbols: Minimum number of symbols that must have data for a date to be considered a trading day
            
        Returns:
            List of actual trading dates based on real market data
        """
        try:
            logger.info(f"📅 Extracting real trading calendar from {start_date.date()} to {end_date.date()}")
            
            # Get symbols with good data coverage for analysis
            symbols_for_analysis = await self._get_symbols_for_calendar_analysis(start_date, end_date)
            
            if len(symbols_for_analysis) < min_symbols:
                logger.warning(f"Only {len(symbols_for_analysis)} symbols available for calendar analysis, using basic weekday calendar")
                return self._generate_business_days(start_date, end_date)
            
            # Count trading dates across all symbols
            date_counts = {}
            
            for symbol in symbols_for_analysis[:10]:  # Analyze top 10 symbols to avoid overload
                try:
                    symbol_data = await self.get_price_data(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        limit=None
                    )
                    
                    for record in symbol_data:
                        trading_date = record.date.date()
                        date_counts[trading_date] = date_counts.get(trading_date, 0) + 1
                        
                except Exception as e:
                    logger.warning(f"Could not analyze {symbol} for calendar: {e}")
                    continue
            
            # Filter dates that appear in at least min_symbols
            real_trading_dates = [
                date for date, count in date_counts.items() 
                if count >= min(min_symbols, len(symbols_for_analysis))
            ]
            
            real_trading_dates.sort()
            
            logger.info(f"📊 Extracted {len(real_trading_dates)} real trading dates from {len(symbols_for_analysis)} symbols")
            
            return real_trading_dates
            
        except Exception as e:
            logger.error(f"Error extracting real trading calendar: {e}")
            # Fallback to basic weekday calendar
            return self._generate_business_days(start_date, end_date)
    
    async def _get_symbols_for_calendar_analysis(self, start_date: datetime, end_date: datetime) -> List[str]:
        """Get symbols with good data coverage for trading calendar analysis"""
        try:
            # Use the data statistics to get actual symbols in our database
            stats = await self.get_data_statistics()
            available_symbols = stats.get('symbols_with_data', [])
            
            if not available_symbols:
                logger.error("No symbols found in database statistics - cannot perform data-driven calendar analysis")
                return []
            
            logger.info(f"Using {len(available_symbols)} actual symbols from database for calendar analysis")
            
            # Return up to 20 symbols for calendar analysis (enough for good accuracy)
            return available_symbols[:20]
            
        except Exception as e:
            logger.error(f"Error getting actual symbols from database: {e}")
            return []
            
            logger.info(f"Found {len(symbols_with_data)} symbols for trading calendar analysis")
            return symbols_with_data
            
        except Exception as e:
            logger.error(f"Error getting symbols for calendar analysis: {e}")
            return []

    def _generate_business_days(self, start_date: datetime, end_date: datetime) -> List[datetime.date]:
        """Generate list of business days between two dates (weekdays only)
        
        Note: This only excludes weekends. For accurate gap analysis, 
        Indian stock market holidays should be provided via configuration.
        """
        from datetime import timedelta
        business_days = []
        current = start_date.date()
        end = end_date.date()
        
        while current <= end:
            if current.weekday() < 5:  # Monday = 0, Friday = 4 (exclude weekends only)
                business_days.append(current)
            current += timedelta(days=1)
        return business_days
    
    def _group_consecutive_dates(self, dates: List[datetime.date]) -> List[List[datetime.date]]:
        """Group consecutive dates into gaps"""
        if not dates:
            return []
        
        dates = sorted(dates)
        gaps = []
        current_gap = [dates[0]]
        
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                current_gap.append(dates[i])
            else:
                gaps.append(current_gap)
                current_gap = [dates[i]]
        
        gaps.append(current_gap)
        return gaps
    
    def _analyze_yearly_gaps(self, business_days: List[datetime.date], existing_dates: set) -> List[Dict]:
        """Analyze gaps by year"""
        yearly_data = {}
        
        for day in business_days:
            year = day.year
            if year not in yearly_data:
                yearly_data[year] = {"expected": 0, "actual": 0}
            yearly_data[year]["expected"] += 1
            if day in existing_dates:
                yearly_data[year]["actual"] += 1
        
        yearly_breakdown = []
        for year, data in sorted(yearly_data.items()):
            missing = data["expected"] - data["actual"]
            percentage = (missing / data["expected"] * 100) if data["expected"] > 0 else 0
            yearly_breakdown.append({
                "year": year,
                "expected_days": data["expected"],
                "actual_days": data["actual"],
                "missing_days": missing,
                "gap_percentage": round(percentage, 2)
            })
        
        return yearly_breakdown

    async def update_symbol_status(self, symbol: str, is_up_to_date: bool = None, 
                                 data_quality_score: float = None, 
                                 force_update: bool = False) -> bool:
        """
        Update up-to-date status for a symbol in database
        
        Args:
            symbol: Stock symbol to update
            is_up_to_date: Whether symbol data is up-to-date (None to calculate)
            data_quality_score: Quality score 0-100 (None to calculate)
            force_update: Force update even if recently checked
            
        Returns:
            bool: True if update was successful
        """
        try:
            symbol_mappings_collection = self.db.symbol_mappings
            
            # Get current mapping
            current_mapping = await symbol_mappings_collection.find_one({"_id": symbol})
            if not current_mapping:
                logger.warning(f"Symbol {symbol} not found in mappings")
                return False
            
            # Check if we need to update (daily check or forced)
            now = datetime.now()
            last_check = current_mapping.get('last_status_check')
            
            if not force_update and last_check:
                # Skip if checked within last 24 hours
                if isinstance(last_check, str):
                    last_check = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                
                if (now - last_check.replace(tzinfo=None)).total_seconds() < 86400:  # 24 hours
                    return True
            
            # Calculate status if not provided
            if is_up_to_date is None or data_quality_score is None:
                try:
                    # Analyze recent 365 days (1 year) for comprehensive quality assessment
                    # This ensures we catch historical gaps, not just recent data
                    end_date = now
                    start_date = end_date - timedelta(days=365)
                    
                    gap_analysis = await self.analyze_data_gaps(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        auto_download=False
                    )
                    
                    # Calculate up-to-date status (stricter criteria for 1-year analysis)
                    if is_up_to_date is None:
                        gap_percentage = gap_analysis.get('gap_percentage', 100)
                        has_data = gap_analysis.get('has_data', False)
                        total_actual_days = gap_analysis.get('total_actual_days', 0)
                        # Stricter criteria: less than 10% gaps and at least 200 trading days
                        is_up_to_date = has_data and gap_percentage < 10 and total_actual_days > 200
                    
                    # Calculate data quality score (0-100)
                    if data_quality_score is None:
                        gap_percentage = gap_analysis.get('gap_percentage', 100)
                        has_data = gap_analysis.get('has_data', False)
                        
                        if not has_data:
                            data_quality_score = 0
                        else:
                            # Score based on completeness: 100 - gap_percentage
                            data_quality_score = max(0, 100 - gap_percentage)
                            
                except Exception as e:
                    logger.warning(f"Could not calculate status for {symbol}: {e}")
                    is_up_to_date = False if is_up_to_date is None else is_up_to_date
                    data_quality_score = 0 if data_quality_score is None else data_quality_score
            
            # Update the document
            update_data = {
                "is_up_to_date": is_up_to_date,
                "last_status_check": now,
                "data_quality_score": data_quality_score
            }
            
            result = await symbol_mappings_collection.update_one(
                {"_id": symbol},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated status for {symbol}: up_to_date={is_up_to_date}, quality={data_quality_score:.1f}")
                return True
            else:
                logger.warning(f"No update performed for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating symbol status for {symbol}: {e}")
            return False

    async def batch_update_symbol_status(self, symbols: List[str] = None, 
                                       force_update: bool = False) -> Dict[str, bool]:
        """
        Update status for multiple symbols (useful for daily batch updates)
        
        Args:
            symbols: List of symbols to update (None for all mapped symbols)
            force_update: Force update even if recently checked
            
        Returns:
            Dict[str, bool]: Results for each symbol {symbol: success}
        """
        try:
            if symbols is None:
                # Get all mapped symbols
                symbol_mappings_collection = self.db.symbol_mappings
                cursor = symbol_mappings_collection.find(
                    {"nse_scrip_code": {"$ne": None}},
                    {"_id": 1}
                )
                symbols = [doc["_id"] async for doc in cursor]
            
            results = {}
            total_symbols = len(symbols)
            
            logger.info(f"Starting batch status update for {total_symbols} symbols")
            
            for i, symbol in enumerate(symbols, 1):
                try:
                    success = await self.update_symbol_status(symbol, force_update=force_update)
                    results[symbol] = success
                    
                    if i % 10 == 0:  # Progress logging every 10 symbols
                        logger.info(f"Processed {i}/{total_symbols} symbols")
                        
                except Exception as e:
                    logger.error(f"Error updating status for {symbol}: {e}")
                    results[symbol] = False
            
            successful = sum(1 for success in results.values() if success)
            logger.info(f"Batch update completed: {successful}/{total_symbols} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch status update: {e}")
            return {}

async def test_stock_data_manager():
    """Test function for stock data manager"""
    async with StockDataManager() as manager:
        # Test 1: Refresh symbol mappings
        print("Testing symbol mappings refresh...")
        result = await manager.refresh_symbol_mappings_from_index_meta()
        print(f"Mapping result: {result}")
        
        # Test 2: Get some mappings
        mappings = await manager.get_symbol_mappings(mapped_only=True)
        print(f"Found {len(mappings)} mapped symbols")
        
        # Test 3: Download data for one symbol (if available)
        if mappings:
            test_symbol = mappings[0].symbol
            print(f"Testing download for symbol: {test_symbol}")
            
            download_result = await manager.download_historical_data_for_symbol(
                symbol=test_symbol,
                start_date=datetime.now() - timedelta(days=30)  # Last 30 days
            )
            print(f"Download result: {download_result}")
        
        # Test 4: Get statistics
        stats = await manager.get_data_statistics()
        print(f"Data statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(test_stock_data_manager())
