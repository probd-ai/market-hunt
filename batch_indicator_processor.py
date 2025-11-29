#!/usr/bin/env python3
"""
Batch Indicator Processing System
Handles bulk calculation and storage of indicators
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from concurrent.futures import ThreadPoolExecutor
import json

from indicator_data_manager import IndicatorDataManager, IndicatorCalculationJob
from indicator_engine import IndicatorEngine

logger = logging.getLogger(__name__)

class BatchIndicatorProcessor:
    """
    Handles batch processing of indicators with progress tracking
    """
    
    def __init__(self):
        self.active_jobs: Dict[str, asyncio.Task] = {}
        # Auto-recover interrupted jobs on startup
        asyncio.create_task(self._recover_interrupted_jobs())
    
    def __init__(self, max_concurrent_jobs: int = 3):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs = {}
        self.job_queue = []
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_jobs)
        
        # Initialize engines
        self.indicator_engine = IndicatorEngine()
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs = {}
        self.job_queue = []
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_jobs)
        
        # Initialize engines
        self.indicator_engine = IndicatorEngine()
        
    async def submit_batch_job(self, job_config: Dict[str, Any]) -> str:
        """
        Submit a batch indicator calculation job
        
        Args:
            job_config: {
                "symbols": ["TCS", "INFY", "RELIANCE"],
                "indicator_type": "truevx",
                "base_symbol": "Nifty 50",
                "parameters": {"s1": 22, "m2": 66, "l3": 222},
                "date_range": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                }
            }
            
        Returns:
            str: Job ID for tracking
        """
        job_id = str(uuid.uuid4())
        
        try:
            async with IndicatorDataManager() as data_manager:
                # Create job record
                job = IndicatorCalculationJob(
                    job_id=job_id,
                    indicator_type=job_config["indicator_type"],
                    symbol=",".join(job_config["symbols"]),  # Store as comma-separated
                    base_symbol=job_config["base_symbol"],
                    parameters=job_config["parameters"],
                    status="pending",
                    created_at=datetime.now()
                )
                
                await data_manager.create_calculation_job(job)
                
                # Add to processing queue
                self.job_queue.append({
                    "job_id": job_id,
                    "config": job_config
                })
                
                # Start processing if not at max capacity
                await self._process_queue()
                
                logger.info(f"✅ Submitted batch job {job_id} for {len(job_config['symbols'])} symbols")
                return job_id
                
        except Exception as e:
            logger.error(f"❌ Failed to submit batch job: {e}")
            raise
    
    async def _process_queue(self):
        """Process jobs in the queue"""
        while len(self.active_jobs) < self.max_concurrent_jobs and self.job_queue:
            job_item = self.job_queue.pop(0)
            job_id = job_item["job_id"]
            
            # Start processing job
            self.active_jobs[job_id] = asyncio.create_task(
                self._process_single_job(job_id, job_item["config"])
            )
    
    async def _process_single_job(self, job_id: str, config: Dict[str, Any]):
        """Process a single batch job"""
        symbols = config["symbols"]
        indicator_type = config["indicator_type"]
        base_symbol = config["base_symbol"]
        parameters = config["parameters"]
        date_range = config["date_range"]
        
        logger.info(f"🚀 Starting batch job {job_id} for {len(symbols)} symbols")
        
        async with IndicatorDataManager() as data_manager:
            try:
                # Update job status to running
                await data_manager.update_job_status(
                    job_id, 
                    "running",
                    started_at=datetime.now(),
                    total_points=len(symbols)
                )
                
                completed_symbols = []
                failed_symbols = []
                
                # Process each symbol
                for i, symbol in enumerate(symbols):
                    try:
                        logger.info(f"📊 Processing {symbol} ({i+1}/{len(symbols)}) for job {job_id}")
                        
                        # Get stock data first
                        from stock_data_manager import StockDataManager
                        
                        async with StockDataManager() as stock_manager:
                            # Parse dates - handle empty strings by using fallback dates
                            start_date_str = date_range["start_date"]
                            end_date_str = date_range["end_date"]
                            
                            # If dates are empty, get full range for the symbol or use fallbacks
                            if not start_date_str or not end_date_str:
                                # Try to get symbol date range
                                try:
                                    symbol_range = await stock_manager.get_symbol_date_range(symbol)
                                    if symbol_range:
                                        start_dt = symbol_range['earliest'] if not start_date_str else datetime.fromisoformat(start_date_str)
                                        if not end_date_str:
                                            end_dt = symbol_range['latest']
                                        else:
                                            # Parse end date and set to end of day to include all data for that date
                                            end_dt = datetime.fromisoformat(end_date_str).replace(hour=23, minute=59, second=59)
                                        logger.info(f"📅 Using symbol {symbol} data range: {start_dt.date()} to {end_dt.date()}")
                                    else:
                                        # Fallback to wide range
                                        start_dt = datetime(2020, 1, 1)
                                        end_dt = datetime.now()
                                        logger.warning(f"⚠️ No data range found for {symbol}, using fallback: {start_dt.date()} to {end_dt.date()}")
                                except Exception as range_error:
                                    logger.error(f"❌ Error getting date range for {symbol}: {range_error}")
                                    start_dt = datetime(2020, 1, 1)
                                    end_dt = datetime.now()
                            else:
                                start_dt = datetime.fromisoformat(start_date_str)
                                # Parse end date and set to end of day to include all data for that date
                                end_dt = datetime.fromisoformat(end_date_str).replace(hour=23, minute=59, second=59)
                            
                            # Get price data for the symbol
                            price_data = await stock_manager.get_price_data(
                                symbol=symbol,
                                start_date=start_dt,
                                end_date=end_dt,
                                limit=None,  # No limit - get all data in range
                                sort_order=1  # Ascending
                            )
                            
                            if not price_data:
                                failed_symbols.append(symbol)
                                logger.error(f"❌ No price data found for {symbol}")
                                continue
                                
                            # Convert to dict format for indicator engine
                            price_records = []
                            for record in price_data:
                                price_dict = {
                                    "date": record.date.isoformat(),
                                    "open_price": record.open_price,
                                    "high_price": record.high_price,
                                    "low_price": record.low_price,
                                    "close_price": record.close_price,
                                    "volume": record.volume,
                                }
                                price_records.append(price_dict)
                        
                        # Calculate indicator
                        if indicator_type == "truevx":
                            result = await self.indicator_engine.calculate_truevx_ranking(
                                data=price_records,
                                base_symbol=base_symbol,
                                start_date=date_range["start_date"],
                                end_date=date_range["end_date"],
                                s1=parameters.get("s1", 22),
                                m2=parameters.get("m2", 66),
                                l3=parameters.get("l3", 222)
                            )
                        else:
                            raise ValueError(f"Unsupported indicator type: {indicator_type}")
                        
                        # Store results
                        if result:
                            success = await data_manager.store_indicator_data(
                                symbol=symbol,
                                indicator_type=indicator_type,
                                base_symbol=base_symbol,
                                data=result,
                                parameters=parameters
                            )
                            
                            if success:
                                completed_symbols.append(symbol)
                                logger.info(f"✅ Completed {symbol} ({len(result)} points)")
                            else:
                                failed_symbols.append(symbol)
                                logger.error(f"❌ Failed to store data for {symbol}")
                        else:
                            failed_symbols.append(symbol)
                            logger.error(f"❌ No data calculated for {symbol}")
                            
                    except Exception as e:
                        failed_symbols.append(symbol)
                        logger.error(f"❌ Error processing {symbol}: {e}")
                        import traceback
                        logger.error(f"❌ Traceback: {traceback.format_exc()}")
                        logger.error(f"❌ Error processing {symbol}: {e}")
                
                # Update final job status
                final_status = "completed" if not failed_symbols else "partial_failure"
                if not completed_symbols:
                    final_status = "failed"
                
                await data_manager.update_job_status(
                    job_id,
                    final_status,
                    completed_at=datetime.now(),
                    error_message=f"Failed symbols: {failed_symbols}" if failed_symbols else None
                )
                
                logger.info(f"🎉 Job {job_id} completed: {len(completed_symbols)} success, {len(failed_symbols)} failed")
                
            except Exception as e:
                # Update job status to failed
                await data_manager.update_job_status(
                    job_id,
                    "failed",
                    completed_at=datetime.now(),
                    error_message=str(e)
                )
                logger.error(f"💥 Job {job_id} failed: {e}")
            
            finally:
                # Remove from active jobs
                if job_id in self.active_jobs:
                    del self.active_jobs[job_id]
                
                # Process next job in queue
                await self._process_queue()
    
    async def get_job_progress(self, job_id: str) -> Dict[str, Any]:
        """Get detailed progress for a specific job"""
        return await self._get_job_progress_from_db(job_id)
    
    async def _get_job_progress_from_db(self, job_id: str) -> Dict[str, Any]:
        """Helper method to get job progress from database with completion percentage calculation"""
        async with IndicatorDataManager() as data_manager:
            # Get job details
            job = await data_manager.get_job_status(job_id)
            
            if not job:
                return {"error": "Job not found"}
            
            # Calculate completion percentage for active jobs
            if job_id in self.active_jobs and job.get("symbol"):
                # Parse symbols and count completed ones using a more efficient method
                all_symbols = job["symbol"].split(",") if job["symbol"] else []
                total_symbols = len(all_symbols)
                
                if total_symbols > 0:
                    # Count completed symbols more efficiently using database count
                    completed_count = 0
                    for symbol in all_symbols:
                        # Use a simple database query to check existence
                        try:
                            existing_count = await data_manager.count_indicator_data(
                                symbol=symbol.strip(),
                                indicator_type=job.get("indicator_type", "truevx"),
                                base_symbol=job.get("base_symbol", "Nifty 50")
                            )
                            if existing_count > 0:
                                completed_count += 1
                        except:
                            # Fallback to the old method if count method doesn't exist
                            existing_data = await data_manager.get_indicator_data(
                                symbol=symbol.strip(),
                                indicator_type=job.get("indicator_type", "truevx"),
                                base_symbol=job.get("base_symbol", "Nifty 50")
                            )
                            if existing_data:
                                completed_count += 1
                    
                    completion_percentage = (completed_count / total_symbols) * 100
                    job["completion_percentage"] = completion_percentage
                else:
                    job["completion_percentage"] = 0.0
            else:
                # For completed jobs or jobs without symbols
                if job.get("status") == "completed":
                    job["completion_percentage"] = 100.0
                else:
                    job["completion_percentage"] = 0.0
            
            return job

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        try:
            # First, try to cancel active job
            if job_id in self.active_jobs:
                # Cancel the task
                self.active_jobs[job_id].cancel()
                del self.active_jobs[job_id]
                logger.info(f"🛑 Cancelled active job task {job_id}")
            
            # Always update database status to cancelled for any job in "running" status
            # This handles stuck jobs after restarts
            async with IndicatorDataManager() as data_manager:
                job_status = await data_manager.get_job_status(job_id)
                
                if job_status:
                    await data_manager.update_job_status(
                        job_id,
                        "cancelled",
                        completed_at=datetime.now()
                    )
                    logger.info(f"🛑 Updated job {job_id} status to cancelled")
                    return True
                else:
                    logger.warning(f"⚠️ Job {job_id} not found in database")
                    return False
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel job {job_id}: {e}")
            return False
    
    async def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all recent jobs with their status"""
        async with IndicatorDataManager() as data_manager:
            jobs = await data_manager.get_recent_jobs(limit=100)
            
            # Add active status and convert symbols string to array
            for job in jobs:
                job["is_active"] = job["job_id"] in self.active_jobs
                # Convert comma-separated symbols string to array
                if "symbol" in job and job["symbol"]:
                    job["symbols"] = job["symbol"].split(",")
                else:
                    job["symbols"] = []
                
                # BUGFIX: Calculate completion percentage for active jobs
                if job["is_active"]:
                    # Get the full job progress including completion percentage
                    try:
                        full_progress = await self._get_job_progress_from_db(job["job_id"])
                        job["completion_percentage"] = full_progress.get("completion_percentage", 0.0)
                    except Exception as e:
                        logger.warning(f"Failed to get completion percentage for job {job['job_id']}: {e}")
                        job["completion_percentage"] = 0.0
                else:
                    # For completed/failed jobs, set appropriate completion percentage
                    if job.get("status") == "completed":
                        job["completion_percentage"] = 100.0
                    else:
                        job["completion_percentage"] = 0.0
            
            return jobs
    
    async def cleanup_old_jobs(self, days_old: int = 30):
        """Clean up job records older than specified days"""
        # This would be implemented to clean up old job records
        # For now, we'll keep all records
        pass

# Global batch processor instance
batch_processor = BatchIndicatorProcessor()

# Convenience functions for API
async def submit_truevx_batch_job(symbols: List[str], base_symbol: str = "Nifty 50", 
                                 start_date: str = "2020-01-01", end_date: str = "2025-12-31",
                                 s1: int = 22, m2: int = 66, l3: int = 222) -> str:
    """
    Submit a TrueValueX batch calculation job
    """
    job_config = {
        "symbols": symbols,
        "indicator_type": "truevx",
        "base_symbol": base_symbol,
        "parameters": {"s1": s1, "m2": m2, "l3": l3},
        "date_range": {
            "start_date": start_date,
            "end_date": end_date
        }
    }
    
    return await batch_processor.submit_batch_job(job_config)

async def get_batch_job_progress(job_id: str) -> Dict[str, Any]:
    """Get batch job progress"""
    return await batch_processor.get_job_progress(job_id)

async def cancel_batch_job(job_id: str) -> bool:
    """Cancel a batch job"""
    return await batch_processor.cancel_job(job_id)

async def list_all_batch_jobs() -> List[Dict[str, Any]]:
    """List all batch jobs"""
    return await batch_processor.get_all_jobs()

# Testing
if __name__ == "__main__":
    async def test_batch_processing():
        # Test with a few symbols
        test_symbols = ["TCS", "INFY", "RELIANCE"]
        
        logger.info("🧪 Testing batch processing...")
        
        job_id = await submit_truevx_batch_job(
            symbols=test_symbols,
            base_symbol="Nifty 50",
            start_date="2024-01-01",
            end_date="2024-01-31"  # Short range for testing
        )
        
        print(f"✅ Submitted test job: {job_id}")
        
        # Monitor progress
        for _ in range(10):
            await asyncio.sleep(5)
            progress = await get_batch_job_progress(job_id)
            print(f"📊 Progress: {progress['completion_percentage']:.1f}% - Status: {progress['status']}")
            
            if progress["status"] in ["completed", "failed", "cancelled"]:
                break
    
    # Run test
    asyncio.run(test_batch_processing())
