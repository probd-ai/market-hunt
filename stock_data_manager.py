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
        """Store symbol mappings in the database"""
        logger.info(f"💾 Storing {len(mappings)} symbol mappings...")
        
        collection = self.db.symbol_mappings
        results = {"inserted": 0, "updated": 0, "errors": 0}
        
        for mapping in mappings:
            try:
                mapping_doc = asdict(mapping)
                mapping_doc['_id'] = mapping.symbol  # Use symbol as primary key
                
                await collection.replace_one(
                    {"_id": mapping.symbol},
                    mapping_doc,
                    upsert=True
                )
                results["updated" if mapping.nse_scrip_code else "inserted"] += 1
                
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
            
            # Bulk upsert
            try:
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
                    total_results["inserted"] += result.upserted_count
                    total_results["updated"] += result.modified_count
                    
                    logger.info(f"✅ Stored {len(documents)} records in partition {year}")
                    
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
        for year in range(start_year, end_year + 1):
            try:
                collection = await self._get_price_collection(year)
                
                cursor = collection.find(query).sort("date", DESCENDING)
                if limit and len(all_records) + await collection.count_documents(query) > limit:
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
                logger.warning(f"⚠️ Error querying partition for year {year}: {e}")
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
    
    async def download_historical_data_for_symbol(
        self,
        symbol: str,
        start_date: datetime = None,
        end_date: datetime = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Download historical data for a single symbol"""
        
        # Get symbol mapping
        mappings = await self.get_symbol_mappings([symbol], mapped_only=True)
        if not mappings:
            return {"error": f"No NSE mapping found for symbol {symbol}"}
        
        mapping = mappings[0]
        scrip_code = mapping.nse_scrip_code
        
        logger.info(f"📈 Downloading historical data for {symbol} (scrip: {scrip_code})")
        
        # Set default date range
        if not start_date:
            start_date = datetime(2005, 1, 1)
        if not end_date:
            end_date = datetime.now()
        
        # Check if we already have recent data (unless force refresh)
        if not force_refresh:
            # For sync mode, check for gaps in the requested range
            existing_data = await self.get_price_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=None  # Get all data to check for gaps
            )
            
            if existing_data:
                # Check if we have complete data in the requested range
                existing_dates = {record.date.date() for record in existing_data}
                business_days = self._generate_business_days(start_date, end_date)
                missing_dates = [day for day in business_days if day not in existing_dates]
                
                if not missing_dates:
                    # No gaps found, data is complete
                    logger.info(f"✅ Complete data exists for {symbol} in requested range")
                    return {
                        "message": f"Complete data exists for {symbol}", 
                        "date_range": f"{start_date.date()} to {end_date.date()}",
                        "total_records": len(existing_data)
                    }
                else:
                    # Gaps found, need to download
                    logger.info(f"📊 Found {len(missing_dates)} missing dates for {symbol}, proceeding with download")
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
        
        return {
            "symbol": symbol,
            "scrip_code": scrip_code,
            "records_fetched": len(historical_data),
            "storage_result": storage_result,
            "date_range": f"{start_date.date()} to {end_date.date()}"
        }
    
    async def download_historical_data_for_index(
        self,
        index_name: str,
        start_date: datetime = None,
        end_date: datetime = None,
        force_refresh: bool = False
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
                    force_refresh=force_refresh
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
        force_refresh: bool = False
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
                    force_refresh=force_refresh
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
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Analyze data gaps for a symbol within a date range
        
        Returns:
            Dict containing gap analysis with missing dates, total gaps, etc.
        """
        try:
            # Get existing data for the symbol
            existing_data = await self.get_price_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=None  # Get all records
            )
            
            if not existing_data:
                # No data exists at all
                total_business_days = self._count_business_days(start_date, end_date)
                return {
                    "total_expected_days": total_business_days,
                    "total_actual_days": 0,
                    "total_missing_days": total_business_days,
                    "gap_percentage": 100.0,
                    "has_data": False,
                    "date_range": {
                        "start": start_date.date().isoformat(),
                        "end": end_date.date().isoformat()
                    },
                    "gaps": [{"start": start_date.date().isoformat(), "end": end_date.date().isoformat()}]
                }
            
            # Convert to date set for easier processing
            existing_dates = {record.date.date() for record in existing_data}
            
            # Generate all business days in the range
            business_days = self._generate_business_days(start_date, end_date)
            missing_dates = [day for day in business_days if day not in existing_dates]
            
            # Group consecutive missing dates into gaps
            gaps = self._group_consecutive_dates(missing_dates)
            
            # Calculate statistics
            total_expected = len(business_days)
            total_actual = len(existing_dates)
            total_missing = len(missing_dates)
            gap_percentage = (total_missing / total_expected * 100) if total_expected > 0 else 0
            
            # Yearly breakdown
            yearly_breakdown = self._analyze_yearly_gaps(business_days, existing_dates)
            
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
                "gaps": [{"start": gap[0].isoformat(), "end": gap[-1].isoformat(), "days": len(gap)} for gap in gaps],
                "yearly_breakdown": yearly_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error analyzing gaps for {symbol}: {e}")
            return {"error": str(e)}
    
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
    
    def _generate_business_days(self, start_date: datetime, end_date: datetime) -> List[datetime.date]:
        """Generate list of business days between two dates"""
        from datetime import timedelta
        business_days = []
        current = start_date.date()
        end = end_date.date()
        while current <= end:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
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
