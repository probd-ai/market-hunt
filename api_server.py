#!/usr/bin/env python3
"""
FastAPI Backend Server for Market Hunt Frontend
Provides RESTful API endpoints for the Next.js frontend
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import pymongo
from pymongo import MongoClient
from bson import ObjectId
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uvicorn
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Market Hunt API",
    description="RESTful API for market research and analysis data",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "market_hunt"

class MongoDBConnection:
    def __init__(self):
        self.client = None
        self.db = None
    
    def connect(self):
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            logger.info(f"Connected to MongoDB: {DB_NAME}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def close(self):
        if self.client:
            self.client.close()

# Global MongoDB connection
mongo_conn = MongoDBConnection()

# In-memory process tracking (in production, this should be in Redis or database)
process_queue = []
running_processes = {}
completed_processes = []
process_counter = 0

# Pydantic models
class URLConfig(BaseModel):
    url: str
    index_name: str
    description: str
    tags: List[str]
    is_active: bool = True

class ProcessURLRequest(BaseModel):
    url_ids: List[str]

class ProcessEntry(BaseModel):
    id: str
    type: str
    status: str
    symbol: Optional[str] = None
    index_name: Optional[str] = None
    industry: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    items_processed: int = 0
    total_items: int = 0
    current_item: Optional[str] = None
    error_message: Optional[str] = None
    processing_details: Optional[List[Dict[str, Any]]] = None
    summary: Optional[Dict[str, Any]] = None

class TaskProgress(BaseModel):
    task_id: str
    status: str
    progress: float
    current_item: Optional[str] = None
    items_processed: int = 0
    total_items: int = 0
    start_time: Optional[str] = None
    estimated_completion: Optional[str] = None

# Helper function to serialize MongoDB documents
def serialize_doc(doc):
    if doc:
        doc['_id'] = str(doc['_id'])
        if 'created_at' in doc and doc['created_at']:
            doc['created_at'] = doc['created_at'].isoformat() if hasattr(doc['created_at'], 'isoformat') else str(doc['created_at'])
        if 'updated_at' in doc and doc['updated_at']:
            doc['updated_at'] = doc['updated_at'].isoformat() if hasattr(doc['updated_at'], 'isoformat') else str(doc['updated_at'])
        if 'last_downloaded' in doc and doc['last_downloaded']:
            doc['last_downloaded'] = doc['last_downloaded'].isoformat() if hasattr(doc['last_downloaded'], 'isoformat') else str(doc['last_downloaded'])
    return doc

# Scheduler helper functions
def create_process_entry(process_type: str, **kwargs) -> ProcessEntry:
    """Create a new process entry"""
    global process_counter
    process_counter += 1
    
    entry = ProcessEntry(
        id=f"process_{process_counter}",
        type=process_type,
        status="pending",
        created_at=datetime.now().isoformat(),
        **kwargs
    )
    return entry

def update_process_status(process_id: str, status: str, **kwargs):
    """Update process status and other fields"""
    # Update in running processes
    if process_id in running_processes:
        process = running_processes[process_id]
        process.status = status
        for key, value in kwargs.items():
            setattr(process, key, value)
        
        # Move to completed if finished
        if status in ["completed", "failed"]:
            completed_processes.append(process)
            del running_processes[process_id]
    
    # Update in queue
    for process in process_queue:
        if process.id == process_id:
            process.status = status
            for key, value in kwargs.items():
                setattr(process, key, value)
            break

def get_process_by_id(process_id: str) -> Optional[ProcessEntry]:
    """Get process by ID from any location"""
    # Check running processes
    if process_id in running_processes:
        return running_processes[process_id]
    
    # Check queue
    for process in process_queue:
        if process.id == process_id:
            return process
    
    # Check completed
    for process in completed_processes:
        if process.id == process_id:
            return process
    
    return None

@app.on_event("startup")
async def startup_event():
    mongo_conn.connect()

@app.on_event("shutdown")
async def shutdown_event():
    mongo_conn.close()

@app.get("/")
async def root():
    return {"message": "Market Hunt API Server", "version": "1.0.0", "status": "operational"}

@app.get("/api/urls")
async def get_urls(active_only: bool = False):
    """Get all URL configurations"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.index_meta_csv_urls
        
        # Build query
        query = {}
        if active_only:
            query["is_active"] = True
        
        # Get URLs
        urls = list(collection.find(query))
        
        # Serialize documents
        serialized_urls = [serialize_doc(url) for url in urls]
        
        return JSONResponse(content=serialized_urls)
        
    except Exception as e:
        logger.error(f"Error fetching URLs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch URLs: {str(e)}")

@app.get("/api/data")
async def get_data_overview():
    """Get data overview and statistics"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.index_meta
        
        # Get total documents
        total_documents = collection.count_documents({})
        
        # Get index-wise statistics
        pipeline = [
            {
                "$group": {
                    "_id": "$index_name",
                    "count": {"$sum": 1},
                    "last_update": {"$max": "$download_timestamp"}
                }
            }
        ]
        
        index_stats = list(collection.aggregate(pipeline))
        
        # Serialize timestamps
        for stat in index_stats:
            if stat.get('last_update'):
                stat['last_update'] = stat['last_update'].isoformat() if hasattr(stat['last_update'], 'isoformat') else str(stat['last_update'])
        
        return JSONResponse(content={
            "total_documents": total_documents,
            "index_stats": index_stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching data overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data overview: {str(e)}")

@app.get("/api/data/index/{index_name}")
async def get_index_companies(index_name: str):
    """Get all companies for a specific index"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        # Fetch all companies for the specified index
        collection = mongo_conn.db.index_meta
        companies = list(collection.find(
            {"index_name": index_name},
            {
                "_id": 0,
                "Company Name": 1,
                "Industry": 1,
                "Symbol": 1,
                "Series": 1,
                "ISIN Code": 1,
                "download_timestamp": 1
            }
        ).sort("Company Name", 1))  # Sort alphabetically by company name
        
        # Convert datetime objects to strings
        for company in companies:
            if 'download_timestamp' in company and company['download_timestamp']:
                company['download_timestamp'] = company['download_timestamp'].isoformat() if hasattr(company['download_timestamp'], 'isoformat') else str(company['download_timestamp'])
        
        return JSONResponse(content={
            "index_name": index_name,
            "total_companies": len(companies),
            "companies": companies
        })
    except Exception as e:
        logger.error(f"Error fetching companies for index {index_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch companies for index: {str(e)}")

@app.get("/api/industries")
async def get_industries_overview():
    """Get overview of all industries with company counts"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.index_meta
        
        # Get total companies count
        total_companies = collection.count_documents({})
        
        # Aggregate industry statistics with unique company counts
        pipeline = [
            {
                "$group": {
                    "_id": "$Industry",
                    "companies": {"$addToSet": "$Symbol"},
                    "indices": {"$addToSet": "$index_name"}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "count": {"$size": "$companies"},
                    "indices": 1
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]
        
        industry_stats = list(collection.aggregate(pipeline))
        
        # Calculate additional metrics
        total_industries = len(industry_stats)
        
        return JSONResponse(content={
            "total_companies": total_companies,
            "total_industries": total_industries,
            "industry_stats": industry_stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching industries overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch industries overview: {str(e)}")

@app.get("/api/industries/{industry_name}")
async def get_industry_companies(industry_name: str):
    """Get all unique companies for a specific industry"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.index_meta
        
        # Aggregate to get unique companies (by Symbol) for the specified industry
        pipeline = [
            {"$match": {"Industry": industry_name}},
            {
                "$group": {
                    "_id": "$Symbol",
                    "Company Name": {"$first": "$Company Name"},
                    "Industry": {"$first": "$Industry"},
                    "Symbol": {"$first": "$Symbol"},
                    "Series": {"$first": "$Series"},
                    "ISIN Code": {"$first": "$ISIN Code"},
                    "indices": {"$addToSet": "$index_name"},
                    "download_timestamp": {"$first": "$download_timestamp"}
                }
            },
            {"$sort": {"Company Name": 1}}
        ]
        
        companies = list(collection.aggregate(pipeline))
        
        # Convert datetime objects to strings and flatten the structure
        unique_companies = []
        for company in companies:
            company_data = {
                "Company Name": company["Company Name"],
                "Industry": company["Industry"],
                "Symbol": company["Symbol"],
                "Series": company["Series"],
                "ISIN Code": company["ISIN Code"],
                "indices": company["indices"],
                "download_timestamp": company["download_timestamp"].isoformat() if hasattr(company["download_timestamp"], 'isoformat') else str(company["download_timestamp"]) if company["download_timestamp"] else None
            }
            unique_companies.append(company_data)
        
        return JSONResponse(content={
            "industry_name": industry_name,
            "total_companies": len(unique_companies),
            "companies": unique_companies
        })
        
    except Exception as e:
        logger.error(f"Error fetching companies for industry {industry_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch companies for industry: {str(e)}")

@app.get("/api/industries/{industry_name}/indices")
async def get_industry_indices(industry_name: str):
    """Get all indices that contain companies from a specific industry"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.index_meta
        
        # Get unique indices for this industry
        indices = collection.distinct("index_name", {"Industry": industry_name})
        
        # Get company count per index for this industry
        pipeline = [
            {"$match": {"Industry": industry_name}},
            {
                "$group": {
                    "_id": "$index_name",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}}
        ]
        
        index_stats = list(collection.aggregate(pipeline))
        
        return JSONResponse(content={
            "industry_name": industry_name,
            "total_indices": len(indices),
            "indices": index_stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching indices for industry {industry_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch indices for industry: {str(e)}")

@app.get("/api/industries/{industry_name}/indices/{index_name}")
async def get_industry_index_companies(industry_name: str, index_name: str):
    """Get all companies for a specific industry within a specific index"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.index_meta
        
        # Fetch companies that belong to both the industry and the index
        companies = list(collection.find(
            {
                "Industry": industry_name,
                "index_name": index_name
            },
            {
                "_id": 0,
                "Company Name": 1,
                "Industry": 1,
                "Symbol": 1,
                "Series": 1,
                "ISIN Code": 1,
                "index_name": 1,
                "download_timestamp": 1
            }
        ).sort("Company Name", 1))
        
        # Convert datetime objects to strings
        for company in companies:
            if 'download_timestamp' in company and company['download_timestamp']:
                company['download_timestamp'] = company['download_timestamp'].isoformat() if hasattr(company['download_timestamp'], 'isoformat') else str(company['download_timestamp'])
        
        return JSONResponse(content={
            "industry_name": industry_name,
            "index_name": index_name,
            "total_companies": len(companies),
            "companies": companies
        })
        
    except Exception as e:
        logger.error(f"Error fetching companies for industry {industry_name} in index {index_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch companies for industry in index: {str(e)}")

@app.get("/api/data/index/{index_name}/industries")
async def get_index_industries(index_name: str):
    """Get all industries for a specific index with company counts"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.index_meta
        
        # Aggregate to get unique industries and their company counts for this index
        pipeline = [
            {"$match": {"index_name": index_name}},
            {
                "$group": {
                    "_id": "$Industry",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}}
        ]
        
        industries = list(collection.aggregate(pipeline))
        
        return JSONResponse(content={
            "index_name": index_name,
            "total_industries": len(industries),
            "industries": industries
        })
        
    except Exception as e:
        logger.error(f"Error fetching industries for index {index_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch industries for index: {str(e)}")

@app.get("/api/data/index/{index_name}/industries/{industry_name}")
async def get_index_industry_companies(index_name: str, industry_name: str):
    """Get all companies for a specific industry within a specific index"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.index_meta
        
        # Fetch companies that belong to both the index and the industry
        companies = list(collection.find(
            {
                "index_name": index_name,
                "Industry": industry_name
            },
            {
                "_id": 0,
                "Company Name": 1,
                "Industry": 1,
                "Symbol": 1,
                "Series": 1,
                "ISIN Code": 1,
                "download_timestamp": 1
            }
        ).sort("Company Name", 1))
        
        # Convert datetime objects to strings
        for company in companies:
            if 'download_timestamp' in company and company['download_timestamp']:
                company['download_timestamp'] = company['download_timestamp'].isoformat() if hasattr(company['download_timestamp'], 'isoformat') else str(company['download_timestamp'])
        
        return JSONResponse(content={
            "index_name": index_name,
            "industry_name": industry_name,
            "total_companies": len(companies),
            "companies": companies
        })
        
    except Exception as e:
        logger.error(f"Error fetching companies for industry {industry_name} in index {index_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch companies for industry in index: {str(e)}")

@app.post("/api/urls")
async def add_url(url_config: URLConfig):
    """Add a new URL configuration"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from url_manager import URLManager
        
        manager = URLManager()
        manager.connect_to_mongodb()
        
        success, message = manager.add_url(
            url=url_config.url,
            index_name=url_config.index_name,
            description=url_config.description,
            tags=url_config.tags
        )
        
        manager.close_connection()
        
        if success:
            return JSONResponse(content={"success": True, "message": message})
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        logger.error(f"Error adding URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add URL: {str(e)}")

class URLUpdateConfig(BaseModel):
    url: Optional[str] = None
    index_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

@app.put("/api/urls/{url_id}")
async def update_url(url_id: str, url_config: URLUpdateConfig):
    """Update an existing URL configuration"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from url_manager import URLManager
        
        manager = URLManager()
        manager.connect_to_mongodb()
        
        # Get the existing URL first
        try:
            existing_url = mongo_conn.db.index_meta_csv_urls.find_one({"_id": ObjectId(url_id)})
            if not existing_url:
                raise HTTPException(status_code=404, detail="URL not found")
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid URL ID format")
        
        # Prepare update data - only include fields that are provided
        update_data = {}
        if url_config.url is not None:
            update_data['url'] = url_config.url
        if url_config.index_name is not None:
            update_data['index_name'] = url_config.index_name
        if url_config.description is not None:
            update_data['description'] = url_config.description
        if url_config.tags is not None:
            update_data['tags'] = url_config.tags
        if url_config.is_active is not None:
            update_data['is_active'] = url_config.is_active
        
        # Always update the updated_at timestamp
        update_data['updated_at'] = datetime.now()
        
        # Update the document
        result = mongo_conn.db.index_meta_csv_urls.update_one(
            {"_id": ObjectId(url_id)},
            {"$set": update_data}
        )
        
        manager.close_connection()
        
        if result.modified_count > 0:
            return JSONResponse(content={"success": True, "message": "URL updated successfully"})
        else:
            return JSONResponse(content={"success": False, "message": "No changes made"})
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update URL: {str(e)}")

@app.post("/api/process")
async def process_urls(request: ProcessURLRequest):
    """Process data from specified URLs"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from generic_data_loader import GenericIndexDataLoader
        
        loader = GenericIndexDataLoader()
        loader.connect_to_mongodb()
        
        # Process specified URLs
        results = loader.process_specific_urls(request.url_ids)
        
        loader.close_connection()
        
        if results.get("success", False):
            processed_count = results.get("processed_count", 0)
            total_count = results.get("total_count", 0)
            
            return JSONResponse(content={
                "success": True, 
                "message": f"Successfully processed {processed_count}/{total_count} URLs",
                "processed_count": processed_count,
                "total_count": total_count,
                "results": results.get("results", [])
            })
        else:
            error_msg = results.get("error", "Unknown error occurred")
            processed_count = results.get("processed_count", 0)
            total_count = results.get("total_count", 0)
            
            return JSONResponse(content={
                "success": False,
                "message": f"Processed {processed_count}/{total_count} URLs with errors",
                "error": error_msg,
                "processed_count": processed_count,
                "total_count": total_count,
                "results": results.get("results", [])
            })
        
    except Exception as e:
        logger.error(f"Error processing URLs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process URLs: {str(e)}")

@app.delete("/api/urls/{url_id}")
async def delete_url(url_id: str):
    """Delete a URL configuration"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from url_manager import URLManager
        
        manager = URLManager()
        manager.connect_to_mongodb()
        
        success, message = manager.delete_url(url_id)
        
        manager.close_connection()
        
        if success:
            return JSONResponse(content={"success": True, "message": message})
        else:
            raise HTTPException(status_code=404, detail=message)
            
    except Exception as e:
        logger.error(f"Error deleting URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete URL: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test MongoDB connection
        if mongo_conn.db is not None:
            mongo_conn.db.command("ping")
            db_status = "connected"
        else:
            db_status = "disconnected"
        
        return JSONResponse(content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_status
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# ================================
# STOCK DATA MANAGEMENT ENDPOINTS
# ================================

class StockDataRequest(BaseModel):
    """Request model for stock data operations"""
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    index_name: Optional[str] = None
    industry_name: Optional[str] = None
    start_date: Optional[str] = None  # ISO format: YYYY-MM-DD
    end_date: Optional[str] = None    # ISO format: YYYY-MM-DD
    force_refresh: Optional[bool] = False
    sync_mode: Optional[str] = None   # 'load', 'refresh', 'delete' - load: smart sync from earliest missing year, refresh: full reload from 2005, delete: remove data

class StockDataResponse(BaseModel):
    """Response model for stock data operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

@app.get("/api/stock/mappings")
async def get_symbol_mappings(
    index_name: Optional[str] = None,
    industry: Optional[str] = None,
    mapped_only: bool = False,
    include_up_to_date: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None
):
    """Get symbol mappings between index_meta and NSE scripcode"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            mappings = await manager.get_symbol_mappings(
                index_name=index_name,
                industry=industry,
                mapped_only=mapped_only
            )
            
            # Apply pagination if specified
            total_mappings = len(mappings)
            if offset is not None:
                mappings = mappings[offset:]
            if limit is not None:
                mappings = mappings[:limit]
            
            # Convert to dict for JSON serialization
            mappings_data = []
            for mapping in mappings:
                # Only calculate up-to-date status if requested (performance optimization)
                is_up_to_date = None
                
                if include_up_to_date:
                    try:
                        if mapping.symbol and mapping.nse_scrip_code:
                            # Use complete historical gap analysis to determine if symbol is up-to-date
                            # Check for gaps in the last 60 days from today
                            from datetime import datetime, timedelta
                            end_date = datetime.now()
                            start_date = end_date - timedelta(days=60)
                            
                            gap_analysis = await manager.analyze_data_gaps(
                                symbol=mapping.symbol,
                                start_date=start_date,
                                end_date=end_date,
                                auto_download=False  # Don't auto-download, just analyze
                            )
                            
                            # Consider up-to-date if gap percentage is less than 20% in recent period
                            # and we have some actual data
                            gap_percentage = gap_analysis.get('gap_percentage', 100)
                            has_data = gap_analysis.get('has_data', False)
                            total_actual_days = gap_analysis.get('total_actual_days', 0)
                            
                            is_up_to_date = has_data and gap_percentage < 20 and total_actual_days > 0
                            
                    except Exception as gap_error:
                        logger.warning(f"Could not determine up-to-date status for {mapping.symbol}: {gap_error}")
                        is_up_to_date = False
                
                mapping_dict = {
                    "symbol": mapping.symbol,
                    "company_name": mapping.company_name,
                    "industry": mapping.industry,
                    "index_names": mapping.index_names,  # Now an array
                    "nse_scrip_code": mapping.nse_scrip_code,
                    "nse_symbol": mapping.nse_symbol,
                    "nse_name": mapping.nse_name,
                    "match_confidence": mapping.match_confidence,
                    "last_updated": mapping.last_updated.isoformat() if mapping.last_updated else None,
                    "is_up_to_date": is_up_to_date
                }
                mappings_data.append(mapping_dict)
            
            return JSONResponse(content={
                "total_mappings": total_mappings,
                "returned_count": len(mappings_data),
                "mapped_count": len([m for m in mappings_data if m["nse_scrip_code"] is not None]),
                "offset": offset or 0,
                "limit": limit,
                "mappings": mappings_data
            })
            
    except Exception as e:
        logger.error(f"Error fetching symbol mappings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch symbol mappings: {str(e)}")

@app.post("/api/stock/mappings/refresh")
async def refresh_symbol_mappings():
    """Refresh symbol mappings from index_meta and NSE masters"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            result = await manager.refresh_symbol_mappings_from_index_meta()
            
            return JSONResponse(content={
                "success": True,
                "message": "Symbol mappings refreshed successfully",
                "result": result
            })
            
    except Exception as e:
        logger.error(f"Error refreshing symbol mappings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh symbol mappings: {str(e)}")

@app.post("/api/stock/mappings/fix-duplicates")
async def fix_duplicate_nse_codes():
    """Fix duplicate NSE scrip codes and incorrect mappings"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.symbol_mappings
        fixed_count = 0
        issues_found = []
        
        # Find duplicate NSE scrip codes
        pipeline = [
            {"$group": {
                "_id": "$nse_scrip_code",
                "symbols": {"$push": {"symbol": "$symbol", "nse_name": "$nse_name", "company_name": "$company_name"}},
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gt": 1}, "_id": {"$ne": None}}}
        ]
        
        duplicates = list(collection.aggregate(pipeline))
        
        for dup in duplicates:
            nse_code = dup["_id"]
            symbols = dup["symbols"]
            
            issues_found.append({
                "nse_scrip_code": nse_code,
                "symbols": symbols,
                "issue": "duplicate_nse_code"
            })
            
            # Specific fix for IOC/BIOCON issue (NSE code 11373)
            if nse_code == 11373:
                # Keep BIOCON with 11373, fix IOC
                for symbol_info in symbols:
                    if symbol_info["symbol"] == "IOC":
                        # Remove incorrect NSE mapping for IOC
                        result = collection.update_one(
                            {"symbol": "IOC"},
                            {"$unset": {
                                "nse_scrip_code": "",
                                "nse_symbol": "",
                                "nse_name": ""
                            },
                             "$set": {
                                "match_confidence": 0.0,
                                "last_updated": datetime.now()
                            }}
                        )
                        if result.modified_count > 0:
                            fixed_count += 1
                            logger.info(f"Fixed IOC mapping - removed incorrect NSE code 11373")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Fixed {fixed_count} duplicate mappings",
            "fixed_count": fixed_count,
            "issues_found": issues_found
        })
        
    except Exception as e:
        logger.error(f"Error fixing duplicate NSE codes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fix duplicates: {str(e)}")

@app.post("/api/stock/mappings/update-status")
async def update_up_to_date_status(
    symbols: Optional[List[str]] = None,
    batch_size: int = 10
):
    """Update up-to-date status for symbols in batches (performance optimized)"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from stock_data_manager import StockDataManager
        from datetime import datetime, timedelta
        
        async with StockDataManager() as manager:
            # Get symbols to update
            if symbols is None:
                # Get all symbols if none specified
                mappings = await manager.get_symbol_mappings(mapped_only=True)
                symbols = [m.symbol for m in mappings if m.symbol and m.nse_scrip_code]
            
            updated_count = 0
            failed_count = 0
            
            # Process in batches for better performance
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                
                for symbol in batch:
                    try:
                        # Quick gap analysis for recent data only
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=30)  # Shorter window for faster processing
                        
                        gap_analysis = await manager.analyze_data_gaps(
                            symbol=symbol,
                            start_date=start_date,
                            end_date=end_date,
                            auto_download=False
                        )
                        
                        # Determine up-to-date status
                        gap_percentage = gap_analysis.get('gap_percentage', 100)
                        has_data = gap_analysis.get('has_data', False)
                        total_actual_days = gap_analysis.get('total_actual_days', 0)
                        
                        is_up_to_date = has_data and gap_percentage < 30 and total_actual_days > 0  # More lenient for faster processing
                        
                        # Update in database
                        collection = mongo_conn.db.symbol_mappings
                        await collection.update_one(
                            {"symbol": symbol},
                            {"$set": {"is_up_to_date": is_up_to_date, "status_updated_at": datetime.now()}}
                        )
                        
                        updated_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to update status for {symbol}: {e}")
                        failed_count += 1
            
            return JSONResponse(content={
                "success": True,
                "message": f"Updated {updated_count} symbols, {failed_count} failed",
                "updated_count": updated_count,
                "failed_count": failed_count,
                "total_processed": len(symbols)
            })
            
    except Exception as e:
        logger.error(f"Error updating up-to-date status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")

@app.get("/api/stock/data/{symbol}")
async def get_stock_price_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = 100
):
    """Get historical price data for a symbol"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from stock_data_manager import StockDataManager
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        async with StockDataManager() as manager:
            price_data = await manager.get_price_data(
                symbol=symbol,
                start_date=start_dt,
                end_date=end_dt,
                limit=limit
            )
            
            # Convert to dict for JSON serialization
            price_records = []
            for record in price_data:
                price_dict = {
                    "scrip_code": record.scrip_code,
                    "symbol": record.symbol,
                    "date": record.date.isoformat(),
                    "open_price": record.open_price,
                    "high_price": record.high_price,
                    "low_price": record.low_price,
                    "close_price": record.close_price,
                    "volume": record.volume,
                    "value": record.value,
                    "year_partition": record.year_partition
                }
                price_records.append(price_dict)
            
            return JSONResponse(content={
                "symbol": symbol,
                "total_records": len(price_records),
                "data": price_records
            })
            
    except Exception as e:
        logger.error(f"Error fetching price data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch price data: {str(e)}")

class GapAnalysisRequest(BaseModel):
    """Request model for gap analysis"""
    symbol: Optional[str] = None
    index_name: Optional[str] = None
    industry: Optional[str] = None
    start_date: str  # ISO format: YYYY-MM-DD
    end_date: str    # ISO format: YYYY-MM-DD
    auto_download: bool = True  # Whether to download missing data first

@app.post("/api/stock/gaps")
async def analyze_data_gaps(request: GapAnalysisRequest):
    """Analyze data gaps for symbols, indexes, or industries
    
    If auto_download=True (default), will attempt to download missing data first
    before performing gap analysis. This ensures accurate gap detection.
    """
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from stock_data_manager import StockDataManager
        
        # Parse dates
        start_dt = datetime.fromisoformat(request.start_date)
        end_dt = datetime.fromisoformat(request.end_date)
        
        async with StockDataManager() as manager:
            if request.symbol:
                # Single symbol gap analysis
                gaps = await manager.analyze_data_gaps(
                    symbol=request.symbol,
                    start_date=start_dt,
                    end_date=end_dt,
                    auto_download=request.auto_download
                )
                return JSONResponse(content={
                    "symbol": request.symbol,
                    "date_range": {
                        "start": request.start_date,
                        "end": request.end_date
                    },
                    "gaps": gaps
                })
            
            elif request.index_name:
                # Index gap analysis
                symbols = await manager.get_index_symbols(request.index_name)
                if not symbols:
                    raise HTTPException(status_code=404, detail=f"Index {request.index_name} not found")
                
                all_gaps = {}
                for symbol in symbols[:5]:  # Limit to first 5 for performance
                    gaps = await manager.analyze_data_gaps(
                        symbol=symbol,
                        start_date=start_dt,
                        end_date=end_dt,
                        auto_download=request.auto_download
                    )
                    all_gaps[symbol] = gaps
                
                return JSONResponse(content={
                    "index_name": request.index_name,
                    "date_range": {
                        "start": request.start_date,
                        "end": request.end_date
                    },
                    "symbols_analyzed": list(all_gaps.keys()),
                    "gaps": all_gaps
                })
            
            elif request.industry:
                # Industry gap analysis
                symbols = await manager.get_industry_symbols(request.industry)
                if not symbols:
                    raise HTTPException(status_code=404, detail=f"Industry {request.industry} not found")
                
                all_gaps = {}
                for symbol in symbols[:5]:  # Limit to first 5 for performance
                    gaps = await manager.analyze_data_gaps(
                        symbol=symbol,
                        start_date=start_dt,
                        end_date=end_dt,
                        auto_download=request.auto_download
                    )
                    all_gaps[symbol] = gaps
                
                return JSONResponse(content={
                    "industry": request.industry,
                    "date_range": {
                        "start": request.start_date,
                        "end": request.end_date
                    },
                    "symbols_analyzed": list(all_gaps.keys()),
                    "gaps": all_gaps
                })
            else:
                raise HTTPException(status_code=400, detail="Must specify symbol, index_name, or industry")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing data gaps: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze gaps: {str(e)}")

@app.post("/api/stock/download")
async def download_stock_data(request: StockDataRequest, background_tasks: BackgroundTasks):
    """Download historical stock data for symbols, indexes, or industries"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        # Parse dates
        start_dt = datetime.fromisoformat(request.start_date) if request.start_date else None
        end_dt = datetime.fromisoformat(request.end_date) if request.end_date else None
        
        # Handle sync_mode mapping
        force_refresh = request.force_refresh
        smart_load = False  # New flag for smart loading from earliest missing year
        
        if request.sync_mode:
            if request.sync_mode == 'refresh':
                force_refresh = True  # Full reload from 2005
                start_dt = datetime(2005, 1, 1)  # Override start date for refresh
            elif request.sync_mode == 'load':
                smart_load = True  # Smart load from earliest missing year
                force_refresh = False
            # 'delete' mode is handled separately in delete endpoints
        
        # Determine download type and create scheduler entry
        if request.symbol:
            # Single symbol download
            process = create_process_entry(
                process_type="symbol_download",
                symbol=request.symbol,
                total_items=1
            )
            process_queue.append(process)
            
            background_tasks.add_task(
                download_symbol_data_task,
                process.id,
                request.symbol,
                start_dt,
                end_dt,
                force_refresh,
                smart_load
            )
            return JSONResponse(content={
                "success": True,
                "message": f"Started downloading data for symbol: {request.symbol}",
                "type": "symbol",
                "process_id": process.id
            })
            
        elif request.symbols:
            # Multiple symbols download
            process = create_process_entry(
                process_type="symbols_download",
                total_items=len(request.symbols)
            )
            process_queue.append(process)
            
            background_tasks.add_task(
                download_symbols_data_task,
                process.id,
                request.symbols,
                start_dt,
                end_dt,
                force_refresh,
                smart_load
            )
            return JSONResponse(content={
                "success": True,
                "message": f"Started downloading data for {len(request.symbols)} symbols",
                "type": "symbols",
                "process_id": process.id
            })
            
        elif request.index_name:
            # Index download - get symbol count first
            try:
                collection = mongo_conn.db.symbol_mappings
                symbol_count = collection.count_documents({"index_names": request.index_name})
                if symbol_count == 0:
                    raise HTTPException(status_code=404, detail=f"No symbols found for index: {request.index_name}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get symbol count: {str(e)}")
            
            process = create_process_entry(
                process_type="index_download",
                index_name=request.index_name,
                total_items=symbol_count
            )
            process_queue.append(process)
            
            background_tasks.add_task(
                download_index_data_task,
                process.id,
                request.index_name,
                start_dt,
                end_dt,
                force_refresh,
                smart_load
            )
            return JSONResponse(content={
                "success": True,
                "message": f"Started downloading data for index: {request.index_name} ({symbol_count} symbols)",
                "type": "index",
                "process_id": process.id
            })
            
        elif request.industry_name:
            # Industry download - get symbol count first
            try:
                collection = mongo_conn.db.index_meta
                symbol_count = collection.count_documents({"Industry": request.industry_name})
                if symbol_count == 0:
                    raise HTTPException(status_code=404, detail=f"No symbols found for industry: {request.industry_name}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get symbol count: {str(e)}")
            
            process = create_process_entry(
                process_type="industry_download",
                industry=request.industry_name,
                total_items=symbol_count
            )
            process_queue.append(process)
            
            background_tasks.add_task(
                download_industry_data_task,
                process.id,
                request.industry_name,
                start_dt,
                end_dt,
                force_refresh,
                smart_load
            )
            return JSONResponse(content={
                "success": True,
                "message": f"Started downloading data for industry: {request.industry_name} ({symbol_count} symbols)",
                "type": "industry",
                "process_id": process.id
            })
        else:
            raise HTTPException(status_code=400, detail="Must specify symbol, symbols, index_name, or industry_name")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting stock data download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start download: {str(e)}")

@app.get("/api/stock/statistics")
async def get_stock_data_statistics():
    """Get statistics about stored stock price data"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            stats = await manager.get_data_statistics()
            
            # Convert datetime objects to strings for JSON serialization
            if stats.get("date_range"):
                if stats["date_range"]["earliest"]:
                    stats["date_range"]["earliest"] = stats["date_range"]["earliest"].isoformat()
                if stats["date_range"]["latest"]:
                    stats["date_range"]["latest"] = stats["date_range"]["latest"].isoformat()
            
            return JSONResponse(content=stats)
            
    except Exception as e:
        logger.error(f"Error fetching stock data statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")

# Background task functions for stock data downloads
async def download_symbol_data_task(process_id: str, symbol: str, start_date: datetime, end_date: datetime, force_refresh: bool, smart_load: bool = False):
    """Background task to download data for a single symbol"""
    processing_details = []
    summary = {
        "total_symbols": 1,
        "successful_symbols": 0,
        "failed_symbols": 0,
        "total_records_added": 0,
        "total_records_updated": 0,
        "total_records_skipped": 0
    }
    
    try:
        # Move process from queue to running
        process = get_process_by_id(process_id)
        if process:
            update_process_status(process_id, "running", started_at=datetime.now().isoformat())
            running_processes[process_id] = process
            # Remove from queue
            global process_queue
            process_queue = [p for p in process_queue if p.id != process_id]
        
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            processing_start = datetime.now()
            detail = {
                "symbol": symbol,
                "status": "error",
                "records_added": 0,
                "records_updated": 0,
                "records_skipped": 0,
                "processing_time": "",
                "error_message": None
            }
            
            try:
                result = await manager.download_historical_data_for_symbol(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    force_refresh=force_refresh,
                    smart_load=smart_load
                )
                
                # Calculate processing time
                processing_end = datetime.now()
                processing_time = processing_end - processing_start
                detail["processing_time"] = f"{processing_time.total_seconds():.2f}s"
                
                # Extract result details
                if isinstance(result, dict):
                    # Check if result contains an error
                    if "error" in result:
                        detail["status"] = "error"
                        detail["error_message"] = result["error"]
                        summary["failed_symbols"] += 1
                    else:
                        detail["records_added"] = result.get("records_added", 0)
                        detail["records_updated"] = result.get("records_updated", 0)
                        detail["records_skipped"] = result.get("records_skipped", 0)
                        detail["status"] = "success"
                        
                        # Update summary
                        summary["total_records_added"] += detail["records_added"]
                        summary["total_records_updated"] += detail["records_updated"]
                        summary["total_records_skipped"] += detail["records_skipped"]
                        summary["successful_symbols"] += 1
                else:
                    detail["status"] = "success"
                    summary["successful_symbols"] += 1
                
                logger.info(f"✅ Background download completed for symbol {symbol}: {result}")
                
            except Exception as e:
                detail["status"] = "error"
                detail["error_message"] = str(e)
                summary["failed_symbols"] += 1
                processing_end = datetime.now()
                processing_time = processing_end - processing_start
                detail["processing_time"] = f"{processing_time.total_seconds():.2f}s"
                logger.error(f"❌ Failed to download data for symbol {symbol}: {e}")
            
            processing_details.append(detail)
            
            # Update process as completed with detailed results
            process = get_process_by_id(process_id)
            if process:
                process.processing_details = processing_details
                process.summary = summary
            
            update_process_status(
                process_id, 
                "completed", 
                completed_at=datetime.now().isoformat(),
                items_processed=1
            )
            
    except Exception as e:
        # Update process as failed
        update_process_status(
            process_id, 
            "failed", 
            completed_at=datetime.now().isoformat(),
            error_message=str(e)
        )
        logger.error(f"❌ Background download failed for symbol {symbol}: {e}")

async def download_symbols_data_task(process_id: str, symbols: List[str], start_date: datetime, end_date: datetime, force_refresh: bool, smart_load: bool = False):
    """Background task to download data for multiple symbols"""
    processing_details = []
    summary = {
        "total_symbols": len(symbols),
        "successful_symbols": 0,
        "failed_symbols": 0,
        "total_records_added": 0,
        "total_records_updated": 0,
        "total_records_skipped": 0
    }
    
    try:
        # Move process from queue to running
        process = get_process_by_id(process_id)
        if process:
            update_process_status(process_id, "running", started_at=datetime.now().isoformat())
            running_processes[process_id] = process
            # Remove from queue
            global process_queue
            process_queue = [p for p in process_queue if p.id != process_id]
        
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            completed_count = 0
            for i, symbol in enumerate(symbols):
                processing_start = datetime.now()
                detail = {
                    "symbol": symbol,
                    "status": "error",
                    "records_added": 0,
                    "records_updated": 0,
                    "records_skipped": 0,
                    "processing_time": "",
                    "error_message": None
                }
                
                try:
                    # Update progress
                    update_process_status(
                        process_id,
                        "running",
                        items_processed=i,
                        current_item=symbol
                    )
                    
                    result = await manager.download_historical_data_for_symbol(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        force_refresh=force_refresh,
                        smart_load=smart_load
                    )
                    
                    # Calculate processing time
                    processing_end = datetime.now()
                    processing_time = processing_end - processing_start
                    detail["processing_time"] = f"{processing_time.total_seconds():.2f}s"
                    
                    # Extract result details
                    if isinstance(result, dict):
                        # Check if result contains an error
                        if "error" in result:
                            detail["status"] = "error"
                            detail["error_message"] = result["error"]
                            summary["failed_symbols"] += 1
                        else:
                            detail["records_added"] = result.get("records_added", 0)
                            detail["records_updated"] = result.get("records_updated", 0)
                            detail["records_skipped"] = result.get("records_skipped", 0)
                            detail["status"] = "success"
                            
                            # Update summary
                            summary["total_records_added"] += detail["records_added"]
                            summary["total_records_updated"] += detail["records_updated"]
                            summary["total_records_skipped"] += detail["records_skipped"]
                            summary["successful_symbols"] += 1
                    else:
                        detail["status"] = "success"
                        summary["successful_symbols"] += 1
                    
                    completed_count += 1
                    logger.info(f"✅ Downloaded data for symbol {symbol}: {result}")
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    detail["status"] = "error"
                    detail["error_message"] = str(e)
                    summary["failed_symbols"] += 1
                    processing_end = datetime.now()
                    processing_time = processing_end - processing_start
                    detail["processing_time"] = f"{processing_time.total_seconds():.2f}s"
                    logger.error(f"❌ Failed to download data for symbol {symbol}: {e}")
                
                processing_details.append(detail)
            
            # Update process as completed with detailed results
            process = get_process_by_id(process_id)
            if process:
                process.processing_details = processing_details
                process.summary = summary
                
            update_process_status(
                process_id, 
                "completed", 
                completed_at=datetime.now().isoformat(),
                items_processed=completed_count
            )
                    
    except Exception as e:
        # Update process as failed
        update_process_status(
            process_id, 
            "failed", 
            completed_at=datetime.now().isoformat(),
            error_message=str(e)
        )
        logger.error(f"❌ Background download failed for symbols: {e}")

async def download_index_data_task(process_id: str, index_name: str, start_date: datetime, end_date: datetime, force_refresh: bool, smart_load: bool = False):
    """Background task to download data for an index with proper progress tracking"""
    try:
        # Move process from queue to running
        process = get_process_by_id(process_id)
        if process:
            update_process_status(process_id, "running", started_at=datetime.now().isoformat())
            running_processes[process_id] = process
            # Remove from queue
            global process_queue
            process_queue = [p for p in process_queue if p.id != process_id]
        
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            # Get all symbols for the index to track progress
            mappings = await manager.get_symbol_mappings(index_name=index_name, mapped_only=True)
            total_symbols = len(mappings)
            
            if total_symbols == 0:
                update_process_status(
                    process_id, 
                    "failed", 
                    completed_at=datetime.now().isoformat(),
                    error_message=f"No mapped symbols found for index {index_name}"
                )
                return
            
            # Update total items count
            update_process_status(process_id, "running", total_items=total_symbols)
            
            # Process each symbol individually for progress tracking
            successful_downloads = 0
            errors = []
            processing_details = []
            total_records_added = 0
            total_records_updated = 0
            total_records_skipped = 0
            
            for i, mapping in enumerate(mappings):
                try:
                    # Update current progress
                    update_process_status(
                        process_id, 
                        "running",
                        items_processed=i,
                        current_item=mapping.symbol
                    )
                    
                    # Download data for this symbol
                    result = await manager.download_historical_data_for_symbol(
                        symbol=mapping.symbol,
                        start_date=start_date,
                        end_date=end_date,
                        force_refresh=force_refresh,
                        smart_load=smart_load
                    )
                    
                    # Extract detailed results
                    detail = {
                        "symbol": mapping.symbol,
                        "company_name": mapping.company_name,
                        "status": "success",
                        "records_added": result.get('records_added', 0),
                        "records_updated": result.get('records_updated', 0),
                        "records_skipped": result.get('records_skipped', 0),
                        "date_range": f"{result.get('start_date', 'N/A')} to {result.get('end_date', 'N/A')}",
                        "processing_time": result.get('processing_time', 'N/A'),
                        "total_records": result.get('total_records', 0)
                    }
                    
                    processing_details.append(detail)
                    total_records_added += detail['records_added']
                    total_records_updated += detail['records_updated']
                    total_records_skipped += detail['records_skipped']
                    successful_downloads += 1
                    
                    logger.info(f"✅ Downloaded data for {mapping.symbol} ({i+1}/{total_symbols})")
                    
                    # Small delay to avoid overwhelming the API
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    error_msg = f"Error downloading data for {mapping.symbol}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)
                    
                    # Add failed symbol to processing details
                    processing_details.append({
                        "symbol": mapping.symbol,
                        "company_name": mapping.company_name,
                        "status": "failed",
                        "error": str(e),
                        "records_added": 0,
                        "records_updated": 0,
                        "records_skipped": 0,
                        "date_range": "N/A",
                        "processing_time": "N/A",
                        "total_records": 0
                    })
            
            # Create summary
            summary = {
                "total_symbols": total_symbols,
                "successful_downloads": successful_downloads,
                "failed_downloads": len(errors),
                "total_records_added": total_records_added,
                "total_records_updated": total_records_updated,
                "total_records_skipped": total_records_skipped,
                "success_rate": round((successful_downloads / total_symbols) * 100, 2) if total_symbols > 0 else 0,
                "date_range": f"{start_date.date() if start_date else 'N/A'} to {end_date.date() if end_date else 'N/A'}",
                "index_name": index_name
            }
            
            # Update process as completed with details
            update_process_status(
                process_id, 
                "completed", 
                completed_at=datetime.now().isoformat(),
                items_processed=total_symbols,
                current_item=None,
                processing_details=processing_details,
                summary=summary
            )
            
            logger.info(f"✅ Background download completed for index {index_name}: {successful_downloads}/{total_symbols} successful")
            
    except Exception as e:
        # Update process as failed
        update_process_status(
            process_id, 
            "failed", 
            completed_at=datetime.now().isoformat(),
            error_message=str(e)
        )
        logger.error(f"❌ Background download failed for index {index_name}: {e}")

async def download_industry_data_task(process_id: str, industry_name: str, start_date: datetime, end_date: datetime, force_refresh: bool, smart_load: bool = False):
    """Background task to download data for an industry with proper progress tracking"""
    try:
        # Move process from queue to running
        process = get_process_by_id(process_id)
        if process:
            update_process_status(process_id, "running", started_at=datetime.now().isoformat())
            running_processes[process_id] = process
            # Remove from queue
            global process_queue
            process_queue = [p for p in process_queue if p.id != process_id]
        
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            # Get all symbols for the industry to track progress
            mappings = await manager.get_symbol_mappings(industry=industry_name, mapped_only=True)
            total_symbols = len(mappings)
            
            if total_symbols == 0:
                update_process_status(
                    process_id, 
                    "failed", 
                    completed_at=datetime.now().isoformat(),
                    error_message=f"No mapped symbols found for industry {industry_name}"
                )
                return
            
            # Update total items count
            update_process_status(process_id, "running", total_items=total_symbols)
            
            # Process each symbol individually for progress tracking
            successful_downloads = 0
            errors = []
            
            for i, mapping in enumerate(mappings):
                try:
                    # Update current progress
                    update_process_status(
                        process_id, 
                        "running",
                        items_processed=i,
                        current_item=mapping.symbol
                    )
                    
                    # Download data for this symbol
                    result = await manager.download_historical_data_for_symbol(
                        symbol=mapping.symbol,
                        start_date=start_date,
                        end_date=end_date,
                        force_refresh=force_refresh,
                        smart_load=smart_load
                    )
                    
                    successful_downloads += 1
                    logger.info(f"✅ Downloaded data for {mapping.symbol} ({i+1}/{total_symbols})")
                    
                    # Small delay to avoid overwhelming the API
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    error_msg = f"Error downloading data for {mapping.symbol}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)
            
            # Update process as completed
            update_process_status(
                process_id, 
                "completed", 
                completed_at=datetime.now().isoformat(),
                items_processed=total_symbols,
                current_item=None
            )
            
            logger.info(f"✅ Background download completed for industry {industry_name}: {successful_downloads}/{total_symbols} successful")
            
    except Exception as e:
        # Update process as failed
        update_process_status(
            process_id, 
            "failed", 
            completed_at=datetime.now().isoformat(),
            error_message=str(e)
        )
        logger.error(f"❌ Background download failed for industry {industry_name}: {e}")

# Scheduler API Endpoints
@app.get("/api/scheduler/processes")
async def get_all_processes():
    """Get all processes (pending, running, completed)"""
    try:
        # Convert ProcessEntry objects to dictionaries
        pending = [process.dict() for process in process_queue if process.status == "pending"]
        running = [process.dict() for process in running_processes.values()]
        completed = [process.dict() for process in completed_processes[-50:]]  # Last 50 completed
        
        return {
            "pending": pending,
            "running": running,
            "completed": completed
        }
    except Exception as e:
        logger.error(f"Error getting processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scheduler/processes/{process_id}/progress")
async def get_process_progress(process_id: str):
    """Get detailed progress for a specific process"""
    try:
        process = get_process_by_id(process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")
        
        # Calculate progress percentage
        progress = 0.0
        if process.total_items > 0:
            progress = (process.items_processed / process.total_items) * 100
        
        # Estimate completion time
        estimated_completion = None
        if process.started_at and process.items_processed > 0 and progress > 0:
            start_time = datetime.fromisoformat(process.started_at)
            elapsed = datetime.now() - start_time
            rate = process.items_processed / elapsed.total_seconds()
            remaining_items = process.total_items - process.items_processed
            if rate > 0:
                eta_seconds = remaining_items / rate
                estimated_completion = (datetime.now() + timedelta(seconds=eta_seconds)).isoformat()
        
        return TaskProgress(
            task_id=process.id,
            status=process.status,
            progress=progress,
            current_item=getattr(process, 'current_item', None),
            items_processed=process.items_processed,
            total_items=process.total_items,
            start_time=process.started_at,
            estimated_completion=estimated_completion
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scheduler/processes/{process_id}/details")
async def get_process_details(process_id: str):
    """Get detailed processing results for a completed process"""
    try:
        process = get_process_by_id(process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")
        
        # Return available process details
        return {
            "process_id": process_id,
            "status": process.status,
            "type": process.type,
            "symbol": process.symbol,
            "index_name": process.index_name,
            "industry": process.industry,
            "started_at": process.started_at,
            "completed_at": process.completed_at,
            "items_processed": process.items_processed,
            "total_items": process.total_items,
            "processing_details": process.processing_details or [],
            "summary": process.summary or {},
            "error_message": process.error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scheduler/processes/{process_id}/cancel")
async def cancel_process(process_id: str):
    """Cancel a pending or running process"""
    try:
        process = get_process_by_id(process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")
        
        if process.status in ["completed", "failed"]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed process")
        
        update_process_status(process_id, "cancelled", completed_at=datetime.now().isoformat())
        
        return {"message": f"Process {process_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/scheduler/processes/{process_id}")
async def delete_process(process_id: str):
    """Delete a completed or failed process from history"""
    try:
        process = get_process_by_id(process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")
        
        if process.status in ["pending", "running"]:
            raise HTTPException(status_code=400, detail="Cannot delete active process")
        
        # Remove from completed processes
        global completed_processes
        completed_processes = [p for p in completed_processes if p.id != process_id]
        
        return {"message": f"Process {process_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=True)
