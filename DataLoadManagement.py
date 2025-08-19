                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                #!/usr/bin/env python3
"""
DataLoadManagement CLI Tool
Command Line Interface for downloading, inserting, and updating historical stock data

This tool manages historical price data for:
- Individual stocks (entities)
- All stocks available under an Index
- All stocks available under an Industry

Database Collections Used:
- symbol_mappings: Maps index symbols to NSE scrip codes
- prices_YYYY_YYYY: Historical price data partitioned by 5-year periods
- stock_metadata: Metadata about processed stocks
- data_processing_logs: Activity logs for downloads and processing

Data Flow:
Symbol Input → NSE Mapping → Historical Data Download → MongoDB Storage
"""

import argparse
import sys
import asyncio
from datetime import datetime, timedelta                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
from stock_data_manager import StockDataManager

class DataLoadManagement:
    def __init__(self):
        """
        Initialize DataLoadManagement CLI tool for historical stock data operations
        
        This tool manages:
        - Historical price data download from NSE
        - Data storage in MongoDB with 5-year partitioning
        - Symbol mapping between index constituents and NSE scrip codes
        - Processing logs and metadata tracking
        """
        self.stock_manager = None
        
    async def initialize(self):
        """Initialize the stock data manager"""
        self.stock_manager = StockDataManager()
        await self.stock_manager.__aenter__()
        return True
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.stock_manager:
            await self.stock_manager.__aexit__(None, None, None)

    async def analyze_gap_status(self, symbol: str, scrip_code: str) -> dict:
        """
        Analyze gap status for a single symbol by comparing NSE data with DB data
        
        Process:
        1. Download complete NSE data from 2005 to current date
        2. Fetch existing DB data for the same period  
        3. Compare both datasets to find actual gaps
        4. Calculate outdated days as current date minus earliest missing date
        
        Returns a dictionary with comprehensive gap analysis information
        """
        try:
            if not scrip_code:
                return {
                    "has_data": False,
                    "total_records": 0,
                    "date_range": {"start": None, "end": None},
                    "data_freshness_days": 0,
                    "coverage_percentage": 0,
                    "last_price": None,
                    "needs_update": True,
                    "gap_summary": ["No NSE scrip code mapping available"]
                }
            
            # Default date range - from 2005 to now
            start_date = datetime(2005, 1, 1)
            end_date = datetime.now()
            
            # Step 1: Download complete NSE data to get the "truth" reference
            try:
                nse_data = await self.stock_manager.nse_client.fetch_historical_data(
                    scrip_code=int(scrip_code),
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if not nse_data:
                    return {
                        "has_data": False,
                        "total_records": 0,
                        "date_range": {"start": None, "end": None},
                        "data_freshness_days": 0,
                        "coverage_percentage": 0,
                        "last_price": None,
                        "needs_update": True,
                        "gap_summary": ["No data available from NSE for this symbol"]
                    }
                
                # Create set of NSE trading dates
                nse_dates = {data.date.date() for data in nse_data}
                nse_min_date = min(nse_dates)
                nse_max_date = max(nse_dates)
                total_nse_trading_days = len(nse_dates)
                
            except Exception as e:
                return {
                    "has_data": False,
                    "total_records": 0,
                    "date_range": {"start": None, "end": None},
                    "data_freshness_days": 0,
                    "coverage_percentage": 0,
                    "last_price": None,
                    "needs_update": True,
                    "gap_summary": [f"Failed to fetch NSE data: {str(e)}"]
                }
            
            # Step 2: Get existing data from database for the same period
            # Convert date objects to datetime objects for MongoDB query
            nse_min_datetime = datetime.combine(nse_min_date, datetime.min.time())
            nse_max_datetime = datetime.combine(nse_max_date, datetime.max.time())
            
            existing_data = await self.stock_manager.get_price_data(
                symbol=symbol,
                start_date=nse_min_datetime,
                end_date=nse_max_datetime
            )
            
            # Step 3: Compare NSE data with DB data to find gaps
            if not existing_data:
                # No DB data at all
                days_behind = (datetime.now().date() - nse_max_date).days
                return {
                    "has_data": False,
                    "total_records": 0,
                    "date_range": {"start": None, "end": None},
                    "data_freshness_days": days_behind,
                    "coverage_percentage": 0,
                    "last_price": None,
                    "needs_update": True,
                    "gap_summary": [f"No local data found. NSE has {total_nse_trading_days:,} trading days available"]
                }
            
            # Create set of existing DB dates
            db_dates = {data.date.date() for data in existing_data}
            db_min_date = min(db_dates)
            db_max_date = max(db_dates)
            total_db_records = len(existing_data)
            
            # Step 4: Find actual gaps by comparing NSE dates with DB dates
            missing_dates = nse_dates - db_dates  # Dates in NSE but not in DB
            extra_dates = db_dates - nse_dates    # Dates in DB but not in NSE (shouldn't happen)
            
            # Calculate coverage based on actual NSE trading days
            coverage_percentage = ((total_nse_trading_days - len(missing_dates)) / total_nse_trading_days * 100) if total_nse_trading_days > 0 else 0
            
            # Step 5: Calculate data freshness - find earliest missing date
            if missing_dates:
                # Find the earliest missing date to calculate how far behind we are
                earliest_missing = min(missing_dates)
                days_behind = (datetime.now().date() - earliest_missing).days
                
                # Special case: if only recent dates are missing, calculate from last available date
                if earliest_missing > db_max_date:
                    days_behind = (datetime.now().date() - db_max_date).days
            else:
                # No missing dates - calculate from the latest available date
                days_behind = (datetime.now().date() - nse_max_date).days
            
            # Get last price from the most recent data
            latest_data = max(existing_data, key=lambda x: x.date) if existing_data else None
            last_price = latest_data.close_price if latest_data else None
            
            # Determine if update is needed
            # Update needed if: missing dates exist OR data is more than 3 days old
            needs_update = len(missing_dates) > 0 or days_behind > 3
            
            # Generate detailed gap summary
            gap_summary = []
            if len(missing_dates) > 0:
                gap_summary.append(f"Missing {len(missing_dates):,} trading days out of {total_nse_trading_days:,}")
                
                # Group missing dates into ranges for better readability
                sorted_missing = sorted(missing_dates)
                if len(sorted_missing) <= 5:
                    gap_summary.append(f"Missing dates: {', '.join([d.strftime('%Y-%m-%d') for d in sorted_missing])}")
                else:
                    gap_summary.append(f"Missing date range: {sorted_missing[0].strftime('%Y-%m-%d')} to {sorted_missing[-1].strftime('%Y-%m-%d')}")
            
            if days_behind > 3:
                gap_summary.append(f"Data is {days_behind} days behind current date")
            
            if len(extra_dates) > 0:
                gap_summary.append(f"Warning: {len(extra_dates)} dates in DB but not in NSE data")
            
            if not gap_summary:
                gap_summary.append("Data is complete and up-to-date")
            
            return {
                "has_data": True,
                "total_records": total_db_records,
                "date_range": {
                    "start": db_min_date.isoformat() if db_min_date else None,
                    "end": db_max_date.isoformat() if db_max_date else None
                },
                "data_freshness_days": days_behind,
                "coverage_percentage": round(coverage_percentage, 1),
                "last_price": last_price,
                "needs_update": needs_update,
                "gap_summary": gap_summary,
                "nse_reference": {
                    "total_trading_days": total_nse_trading_days,
                    "date_range": {
                        "start": nse_min_date.isoformat(),
                        "end": nse_max_date.isoformat()
                    },
                    "missing_days": len(missing_dates)
                }
            }
            
        except Exception as e:
            return {
                "has_data": False,
                "total_records": 0,
                "date_range": {"start": None, "end": None},
                "data_freshness_days": 0,
                "coverage_percentage": 0,
                "last_price": None,
                "needs_update": True,
                "gap_summary": [f"Error analyzing data: {str(e)}"]
            }
    
    
    async def download_single_stock(self, symbol, start_date=None, end_date=None, force_refresh=False):
        """
        Download historical data for a single stock symbol
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')
            start_date: Start date in YYYY-MM-DD format (default: 2005-01-01)
            end_date: End date in YYYY-MM-DD format (default: current date)
            force_refresh: Force download even if recent data exists
        """
        print(f"📈 Downloading historical data for stock: {symbol}")
        print("    Data will be stored in: prices_YYYY_YYYY collections (5-year partitions)")
        print("    Symbol mapping from: symbol_mappings collection")
        print("=" * 70)
        
        try:
            # Parse dates if provided
            parsed_start_date = None
            parsed_end_date = None
            
            if start_date:
                try:
                    parsed_start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    print(f"   Start Date: {parsed_start_date.strftime('%Y-%m-%d')}")
                except ValueError:
                    print(f"❌ Invalid start date format. Use YYYY-MM-DD format.")
                    return False
            
            if end_date:
                try:
                    parsed_end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    print(f"   End Date: {parsed_end_date.strftime('%Y-%m-%d')}")
                except ValueError:
                    print(f"❌ Invalid end date format. Use YYYY-MM-DD format.")
                    return False
            
            # Set default dates if not provided
            if not parsed_start_date:
                parsed_start_date = datetime(2005, 1, 1)
                print(f"   Start Date: {parsed_start_date.strftime('%Y-%m-%d')} (default)")
            
            if not parsed_end_date:
                parsed_end_date = datetime.now()
                print(f"   End Date: {parsed_end_date.strftime('%Y-%m-%d')} (current)")
                
            print(f"   Force Refresh: {'Yes' if force_refresh else 'No'}")
            print()
            
            # Download historical data
            result = await self.stock_manager.download_historical_data_for_symbol(
                symbol=symbol,  # Don't convert to uppercase for index symbols
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                force_refresh=force_refresh
            )
            
            # Display results
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                return False
            elif 'message' in result:
                print(f"ℹ️  {result['message']}")
                
                # Show gap analysis if available
                if 'gap_analysis' in result and result['gap_analysis']:
                    gap_info = result['gap_analysis']
                    print(f"   📊 Gap Analysis:")
                    print(f"      Strategy: {gap_info.get('action', 'N/A')}")
                    print(f"      Reason: {gap_info.get('reason', 'N/A')}")
                    if gap_info.get('gap_days', 0) > 0:
                        print(f"      Gap Days: {gap_info['gap_days']}")
                
                if 'last_date' in result:
                    print(f"   Last available data: {result['last_date']}")
                return True
            else:
                print(f"✅ Successfully downloaded data for {symbol}")
                print(f"   Symbol: {result.get('symbol', 'N/A')}")
                print(f"   NSE Scrip Code: {result.get('scrip_code', 'N/A')}")
                print(f"   Records Fetched: {result.get('records_fetched', 0):,}")
                print(f"   Date Range: {result.get('date_range', 'N/A')}")
                
                # Storage result details
                storage_result = result.get('storage_result', {})
                if storage_result:
                    print(f"   Records Inserted: {storage_result.get('inserted', 0):,}")
                    print(f"   Records Updated: {storage_result.get('updated', 0):,}")
                
                # Gap analysis details (new intelligent analysis)
                gap_analysis = result.get('gap_analysis', {})
                if gap_analysis and gap_analysis.get('statistics'):
                    stats = gap_analysis['statistics']
                    storage_result = result.get('storage_result', {})
                    
                    print(f"   📊 Intelligent Gap Analysis:")
                    print(f"      Trading Days Coverage: {stats.get('coverage_percentage', 0):.1f}%")
                    print(f"      Data Freshness: {stats.get('data_freshness', 'unknown')}")
                    
                    # Show actual storage results instead of gap analysis numbers
                    actual_inserted = storage_result.get('inserted', 0)
                    actual_updated = storage_result.get('updated', 0) 
                    actual_skipped = storage_result.get('skipped', 0)
                    
                    if actual_skipped > 0:
                        print(f"      Actions: {actual_inserted} inserted, {actual_updated} updated, {actual_skipped} skipped")
                    else:
                        print(f"      Actions: {actual_inserted} inserted, {actual_updated} updated")
                    
                    if gap_analysis.get('message'):
                        print(f"      Decision: {gap_analysis['message']}")
                
                print(f"   💾 Storage: Data stored in partitioned collections based on dates")
                
                return True
                
        except Exception as e:
            print(f"❌ Unexpected error during download: {str(e)}")
            return False
    
    async def show_symbol_info(self, symbol):
        """
        Show information about a symbol including NSE mapping
        
        Args:
            symbol: Stock symbol to check
        """
        print(f"🔍 Symbol Information for: {symbol}")
        print("    Checking: symbol_mappings collection")
        print("=" * 50)
        
        try:
            # Get symbol mappings
            mappings = await self.stock_manager.get_symbol_mappings([symbol], mapped_only=False)
            
            if not mappings:
                print(f"   ❌ No mapping found for symbol: {symbol}")
                print(f"   💡 This symbol may not exist in the index constituent data.")
                print(f"      To add symbols, use the IndexManagement CLI tool first.")
                return False
            
            mapping = mappings[0]
            print(f"   Symbol: {mapping.symbol}")
            print(f"   Company Name: {mapping.company_name}")
            print(f"   Industry: {mapping.industry}")
            print(f"   Index Names: {', '.join(mapping.index_names)}")
            
            if mapping.nse_scrip_code:
                print(f"   ✅ NSE Mapping Found:")
                print(f"      NSE Scrip Code: {mapping.nse_scrip_code}")
                print(f"      NSE Symbol: {mapping.nse_symbol}")
                print(f"      NSE Name: {mapping.nse_name}")
                print(f"      Match Confidence: {mapping.match_confidence:.2f}")
                print(f"      Last Updated: {mapping.last_updated}")
                
                # Check if we have historical data
                recent_data = await self.stock_manager.get_price_data(
                    symbol=symbol,
                    limit=1
                )
                
                if recent_data:
                    latest_record = recent_data[0]
                    print(f"   📊 Historical Data Available:")
                    print(f"      Latest Date: {latest_record.date.strftime('%Y-%m-%d')}")
                    print(f"      Latest Close: ₹{latest_record.close_price:.2f}")
                    print(f"      Data Collection: prices_{latest_record.year_partition}_*")
                else:
                    print(f"   📊 No historical data found - ready for download")
                    
            else:
                print(f"   ❌ No NSE mapping found")
                print(f"      Match Confidence: {mapping.match_confidence:.2f}")
                print(f"      💡 Use symbol mapping refresh to try again")
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking symbol info: {str(e)}")
            return False
    
    async def refresh_mappings(self):
        """
        Refresh symbol mappings from index_meta data to NSE scrip codes
        
        This should be run after adding new URLs or processing new index data
        to ensure all symbols are mapped to NSE scrip codes for data download.
        """
        print("🔄 Refreshing Symbol Mappings from Index Data")
        print("    Reading from: index_meta collection")
        print("    Updating: symbol_mappings collection")
        print("    NSE Masters: Fetching latest equity masters from NSE")
        print("=" * 70)
        
        try:
            # Refresh symbol mappings
            print("   📡 Fetching NSE equity masters...")
            result = await self.stock_manager.refresh_symbol_mappings_from_index_meta()
            
            if 'error' in result:
                print(f"❌ Error during mapping refresh: {result['error']}")
                return False
            
            print("✅ Symbol mapping refresh completed successfully!")
            print(f"   Total Symbols Processed: {result.get('total_symbols', 0):,}")
            print(f"   Successfully Mapped: {result.get('mapped_symbols', 0):,}")
            print(f"   Unmapped Symbols: {result.get('unmapped_symbols', 0):,}")
            print(f"   New Mappings Created: {result.get('new_mappings', 0):,}")
            print(f"   Updated Existing: {result.get('updated_mappings', 0):,}")
            
            # Show some mapping details
            if result.get('unmapped_symbols', 0) > 0:
                print()
                print("⚠️  Some symbols could not be mapped to NSE:")
                print("   This might be due to:")
                print("   - Symbol name differences between index data and NSE")
                print("   - Delisted companies")
                print("   - New companies not yet in NSE masters")
                print("   💡 These symbols will be skipped during data download")
            
            print()
            print("   💡 Mapping refresh should be run after:")
            print("      - Adding new URLs with IndexManagement CLI")
            print("      - Processing new index constituent data")
            print("      - When NSE introduces new symbols")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during mapping refresh: {str(e)}")
            return False

    async def show_stats(self):
        """Show statistics about the stock data system"""
        print("📊 Stock Data Management Statistics")
        print("    Database Collections Overview")
        print("=" * 60)
        
        try:
            # Get symbol mappings statistics
            mappings = await self.stock_manager.get_symbol_mappings()
            mapped_count = len([m for m in mappings if m.nse_scrip_code is not None])
            
            print(f"   Symbol Mappings (symbol_mappings collection):")
            print(f"      Total Symbols: {len(mappings):,}")
            print(f"      Mapped to NSE: {mapped_count:,}")
            print(f"      Unmapped: {len(mappings) - mapped_count:,}")
            print()
            
            # Get price data statistics
            stats = await self.stock_manager.get_data_statistics()
            
            print(f"   Historical Price Data:")
            print(f"      Total Records: {stats.get('total_records', 0):,}")
            print(f"      Active Collections: {len(stats.get('collections', {}))}")
            
            # Format date range
            date_range = stats.get('date_range', {})
            earliest = date_range.get('earliest')
            latest = date_range.get('latest')
            if earliest and latest:
                print(f"      Date Range: {earliest.strftime('%Y-%m-%d')} to {latest.strftime('%Y-%m-%d')}")
            else:
                print(f"      Date Range: No data available")
            print()
            
            # Show collection details
            collections = stats.get('collections', {})
            if collections:
                print(f"   Price Data Collections (5-year partitions):")
                for collection_name, collection_info in collections.items():
                    record_count = collection_info.get('record_count', 0)
                    print(f"      {collection_name}: {record_count:,} records")
            
            # Get stock metadata statistics
            try:
                metadata_count = await self.stock_manager.db.stock_metadata.count_documents({})
                print(f"   Stock Metadata (stock_metadata collection): {metadata_count:,} stocks")
                
                logs_count = await self.stock_manager.db.data_processing_logs.count_documents({})
                print(f"   Processing Logs (data_processing_logs collection): {logs_count:,} entries")
            except Exception as e:
                print(f"   Additional stats unavailable: {e}")
            
            print()
            print("   💡 Collections are automatically created during data processing")
            print("   💡 Price data is partitioned by 5-year periods for scalability")
            
            return True
            
        except Exception as e:
            print(f"❌ Error getting statistics: {str(e)}")
            return False
    
    async def delete_stock_data(self, symbol, confirm=False):
        """
        Delete all price data for a specific stock symbol
        
        Args:
            symbol: Stock symbol to delete
            confirm: Safety confirmation flag
        """
        if not confirm:
            print(f"⚠️ DELETE OPERATION REQUIRES CONFIRMATION")
            print(f"   This will permanently delete ALL price data for {symbol} from ALL partitions")
            print(f"   To proceed, use: --confirm")
            return False
        
        print(f"🗑️ Deleting all price data for stock: {symbol}")
        print("   ⚠️ WARNING: This operation cannot be undone!")
        print("=" * 70)
        
        try:
            result = await self.stock_manager.delete_price_data_for_symbol(symbol)
            
            if result.get('success', False):
                total_deleted = result.get('total_deleted', 0)
                partitions_affected = result.get('partitions_affected', [])
                
                if total_deleted > 0:
                    print(f"✅ Successfully deleted {total_deleted:,} records for {symbol}")
                    print(f"   Partitions affected: {len(partitions_affected)}")
                    
                    for partition_info in partitions_affected:
                        print(f"      - {partition_info['partition']}: {partition_info['deleted']:,} records deleted")
                    
                    print(f"   💾 Data cleanup completed successfully")
                else:
                    print(f"ℹ️ No data found for symbol {symbol}")
                    print(f"   No records were deleted")
                
                return True
            else:
                errors = result.get('errors', [])
                print(f"❌ Failed to delete data for {symbol}")
                for error in errors:
                    print(f"   Error: {error}")
                return False
                
        except Exception as e:
            print(f"❌ Unexpected error during deletion: {str(e)}")
            return False
    
    async def check_data_gaps(self, symbol, start_date=None, end_date=None):
        """
        Check data gaps for a stock without downloading from NSE
        This analyzes what data exists vs expected trading days
        
        Args:
            symbol: Stock symbol to analyze
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
        """
        print(f"🔍 Analyzing data gaps for stock: {symbol}")
        print("    This checks existing data without downloading from NSE")
        print("=" * 70)
        
        try:
            # Parse dates if provided
            parsed_start_date = None
            parsed_end_date = None
            
            if start_date:
                try:
                    parsed_start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    print(f"   Start Date: {parsed_start_date.strftime('%Y-%m-%d')}")
                except ValueError:
                    print(f"❌ Invalid start date format. Use YYYY-MM-DD format.")
                    return False
            
            if end_date:
                try:
                    parsed_end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    print(f"   End Date: {parsed_end_date.strftime('%Y-%m-%d')}")
                except ValueError:
                    print(f"❌ Invalid end date format. Use YYYY-MM-DD format.")
                    return False
            
            # Set defaults
            if not parsed_start_date:
                parsed_start_date = datetime(2005, 1, 1)
                print(f"   Start Date: {parsed_start_date.strftime('%Y-%m-%d')} (default)")
            
            if not parsed_end_date:
                parsed_end_date = datetime.now()
                print(f"   End Date: {parsed_end_date.strftime('%Y-%m-%d')} (current)")
            
            print()
            
            # Check if symbol mapping exists
            mappings = await self.stock_manager.get_symbol_mappings([symbol], mapped_only=True)
            if not mappings:
                print(f"❌ No NSE mapping found for symbol {symbol}")
                print(f"   Run 'refresh-mappings' command first to update symbol mappings")
                return False
            
            mapping = mappings[0]
            scrip_code = mapping.nse_scrip_code
            print(f"📋 Symbol Info:")
            print(f"   Symbol: {symbol}")
            print(f"   NSE Scrip Code: {scrip_code}")
            print(f"   Company: {mapping.company_name}")
            print()
            
            # Get existing data for the specified range
            existing_data = await self.stock_manager.get_price_data(
                symbol=symbol,
                start_date=parsed_start_date,
                end_date=parsed_end_date
            )
            
            if not existing_data:
                print(f"📊 Gap Analysis Results:")
                print(f"   ❌ No existing data found for {symbol}")
                print(f"   📅 Date Range: {parsed_start_date.date()} to {parsed_end_date.date()}")
                print(f"   🔄 Recommendation: Run download-stock to fetch all data")
                return True
            
            # Analyze existing data
            existing_dates = {data.date.date() for data in existing_data}
            date_range_days = (parsed_end_date.date() - parsed_start_date.date()).days + 1
            
            # Estimate expected trading days (rough calculation)
            # Assume ~70% of days are trading days (excluding weekends and holidays)
            estimated_trading_days = int(date_range_days * 0.7)
            
            # Get date range info
            min_existing_date = min(existing_dates)
            max_existing_date = max(existing_dates)
            
            # Calculate coverage
            coverage_percentage = min(100.0, (len(existing_dates) / estimated_trading_days * 100)) if estimated_trading_days > 0 else 0
            
            # Calculate data freshness
            days_behind = (datetime.now().date() - max_existing_date).days
            data_freshness = "current" if days_behind <= 1 else f"{days_behind} days old"
            
            print(f"📊 Gap Analysis Results:")
            print(f"   📅 Requested Range: {parsed_start_date.date()} to {parsed_end_date.date()}")
            print(f"   📅 Existing Data Range: {min_existing_date} to {max_existing_date}")
            print(f"   📈 Total Records Found: {len(existing_data):,}")
            print(f"   📈 Unique Trading Days: {len(existing_dates):,}")
            print(f"   📈 Estimated Coverage: ~{coverage_percentage:.1f}% of trading days")
            print(f"   📈 Data Freshness: {data_freshness}")
            print()
            
            # Provide recommendations
            print(f"🎯 Recommendations:")
            if coverage_percentage >= 95 and days_behind <= 7:
                print(f"   ✅ Data appears complete and current")
                print(f"   💡 Use 'download-stock --force-refresh' only if you need latest updates")
            elif coverage_percentage >= 80:
                if days_behind > 7:
                    print(f"   🔄 Data coverage is good but may need updates")
                    print(f"   💡 Run 'download-stock' to get latest data")
                else:
                    print(f"   ✅ Data coverage is good and current")
            else:
                print(f"   ⚠️ Significant data gaps detected")
                print(f"   🔄 Run 'download-stock' to fill gaps and get complete data")
            
            # Show partitions info
            print()
            print(f"📂 Data Distribution by Partition:")
            
            # Query each unique partition only once
            partition_counts = {}
            checked_partitions = set()
            
            # Determine which partitions to check based on date range
            start_year = parsed_start_date.year
            end_year = parsed_end_date.year
            
            for year in range(start_year, end_year + 1):
                try:
                    # Get the partition name for this year
                    partition_year = (year // 5) * 5
                    if partition_year < 2005:
                        partition_year = 2005
                    partition_name = f"prices_{partition_year}_{partition_year + 4}"
                    
                    # Skip if we already checked this partition
                    if partition_name in checked_partitions:
                        continue
                    
                    checked_partitions.add(partition_name)
                    
                    # Query this specific partition for the symbol and date range
                    collection = await self.stock_manager._get_price_collection(year)
                    count = await collection.count_documents({
                        'symbol': symbol,
                        'date': {
                            '$gte': parsed_start_date,
                            '$lte': parsed_end_date
                        }
                    })
                    
                    if count > 0:
                        partition_counts[partition_name] = count
                        
                except Exception as e:
                    # Skip partitions that don't exist or have errors
                    continue
            
            # Display actual partition counts
            for partition, count in sorted(partition_counts.items()):
                print(f"   {partition}: {count:,} records")
            
            return True
            
        except Exception as e:
            print(f"❌ Error analyzing gaps: {str(e)}")
            return False
    
    async def get_symbols_for_index(self, index_name):
        """Get all symbols for a specific index from index_meta collection"""
        try:
            # Query the index_meta collection for symbols in this index
            collection = self.stock_manager.db.index_meta
            symbols = await collection.distinct("Symbol", {"index_name": index_name})
            
            # Filter out any None or empty symbols
            symbols = [symbol for symbol in symbols if symbol and symbol.strip()]
            
            return sorted(symbols)
            
        except Exception as e:
            print(f"❌ Error getting symbols for index {index_name}: {str(e)}")
            return []
    
    async def get_symbols_for_industry(self, industry_name):
        """Get all symbols for a specific industry from index_meta collection"""
        try:
            # Query the index_meta collection for symbols in this industry
            collection = self.stock_manager.db.index_meta
            symbols = await collection.distinct("Symbol", {"Industry": industry_name})
            
            # Filter out any None or empty symbols
            symbols = [symbol for symbol in symbols if symbol and symbol.strip()]
            
            return sorted(symbols)
            
        except Exception as e:
            print(f"❌ Error getting symbols for industry {industry_name}: {str(e)}")
            return []
    
    async def get_available_indices(self):
        """Get list of all available indices"""
        try:
            collection = self.stock_manager.db.index_meta
            indices = await collection.distinct("index_name")
            return sorted([index for index in indices if index])
        except Exception as e:
            print(f"❌ Error getting available indices: {str(e)}")
            return []
    
    async def get_available_industries(self):
        """Get list of all available industries"""
        try:
            collection = self.stock_manager.db.index_meta
            industries = await collection.distinct("Industry")
            return sorted([industry for industry in industries if industry])
        except Exception as e:
            print(f"❌ Error getting available industries: {str(e)}")
            return []
    
    async def process_symbols_concurrently(self, symbols, operation_type, start_date=None, end_date=None, force_refresh=False, max_concurrent=5, verbose_gaps=False):
        """Process multiple symbols concurrently with progress tracking and error collection"""
        if not symbols:
            print("No symbols to process.")
            return {"success": 0, "failed": 0, "errors": []}
        
        total_symbols = len(symbols)
        completed = 0
        errors = []
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_symbol(symbol):
            nonlocal completed, errors
            
            async with semaphore:
                try:
                    if operation_type == "download":
                        success = await self.download_single_stock_async(symbol, start_date, end_date, force_refresh, show_progress=False)
                    elif operation_type == "check_gaps":
                        # For gap analysis, show detailed progress if verbose or single-threaded
                        show_details = verbose_gaps or max_concurrent == 1
                        success = await self.check_data_gaps_async(symbol, show_progress=show_details)
                    elif operation_type == "delete":
                        success = await self.delete_stock_data_async(symbol, show_progress=False)
                    else:
                        raise ValueError(f"Unknown operation type: {operation_type}")
                    
                    if not success:
                        errors.append(f"{symbol}: Operation failed")
                    
                    return success
                    
                except Exception as e:
                    error_msg = f"{symbol}: {str(e)}"
                    errors.append(error_msg)
                    return False
                
                finally:
                    completed += 1
                    # Only show progress every 10% or for small batches
                    if total_symbols <= 10 or completed % max(1, total_symbols // 10) == 0 or completed == total_symbols:
                        progress = (completed / total_symbols) * 100
                        print(f"\r📊 Overall Progress: {completed}/{total_symbols} ({progress:.0f}%) | Errors: {len(errors)}", end='', flush=True)
        
        # Start all tasks concurrently
        tasks = [process_single_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        successful = sum(1 for result in results if result is True)
        failed = total_symbols - successful
        
        print()  # New line after progress
        
        return {
            "success": successful,
            "failed": failed,
            "errors": errors,
            "total": total_symbols
        }
    
    async def download_single_stock_async(self, symbol, start_date=None, end_date=None, force_refresh=False, show_progress=True):
        """Async version of download_single_stock for concurrent processing"""
        try:
            # Parse dates if provided
            parsed_start_date = None
            parsed_end_date = None
            
            if start_date:
                if isinstance(start_date, str):
                    parsed_start_date = datetime.strptime(start_date, '%Y-%m-%d')
                else:
                    parsed_start_date = start_date
            
            if end_date:
                if isinstance(end_date, str):
                    parsed_end_date = datetime.strptime(end_date, '%Y-%m-%d')
                else:
                    parsed_end_date = end_date
            
            if show_progress:
                print(f"\n{'='*60}")
                print(f"📈 Starting download for: {symbol}")
                print(f"{'='*60}")
            
            result = await self.stock_manager.download_historical_data_for_symbol(
                symbol=symbol,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                force_refresh=force_refresh
            )
            
            # Check if result contains error
            success = "error" not in result
            
            if show_progress:
                if success:
                    print(f"✅ Successfully processed: {symbol}")
                else:
                    print(f"❌ Failed to process: {symbol} - {result.get('error', 'Unknown error')}")
            
            return success
            
        except Exception as e:
            if show_progress:
                print(f"❌ Error processing {symbol}: {str(e)}")
            return False
    
    async def check_data_gaps_async(self, symbol, show_progress=True):
        """Async version of check_data_gaps for concurrent processing"""
        try:
            if show_progress:
                print(f"\n📊 {symbol}")
            
            # Get symbol mapping
            mappings = await self.stock_manager.get_symbol_mappings([symbol], mapped_only=True)
            if not mappings:
                if show_progress:
                    print(f"❌ No NSE mapping found")
                return False
            
            mapping = mappings[0]
            scrip_code = mapping.nse_scrip_code
            
            # Get detailed data analysis
            recent_data = await self.stock_manager.get_price_data(symbol=symbol, limit=1)
            
            if show_progress:
                if recent_data:
                    latest_record = recent_data[0]
                    
                    # Get total record count
                    total_records = await self.stock_manager.get_price_data_count(symbol=symbol)
                    
                    # Get date range
                    earliest_data = await self.stock_manager.get_price_data(
                        symbol=symbol, 
                        limit=1, 
                        sort_order=1  # Ascending to get earliest
                    )
                    
                    # Calculate data freshness
                    from datetime import datetime
                    days_old = (datetime.now() - latest_record.date).days
                    
                    if earliest_data:
                        earliest_record = earliest_data[0]
                        date_range = f"{earliest_record.date.strftime('%Y-%m-%d')} to {latest_record.date.strftime('%Y-%m-%d')}"
                    else:
                        date_range = latest_record.date.strftime('%Y-%m-%d')
                    
                    print(f"   📈 {total_records} records | {date_range} | {days_old} days old | ₹{latest_record.close_price:.2f}")
                else:
                    print(f"   ⚠️ No data found")
            
            return True
            
        except Exception as e:
            if show_progress:
                print(f"   ❌ Error: {str(e)}")
            return False
    
    async def delete_stock_data_async(self, symbol, show_progress=True):
        """Async version of delete_stock_data for concurrent processing"""
        try:
            if show_progress:
                print(f"\n🗑️ Deleting data for: {symbol}")
            
            result = await self.stock_manager.delete_price_data_for_symbol(symbol)
            
            if show_progress:
                if result["success"]:
                    print(f"✅ Successfully deleted data for: {symbol}")
                else:
                    print(f"❌ Failed to delete data for: {symbol}")
            
            return result["success"]
            
        except Exception as e:
            if show_progress:
                print(f"❌ Error deleting data for {symbol}: {str(e)}")
            return False
    
    # Index-level operations
    async def handle_download_index(self, args):
        """Handle index-level download command"""
        try:
            print(f"\n🔍 Getting symbols for index: {args.index_name}")
            symbols = await self.get_symbols_for_index(args.index_name)
            
            if not symbols:
                print(f"❌ No symbols found for index: {args.index_name}")
                return False
            
            print(f"📊 Found {len(symbols)} symbols for index: {args.index_name}")
            print(f"🚀 Starting concurrent download with max {args.max_concurrent} parallel operations...")
            
            # Process all symbols concurrently
            results = await self.process_symbols_concurrently(
                symbols=symbols,
                operation_type="download",
                start_date=args.start_date,
                end_date=args.end_date,
                force_refresh=args.force_refresh,
                max_concurrent=args.max_concurrent
            )
            
            # Report final results
            print(f"\n{'='*60}")
            print(f"📊 INDEX DOWNLOAD SUMMARY for {args.index_name}")
            print(f"{'='*60}")
            print(f"✅ Successful: {results['success']}/{results['total']}")
            print(f"❌ Failed: {results['failed']}/{results['total']}")
            
            if results['errors']:
                print(f"\n🚨 ERRORS ENCOUNTERED:")
                for error in results['errors']:
                    print(f"  • {error}")
            
            return results['failed'] == 0
            
        except Exception as e:
            print(f"❌ Error in index download: {str(e)}")
            return False
    
    async def handle_download_industry(self, args):
        """Handle industry-level download command"""
        try:
            print(f"\n🔍 Getting symbols for industry: {args.industry_name}")
            symbols = await self.get_symbols_for_industry(args.industry_name)
            
            if not symbols:
                print(f"❌ No symbols found for industry: {args.industry_name}")
                return False
            
            print(f"📊 Found {len(symbols)} symbols for industry: {args.industry_name}")
            print(f"🚀 Starting concurrent download with max {args.max_concurrent} parallel operations...")
            
            # Process all symbols concurrently
            results = await self.process_symbols_concurrently(
                symbols=symbols,
                operation_type="download",
                start_date=args.start_date,
                end_date=args.end_date,
                force_refresh=args.force_refresh,
                max_concurrent=args.max_concurrent
            )
            
            # Report final results
            print(f"\n{'='*60}")
            print(f"📊 INDUSTRY DOWNLOAD SUMMARY for {args.industry_name}")
            print(f"{'='*60}")
            print(f"✅ Successful: {results['success']}/{results['total']}")
            print(f"❌ Failed: {results['failed']}/{results['total']}")
            
            if results['errors']:
                print(f"\n🚨 ERRORS ENCOUNTERED:")
                for error in results['errors']:
                    print(f"  • {error}")
            
            return results['failed'] == 0
            
        except Exception as e:
            print(f"❌ Error in industry download: {str(e)}")
            return False
    
    async def handle_check_gaps_index(self, args):
        """Handle index-level gap checking command"""
        try:
            print(f"\n🔍 Getting symbols for index: {args.index_name}")
            symbols = await self.get_symbols_for_index(args.index_name)
            
            if not symbols:
                print(f"❌ No symbols found for index: {args.index_name}")
                return False
            
            print(f"📊 Found {len(symbols)} symbols for index: {args.index_name}")
            print(f"🚀 Starting concurrent gap analysis with max {args.max_concurrent} parallel operations...")
            
            # Process all symbols concurrently
            results = await self.process_symbols_concurrently(
                symbols=symbols,
                operation_type="check_gaps",
                max_concurrent=args.max_concurrent,
                verbose_gaps=True  # Enable detailed gap analysis output
            )
            
            # Report final results
            print(f"\n{'='*60}")
            print(f"📊 INDEX GAP ANALYSIS SUMMARY for {args.index_name}")
            print(f"{'='*60}")
            print(f"✅ Successful: {results['success']}/{results['total']}")
            print(f"❌ Failed: {results['failed']}/{results['total']}")
            
            if results['errors']:
                print(f"\n🚨 ERRORS ENCOUNTERED:")
                for error in results['errors']:
                    print(f"  • {error}")
            
            return results['failed'] == 0
            
        except Exception as e:
            print(f"❌ Error in index gap analysis: {str(e)}")
            return False
    
    async def handle_check_gaps_industry(self, args):
        """Handle industry-level gap checking command"""
        try:
            print(f"\n🔍 Getting symbols for industry: {args.industry_name}")
            symbols = await self.get_symbols_for_industry(args.industry_name)
            
            if not symbols:
                print(f"❌ No symbols found for industry: {args.industry_name}")
                return False
            
            print(f"📊 Found {len(symbols)} symbols for industry: {args.industry_name}")
            print(f"🚀 Starting concurrent gap analysis with max {args.max_concurrent} parallel operations...")
            
            # Process all symbols concurrently
            results = await self.process_symbols_concurrently(
                symbols=symbols,
                operation_type="check_gaps",
                max_concurrent=args.max_concurrent,
                verbose_gaps=True  # Enable detailed gap analysis output
            )
            
            # Report final results
            print(f"\n{'='*60}")
            print(f"📊 INDUSTRY GAP ANALYSIS SUMMARY for {args.industry_name}")
            print(f"{'='*60}")
            print(f"✅ Successful: {results['success']}/{results['total']}")
            print(f"❌ Failed: {results['failed']}/{results['total']}")
            
            if results['errors']:
                print(f"\n🚨 ERRORS ENCOUNTERED:")
                for error in results['errors']:
                    print(f"  • {error}")
            
            return results['failed'] == 0
            
        except Exception as e:
            print(f"❌ Error in industry gap analysis: {str(e)}")
            return False
    
    async def handle_delete_index(self, args):
        """Handle index-level delete command"""
        try:
            print(f"\n🔍 Getting symbols for index: {args.index_name}")
            symbols = await self.get_symbols_for_index(args.index_name)
            
            if not symbols:
                print(f"❌ No symbols found for index: {args.index_name}")
                return False
            
            print(f"📊 Found {len(symbols)} symbols for index: {args.index_name}")
            
            # Confirmation for delete operations
            if not args.force:
                print(f"\n⚠️  WARNING: This will delete all price data for {len(symbols)} symbols in index '{args.index_name}'")
                print("   This action cannot be undone!")
                confirm = input("\nType 'DELETE' to confirm: ")
                if confirm != 'DELETE':
                    print("❌ Operation cancelled.")
                    return False
            
            print(f"🚀 Starting concurrent deletion with max {args.max_concurrent} parallel operations...")
            
            # Process all symbols concurrently
            results = await self.process_symbols_concurrently(
                symbols=symbols,
                operation_type="delete",
                max_concurrent=args.max_concurrent
            )
            
            # Report final results
            print(f"\n{'='*60}")
            print(f"📊 INDEX DELETION SUMMARY for {args.index_name}")
            print(f"{'='*60}")
            print(f"✅ Successful: {results['success']}/{results['total']}")
            print(f"❌ Failed: {results['failed']}/{results['total']}")
            
            if results['errors']:
                print(f"\n🚨 ERRORS ENCOUNTERED:")
                for error in results['errors']:
                    print(f"  • {error}")
            
            return results['failed'] == 0
            
        except Exception as e:
            print(f"❌ Error in index deletion: {str(e)}")
            return False
    
    async def handle_delete_industry(self, args):
        """Handle industry-level delete command"""
        try:
            print(f"\n🔍 Getting symbols for industry: {args.industry_name}")
            symbols = await self.get_symbols_for_industry(args.industry_name)
            
            if not symbols:
                print(f"❌ No symbols found for industry: {args.industry_name}")
                return False
            
            print(f"📊 Found {len(symbols)} symbols for industry: {args.industry_name}")
            
            # Confirmation for delete operations
            if not args.force:
                print(f"\n⚠️  WARNING: This will delete all price data for {len(symbols)} symbols in industry '{args.industry_name}'")
                print("   This action cannot be undone!")
                confirm = input("\nType 'DELETE' to confirm: ")
                if confirm != 'DELETE':
                    print("❌ Operation cancelled.")
                    return False
            
            print(f"🚀 Starting concurrent deletion with max {args.max_concurrent} parallel operations...")
            
            # Process all symbols concurrently
            results = await self.process_symbols_concurrently(
                symbols=symbols,
                operation_type="delete",
                max_concurrent=args.max_concurrent
            )
            
            # Report final results
            print(f"\n{'='*60}")
            print(f"📊 INDUSTRY DELETION SUMMARY for {args.industry_name}")
            print(f"{'='*60}")
            print(f"✅ Successful: {results['success']}/{results['total']}")
            print(f"❌ Failed: {results['failed']}/{results['total']}")
            
            if results['errors']:
                print(f"\n🚨 ERRORS ENCOUNTERED:")
                for error in results['errors']:
                    print(f"  • {error}")
            
            return results['failed'] == 0
            
        except Exception as e:
            print(f"❌ Error in industry deletion: {str(e)}")
            return False
    
    async def handle_list_indices(self, args):
        """Handle list indices command"""
        try:
            print("\n🔍 Getting available indices...")
            indices = await self.get_available_indices()
            
            if not indices:
                print("❌ No indices found in database")
                return False
            
            print(f"\n📊 Available Indices ({len(indices)}):")
            print("="*50)
            for i, index in enumerate(indices, 1):
                # Get symbol count for this index
                symbols = await self.get_symbols_for_index(index)
                print(f"{i:2d}. {index} ({len(symbols)} symbols)")
            
            return True
            
        except Exception as e:
            print(f"❌ Error listing indices: {str(e)}")
            return False
    
    async def handle_list_industries(self, args):
        """Handle list industries command"""
        try:
            print("\n🔍 Getting available industries...")
            industries = await self.get_available_industries()
            
            if not industries:
                print("❌ No industries found in database")
                return False
            
            print(f"\n📊 Available Industries ({len(industries)}):")
            print("="*50)
            for i, industry in enumerate(industries, 1):
                # Get symbol count for this industry
                symbols = await self.get_symbols_for_industry(industry)
                print(f"{i:2d}. {industry} ({len(symbols)} symbols)")
            
            return True
            
        except Exception as e:
            print(f"❌ Error listing industries: {str(e)}")
            return False

    async def handle_update_gap_status(self, args):
        """Handle update gap status command - calculate and store gap status for all symbols"""
        try:
            print("\n🔍 Updating gap status for all symbols...")
            
            # Get all symbols with NSE mapping
            mappings = await self.stock_manager.get_symbol_mappings(mapped_only=True)
            if not mappings:
                print("❌ No mapped symbols found")
                return False
            
            print(f"📊 Found {len(mappings)} mapped symbols")
            
            # Initialize semaphore for concurrent processing
            semaphore = asyncio.Semaphore(args.max_concurrent)
            
            # Update status for each symbol
            async def update_single_status(mapping):
                async with semaphore:
                    try:
                        # Check if status already exists and not forcing refresh
                        if not args.force_refresh:
                            existing = await self.stock_manager.db["gap_status"].find_one(
                                {"symbol": mapping.symbol}
                            )
                            if existing:
                                print(f"⏭️  {mapping.symbol} - Status already exists (use --force-refresh to update)")
                                return True
                        
                        # Calculate gap status using the new gap analysis method
                        gap_info = await self.analyze_gap_status(
                            mapping.symbol, 
                            mapping.nse_scrip_code
                        )
                        
                        if not gap_info:
                            print(f"❌ {mapping.symbol} - Failed to calculate gap status")
                            return False
                        
                        # Create gap status document
                        status_doc = {
                            "symbol": mapping.symbol,
                            "company_name": mapping.company_name,
                            "industry": mapping.industry,
                            "index_names": mapping.index_names,
                            "nse_scrip_code": mapping.nse_scrip_code,
                            "nse_symbol": mapping.nse_symbol,
                            "nse_name": mapping.nse_name,
                            "has_data": gap_info["has_data"],
                            "record_count": gap_info["total_records"],
                            "date_range": {
                                "start": gap_info["date_range"]["start"],
                                "end": gap_info["date_range"]["end"]
                            },
                            "data_freshness_days": gap_info["data_freshness_days"],
                            "coverage_percentage": gap_info["coverage_percentage"],
                            "last_price": gap_info.get("last_price"),
                            "needs_update": gap_info["needs_update"],
                            "gap_details": gap_info["gap_summary"],
                            "last_calculated": datetime.utcnow(),
                            "calculation_status": "completed"
                        }
                        
                        # Upsert the document
                        await self.stock_manager.db["gap_status"].replace_one(
                            {"symbol": mapping.symbol},
                            status_doc,
                            upsert=True
                        )
                        
                        status_indicator = "🔴" if not gap_info["has_data"] else "🟡" if gap_info["needs_update"] else "🟢"
                        print(f"{status_indicator} {mapping.symbol} - {gap_info['total_records']:,} records, {gap_info['coverage_percentage']}% coverage, {gap_info['data_freshness_days']} days old")
                        return True
                        
                    except Exception as e:
                        print(f"❌ {mapping.symbol} - Error: {str(e)}")
                        return False
            
            # Process all symbols concurrently
            tasks = [update_single_status(mapping) for mapping in mappings]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes
            successful = sum(1 for result in results if result is True)
            failed = len(results) - successful
            
            print(f"\n✅ Gap status update completed:")
            print(f"   📊 Total symbols: {len(mappings)}")
            print(f"   ✅ Successful: {successful}")
            print(f"   ❌ Failed: {failed}")
            
            return successful > 0
            
        except Exception as e:
            print(f"❌ Error updating gap status: {str(e)}")
            return False

    async def handle_get_gap_status(self, args):
        """Handle get gap status command - retrieve gap status for specific symbols"""
        try:
            print(f"\n🔍 Getting gap status for {len(args.symbols)} symbol(s)...")
            
            for symbol in args.symbols:
                symbol = symbol.upper()
                
                # Get gap status from database
                status = await self.stock_manager.db["gap_status"].find_one(
                    {"symbol": symbol}
                )
                
                if not status:
                    print(f"\n❌ {symbol} - No gap status found (run 'update-gap-status' first)")
                    continue
                
                # Display status
                status_indicator = "🔴" if not status["has_data"] else "🟡" if status["needs_update"] else "🟢"
                print(f"\n{status_indicator} {symbol} - {status['company_name']}")
                print(f"   Industry: {status['industry']}")
                print(f"   NSE Code: {status['nse_scrip_code']}")
                print(f"   Has Data: {'Yes' if status['has_data'] else 'No'}")
                
                if status["has_data"]:
                    print(f"   Records: {status['record_count']:,}")
                    print(f"   Date Range: {status['date_range']['start']} to {status['date_range']['end']}")
                    print(f"   Coverage: {status['coverage_percentage']}%")
                    print(f"   Data Age: {status['data_freshness_days']} days")
                    if status.get("last_price"):
                        print(f"   Last Price: ₹{status['last_price']:.2f}")
                    print(f"   Needs Update: {'Yes' if status['needs_update'] else 'No'}")
                
                if status.get("gap_details"):
                    print(f"   Gap Details: {', '.join(status['gap_details'])}")
                
                print(f"   Last Calculated: {status['last_calculated']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error getting gap status: {str(e)}")
            return False

    async def handle_list_gap_status(self, args):
        """Handle list gap status command - list gap status for all symbols with filters"""
        try:
            print("\n🔍 Listing gap status...")
            
            # Build query filter
            query_filter = {}
            if args.needs_update_only:
                query_filter["needs_update"] = True
            elif args.no_data_only:
                query_filter["has_data"] = False
            
            # Get gap status documents
            cursor = self.stock_manager.db["gap_status"].find(query_filter).sort("symbol", 1)
            statuses = await cursor.to_list(length=None)
            
            if not statuses:
                filter_desc = ""
                if args.needs_update_only:
                    filter_desc = " (needs update only)"
                elif args.no_data_only:
                    filter_desc = " (no data only)"
                print(f"❌ No gap status found{filter_desc}")
                return False
            
            # Group by status
            no_data = [s for s in statuses if not s["has_data"]]
            needs_update = [s for s in statuses if s["has_data"] and s["needs_update"]]
            up_to_date = [s for s in statuses if s["has_data"] and not s["needs_update"]]
            
            # Display summary
            filter_desc = ""
            if args.needs_update_only:
                filter_desc = " (Needs Update Only)"
            elif args.no_data_only:
                filter_desc = " (No Data Only)"
            
            print(f"\n📊 Gap Status Summary{filter_desc}:")
            print("="*60)
            print(f"🔴 No Data: {len(no_data)} symbols")
            print(f"🟡 Needs Update: {len(needs_update)} symbols")
            print(f"🟢 Up to Date: {len(up_to_date)} symbols")
            print(f"📊 Total: {len(statuses)} symbols")
            
            # Display detailed list
            for status_group, color, label in [
                (no_data, "🔴", "No Data"),
                (needs_update, "🟡", "Needs Update"),
                (up_to_date, "🟢", "Up to Date")
            ]:
                if not status_group or (args.needs_update_only and label != "Needs Update") or (args.no_data_only and label != "No Data"):
                    continue
                
                print(f"\n{color} {label} ({len(status_group)} symbols):")
                print("-" * 40)
                
                for status in status_group[:20]:  # Show first 20 in each category
                    if status["has_data"]:
                        print(f"  {status['symbol']:12} {status['record_count']:8,} records  {status['coverage_percentage']:3}%  {status['data_freshness_days']:3} days  {status['company_name'][:40]}")
                    else:
                        print(f"  {status['symbol']:12} {'':8} {'':8} {'':8} {'':8} {status['company_name'][:40]}")
                
                if len(status_group) > 20:
                    print(f"  ... and {len(status_group) - 20} more")
            
            return True
            
        except Exception as e:
            print(f"❌ Error listing gap status: {str(e)}")
            return False

def create_parser():
    """Create argument parser for the CLI"""
    parser = argparse.ArgumentParser(
        description='DataLoadManagement CLI - Historical Stock Data Operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Refresh symbol mappings (run after adding new index data)
  python DataLoadManagement.py refresh-mappings
  
  # Show symbol information
  python DataLoadManagement.py symbol-info RELIANCE
  
  # Download data for a single stock (default: 2005 to now)
  python DataLoadManagement.py download-stock RELIANCE
  
  # Download with custom date range
  python DataLoadManagement.py download-stock TCS --start-date 2020-01-01 --end-date 2023-12-31
  
  # Force refresh (re-download even if recent data exists)
  python DataLoadManagement.py download-stock HDFC --force-refresh
  
  # Show system statistics
  python DataLoadManagement.py show-stats
  
  # Check data gaps for a stock (without downloading)
  python DataLoadManagement.py check-gaps TCS
  
  # Check gaps for specific date range
  python DataLoadManagement.py check-gaps RELIANCE --start-date 2020-01-01 --end-date 2023-12-31
  
  # Delete stock data (useful for testing)
  python DataLoadManagement.py delete-stock TCS --confirm

Workflow:
  1. Add new URLs using IndexManagement CLI
  2. Process the URLs to get index constituent data
  3. Run refresh-mappings to map symbols to NSE scrip codes
  4. Download historical data for individual stocks

Database Collections:
  - index_meta: Index constituent data (source for symbol mapping)
  - symbol_mappings: Symbol to NSE scrip code mapping
  - prices_YYYY_YYYY: Historical price data (5-year partitions)
  - stock_metadata: Processing metadata for stocks
  - data_processing_logs: Download and processing activity logs
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Refresh mappings command
    refresh_parser = subparsers.add_parser('refresh-mappings', help='Refresh symbol mappings from index data to NSE scrip codes')
    
    # Symbol info command
    symbol_info_parser = subparsers.add_parser('symbol-info', help='Show information about a stock symbol')
    symbol_info_parser.add_argument('symbol', help='Stock symbol (e.g., RELIANCE, TCS)')
    
    # Download single stock command
    download_parser = subparsers.add_parser('download-stock', help='Download historical data for a single stock')
    download_parser.add_argument('symbol', help='Stock symbol (e.g., RELIANCE, TCS)')
    download_parser.add_argument('--start-date', help='Start date in YYYY-MM-DD format (default: 2005-01-01)')
    download_parser.add_argument('--end-date', help='End date in YYYY-MM-DD format (default: current date)')
    download_parser.add_argument('--force-refresh', action='store_true', help='Force download even if recent data exists')
    
    # Show statistics command
    stats_parser = subparsers.add_parser('show-stats', help='Show statistics about the stock data system')
    
    # Delete stock data command
    delete_parser = subparsers.add_parser('delete-stock', help='Delete all price data for a specific stock (useful for testing)')
    delete_parser.add_argument('symbol', help='Stock symbol to delete (e.g., RELIANCE, TCS)')
    delete_parser.add_argument('--confirm', action='store_true', help='Confirm deletion (required for safety)')
    
    # Check gaps command
    gaps_parser = subparsers.add_parser('check-gaps', help='Check data gaps for a stock without downloading')
    gaps_parser.add_argument('symbol', help='Stock symbol to analyze (e.g., RELIANCE, TCS)')
    gaps_parser.add_argument('--start-date', help='Start date in YYYY-MM-DD format (default: 2005-01-01)')
    gaps_parser.add_argument('--end-date', help='End date in YYYY-MM-DD format (default: current date)')
    
    # Index-level commands
    download_index_parser = subparsers.add_parser('download-index', help='Download historical data for all stocks in an index')
    download_index_parser.add_argument('index_name', help='Index name (e.g., "NIFTY 50", "NIFTY BANK")')
    download_index_parser.add_argument('--start-date', help='Start date in YYYY-MM-DD format (default: 2005-01-01)')
    download_index_parser.add_argument('--end-date', help='End date in YYYY-MM-DD format (default: current date)')
    download_index_parser.add_argument('--force-refresh', action='store_true', help='Force download even if recent data exists')
    download_index_parser.add_argument('--max-concurrent', type=int, default=5, help='Maximum concurrent downloads (default: 5)')
    
    check_index_gaps_parser = subparsers.add_parser('check-gaps-index', help='Check data gaps for all stocks in an index')
    check_index_gaps_parser.add_argument('index_name', help='Index name (e.g., "NIFTY 50", "NIFTY BANK")')
    check_index_gaps_parser.add_argument('--max-concurrent', type=int, default=5, help='Maximum concurrent operations (default: 5)')
    
    delete_index_parser = subparsers.add_parser('delete-index', help='Delete all price data for stocks in an index (useful for testing)')
    delete_index_parser.add_argument('index_name', help='Index name to delete (e.g., "NIFTY 50", "NIFTY BANK")')
    delete_index_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    delete_index_parser.add_argument('--max-concurrent', type=int, default=5, help='Maximum concurrent operations (default: 5)')
    
    # Industry-level commands
    download_industry_parser = subparsers.add_parser('download-industry', help='Download historical data for all stocks in an industry')
    download_industry_parser.add_argument('industry_name', help='Industry name (e.g., "Information Technology", "Banking")')
    download_industry_parser.add_argument('--start-date', help='Start date in YYYY-MM-DD format (default: 2005-01-01)')
    download_industry_parser.add_argument('--end-date', help='End date in YYYY-MM-DD format (default: current date)')
    download_industry_parser.add_argument('--force-refresh', action='store_true', help='Force download even if recent data exists')
    download_industry_parser.add_argument('--max-concurrent', type=int, default=5, help='Maximum concurrent downloads (default: 5)')
    
    check_industry_gaps_parser = subparsers.add_parser('check-gaps-industry', help='Check data gaps for all stocks in an industry')
    check_industry_gaps_parser.add_argument('industry_name', help='Industry name (e.g., "Information Technology", "Banking")')
    check_industry_gaps_parser.add_argument('--max-concurrent', type=int, default=5, help='Maximum concurrent operations (default: 5)')
    
    delete_industry_parser = subparsers.add_parser('delete-industry', help='Delete all price data for stocks in an industry (useful for testing)')
    delete_industry_parser.add_argument('industry_name', help='Industry name to delete (e.g., "Information Technology", "Banking")')
    delete_industry_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    delete_industry_parser.add_argument('--max-concurrent', type=int, default=5, help='Maximum concurrent operations (default: 5)')
    
    # List commands
    list_indices_parser = subparsers.add_parser('list-indices', help='List all available indices')
    list_industries_parser = subparsers.add_parser('list-industries', help='List all available industries')
    
    # Gap status management commands
    update_gap_status_parser = subparsers.add_parser('update-gap-status', help='Update gap status for all symbols (creates/updates gap_status collection)')
    update_gap_status_parser.add_argument('--max-concurrent', type=int, default=10, help='Maximum concurrent operations (default: 10)')
    update_gap_status_parser.add_argument('--force-refresh', action='store_true', help='Force refresh even if status exists')
    
    get_gap_status_parser = subparsers.add_parser('get-gap-status', help='Get gap status for specific symbols')
    get_gap_status_parser.add_argument('symbols', nargs='+', help='Symbol(s) to check status for')
    
    list_gap_status_parser = subparsers.add_parser('list-gap-status', help='List gap status for all symbols')
    list_gap_status_parser.add_argument('--needs-update-only', action='store_true', help='Show only symbols that need updates')
    list_gap_status_parser.add_argument('--no-data-only', action='store_true', help='Show only symbols with no data')
    
    return parser

async def main():
    """Main function to run the CLI"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize the data load management tool
    tool = DataLoadManagement()
    
    try:
        # Initialize connection
        print("🔗 Connecting to MongoDB and NSE data client...")
        if not await tool.initialize():
            print("❌ Failed to initialize data connections")
            sys.exit(1)
        print("✅ Connected successfully")
        print()
        
        # Execute commands
        success = False
        
        if args.command == 'refresh-mappings':
            success = await tool.refresh_mappings()
            
        elif args.command == 'symbol-info':
            success = await tool.show_symbol_info(args.symbol)
            
        elif args.command == 'download-stock':
            success = await tool.download_single_stock(
                symbol=args.symbol,
                start_date=args.start_date,
                end_date=args.end_date,
                force_refresh=args.force_refresh
            )
            
        elif args.command == 'show-stats':
            success = await tool.show_stats()
            
        elif args.command == 'delete-stock':
            success = await tool.delete_stock_data(
                symbol=args.symbol,
                confirm=args.confirm
            )
            
        elif args.command == 'check-gaps':
            success = await tool.check_data_gaps(
                symbol=args.symbol,
                start_date=args.start_date,
                end_date=args.end_date
            )
        
        elif args.command == 'download-index':
            success = await tool.handle_download_index(args)
        
        elif args.command == 'download-industry':
            success = await tool.handle_download_industry(args)
        
        elif args.command == 'check-gaps-index':
            success = await tool.handle_check_gaps_index(args)
        
        elif args.command == 'check-gaps-industry':
            success = await tool.handle_check_gaps_industry(args)
        
        elif args.command == 'delete-index':
            success = await tool.handle_delete_index(args)
        
        elif args.command == 'delete-industry':
            success = await tool.handle_delete_industry(args)
        
        elif args.command == 'list-indices':
            success = await tool.handle_list_indices(args)
        
        elif args.command == 'list-industries':
            success = await tool.handle_list_industries(args)
        
        elif args.command == 'update-gap-status':
            success = await tool.handle_update_gap_status(args)
        
        elif args.command == 'get-gap-status':
            success = await tool.handle_get_gap_status(args)
        
        elif args.command == 'list-gap-status':
            success = await tool.handle_list_gap_status(args)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        # Cleanup
        await tool.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
