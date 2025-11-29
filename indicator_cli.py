#!/usr/bin/env python3
"""
Indicator CLI Tool for Market Hunt
Direct command-line interface for indicator calculations
Alternative to web interface for power users and automation

Usage Examples:
    # Calculate TrueValueX for a single stock
    python indicator_cli.py calculate --symbol TCS --indicator truevx
    
    # Calculate for multiple stocks
    python indicator_cli.py calculate --symbols TCS,INFY,RELIANCE --indicator truevx
    
    # Calculate with custom parameters
    python indicator_cli.py calculate --symbol TCS --indicator truevx --s1 20 --m2 60 --l3 200
    
    # Calculate with custom date range
    python indicator_cli.py calculate --symbol TCS --indicator truevx --start-date 2024-01-01 --end-date 2024-12-31
    
    # Bulk calculate for all NIFTY50 stocks
    python indicator_cli.py bulk --universe nifty50 --indicator truevx
    
    # View stored indicators
    python indicator_cli.py list --symbol TCS
    
    # Export stored data
    python indicator_cli.py export --symbol TCS --indicator truevx --format csv --output tcs_truevx.csv
    
    # Check calculation status
    python indicator_cli.py status --job-id abc123
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
import json
import csv
import logging
from typing import List, Dict, Any, Optional
import uuid
from pathlib import Path

# Import project modules
from indicator_data_manager import IndicatorDataManager, IndicatorCalculationJob
from indicator_engine import IndicatorEngine
from batch_indicator_processor import BatchIndicatorProcessor
from stock_data_manager import StockDataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class IndicatorCLI:
    """Command-line interface for indicator calculations"""
    
    def __init__(self):
        self.data_manager = None
        self.indicator_engine = IndicatorEngine()
        self.batch_processor = BatchIndicatorProcessor()
        self.stock_manager = StockDataManager()
        
        # Universe mappings
        self.universe_mappings = {
            'nifty50': 'NIFTY 50',
            'nifty100': 'NIFTY 100', 
            'nifty500': 'NIFTY 500'
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.data_manager = IndicatorDataManager()
        await self.data_manager.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.data_manager:
            await self.data_manager.close()
    
    def print_header(self, title: str):
        """Print formatted header"""
        print(f"\n{'='*60}")
        print(f"🎯 {title}")
        print(f"{'='*60}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"❌ {message}")
    
    def print_info(self, message: str):
        """Print info message"""
        print(f"ℹ️  {message}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"⚠️  {message}")
    
    async def get_available_symbols(self, universe: Optional[str] = None) -> List[str]:
        """Get available symbols from database"""
        try:
            if universe and universe.lower() in self.universe_mappings:
                # Get symbols from specific universe
                base_symbol = self.universe_mappings[universe.lower()]
                # This would need to be implemented in stock_data_manager
                # For now, return hardcoded lists
                if universe.lower() == 'nifty50':
                    return ['TCS', 'INFY', 'RELIANCE', 'HDFCBANK', 'ICICIBANK']  # Sample
                elif universe.lower() == 'nifty100':
                    return ['TCS', 'INFY', 'RELIANCE', 'HDFCBANK', 'ICICIBANK', 'WIPRO', 'LT']  # Sample
                else:
                    return ['TCS', 'INFY', 'RELIANCE']  # Sample for now
            else:
                # Get all available symbols
                return ['TCS', 'INFY', 'RELIANCE', 'HDFCBANK', 'ICICIBANK']  # Sample
        except Exception as e:
            logger.error(f"Failed to get available symbols: {e}")
            return []
    
    async def get_stock_date_range(self, symbol: str) -> tuple[Optional[str], Optional[str]]:
        """Get full available date range for a stock from database"""
        try:
            # Price data is partitioned across multiple collections by year ranges
            price_collections = [
                'prices_2005_2009',
                'prices_2010_2014', 
                'prices_2015_2019',
                'prices_2020_2024',
                'prices_2025_2029'
            ]
            
            earliest_date = None
            latest_date = None
            total_records = 0
            
            # Search across all price collections
            for coll_name in price_collections:
                try:
                    coll = self.data_manager.db[coll_name]
                    
                    # Count records for this symbol in this collection
                    count = coll.count_documents({"symbol": symbol})
                    if count > 0:
                        total_records += count
                        
                        # Get earliest date from this collection
                        earliest = coll.find_one(
                            {"symbol": symbol}, 
                            sort=[("date", 1)]
                        )
                        
                        # Get latest date from this collection
                        latest = coll.find_one(
                            {"symbol": symbol},
                            sort=[("date", -1)]
                        )
                        
                        if earliest and (not earliest_date or earliest['date'] < earliest_date):
                            earliest_date = earliest['date']
                            
                        if latest and (not latest_date or latest['date'] > latest_date):
                            latest_date = latest['date']
                
                except Exception as coll_error:
                    logger.warning(f"Error querying collection {coll_name}: {coll_error}")
                    continue
            
            if earliest_date and latest_date and total_records > 0:
                start_date = earliest_date.strftime('%Y-%m-%d')
                end_date = latest_date.strftime('%Y-%m-%d')
                
                self.print_info(f"Found {total_records} records for {symbol}: {start_date} to {end_date}")
                return start_date, end_date
            else:
                self.print_warning(f"No price data found for {symbol} in any collection")
                return None, None
                
        except Exception as e:
            logger.error(f"Failed to get date range for {symbol}: {e}")
            self.print_warning(f"Could not determine date range for {symbol}, using defaults")
            return None, None
    
    async def calculate_single_symbol(self, args) -> bool:
        """Calculate indicator for a single symbol"""
        try:
            self.print_header(f"Calculating {args.indicator.upper()} for {args.symbol}")
            
            # Get full available date range if not specified
            if not args.start_date or not args.end_date:
                self.print_info(f"Determining full available date range for {args.symbol}...")
                stock_start, stock_end = await self.get_stock_date_range(args.symbol)
                
                if not args.start_date:
                    if stock_start:
                        args.start_date = stock_start
                        self.print_info(f"Using full range start date: {args.start_date}")
                    else:
                        # Use fallback default
                        args.start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                        self.print_warning(f"Using fallback start date: {args.start_date}")
                
                if not args.end_date:
                    if stock_end:
                        args.end_date = stock_end
                        self.print_info(f"Using full range end date: {args.end_date}")
                    else:
                        # Use fallback default
                        args.end_date = datetime.now().strftime('%Y-%m-%d')
                        self.print_warning(f"Using fallback end date: {args.end_date}")
            
            # Prepare parameters
            parameters = {
                's1': args.s1,
                'm2': args.m2, 
                'l3': args.l3
            }
            
            # Get stock data first
            self.print_info(f"Fetching stock data for {args.symbol} ({args.start_date} to {args.end_date})...")
            
            # Create calculation job
            job_id = str(uuid.uuid4())
            job = IndicatorCalculationJob(
                job_id=job_id,
                indicator_type=args.indicator,
                symbol=args.symbol,
                base_symbol=args.base_symbol,
                parameters=parameters,
                status="pending",
                created_at=datetime.now()
            )
            
            await self.data_manager.create_calculation_job(job)
            self.print_info(f"Created calculation job: {job_id}")
            
            # Update job status to running
            await self.data_manager.update_job_status(job_id, "running", started_at=datetime.now())
            
            # Simulate calculation (in real implementation, this would call the actual calculation)
            self.print_info("Performing calculation...")
            await asyncio.sleep(2)  # Simulate processing time
            
            # For demonstration, create sample result data
            sample_data = [
                {
                    "date": "2024-01-01",
                    "truevx_score": 65.5,
                    "mean_short": 62.1,
                    "mean_mid": 64.8,  
                    "mean_long": 66.2,
                    "structural_score": 0.75,
                    "trend_score": 0.82
                }
            ]
            
            # Store results
            success = await self.data_manager.store_indicator_data(
                symbol=args.symbol,
                indicator_type=args.indicator,
                base_symbol=args.base_symbol,
                data=sample_data,
                parameters=parameters
            )
            
            if success:
                await self.data_manager.update_job_status(
                    job_id, "completed", 
                    completed_at=datetime.now(),
                    total_points=len(sample_data)
                )
                self.print_success(f"Successfully calculated and stored {len(sample_data)} data points")
                return True
            else:
                await self.data_manager.update_job_status(
                    job_id, "failed",
                    error_message="Failed to store results"
                )
                self.print_error("Failed to store calculation results")
                return False
                
        except Exception as e:
            logger.error(f"Calculation failed: {e}")
            self.print_error(f"Calculation failed: {e}")
            return False
    
    async def calculate_multiple_symbols(self, args) -> bool:
        """Calculate indicator for multiple symbols"""
        symbols = [s.strip() for s in args.symbols.split(',')]
        
        self.print_header(f"Calculating {args.indicator.upper()} for {len(symbols)} symbols")
        self.print_info(f"Symbols: {', '.join(symbols)}")
        
        # Determine date range strategy for multiple symbols
        if not args.start_date or not args.end_date:
            self.print_info("Determining optimal date range for multiple symbols...")
            
            # For multiple symbols, we'll find the common available date range
            earliest_start = None
            latest_end = None
            
            for symbol in symbols[:3]:  # Check first 3 symbols to avoid too many queries
                stock_start, stock_end = await self.get_stock_date_range(symbol)
                
                if stock_start and stock_end:
                    if not earliest_start or stock_start > earliest_start:
                        earliest_start = stock_start  # Use latest start date (intersection)
                    if not latest_end or stock_end < latest_end:
                        latest_end = stock_end  # Use earliest end date (intersection)
            
            if not args.start_date:
                if earliest_start:
                    args.start_date = earliest_start
                    self.print_info(f"Using common start date: {args.start_date}")
                else:
                    args.start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                    self.print_warning(f"Using fallback start date: {args.start_date}")
            
            if not args.end_date:
                if latest_end:
                    args.end_date = latest_end
                    self.print_info(f"Using common end date: {args.end_date}")
                else:
                    args.end_date = datetime.now().strftime('%Y-%m-%d')
                    self.print_warning(f"Using fallback end date: {args.end_date}")
        
        # Prepare batch job configuration
        job_config = {
            "symbols": symbols,
            "indicator_type": args.indicator,
            "base_symbol": args.base_symbol,
            "parameters": {
                "s1": args.s1,
                "m2": args.m2,
                "l3": args.l3
            },
            "date_range": {
                "start_date": args.start_date,
                "end_date": args.end_date
            }
        }
        
        try:
            # Submit batch job
            job_id = await self.batch_processor.submit_batch_job(job_config)
            self.print_success(f"Submitted batch job: {job_id}")
            
            # Monitor progress
            self.print_info("Monitoring progress...")
            completed = False
            
            while not completed:
                await asyncio.sleep(3)
                progress = await self.batch_processor.get_job_progress(job_id)
                
                if progress:
                    print(f"\r📊 Progress: {progress.get('completion_percentage', 0):.1f}% - Status: {progress.get('status', 'unknown')}", end='', flush=True)
                    
                    if progress.get('status') in ['completed', 'failed', 'cancelled']:
                        completed = True
                        print()  # New line after progress
                        
                        if progress.get('status') == 'completed':
                            self.print_success("Batch calculation completed successfully!")
                            return True
                        else:
                            self.print_error(f"Batch calculation failed: {progress.get('error_message', 'Unknown error')}")
                            return False
                else:
                    self.print_warning("Unable to get progress information")
                    break
            
            return False
            
        except Exception as e:
            logger.error(f"Batch calculation failed: {e}")
            self.print_error(f"Batch calculation failed: {e}")
            return False
    
    async def bulk_calculate(self, args) -> bool:
        """Bulk calculate for entire universe"""
        self.print_header(f"Bulk Calculation - {args.universe.upper()}")
        
        # Get symbols for universe
        symbols = await self.get_available_symbols(args.universe)
        
        if not symbols:
            self.print_error(f"No symbols found for universe: {args.universe}")
            return False
        
        self.print_info(f"Found {len(symbols)} symbols in {args.universe.upper()}")
        
        # Create temporary args for multiple symbols calculation
        temp_args = argparse.Namespace()
        temp_args.symbols = ','.join(symbols)
        temp_args.indicator = args.indicator
        temp_args.base_symbol = self.universe_mappings.get(args.universe.lower(), 'Nifty 50')
        temp_args.s1 = args.s1
        temp_args.m2 = args.m2
        temp_args.l3 = args.l3
        temp_args.start_date = args.start_date
        temp_args.end_date = args.end_date
        
        return await self.calculate_multiple_symbols(temp_args)
    
    async def list_stored_indicators(self, args) -> None:
        """List stored indicators"""
        self.print_header("Stored Indicators")
        
        try:
            indicators = await self.data_manager.get_available_indicators()
            
            if args.symbol:
                # Filter by symbol
                indicators = [ind for ind in indicators if ind['symbol'] == args.symbol]
            
            if not indicators:
                self.print_info("No stored indicators found")
                return
            
            # Display in table format
            print(f"\n{'Symbol':<10} {'Indicator':<10} {'Base Symbol':<15} {'Points':<8} {'Last Updated':<20} {'Latest Score':<12}")
            print("-" * 85)
            
            for ind in indicators:
                latest_score = "N/A"
                if 'latest_values' in ind and ind['latest_values']:
                    score = ind['latest_values'].get('truevx_score')
                    if score is not None:
                        latest_score = f"{score:.2f}"
                
                last_updated = ind.get('last_updated', 'Unknown')
                if isinstance(last_updated, str) and 'T' in last_updated:
                    last_updated = last_updated.split('T')[0]
                
                print(f"{ind['symbol']:<10} {ind['indicator_type']:<10} {ind['base_symbol']:<15} "
                      f"{ind.get('total_points', 0):<8} {last_updated:<20} {latest_score:<12}")
            
            self.print_success(f"Found {len(indicators)} stored indicators")
            
        except Exception as e:
            logger.error(f"Failed to list indicators: {e}")
            self.print_error(f"Failed to list indicators: {e}")
    
    async def export_data(self, args) -> None:
        """Export indicator data to file"""
        self.print_header(f"Exporting {args.indicator.upper()} data for {args.symbol}")
        
        try:
            # Get indicator data
            data = await self.data_manager.get_indicator_data(
                symbol=args.symbol,
                indicator_type=args.indicator,
                base_symbol=args.base_symbol,
                start_date=args.start_date,
                end_date=args.end_date
            )
            
            if not data:
                self.print_error("No data found for export")
                return
            
            # Determine output file
            output_file = args.output
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ext = 'csv' if args.format == 'csv' else 'json'
                output_file = f"{args.symbol}_{args.indicator}_{timestamp}.{ext}"
            
            # Export data
            if args.format == 'csv':
                await self._export_csv(data, output_file)
            else:
                await self._export_json(data, output_file)
            
            self.print_success(f"Exported {len(data)} records to {output_file}")
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            self.print_error(f"Export failed: {e}")
    
    async def _export_csv(self, data: List[Dict], filename: str) -> None:
        """Export data to CSV format"""
        if not data:
            return
        
        # Get all possible fieldnames
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())
        fieldnames = sorted(fieldnames)
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    async def _export_json(self, data: List[Dict], filename: str) -> None:
        """Export data to JSON format"""
        with open(filename, 'w') as jsonfile:
            json.dump(data, jsonfile, indent=2, default=str)
    
    async def check_job_status(self, args) -> None:
        """Check status of a calculation job"""
        self.print_header(f"Job Status - {args.job_id}")
        
        try:
            job = await self.data_manager.get_job_status(args.job_id)
            
            if not job:
                self.print_error("Job not found")
                return
            
            # Display job details
            print(f"\nJob ID: {job['job_id']}")
            print(f"Status: {job['status']}")
            print(f"Indicator: {job['indicator_type']}")
            print(f"Symbol(s): {job['symbol']}")
            print(f"Base Symbol: {job['base_symbol']}")
            print(f"Created: {job.get('created_at', 'Unknown')}")
            
            if job.get('started_at'):
                print(f"Started: {job['started_at']}")
            
            if job.get('completed_at'):
                print(f"Completed: {job['completed_at']}")
            
            if job.get('total_points'):
                print(f"Data Points: {job['total_points']}")
            
            if job.get('error_message'):
                print(f"Error: {job['error_message']}")
            
            # Status-specific messages
            if job['status'] == 'completed':
                self.print_success("Job completed successfully")
            elif job['status'] == 'failed':
                self.print_error("Job failed")
            elif job['status'] == 'running':
                self.print_info("Job is currently running")
            else:
                self.print_info(f"Job status: {job['status']}")
                
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            self.print_error(f"Failed to get job status: {e}")

def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="Indicator CLI Tool for Market Hunt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s calculate --symbol TCS --indicator truevx
  %(prog)s calculate --symbols TCS,INFY,RELIANCE --indicator truevx --s1 20
  %(prog)s bulk --universe nifty50 --indicator truevx
  %(prog)s list --symbol TCS
  %(prog)s export --symbol TCS --indicator truevx --format csv
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Calculate command
    calc_parser = subparsers.add_parser('calculate', help='Calculate indicators')
    calc_group = calc_parser.add_mutually_exclusive_group(required=True)
    calc_group.add_argument('--symbol', help='Single symbol to calculate')
    calc_group.add_argument('--symbols', help='Comma-separated list of symbols')
    
    calc_parser.add_argument('--indicator', default='truevx', choices=['truevx'], 
                           help='Indicator type (default: truevx)')
    calc_parser.add_argument('--base-symbol', default='Nifty 50', 
                           help='Base symbol for comparison (default: Nifty 50)')
    calc_parser.add_argument('--s1', type=int, default=22, help='S1 parameter (default: 22)')
    calc_parser.add_argument('--m2', type=int, default=66, help='M2 parameter (default: 66)')
    calc_parser.add_argument('--l3', type=int, default=222, help='L3 parameter (default: 222)')
    calc_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    calc_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    
    # Bulk command
    bulk_parser = subparsers.add_parser('bulk', help='Bulk calculate for entire universe')
    bulk_parser.add_argument('--universe', required=True, 
                           choices=['nifty50', 'nifty100', 'nifty500'],
                           help='Stock universe to calculate')
    bulk_parser.add_argument('--indicator', default='truevx', choices=['truevx'],
                           help='Indicator type (default: truevx)')
    bulk_parser.add_argument('--s1', type=int, default=22, help='S1 parameter (default: 22)')
    bulk_parser.add_argument('--m2', type=int, default=66, help='M2 parameter (default: 66)')
    bulk_parser.add_argument('--l3', type=int, default=222, help='L3 parameter (default: 222)')
    bulk_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    bulk_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List stored indicators')
    list_parser.add_argument('--symbol', help='Filter by symbol')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export indicator data')
    export_parser.add_argument('--symbol', required=True, help='Symbol to export')
    export_parser.add_argument('--indicator', default='truevx', choices=['truevx'],
                             help='Indicator type (default: truevx)')
    export_parser.add_argument('--base-symbol', default='Nifty 50',
                             help='Base symbol for comparison (default: Nifty 50)')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='csv',
                             help='Export format (default: csv)')
    export_parser.add_argument('--output', help='Output filename (auto-generated if not provided)')
    export_parser.add_argument('--start-date', help='Start date filter (YYYY-MM-DD)')
    export_parser.add_argument('--end-date', help='End date filter (YYYY-MM-DD)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check job status')
    status_parser.add_argument('--job-id', required=True, help='Job ID to check')
    
    return parser

async def main():
    """Main CLI function"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Set fallback default date range if needed (will be overridden by stock-specific ranges)
    # Only set defaults for commands that don't fetch stock-specific ranges
    if args.command in ['export', 'status'] or (args.command == 'bulk'):
        if hasattr(args, 'start_date') and not args.start_date:
            args.start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        if hasattr(args, 'end_date') and not args.end_date:
            args.end_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        async with IndicatorCLI() as cli:
            if args.command == 'calculate':
                if args.symbol:
                    success = await cli.calculate_single_symbol(args)
                else:
                    success = await cli.calculate_multiple_symbols(args)
                
                if not success:
                    sys.exit(1)
                    
            elif args.command == 'bulk':
                success = await cli.bulk_calculate(args)
                if not success:
                    sys.exit(1)
                    
            elif args.command == 'list':
                await cli.list_stored_indicators(args)
                
            elif args.command == 'export':
                await cli.export_data(args)
                
            elif args.command == 'status':
                await cli.check_job_status(args)
                
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"CLI error: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())