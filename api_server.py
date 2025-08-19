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

# Pydantic models
class URLConfig(BaseModel):
    url: str
    index_name: str
    description: str
    tags: List[str]
    is_active: bool = True

class ProcessURLRequest(BaseModel):
    url_ids: List[str]

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
                    "_id": {
                        "industry": "$Industry",
                        "symbol": "$Symbol"
                    },
                    "index_name": {"$first": "$index_name"}
                }
            },
            {
                "$group": {
                    "_id": "$_id.industry",
                    "count": {"$sum": 1},
                    "indices": {"$addToSet": "$index_name"}
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
        if mongo_conn.db:
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
    mapped_only: bool = False
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
            
            # Convert to dict for JSON serialization
            mappings_data = []
            for mapping in mappings:
                mapping_dict = {
                    "symbol": mapping.symbol,
                    "company_name": mapping.company_name,
                    "industry": mapping.industry,
                    "index_names": mapping.index_names,  # Now an array
                    "nse_scrip_code": mapping.nse_scrip_code,
                    "nse_symbol": mapping.nse_symbol,
                    "nse_name": mapping.nse_name,
                    "match_confidence": mapping.match_confidence,
                    "last_updated": mapping.last_updated.isoformat() if mapping.last_updated else None
                }
                mappings_data.append(mapping_dict)
            
            return JSONResponse(content={
                "total_mappings": len(mappings_data),
                "mapped_count": len([m for m in mappings_data if m["nse_scrip_code"] is not None]),
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

@app.get("/api/stock/data/{symbol}")
async def get_stock_price_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = 1000  # Increased default limit
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
            # Get total count without limit for progress tracking
            total_count = await manager.get_price_data_count(
                symbol=symbol,
                start_date=start_dt,
                end_date=end_dt
            )
            
            # Get actual data with limit (sorted by date descending - newest first)
            price_data = await manager.get_price_data(
                symbol=symbol,
                start_date=start_dt,
                end_date=end_dt,
                limit=limit,
                sort_order=-1  # -1 for descending (newest first)
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
                "total_records": total_count,  # Actual total count
                "returned_records": len(price_records),  # Records in this response
                "data": price_records
            })
            
    except Exception as e:
        logger.error(f"Error fetching price data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch price data: {str(e)}")

@app.post("/api/stock/download")
async def download_stock_data(request: StockDataRequest, background_tasks: BackgroundTasks):
    """Download historical stock data for symbols, indexes, or industries"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        # Parse dates
        start_dt = datetime.fromisoformat(request.start_date) if request.start_date else None
        end_dt = datetime.fromisoformat(request.end_date) if request.end_date else None
        
        # Determine download type
        if request.symbol:
            # Single symbol download
            background_tasks.add_task(
                download_symbol_data_task,
                request.symbol,
                start_dt,
                end_dt,
                request.force_refresh
            )
            return JSONResponse(content={
                "success": True,
                "message": f"Started downloading data for symbol: {request.symbol}",
                "type": "symbol"
            })
            
        elif request.symbols:
            # Multiple symbols download
            background_tasks.add_task(
                download_symbols_data_task,
                request.symbols,
                start_dt,
                end_dt,
                request.force_refresh
            )
            return JSONResponse(content={
                "success": True,
                "message": f"Started downloading data for {len(request.symbols)} symbols",
                "type": "symbols"
            })
            
        elif request.index_name:
            # Index download
            background_tasks.add_task(
                download_index_data_task,
                request.index_name,
                start_dt,
                end_dt,
                request.force_refresh
            )
            return JSONResponse(content={
                "success": True,
                "message": f"Started downloading data for index: {request.index_name}",
                "type": "index"
            })
            
        elif request.industry_name:
            # Industry download
            background_tasks.add_task(
                download_industry_data_task,
                request.industry_name,
                start_dt,
                end_dt,
                request.force_refresh
            )
            return JSONResponse(content={
                "success": True,
                "message": f"Started downloading data for industry: {request.industry_name}",
                "type": "industry"
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

@app.post("/api/stock/check-gaps")
def check_stock_gaps(symbols: List[str]):
    """Get gap status for multiple symbols from the cached gap_status collection"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        gap_statuses = []
        for symbol in symbols:
            symbol = symbol.upper()
            
            # Get cached gap status from database
            gap_doc = mongo_conn.db["gap_status"].find_one({"symbol": symbol})
            
            if not gap_doc:
                # No cached status found, return default values
                gap_statuses.append({
                    "symbol": symbol,
                    "company_name": "Unknown",
                    "industry": "Unknown",
                    "index_names": [],
                    "nse_scrip_code": None,
                    "has_data": False,
                    "record_count": 0,
                    "date_range": {"start": None, "end": None},
                    "data_freshness_days": 0,
                    "coverage_percentage": 0,
                    "last_price": None,
                    "needs_update": True,
                    "gap_details": ["Gap status not calculated yet. Run 'update-gap-status' command."],
                    "last_calculated": None
                })
            else:
                # Convert cached status to response format
                gap_statuses.append({
                    "symbol": gap_doc["symbol"],
                    "company_name": gap_doc["company_name"],
                    "industry": gap_doc["industry"],
                    "index_names": gap_doc["index_names"],
                    "nse_scrip_code": gap_doc["nse_scrip_code"],
                    "has_data": gap_doc["has_data"],
                    "record_count": gap_doc["record_count"],
                    "date_range": gap_doc["date_range"],
                    "data_freshness_days": gap_doc["data_freshness_days"],
                    "coverage_percentage": gap_doc["coverage_percentage"],
                    "last_price": gap_doc.get("last_price"),
                    "needs_update": gap_doc["needs_update"],
                    "gap_details": gap_doc["gap_details"],
                    "last_calculated": gap_doc["last_calculated"].isoformat() if gap_doc.get("last_calculated") else None
                })
        
        return JSONResponse(content=gap_statuses)
        
    except Exception as e:
        logger.error(f"Error checking stock gaps: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check gaps: {str(e)}")

# Background task functions for stock data downloads
async def download_symbol_data_task(symbol: str, start_date: datetime, end_date: datetime, force_refresh: bool):
    """Background task to download data for a single symbol"""
    try:
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            result = await manager.download_historical_data_for_symbol(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                force_refresh=force_refresh
            )
            logger.info(f"✅ Background download completed for symbol {symbol}: {result}")
            
    except Exception as e:
        logger.error(f"❌ Background download failed for symbol {symbol}: {e}")

async def download_symbols_data_task(symbols: List[str], start_date: datetime, end_date: datetime, force_refresh: bool):
    """Background task to download data for multiple symbols"""
    try:
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            for symbol in symbols:
                try:
                    result = await manager.download_historical_data_for_symbol(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        force_refresh=force_refresh
                    )
                    logger.info(f"✅ Downloaded data for symbol {symbol}: {result}")
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.error(f"❌ Failed to download data for symbol {symbol}: {e}")
                    
    except Exception as e:
        logger.error(f"❌ Background download failed for symbols: {e}")

async def download_index_data_task(index_name: str, start_date: datetime, end_date: datetime, force_refresh: bool):
    """Background task to download data for an index"""
    try:
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            result = await manager.download_historical_data_for_index(
                index_name=index_name,
                start_date=start_date,
                end_date=end_date,
                force_refresh=force_refresh
            )
            logger.info(f"✅ Background download completed for index {index_name}: {result}")
            
    except Exception as e:
        logger.error(f"❌ Background download failed for index {index_name}: {e}")

async def download_industry_data_task(industry_name: str, start_date: datetime, end_date: datetime, force_refresh: bool):
    """Background task to download data for an industry"""
    try:
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            result = await manager.download_historical_data_for_industry(
                industry_name=industry_name,
                start_date=start_date,
                end_date=end_date,
                force_refresh=force_refresh
            )
            logger.info(f"✅ Background download completed for industry {industry_name}: {result}")
            
    except Exception as e:
        logger.error(f"❌ Background download failed for industry {industry_name}: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=True)
