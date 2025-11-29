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
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
import uvicorn
import asyncio
import aiohttp
import pandas as pd  # Added for indicator optimizations
import numpy as np  # Added for enhanced analytics
import random  # Added for simulation
import json  # Added for enhanced JSON serialization
import io  # Added for PDF generation
from fastapi.responses import StreamingResponse  # Added for PDF downloads
from brokerage_calculator import (
    BrokerageCalculator, 
    TransactionCharges, 
    TradeDetails, 
    calculate_single_trade_charges,
    estimate_portfolio_charges
)  # Added for brokerage calculation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# JSON serialization helper
def sanitize_for_json(obj):
    """Recursively sanitize objects for JSON serialization"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return sanitize_for_json(obj.__dict__)
    else:
        return obj

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

class IndicatorRequest(BaseModel):
    symbol: str
    indicator_type: str
    period: Optional[int] = 20
    fast_period: Optional[int] = 12
    slow_period: Optional[int] = 26
    signal_period: Optional[int] = 9
    std_dev: Optional[float] = 2.0
    base_symbol: Optional[str] = "Nifty 500"  # Default base for CRS
    lookback: Optional[List[int]] = None  # Multiple lookback periods for Dynamic Fibonacci
    start_date: Optional[str] = None  # ISO format: YYYY-MM-DD
    end_date: Optional[str] = None    # ISO format: YYYY-MM-DD
    price_field: Optional[str] = "close_price"  # Field to use for calculation
    
    # TrueValueX specific parameters
    s1: Optional[int] = None  # Alpha (short lookback)
    m2: Optional[int] = None  # Beta (mid lookback)
    l3: Optional[int] = None  # Gamma (long lookback)
    strength: Optional[int] = None  # Trend Strength (bars)
    w_long: Optional[float] = None  # Weight Long
    w_mid: Optional[float] = None   # Weight Mid
    w_short: Optional[float] = None # Weight Short
    deadband_frac: Optional[float] = None  # Deadband γ (fraction of range)
    min_deadband: Optional[float] = None   # Minimum Deadband
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

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
        
        # Get total unique companies (by Symbol)
        unique_companies_pipeline = [
            {
                "$group": {
                    "_id": "$Symbol"
                }
            },
            {
                "$count": "unique_companies"
            }
        ]
        unique_companies_result = list(collection.aggregate(unique_companies_pipeline))
        unique_companies_count = unique_companies_result[0]["unique_companies"] if unique_companies_result else 0
        
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
            "total_documents": unique_companies_count,
            "index_stats": index_stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching data overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data overview: {str(e)}")

@app.get("/api/data/universes")
async def get_available_universes():
    """Get all available universes (indexes) from the database"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = mongo_conn.db.index_meta
        
        # Get all unique index names with their stock counts
        pipeline = [
            {
                "$group": {
                    "_id": "$index_name",
                    "stock_count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        universes_data = list(collection.aggregate(pipeline))
        
        # Format the response
        universes = []
        for universe in universes_data:
            index_name = universe["_id"]
            stock_count = universe["stock_count"]
            
            # Create display name with stock count
            display_name = f"{index_name} ({stock_count} stocks)"
            
            universes.append({
                "value": index_name,
                "label": display_name,
                "stock_count": stock_count
            })
        
        logger.info(f"📊 Found {len(universes)} available universes")
        
        return JSONResponse(content={
            "universes": universes,
            "total_universes": len(universes)
        })
        
    except Exception as e:
        logger.error(f"Error fetching universes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch universes: {str(e)}")

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
        
        # Get total unique companies count (by Symbol)
        unique_companies_pipeline = [
            {
                "$group": {
                    "_id": "$Symbol"
                }
            },
            {
                "$count": "unique_companies"
            }
        ]
        unique_companies_result = list(collection.aggregate(unique_companies_pipeline))
        unique_companies_count = unique_companies_result[0]["unique_companies"] if unique_companies_result else 0
        
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
            "total_companies": unique_companies_count,
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

@app.get("/api/stock/available")
async def get_available_symbols(
    index_name: Optional[str] = None,
    industry: Optional[str] = None,
    limit: Optional[int] = None,
    search: Optional[str] = None
):
    """Get all available symbols from the database with optional filtering"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from stock_data_manager import StockDataManager
        
        async with StockDataManager() as manager:
            mappings = await manager.get_symbol_mappings(
                index_name=index_name,
                industry=industry,
                mapped_only=True  # Only return symbols with NSE mapping
            )
            
            # Convert to simplified format for frontend
            symbols_data = []
            for mapping in mappings:
                symbol_dict = {
                    "symbol": mapping.symbol,
                    "name": mapping.company_name,
                    "sector": mapping.industry,
                    "index_names": mapping.index_names,
                    "nse_symbol": mapping.nse_symbol,
                    "last_updated": mapping.last_updated.isoformat() if mapping.last_updated else None
                }
                symbols_data.append(symbol_dict)
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                symbols_data = [
                    s for s in symbols_data 
                    if search_lower in s["symbol"].lower() or 
                       search_lower in s["name"].lower() or
                       search_lower in (s["sector"] or "").lower()
                ]
            
            # Apply limit if provided
            if limit:
                symbols_data = symbols_data[:limit]
            
            # Sort by symbol name for consistent ordering
            symbols_data.sort(key=lambda x: x["symbol"])
            
            return JSONResponse(content={
                "success": True,
                "total": len(symbols_data),
                "symbols": symbols_data,
                "filters": {
                    "index_name": index_name,
                    "industry": industry,
                    "search": search,
                    "limit": limit
                }
            })
            
    except Exception as e:
        logger.error(f"Error fetching available symbols: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch available symbols: {str(e)}")

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

@app.post("/api/stock/indicators")
async def calculate_stock_indicators(request: IndicatorRequest):
    """Calculate technical indicators for stock price data - Optimized"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        from stock_data_manager import StockDataManager
        from indicator_engine import IndicatorEngine
        
        # Optimize date range - if not provided, use smart defaults based on indicator period
        if not request.start_date or not request.end_date:
            end_dt = datetime.now()
            
            # Special handling for TrueValueX which needs much more data (l3=222 default)
            if request.indicator_type == 'truevx':
                # TrueValueX needs at least 222 points + buffer, so get ~2 years of data
                min_points_needed = 500  # Conservative estimate for TrueValueX
                days_needed = min_points_needed * 1.8  # Account for weekends/holidays
                start_dt = end_dt - pd.Timedelta(days=days_needed)
                logger.info(f"Auto-calculated TrueValueX date range: {start_dt.date()} to {end_dt.date()}")
            else:
                # Calculate minimum required data points (period * 3 for better SMA accuracy)
                min_points_needed = max(request.period * 3, 100)  
                
                # Estimate days needed (accounting for weekends/holidays)
                days_needed = min_points_needed * 1.5
                start_dt = end_dt - pd.Timedelta(days=days_needed)
                
                logger.info(f"Auto-calculated date range: {start_dt.date()} to {end_dt.date()} for {request.period}-period indicator")
        else:
            start_dt = datetime.fromisoformat(request.start_date)
            end_dt = datetime.fromisoformat(request.end_date)
        
        # Get price data with optimized limit
        async with StockDataManager() as manager:
            # Calculate appropriate limit based on date range
            date_range_days = (end_dt - start_dt).days
            if date_range_days > 365 * 5:  # More than 5 years
                initial_limit = 50000  # Large limit for ALL timeframe
            elif date_range_days > 365:    # More than 1 year
                initial_limit = 20000  # Medium limit for 5Y timeframe
            else:
                initial_limit = 10000  # Small limit for 1Y timeframe
            
            logger.info(f"Using limit {initial_limit} for {date_range_days} days of data")
            
            price_data = await manager.get_price_data(
                symbol=request.symbol,
                start_date=start_dt,
                end_date=end_dt,
                limit=initial_limit,
                sort_order=1  # Ascending order for indicator calculation
            )
            
            if not price_data:
                raise HTTPException(status_code=404, detail=f"No price data found for symbol {request.symbol}")
            
            # Check if we have enough data for the indicator
            if len(price_data) < request.period:
                # Try to get more data by extending the date range
                extended_start = start_dt - pd.Timedelta(days=365)  # Go back 1 year
                logger.info(f"Insufficient data ({len(price_data)} points), extending range to {extended_start.date()}")
                
                price_data = await manager.get_price_data(
                    symbol=request.symbol,
                    start_date=extended_start,
                    end_date=end_dt,
                    limit=20000,
                    sort_order=1
                )
                
                if len(price_data) < request.period:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Insufficient data for {request.period}-period indicator. Found {len(price_data)} points, need at least {request.period}"
                    )
            
            # Convert price data to dict format for indicator engine (optimized)
            price_records = []
            for record in price_data:
                price_dict = {
                    "date": record.date.isoformat(),
                    "close_price": record.close_price,  # Always include close_price
                }
                
                # Only include other fields if needed
                if request.price_field != 'close_price':
                    price_dict[request.price_field] = getattr(record, request.price_field)
                
                # For MACD, Bollinger, CRS, Dynamic Fibonacci, and TrueValueX indicators, include OHLC
                if request.indicator_type in ['macd', 'bollinger', 'crs', 'dynamic_fib', 'truevx']:
                    price_dict.update({
                        "open_price": record.open_price,
                        "high_price": record.high_price,
                        "low_price": record.low_price,
                        "volume": record.volume,
                    })
                
                price_records.append(price_dict)
            
            # Initialize indicator engine
            engine = IndicatorEngine()
            
            # Prepare parameters for indicator calculation
            calc_params = {
                "period": request.period,
                "price_field": request.price_field
            }
            
            # Add specific parameters for different indicators
            if request.indicator_type == 'macd':
                calc_params.update({
                    "fast_period": request.fast_period,
                    "slow_period": request.slow_period,
                    "signal_period": request.signal_period
                })
            elif request.indicator_type == 'bollinger':
                calc_params.update({
                    "std_dev": request.std_dev
                })
            elif request.indicator_type == 'crs':
                calc_params.update({
                    "base_symbol": request.base_symbol,
                    "start_date": start_dt.isoformat() if start_dt else None,
                    "end_date": end_dt.isoformat() if end_dt else None
                })
            elif request.indicator_type == 'dynamic_fib':
                # Set default lookback periods if not provided
                lookback_periods = request.lookback if request.lookback else [22, 66, 222]
                calc_params.update({
                    "lookback": lookback_periods
                })
            elif request.indicator_type == 'truevx':
                calc_params.update({
                    "base_symbol": request.base_symbol or "Nifty 50",
                    "start_date": start_dt.isoformat() if start_dt else None,
                    "end_date": end_dt.isoformat() if end_dt else None
                })
            
            # Calculate indicator (now with caching and optimization)
            try:
                calculation_start = datetime.now()
                
                # Special handling for CRS and TrueValueX since they're async
                if request.indicator_type == 'crs':
                    indicator_data = await engine.calculate_crs(
                        data=price_records,
                        base_symbol=request.base_symbol,
                        start_date=start_dt.isoformat() if start_dt else None,
                        end_date=end_dt.isoformat() if end_dt else None
                    )
                elif request.indicator_type == 'truevx':
                    # Pass additional TrueValueX parameters
                    truevx_params = {}
                    if request.s1 is not None:
                        truevx_params['s1'] = request.s1
                    if request.m2 is not None:
                        truevx_params['m2'] = request.m2
                    if request.l3 is not None:
                        truevx_params['l3'] = request.l3
                    if request.strength is not None:
                        truevx_params['strength'] = request.strength
                    if request.w_long is not None:
                        truevx_params['w_long'] = request.w_long
                    if request.w_mid is not None:
                        truevx_params['w_mid'] = request.w_mid
                    if request.w_short is not None:
                        truevx_params['w_short'] = request.w_short
                    if request.deadband_frac is not None:
                        truevx_params['deadband_frac'] = request.deadband_frac
                    if request.min_deadband is not None:
                        truevx_params['min_deadband'] = request.min_deadband
                    
                    indicator_data = await engine.calculate_truevx_ranking(
                        data=price_records,
                        base_symbol=request.base_symbol or "Nifty 50",
                        start_date=start_dt.isoformat() if start_dt else None,
                        end_date=end_dt.isoformat() if end_dt else None,
                        **truevx_params
                    )
                else:
                    indicator_data = engine.calculate_indicator(
                        indicator_type=request.indicator_type,
                        data=price_records,
                        **calc_params
                    )
                calculation_time = (datetime.now() - calculation_start).total_seconds()
                
                logger.info(f"Indicator calculation completed in {calculation_time:.3f}s")
                
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            
            return JSONResponse(content={
                "symbol": request.symbol,
                "indicator_type": request.indicator_type,
                "parameters": calc_params,
                "total_points": len(indicator_data),
                "price_data_points": len(price_records),
                "calculation_time_seconds": round(calculation_time, 3),
                "data": indicator_data
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating indicators for {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate indicators: {str(e)}")

@app.get("/api/stock/indicators/supported")
async def get_supported_indicators():
    """Get list of supported technical indicators"""
    try:
        from indicator_engine import IndicatorEngine
        
        engine = IndicatorEngine()
        supported = engine.get_supported_indicators()
        
        # Add metadata about each indicator
        indicator_info = {
            'sma': {
                'name': 'Simple Moving Average',
                'description': 'Average price over a specified period',
                'parameters': ['period', 'price_field'],
                'default_period': 20
            },
            'ema': {
                'name': 'Exponential Moving Average', 
                'description': 'Weighted moving average giving more importance to recent prices',
                'parameters': ['period', 'price_field'],
                'default_period': 20
            },
            'rsi': {
                'name': 'Relative Strength Index',
                'description': 'Momentum oscillator measuring speed and magnitude of price changes',
                'parameters': ['period', 'price_field'],
                'default_period': 14,
                'range': [0, 100]
            },
            'macd': {
                'name': 'Moving Average Convergence Divergence',
                'description': 'Trend-following momentum indicator',
                'parameters': ['fast_period', 'slow_period', 'signal_period', 'price_field'],
                'default_periods': {'fast': 12, 'slow': 26, 'signal': 9}
            },
            'bollinger': {
                'name': 'Bollinger Bands',
                'description': 'Volatility bands around moving average',
                'parameters': ['period', 'std_dev', 'price_field'],
                'default_period': 20,
                'default_std_dev': 2.0
            },
            'truevx': {
                'name': 'TrueValueX Ranking',
                'description': 'Advanced ranking system with structural and trend analysis',
                'parameters': ['base_symbol', 'start_date', 'end_date'],
                'default_base_symbol': 'Nifty 50',
                'range': [50, 100]
            }
        }
        
        return JSONResponse(content={
            "supported_indicators": supported,
            "indicator_details": {k: v for k, v in indicator_info.items() if k in supported}
        })
        
    except Exception as e:
        logger.error(f"Error getting supported indicators: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get supported indicators: {str(e)}")

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

# ==========================================
# BATCH INDICATOR PROCESSING ENDPOINTS
# ==========================================

class BatchIndicatorRequest(BaseModel):
    symbols: List[str]
    indicator_type: str = "truevx"
    base_symbol: str = "Nifty 50"
    start_date: str = ""  # Empty string means full range
    end_date: str = ""    # Empty string means full range
    parameters: Dict[str, Any] = {"s1": 22, "m2": 66, "l3": 222}

@app.post("/api/indicators/batch")
async def submit_batch_indicator_job(request: BatchIndicatorRequest):
    """
    Submit a batch indicator calculation job
    """
    try:
        from batch_indicator_processor import submit_truevx_batch_job
        
        if request.indicator_type != "truevx":
            raise HTTPException(status_code=400, detail="Only TrueValueX indicator is currently supported for batch processing")
        
        if not request.symbols:
            raise HTTPException(status_code=400, detail="At least one symbol must be provided")
        
        # Determine date range - if not provided (empty string), get full range from base symbol data
        start_date = request.start_date
        end_date = request.end_date
        
        logger.info(f"🔍 Received request: start_date='{start_date}', end_date='{end_date}'")
        
        if not start_date or not end_date:
            logger.info(f"📅 Empty dates received, determining full range for {request.base_symbol}")
            # Get full data range for base symbol
            try:
                from stock_data_manager import StockDataManager
                from datetime import datetime
                
                async with StockDataManager() as data_manager:
                    base_symbol_range = await data_manager.get_symbol_date_range(request.base_symbol)
                    if base_symbol_range:
                        if not start_date:
                            start_date = base_symbol_range['earliest'].strftime('%Y-%m-%d')
                        if not end_date:
                            end_date = base_symbol_range['latest'].strftime('%Y-%m-%d')
                        logger.info(f"📅 Using full data range for {request.base_symbol}: {start_date} to {end_date}")
                    else:
                        # Fallback to default range if no data found
                        start_date = start_date or "2020-01-01"
                        end_date = end_date or datetime.now().strftime('%Y-%m-%d')
                        logger.warning(f"⚠️ No data range found for {request.base_symbol}, using fallback: {start_date} to {end_date}")
            except Exception as e:
                from datetime import datetime
                logger.error(f"❌ Failed to get data range for {request.base_symbol}: {e}")
                # Fallback to default range
                start_date = start_date or "2020-01-01"
                end_date = end_date or datetime.now().strftime('%Y-%m-%d')
                logger.warning(f"🔄 Using fallback dates: {start_date} to {end_date}")
        
        logger.info(f"📋 Final dates for job: {start_date} to {end_date}")
        
        # Submit the batch job
        job_id = await submit_truevx_batch_job(
            symbols=request.symbols,
            base_symbol=request.base_symbol,
            start_date=start_date,
            end_date=end_date,
            s1=request.parameters.get("s1", 22),
            m2=request.parameters.get("m2", 66),
            l3=request.parameters.get("l3", 222)
        )
        
        logger.info(f"✅ Submitted batch job {job_id} for {len(request.symbols)} symbols")
        
        return JSONResponse(content={
            "job_id": job_id,
            "status": "submitted",
            "symbols": request.symbols,
            "indicator_type": request.indicator_type,
            "base_symbol": request.base_symbol,
            "parameters": request.parameters,
            "estimated_completion_minutes": len(request.symbols) * 0.5  # Rough estimate
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to submit batch job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit batch job: {str(e)}")

@app.get("/api/indicators/batch/{job_id}")
async def get_batch_job_progress(job_id: str):
    """
    Get batch job progress and status
    """
    try:
        from batch_indicator_processor import get_batch_job_progress
        
        progress = await get_batch_job_progress(job_id)
        
        if "error" in progress:
            raise HTTPException(status_code=404, detail=progress["error"])
        
        return JSONResponse(content=progress)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get job progress: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job progress: {str(e)}")

@app.delete("/api/indicators/batch/{job_id}")
async def cancel_batch_job(job_id: str):
    """
    Cancel a running batch job
    """
    try:
        from batch_indicator_processor import cancel_batch_job
        
        success = await cancel_batch_job(job_id)
        
        if success:
            return JSONResponse(content={
                "job_id": job_id,
                "status": "cancelled",
                "message": "Job cancelled successfully"
            })
        else:
            raise HTTPException(status_code=404, detail="Job not found or not cancellable")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")

@app.get("/api/indicators/batch")
async def list_batch_jobs():
    """
    List all recent batch jobs
    """
    try:
        from batch_indicator_processor import list_all_batch_jobs
        
        jobs = await list_all_batch_jobs()
        
        return JSONResponse(content={
            "total_jobs": len(jobs),
            "jobs": jobs
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to list batch jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list batch jobs: {str(e)}")

@app.get("/api/indicators/stored")
async def get_stored_indicators():
    """
    Get list of all stored pre-calculated indicators
    """
    try:
        from indicator_data_manager import IndicatorDataManager
        
        async with IndicatorDataManager() as data_manager:
            indicators = await data_manager.get_available_indicators()
            
            return JSONResponse(content={
                "total_indicators": len(indicators),
                "indicators": indicators
            })
        
    except Exception as e:
        logger.error(f"❌ Failed to get stored indicators: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stored indicators: {str(e)}")

@app.get("/api/indicators/stored/{symbol}/{indicator_type}/{base_symbol}")
async def get_stored_indicator_data(symbol: str, indicator_type: str, base_symbol: str, 
                                   start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Get stored indicator data for a specific symbol
    """
    try:
        from indicator_data_manager import IndicatorDataManager
        
        async with IndicatorDataManager() as data_manager:
            data = await data_manager.get_indicator_data(
                symbol=symbol,
                indicator_type=indicator_type,
                base_symbol=base_symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            return JSONResponse(content={
                "symbol": symbol,
                "indicator_type": indicator_type,
                "base_symbol": base_symbol,
                "total_points": len(data),
                "date_range": {
                    "start": start_date,
                    "end": end_date
                },
                "data": data
            })
        
    except Exception as e:
        logger.error(f"❌ Failed to get stored indicator data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stored indicator data: {str(e)}")

async def get_available_indices():
    """Helper function to get available indices"""
    try:
        if mongo_conn.db is None:
            return []
        
        collection = mongo_conn.db.index_meta
        pipeline = [
            {
                "$group": {
                    "_id": "$index_name",
                    "count": {"$sum": 1}
                }
            }
        ]
        index_stats = list(collection.aggregate(pipeline))
        return [stat["_id"] for stat in index_stats if stat["count"] > 10]
    except Exception:
        return ["NIFTY50", "NIFTY100", "NIFTY 500"]

@app.get("/api/analytics/index-distribution")
async def get_index_distribution(
    index_symbol: str = "NIFTY50", 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    score_ranges: Optional[str] = None,
    metric: Optional[str] = "truevx_score",  # New parameter for metric selection
    include_price: Optional[bool] = True,  # New parameter to include price data
    include_symbols: Optional[bool] = False  # New parameter to include symbol breakdown
):
    """
    Get TrueValueX score distribution for an index over time
    
    Args:
        index_symbol: Index to analyze (default: "NIFTY50")
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        score_ranges: Comma-separated score ranges (e.g., "0-20,20-40,40-60,60-80,80-100")
        metric: Metric to analyze (truevx_score, mean_short, mean_mid, mean_long)
        include_price: Whether to include base symbol price data (default: True)
        include_symbols: Whether to include detailed symbol breakdown for each date (default: False)
    
    Returns:
        Historical score distribution data with optional price data and symbol breakdown for visualization
    """
    try:
        from indicator_data_manager import IndicatorDataManager
        from datetime import datetime, timedelta
        import pandas as pd
        from collections import defaultdict
        
        logger.info(f"🔍 Getting index distribution for: {index_symbol}, metric: {metric}, include_price: {include_price}, include_symbols: {include_symbols}")
        
        # Validate metric parameter
        valid_metrics = ["truevx_score", "mean_short", "mean_mid", "mean_long"]
        if metric not in valid_metrics:
            raise HTTPException(status_code=400, detail=f"Invalid metric. Must be one of: {valid_metrics}")
        
        # Set default date range (last 5 years)
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_dt = datetime.now() - timedelta(days=5*365)
            start_date = start_dt.strftime('%Y-%m-%d')
        
        logger.info(f"📅 Date range: {start_date} to {end_date}")
        
        # Default score ranges
        if not score_ranges:
            score_ranges = "0-20,20-40,40-60,60-80,80-100"
        
        ranges = []
        for range_str in score_ranges.split(','):
            start_score, end_score = map(int, range_str.split('-'))
            ranges.append((start_score, end_score))
        
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        # First, get all stock symbols that belong to this index
        index_meta_coll = mongo_conn.db.index_meta
        index_stocks_cursor = index_meta_coll.find({"index_name": index_symbol}, {"Symbol": 1})
        index_stock_symbols = [doc["Symbol"] for doc in index_stocks_cursor]
        
        logger.info(f"📊 Found {len(index_stock_symbols)} stocks in {index_symbol} index")
        
        if not index_stock_symbols:
            return JSONResponse(content={
                "success": False,
                "error": f"No stocks found for index: {index_symbol}",
                "available_indices": await get_available_indices()
            })
        
        # Get stock metadata for company names if symbols are requested
        stock_metadata = {}
        if include_symbols:
            try:
                stock_meta_coll = mongo_conn.db.symbol_mappings
                for stock_doc in stock_meta_coll.find({"symbol": {"$in": index_stock_symbols}}):
                    stock_metadata[stock_doc["symbol"]] = {
                        "company_name": stock_doc.get("company_name", stock_doc["symbol"]),
                        "industry": stock_doc.get("industry", "Unknown"),
                        "sector": stock_doc.get("sector", "Unknown")
                    }
                logger.info(f"📋 Retrieved metadata for {len(stock_metadata)} symbols")
            except Exception as e:
                logger.warning(f"⚠️ Could not retrieve stock metadata: {e}")
                # Fallback: use symbol as company name
                for symbol in index_stock_symbols:
                    stock_metadata[symbol] = {
                        "company_name": symbol,
                        "industry": "Unknown",
                        "sector": "Unknown"
                    }
        
        async with IndicatorDataManager() as data_manager:
            # Get all available indicators for these stocks
            indicators_coll = data_manager.db[data_manager.indicators_collection]
            
            # Query for TrueValueX indicators for stocks in this index
            query = {
                "indicator_type": "truevx",
                "symbol": {"$in": index_stock_symbols},
                "date": {
                    "$gte": datetime.strptime(start_date, "%Y-%m-%d"),
                    "$lte": datetime.strptime(end_date, "%Y-%m-%d")
                }
            }
            
            logger.info(f"🔍 Querying indicators with: {query}")
            
            # Get all data points
            cursor = indicators_coll.find(query).sort("date", 1)
            
            # Process data for distribution analysis
            distribution_data = defaultdict(lambda: defaultdict(int))
            date_symbols = defaultdict(set)
            date_symbols_by_range = defaultdict(lambda: defaultdict(list))  # For detailed symbol breakdown
            
            doc_count = 0
            for doc in cursor:
                doc_count += 1
                date_str = doc["date"].strftime('%Y-%m-%d')
                symbol = doc["symbol"]
                
                # Get the specified metric value, defaulting to 0 if not found
                metric_value = doc["data"].get(metric, 0)
                
                # Skip if metric value is None or invalid
                if metric_value is None:
                    continue
                
                # Add symbol to date tracking
                date_symbols[date_str].add(symbol)
                
                # Categorize score into ranges
                for i, (range_start, range_end) in enumerate(ranges):
                    if range_start <= metric_value < range_end or (i == len(ranges)-1 and metric_value >= range_start):
                        range_label = f"{range_start}-{range_end}"
                        distribution_data[date_str][range_label] += 1
                        
                        # Store symbol details if requested
                        if include_symbols:
                            symbol_info = {
                                "symbol": symbol,
                                "value": round(metric_value, 2),
                                "company_name": stock_metadata.get(symbol, {}).get("company_name", symbol),
                                "industry": stock_metadata.get(symbol, {}).get("industry", "Unknown"),
                                "sector": stock_metadata.get(symbol, {}).get("sector", "Unknown")
                            }
                            date_symbols_by_range[date_str][range_label].append(symbol_info)
                        break
            
            logger.info(f"📈 Processed {doc_count} indicator data points")
            
            # Fetch base symbol price data if requested
            price_data = {}
            actual_base_symbol = None
            
            if include_price:
                try:
                    # First, get the base_symbol from one of the TrueValueX records for this index
                    sample_record = indicators_coll.find_one(
                        {"indicator_type": "truevx", "symbol": {"$in": index_stock_symbols}},
                        {"base_symbol": 1}
                    )
                    
                    if sample_record and "base_symbol" in sample_record:
                        actual_base_symbol = sample_record["base_symbol"]
                        logger.info(f"💰 Detected base symbol: {actual_base_symbol}")
                        
                        # Fetch price data for the actual base symbol used in calculations
                        logger.info(f"💰 Fetching {actual_base_symbol} price data for date range: {start_date} to {end_date}")
                        
                        # Query price data directly from database to avoid API sorting limitations
                        # The stock data API sorts newest first, but we need full historical range
                        from stock_data_manager import StockDataManager
                        
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        days_diff = (end_dt - start_dt).days
                        
                        logger.info(f"💰 Querying {actual_base_symbol} price data directly from database for {days_diff} days ({days_diff/365:.1f} years)")
                        
                        async with StockDataManager() as price_manager:
                            # Get all price data for the date range, sorted oldest first
                            price_records = await price_manager.get_price_data(
                                symbol=actual_base_symbol,
                                start_date=start_dt,
                                end_date=end_dt,
                                limit=None,  # No limit - get all available data
                                sort_order=1  # 1 for ascending (oldest first)
                            )
                            
                            logger.info(f"💰 Retrieved {len(price_records)} price records from database")
                            
                            # Convert to date-indexed dictionary
                            for price_record in price_records:
                                date_str = price_record.date.strftime('%Y-%m-%d')
                                price_data[date_str] = {
                                    "open": price_record.open_price,
                                    "high": price_record.high_price,
                                    "low": price_record.low_price,
                                    "close": price_record.close_price,
                                    "volume": price_record.volume
                                }
                            
                            logger.info(f"💰 Fetched {len(price_data)} {actual_base_symbol} price records from database")
                            
                    else:
                        logger.warning("💰 No base_symbol found in TrueValueX records, skipping price data")
                        
                except Exception as price_error:
                    logger.error(f"💰 Error fetching base symbol price data via API: {price_error}")
                    price_data = {}
            
            # Format data for frontend
            result_data = []
            all_dates = sorted(distribution_data.keys())
            
            for date_str in all_dates:
                date_data = {
                    "date": date_str,
                    "total_symbols": len(date_symbols[date_str]),
                    "distribution": {}
                }
                
                # Add price data if available
                if include_price and date_str in price_data:
                    date_data["price"] = price_data[date_str]
                
                # Add all score ranges with counts
                for range_start, range_end in ranges:
                    range_label = f"{range_start}-{range_end}"
                    count = distribution_data[date_str].get(range_label, 0)
                    total = len(date_symbols[date_str])
                    percentage = (count / total * 100) if total > 0 else 0
                    
                    range_data = {
                        "count": count,
                        "percentage": round(percentage, 2)
                    }
                    
                    # Add symbol details if requested
                    if include_symbols:
                        symbols_in_range = date_symbols_by_range[date_str].get(range_label, [])
                        # Sort symbols by value (highest first within each range)
                        symbols_in_range.sort(key=lambda x: x["value"], reverse=True)
                        range_data["symbols"] = symbols_in_range
                    
                    date_data["distribution"][range_label] = range_data
                
                result_data.append(date_data)
            
            # Summary statistics
            total_data_points = sum(len(date_symbols[date]) for date in date_symbols)
            unique_symbols = set()
            for symbols in date_symbols.values():
                unique_symbols.update(symbols)
            
            return JSONResponse(content={
                "success": True,
                "index_symbol": index_symbol,
                "metric": metric,
                "include_price": include_price,
                "include_symbols": include_symbols,
                "base_symbol": actual_base_symbol,  # Include the actual base symbol used
                "date_range": {
                    "start": start_date,
                    "end": end_date
                },
                "score_ranges": [f"{start}-{end}" for start, end in ranges],
                "summary": {
                    "total_data_points": total_data_points,
                    "unique_symbols": len(unique_symbols),
                    "date_count": len(all_dates),
                    "symbols_per_date_avg": round(total_data_points / len(all_dates), 2) if all_dates else 0,
                    "price_data_points": len(price_data) if include_price else 0
                },
                "data": result_data
            })
            
    except Exception as e:
        logger.error(f"❌ Error in get_index_distribution: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "available_indices": await get_available_indices()
            }
        )
            
    except Exception as e:
        logger.error(f"❌ Error in get_index_distribution: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "available_indices": await get_available_indices()
            }
        )

@app.get("/api/analytics/index-distribution/symbols")
async def get_index_distribution_symbols(
    index_symbol: str = "NIFTY50",
    date: str = None,  # Specific date to get symbol breakdown
    metric: str = "truevx_score"
):
    """
    Get detailed symbol breakdown by score ranges for a specific date
    
    Args:
        index_symbol: Index to analyze (default: "NIFTY50")
        date: Specific date to analyze (YYYY-MM-DD format)
        metric: Metric to analyze (truevx_score, mean_short, mean_mid, mean_long)
        
    Returns:
        Detailed breakdown of symbols in each score range for the specified date
    """
    try:
        from indicator_data_manager import IndicatorDataManager
        from datetime import datetime
        from collections import defaultdict
        
        logger.info(f"🔍 Getting symbol breakdown for: {index_symbol}, date: {date}, metric: {metric}")
        
        # Validate inputs
        if not date:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Date parameter is required"}
            )
        
        # Parse and validate date
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
            )
        
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        # Get stock symbols for this index
        index_meta_coll = mongo_conn.db.index_meta
        index_stocks_cursor = index_meta_coll.find({"index_name": index_symbol}, {"Symbol": 1})
        index_stock_symbols = [doc["Symbol"] for doc in index_stocks_cursor]
        
        if not index_stock_symbols:
            return JSONResponse(content={
                "success": False,
                "error": f"No stocks found for index: {index_symbol}"
            })
        
        # Get stock metadata for company names
        stock_meta_coll = mongo_conn.db.symbol_mappings
        stock_metadata = {}
        for stock_doc in stock_meta_coll.find({"symbol": {"$in": index_stock_symbols}}):
            stock_metadata[stock_doc["symbol"]] = {
                "name": stock_doc.get("name", stock_doc["symbol"]),
                "industry": stock_doc.get("industry", "Unknown"),
                "sector": stock_doc.get("sector", "Unknown")
            }
        
        async with IndicatorDataManager() as data_manager:
            indicators_coll = data_manager.db[data_manager.indicators_collection]
            
            # Query for TrueValueX indicators for this specific date
            query = {
                "indicator_type": "truevx",
                "symbol": {"$in": index_stock_symbols},
                "date": target_date
            }
            
            # Get indicator data for the specific date
            cursor = indicators_coll.find(query)
            
            # Define score ranges
            score_ranges = [
                (0, 20, "Weak (0-20)", "#ef4444"),
                (20, 40, "Below Average (20-40)", "#f97316"),
                (40, 60, "Average (40-60)", "#eab308"),
                (60, 80, "Above Average (60-80)", "#3b82f6"),
                (80, 100, "Strong (80-100)", "#22c55e")
            ]
            
            # Organize symbols by score ranges
            range_symbols = defaultdict(list)
            total_symbols = 0
            
            for doc in cursor:
                symbol = doc["symbol"]
                metric_value = doc["data"].get(metric, 0)
                
                if metric_value is None:
                    continue
                
                total_symbols += 1
                
                # Find appropriate range
                for range_start, range_end, range_label, color in score_ranges:
                    if range_start <= metric_value < range_end or (range_start == 80 and metric_value >= range_start):
                        range_key = f"{range_start}-{range_end}"
                        
                        symbol_info = {
                            "symbol": symbol,
                            "name": stock_metadata.get(symbol, {}).get("name", symbol),
                            "industry": stock_metadata.get(symbol, {}).get("industry", "Unknown"),
                            "sector": stock_metadata.get(symbol, {}).get("sector", "Unknown"),
                            "score": round(metric_value, 2),
                            "range_label": range_label,
                            "color": color
                        }
                        range_symbols[range_key].append(symbol_info)
                        break
            
            # Sort symbols within each range by score (descending)
            for range_key in range_symbols:
                range_symbols[range_key].sort(key=lambda x: x["score"], reverse=True)
            
            # Format response
            result = {
                "success": True,
                "index_symbol": index_symbol,
                "date": date,
                "metric": metric,
                "total_symbols": total_symbols,
                "ranges": {}
            }
            
            # Add range data
            for range_start, range_end, range_label, color in score_ranges:
                range_key = f"{range_start}-{range_end}"
                symbols_in_range = range_symbols.get(range_key, [])
                
                result["ranges"][range_key] = {
                    "label": range_label,
                    "color": color,
                    "count": len(symbols_in_range),
                    "percentage": round((len(symbols_in_range) / total_symbols * 100), 2) if total_symbols > 0 else 0,
                    "symbols": symbols_in_range
                }
            
            return JSONResponse(content=result)
            
    except Exception as e:
        logger.error(f"❌ Error in get_index_distribution_symbols: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get index distribution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get index distribution: {str(e)}")

# =============================================================================
# STRATEGY SIMULATION ENDPOINTS
# =============================================================================

class StrategyRule(BaseModel):
    id: str
    metric: str  # 'truevx_score', 'mean_short', 'mean_mid', 'mean_long'
    operator: str  # '>', '<', '>=', '<=', '==', '!='
    threshold: float
    name: str

class Strategy(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    rules: List[StrategyRule]
    created_at: Optional[str] = None
    last_modified: Optional[str] = None

class SimulationParams(BaseModel):
    strategy_id: str
    portfolio_base_value: float = 100000
    rebalance_frequency: str = "monthly"  # 'monthly', 'weekly', 'quarterly', 'dynamic'
    rebalance_date: str = "first"  # 'first', 'last', 'mid'
    rebalance_type: str = "equal_weight"  # 'equal_weight', 'skewed' - allocation method
    universe: str = "NIFTY50"  # 'NIFTY50', 'NIFTY100', 'NIFTY500'
    benchmark_symbol: Optional[str] = None  # Optional benchmark symbol override
    max_holdings: int = 50  # Maximum number of stocks in portfolio
    momentum_ranking: str = "20_day_return"  # Momentum ranking method - supports:
    # Price-based: '20_day_return', 'price_roc_66d', 'price_roc_222d', 'risk_adjusted', 'technical'
    # Indicator-based: 'truevx_roc', 'short_mean_roc', 'mid_mean_roc', 'long_mean_roc', 'stock_score_roc'
    start_date: str
    end_date: str
    # New brokerage-related parameters
    include_brokerage: bool = True  # Enable/disable brokerage calculation
    exchange: str = "NSE"  # Default exchange for charges ("NSE" or "BSE")
    custom_brokerage_rate: float = 0.0  # Custom brokerage rate override (as decimal, e.g., 0.001 for 0.1%)
    portfolio_turnover_estimate: float = 0.5  # Expected portfolio churn per rebalance (0.0-1.0)


class HoldingsMultiParams(BaseModel):
    """Parameters for holdings multi-dimension simulation"""
    strategy_id: str
    portfolio_base_value: float = 100000
    rebalance_frequency: str = "monthly"
    rebalance_date: str = "first"
    rebalance_type: str = "equal_weight"
    universe: str = "NIFTY50"
    benchmark_symbol: Optional[str] = None
    base_max_holdings: int = 10  # Base holdings value
    momentum_ranking: str = "20_day_return"
    start_date: str
    end_date: str
    include_brokerage: bool = True
    exchange: str = "NSE"
    custom_brokerage_rate: float = 0.0
    portfolio_turnover_estimate: float = 0.5
    multipliers: list[int] = [1, 2, 3, 4]  # Holding size multipliers
    multipliers: list = [1, 2, 3, 4]  # Multipliers for base_max_holdings

@app.post("/api/simulation/strategies")
async def save_strategy(strategy: Strategy):
    """Save a new trading strategy"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        strategies_coll = mongo_conn.db.simulation_strategies
        
        # Generate ID and timestamps
        strategy_data = strategy.dict()
        strategy_data["id"] = f"strategy_{int(datetime.now().timestamp() * 1000)}"
        strategy_data["created_at"] = datetime.now().isoformat()
        strategy_data["last_modified"] = datetime.now().isoformat()
        
        # Insert into database
        result = strategies_coll.insert_one(strategy_data)
        strategy_data["_id"] = str(result.inserted_id)
        
        logger.info(f"💾 Saved strategy: {strategy.name} with {len(strategy.rules)} rules")
        
        return JSONResponse(content={
            "success": True,
            "strategy_id": strategy_data["id"],
            "message": "Strategy saved successfully"
        })
        
    except Exception as e:
        logger.error(f"❌ Error saving strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save strategy: {str(e)}")

@app.get("/api/simulation/strategies")
async def get_strategies():
    """Get all saved trading strategies"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        strategies_coll = mongo_conn.db.simulation_strategies
        
        # Get all strategies
        strategies = []
        for strategy_doc in strategies_coll.find().sort("last_modified", -1):
            strategy_doc["_id"] = str(strategy_doc["_id"])
            strategies.append(strategy_doc)
        
        logger.info(f"📋 Retrieved {len(strategies)} strategies")
        
        return JSONResponse(content={
            "success": True,
            "strategies": strategies
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get strategies: {str(e)}")

@app.put("/api/simulation/strategies/{strategy_id}")
async def update_strategy(strategy_id: str, strategy: Strategy):
    """Update an existing trading strategy"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        strategies_coll = mongo_conn.db.simulation_strategies
        
        # Check if strategy exists
        existing_strategy = strategies_coll.find_one({"id": strategy_id})
        if not existing_strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Update strategy data (preserve the ID)
        strategy_data = strategy.dict()
        strategy_data["last_modified"] = datetime.now().isoformat()
        
        # Remove id from update data to prevent overwriting
        if "id" in strategy_data:
            del strategy_data["id"]
        
        # Update in database
        result = strategies_coll.update_one(
            {"id": strategy_id}, 
            {"$set": strategy_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to strategy")
        
        logger.info(f"✏️ Updated strategy: {strategy.name} with {len(strategy.rules)} rules")
        
        return JSONResponse(content={
            "success": True,
            "strategy_id": strategy_id,
            "message": "Strategy updated successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update strategy: {str(e)}")

@app.delete("/api/simulation/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """Delete a trading strategy"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        strategies_coll = mongo_conn.db.simulation_strategies
        
        # Check if strategy exists
        existing_strategy = strategies_coll.find_one({"id": strategy_id})
        if not existing_strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Delete from database
        result = strategies_coll.delete_one({"id": strategy_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=400, detail="Failed to delete strategy")
        
        logger.info(f"🗑️ Deleted strategy: {existing_strategy.get('name', 'Unknown')}")
        
        return JSONResponse(content={
            "success": True,
            "strategy_id": strategy_id,
            "message": "Strategy deleted successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete strategy: {str(e)}")

@app.post("/api/simulation/run")
async def run_simulation(params: SimulationParams):
    """Run a trading strategy simulation"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        logger.info(f"🚀 Starting simulation for strategy {params.strategy_id}")
        logger.info(f"📅 Period: {params.start_date} to {params.end_date}")
        logger.info(f"🎯 Universe: {params.universe}")
        
        # Normalize universe name to match database format
        universe_mapping = {
            "NIFTY50": "NIFTY50",
            "NIFTY100": "NIFTY100", 
            "NIFTY500": "NIFTY 500",  # Map to database format with space
            "NIFTY 500": "NIFTY 500"  # Also handle if already correct
        }
        
        normalized_universe = universe_mapping.get(params.universe, params.universe)
        logger.info(f"🔄 Normalized universe: {params.universe} → {normalized_universe}")
        
        # Get strategy details
        strategies_coll = mongo_conn.db.simulation_strategies
        strategy = strategies_coll.find_one({"id": params.strategy_id})
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get universe symbols using normalized name
        index_meta_coll = mongo_conn.db.index_meta
        universe_symbols = []
        for doc in index_meta_coll.find({"index_name": normalized_universe}, {"Symbol": 1}):
            universe_symbols.append(doc["Symbol"])
        
        logger.info(f"📊 Found {len(universe_symbols)} symbols in {normalized_universe}")
        
        # Run simulation
        from indicator_data_manager import IndicatorDataManager
        
        async with IndicatorDataManager() as data_manager:
            simulation_results = await run_strategy_simulation(
                data_manager, 
                strategy, 
                universe_symbols, 
                params
            )
        
        logger.info(f"✅ Simulation completed with {len(simulation_results['results'])} data points")
        
        return JSONResponse(content={
            "success": True,
            "simulation": simulation_results
        })
        
    except Exception as e:
        logger.error(f"❌ Error running simulation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run simulation: {str(e)}")


def calculate_monthly_metrics(daily_results, base_value):
    """Calculate monthly-level metrics from daily simulation results"""
    from datetime import datetime
    from collections import defaultdict
    
    # Group results by month
    monthly_groups = defaultdict(list)
    for day_result in daily_results:
        date_obj = datetime.strptime(day_result["date"], "%Y-%m-%d")
        month_key = f"{date_obj.year}-{date_obj.month:02d}"
        monthly_groups[month_key].append(day_result)
    
    # Calculate monthly returns
    monthly_returns = []
    monthly_churn_rates = []
    
    for month_key in sorted(monthly_groups.keys()):
        month_days = monthly_groups[month_key]
        
        if len(month_days) > 0:
            first_day = month_days[0]
            last_day = month_days[-1]
            
            # Monthly return
            month_return = ((last_day["portfolio_value"] / first_day["portfolio_value"]) - 1) * 100
            monthly_returns.append({
                "month": month_key,
                "return": round(month_return, 2)
            })
            
            # Monthly churn (count rebalances in this month)
            month_trades = sum(len(day.get("new_added", [])) + len(day.get("exited", [])) for day in month_days)
            # Average portfolio size for the month
            avg_portfolio_size = sum(len(day.get("holdings", [])) for day in month_days) / len(month_days)
            churn_rate = (month_trades / (avg_portfolio_size * 2)) * 100 if avg_portfolio_size > 0 else 0
            monthly_churn_rates.append(churn_rate)
    
    # Calculate metrics
    avg_monthly_return = sum(m["return"] for m in monthly_returns) / len(monthly_returns) if monthly_returns else 0
    monthly_win_rate = (sum(1 for m in monthly_returns if m["return"] > 0) / len(monthly_returns) * 100) if monthly_returns else 0
    avg_monthly_churn = sum(monthly_churn_rates) / len(monthly_churn_rates) if monthly_churn_rates else 0
    
    # Calculate volatility (standard deviation of monthly returns)
    if len(monthly_returns) > 1:
        import statistics
        volatility = statistics.stdev([m["return"] for m in monthly_returns])
    else:
        volatility = 0
    
    return {
        "monthly_returns": monthly_returns,
        "avg_monthly_return": round(avg_monthly_return, 2),
        "monthly_win_rate": round(monthly_win_rate, 2),
        "avg_monthly_churn": round(avg_monthly_churn, 2),
        "volatility": round(volatility, 2)
    }


@app.post("/api/simulation/multi-run")
async def run_multi_dimension_simulation(params: SimulationParams):
    """Run parallel simulations across multiple time periods ending on the same date"""
    try:
        import asyncio
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        logger.info(f"🎯 Starting multi-dimension simulation for strategy {params.strategy_id}")
        logger.info(f"📅 Base period: {params.start_date} to {params.end_date}")
        
        # Parse end date
        end_date = datetime.strptime(params.end_date, "%Y-%m-%d")
        base_start_date = datetime.strptime(params.start_date, "%Y-%m-%d")
        
        # Generate time periods - all ending on same end_date
        # Calculate years between start and end
        years_diff = end_date.year - base_start_date.year
        
        periods = []
        # Generate periods: original, -1 year, -2 years, -3 years, -4 years (if applicable)
        for year_offset in range(min(years_diff + 1, 5)):
            period_start = base_start_date + relativedelta(years=year_offset)
            
            # Skip if start date would be after end date
            if period_start >= end_date:
                continue
                
            periods.append({
                "label": f"{period_start.year}-{end_date.year}",
                "start_date": period_start.strftime("%Y-%m-%d"),
                "end_date": params.end_date
            })
        
        logger.info(f"🔢 Generated {len(periods)} time periods for parallel simulation")
        for p in periods:
            logger.info(f"  📆 {p['label']}: {p['start_date']} to {p['end_date']}")
        
        # Normalize universe
        universe_mapping = {
            "NIFTY50": "NIFTY50",
            "NIFTY100": "NIFTY100", 
            "NIFTY500": "NIFTY 500",
            "NIFTY 500": "NIFTY 500"
        }
        normalized_universe = universe_mapping.get(params.universe, params.universe)
        
        # Get strategy and universe symbols
        strategies_coll = mongo_conn.db.simulation_strategies
        strategy = strategies_coll.find_one({"id": params.strategy_id})
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        index_meta_coll = mongo_conn.db.index_meta
        universe_symbols = []
        for doc in index_meta_coll.find({"index_name": normalized_universe}, {"Symbol": 1}):
            universe_symbols.append(doc["Symbol"])
        
        logger.info(f"📊 Using {len(universe_symbols)} symbols from {normalized_universe}")
        
        # Run simulations in parallel
        from indicator_data_manager import IndicatorDataManager
        
        async def run_single_period(period_config):
            """Run simulation for a single time period"""
            try:
                logger.info(f"⚡ Starting simulation for {period_config['label']}")
                
                # Create params for this period
                period_params = params.copy()
                period_params.start_date = period_config["start_date"]
                period_params.end_date = period_config["end_date"]
                
                async with IndicatorDataManager() as data_manager:
                    results = await run_strategy_simulation(
                        data_manager,
                        strategy,
                        universe_symbols,
                        period_params
                    )
                
                # Extract key metrics from summary (which has all calculated metrics)
                summary = results.get("summary", {})
                
                total_return = summary.get("total_return", 0)
                benchmark_return = summary.get("benchmark_return", 0)
                alpha = summary.get("alpha", 0)
                max_drawdown_summary = summary.get("max_drawdown", 0)
                sharpe_ratio_summary = summary.get("sharpe_ratio", 0)
                total_trades_summary = summary.get("total_trades", 0)
                
                # Get final portfolio value
                last_day = results["results"][-1] if results["results"] else None
                final_portfolio_value = last_day["portfolio_value"] if last_day else params.portfolio_base_value
                
                # Get final portfolio value
                last_day = results["results"][-1] if results["results"] else None
                final_portfolio_value = last_day["portfolio_value"] if last_day else params.portfolio_base_value
                
                logger.info(f"✅ Completed {period_config['label']}: {total_return:.2f}% return, Alpha: {alpha:.2f}%")
                
                return {
                    "period_label": period_config["label"],
                    "start_date": period_config["start_date"],
                    "end_date": period_config["end_date"],
                    "total_return": round(total_return, 2),
                    "benchmark_return": round(benchmark_return, 2),
                    "alpha": round(alpha, 2),
                    "max_drawdown": round(max_drawdown_summary, 2),
                    "sharpe_ratio": round(sharpe_ratio_summary, 2),
                    "total_trades": total_trades_summary,
                    "final_portfolio_value": final_portfolio_value,
                    "days_count": len(results["results"]),
                    "status": "completed"
                }
                
            except Exception as e:
                logger.error(f"❌ Error in simulation for {period_config['label']}: {e}")
                return {
                    "period_label": period_config["label"],
                    "start_date": period_config["start_date"],
                    "end_date": period_config["end_date"],
                    "total_return": 0,
                    "benchmark_return": 0,
                    "alpha": 0,
                    "max_drawdown": 0,
                    "sharpe_ratio": 0,
                    "total_trades": 0,
                    "final_portfolio_value": params.portfolio_base_value,
                    "days_count": 0,
                    "status": "error",
                    "error_message": str(e)
                }
        
        # Execute all simulations in parallel
        logger.info(f"🚀 Launching {len(periods)} parallel simulations...")
        period_results = await asyncio.gather(*[run_single_period(p) for p in periods])
        
        # Calculate aggregate metrics
        completed_results = [r for r in period_results if r["status"] == "completed"]
        
        if completed_results:
            avg_return = sum(r["total_return"] for r in completed_results) / len(completed_results)
            avg_alpha = sum(r["alpha"] for r in completed_results) / len(completed_results)
            avg_sharpe = sum(r["sharpe_ratio"] for r in completed_results) / len(completed_results)
            
            best_period = max(completed_results, key=lambda x: x["total_return"])
            worst_period = min(completed_results, key=lambda x: x["total_return"])
            
            # Consistency score: how close are returns to average (lower std = higher consistency)
            returns = [r["total_return"] for r in completed_results]
            if len(returns) > 1:
                import statistics
                std_returns = statistics.stdev(returns)
                # Convert to 0-100 scale (100 = perfect consistency)
                consistency_score = max(0, 100 - (std_returns / max(abs(avg_return), 1) * 100))
            else:
                consistency_score = 100
        else:
            avg_return = avg_alpha = avg_sharpe = consistency_score = 0
            best_period = worst_period = {"period_label": "N/A"}
        
        multi_simulation_result = {
            "params": params.dict(),
            "periods": period_results,
            "aggregate_metrics": {
                "avg_return": round(avg_return, 2),
                "avg_alpha": round(avg_alpha, 2),
                "avg_sharpe": round(avg_sharpe, 2),
                "best_period": best_period["period_label"],
                "worst_period": worst_period["period_label"],
                "consistency_score": round(consistency_score, 1)
            }
        }
        
        logger.info(f"🎉 Multi-dimension simulation completed!")
        logger.info(f"📊 Avg Return: {avg_return:.2f}%, Avg Alpha: {avg_alpha:.2f}%, Consistency: {consistency_score:.1f}%")
        
        return JSONResponse(content={
            "success": True,
            "multi_simulation": multi_simulation_result
        })
        
    except Exception as e:
        logger.error(f"❌ Error in multi-dimension simulation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to run multi-dimension simulation: {str(e)}")


@app.post("/api/simulation/holdings-multi-run")
async def run_holdings_multi_dimension_simulation(params: HoldingsMultiParams):
    """Run parallel simulations with different max holdings (base * multipliers)"""
    try:
        import asyncio
        from datetime import datetime
        
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        logger.info(f"🎯 Starting holdings multi-dimension simulation for strategy {params.strategy_id}")
        logger.info(f"📊 Base max holdings: {params.base_max_holdings}, Multipliers: {params.multipliers}")
        
        # Normalize universe
        universe_mapping = {
            "NIFTY50": "NIFTY50",
            "NIFTY100": "NIFTY100", 
            "NIFTY500": "NIFTY 500",
            "NIFTY 500": "NIFTY 500"
        }
        normalized_universe = universe_mapping.get(params.universe, params.universe)
        
        # Get strategy and universe symbols
        strategies_coll = mongo_conn.db.simulation_strategies
        strategy = strategies_coll.find_one({"id": params.strategy_id})
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        index_meta_coll = mongo_conn.db.index_meta
        universe_symbols = []
        for doc in index_meta_coll.find({"index_name": normalized_universe}, {"Symbol": 1}):
            universe_symbols.append(doc["Symbol"])
        
        logger.info(f"📊 Using {len(universe_symbols)} symbols from {normalized_universe}")
        
        # Generate holding configurations
        base_holdings = params.base_max_holdings
        holding_configs = []
        for multiplier in params.multipliers:
            holding_size = base_holdings * multiplier
            holding_configs.append({
                "multiplier": multiplier,
                "holding_size": holding_size
            })
        
        logger.info(f"🔢 Generated {len(holding_configs)} holding configurations: {[h['holding_size'] for h in holding_configs]}")
        
        # Run simulations in parallel
        from indicator_data_manager import IndicatorDataManager
        
        async def run_single_holding_simulation(holding_config):
            """Run simulation for a single holding size"""
            try:
                holding_size = holding_config["holding_size"]
                logger.info(f"⚡ Starting simulation for {holding_size} holdings")
                
                # Create SimulationParams for this holding size
                holding_params = SimulationParams(
                    strategy_id=params.strategy_id,
                    portfolio_base_value=params.portfolio_base_value,
                    rebalance_frequency=params.rebalance_frequency,
                    rebalance_date=params.rebalance_date,
                    rebalance_type=params.rebalance_type,
                    universe=params.universe,
                    benchmark_symbol=params.benchmark_symbol,
                    max_holdings=holding_size,
                    momentum_ranking=params.momentum_ranking,
                    start_date=params.start_date,
                    end_date=params.end_date,
                    include_brokerage=params.include_brokerage,
                    exchange=params.exchange,
                    custom_brokerage_rate=params.custom_brokerage_rate,
                    portfolio_turnover_estimate=params.portfolio_turnover_estimate
                )
                
                async with IndicatorDataManager() as data_manager:
                    results = await run_strategy_simulation(
                        data_manager,
                        strategy,
                        universe_symbols,
                        holding_params
                    )
                
                # Extract metrics from summary
                summary = results.get("summary", {})
                
                total_return = summary.get("total_return", 0)
                benchmark_return = summary.get("benchmark_return", 0)
                alpha = summary.get("alpha", 0)
                max_drawdown_summary = summary.get("max_drawdown", 0)
                sharpe_ratio_summary = summary.get("sharpe_ratio", 0)
                total_trades_summary = summary.get("total_trades", 0)
                
                # Calculate volatility from daily returns
                portfolio_values = [day["portfolio_value"] for day in results["results"]]
                daily_returns = []
                for i in range(1, len(portfolio_values)):
                    daily_ret = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1] * 100
                    daily_returns.append(daily_ret)
                
                import statistics
                volatility = statistics.stdev(daily_returns) * (252 ** 0.5) if len(daily_returns) > 1 else 0
                
                # Calculate monthly metrics
                monthly_data = {}
                for day in results["results"]:
                    date_str = day["date"]
                    month_key = date_str[:7]  # YYYY-MM
                    
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {
                            "start_value": day["portfolio_value"],
                            "end_value": day["portfolio_value"],
                            "trades": 0
                        }
                    
                    monthly_data[month_key]["end_value"] = day["portfolio_value"]
                    monthly_data[month_key]["trades"] += len(day.get("new_added", [])) + len(day.get("exited", []))
                
                # Calculate monthly returns and churn
                monthly_returns = []
                monthly_churns = []
                for month_key, data in monthly_data.items():
                    monthly_return = (data["end_value"] - data["start_value"]) / data["start_value"] * 100
                    monthly_returns.append(monthly_return)
                    
                    # Churn = trades / (holdings * 2) to normalize
                    monthly_churn = (data["trades"] / (holding_size * 2)) * 100 if holding_size > 0 else 0
                    monthly_churns.append(monthly_churn)
                
                # Calculate monthly win rate
                positive_months = sum(1 for r in monthly_returns if r > 0)
                monthly_win_rate = (positive_months / len(monthly_returns)) * 100 if monthly_returns else 0
                
                avg_monthly_churn = statistics.mean(monthly_churns) if monthly_churns else 0
                
                # Prepare portfolio values for charting
                portfolio_values_data = [
                    {
                        "date": day["date"],
                        "value": day["portfolio_value"],
                        "benchmark": day["benchmark_value"]
                    }
                    for day in results["results"]
                ]
                
                # Get final portfolio value
                last_day = results["results"][-1] if results["results"] else None
                final_portfolio_value = last_day["portfolio_value"] if last_day else params.portfolio_base_value
                
                logger.info(f"✅ Completed {holding_size} holdings: {total_return:.2f}% return, Sharpe: {sharpe_ratio_summary:.2f}")
                
                return {
                    "holding_size": holding_size,
                    "total_return": round(total_return, 2),
                    "benchmark_return": round(benchmark_return, 2),
                    "alpha": round(alpha, 2),
                    "max_drawdown": round(max_drawdown_summary, 2),
                    "sharpe_ratio": round(sharpe_ratio_summary, 2),
                    "volatility": round(volatility, 2),
                    "total_trades": total_trades_summary,
                    "avg_monthly_churn": round(avg_monthly_churn, 2),
                    "monthly_win_rate": round(monthly_win_rate, 2),
                    "final_portfolio_value": final_portfolio_value,
                    "days_count": len(results["results"]),
                    "monthly_returns": [round(r, 2) for r in monthly_returns],
                    "portfolio_values": portfolio_values_data,
                    "status": "completed"
                }
                
            except Exception as e:
                logger.error(f"❌ Error in simulation for {holding_config['holding_size']} holdings: {e}")
                return {
                    "holding_size": holding_config["holding_size"],
                    "total_return": 0,
                    "benchmark_return": 0,
                    "alpha": 0,
                    "max_drawdown": 0,
                    "sharpe_ratio": 0,
                    "volatility": 0,
                    "total_trades": 0,
                    "avg_monthly_churn": 0,
                    "monthly_win_rate": 0,
                    "final_portfolio_value": params.portfolio_base_value,
                    "days_count": 0,
                    "monthly_returns": [],
                    "portfolio_values": [],
                    "status": "error",
                    "error_message": str(e)
                }
        
        # Execute all simulations sequentially to avoid resource conflicts
        logger.info(f"🚀 Starting {len(holding_configs)} sequential simulations...")
        holding_results = []
        for holding_config in holding_configs:
            result = await run_single_holding_simulation(holding_config)
            holding_results.append(result)
        
        # Calculate aggregate metrics
        completed_results = [r for r in holding_results if r["status"] == "completed"]
        
        if completed_results:
            avg_return = sum(r["total_return"] for r in completed_results) / len(completed_results)
            avg_alpha = sum(r["alpha"] for r in completed_results) / len(completed_results)
            avg_sharpe = sum(r["sharpe_ratio"] for r in completed_results) / len(completed_results)
            
            best_return_result = max(completed_results, key=lambda x: x["total_return"])
            worst_return_result = min(completed_results, key=lambda x: x["total_return"])
            
            # Find optimal risk-adjusted (best Sharpe ratio)
            best_sharpe_result = max(completed_results, key=lambda x: x["sharpe_ratio"])
        else:
            avg_return = avg_alpha = avg_sharpe = 0
            best_return_result = worst_return_result = best_sharpe_result = {"holding_size": 0}
        
        multi_holdings_result = {
            "params": params.dict(),
            "holdings_results": holding_results,
            "aggregate_metrics": {
                "average_return": round(avg_return, 2),
                "average_alpha": round(avg_alpha, 2),
                "average_sharpe": round(avg_sharpe, 2),
                "best_holding_size": best_return_result["holding_size"],
                "worst_holding_size": worst_return_result["holding_size"],
                "optimal_risk_adjusted": best_sharpe_result["holding_size"]
            }
        }
        
        logger.info(f"🎉 Holdings multi-dimension simulation completed!")
        logger.info(f"📊 Best: {best_return_result['holding_size']} holdings, Optimal: {best_sharpe_result['holding_size']} holdings")
        
        return JSONResponse(content={
            "success": True,
            "multi_holdings_simulation": multi_holdings_result
        })
        
    except Exception as e:
        logger.error(f"❌ Error in holdings multi-dimension simulation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to run holdings multi-dimension simulation: {str(e)}")


@app.post("/api/simulation/debug")
async def debug_simulation(params: SimulationParams):
    """Run simulation with detailed debugging for first few days"""
    try:
        if mongo_conn.db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        logger.info(f"🔍 DEBUG MODE: Starting simulation for strategy {params.strategy_id}")
        
        # Normalize universe name to match database format
        universe_mapping = {
            "NIFTY50": "NIFTY50",
            "NIFTY100": "NIFTY100", 
            "NIFTY500": "NIFTY 500",  # Map to database format with space
            "NIFTY 500": "NIFTY 500"  # Also handle if already correct
        }
        
        normalized_universe = universe_mapping.get(params.universe, params.universe)
        logger.info(f"🔄 DEBUG: Normalized universe: {params.universe} → {normalized_universe}")
        
        # Get strategy details
        strategies_coll = mongo_conn.db.simulation_strategies
        strategy = strategies_coll.find_one({"id": params.strategy_id})
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get universe symbols (limit to first 20 for debugging)
        index_meta_coll = mongo_conn.db.index_meta
        universe_symbols = []
        for doc in index_meta_coll.find({"index_name": normalized_universe}, {"Symbol": 1}).limit(20):
            universe_symbols.append(doc["Symbol"])
        
        logger.info(f"🧪 DEBUG: Using {len(universe_symbols)} symbols: {universe_symbols}")
        
        # Use the full date range provided by user (no artificial limits)
        debug_params = params.copy()
        # Keep original start_date and end_date from user
        
        from indicator_data_manager import IndicatorDataManager
        
        async with IndicatorDataManager() as data_manager:
            simulation_results = await run_strategy_simulation_debug(
                data_manager, 
                strategy, 
                universe_symbols, 
                debug_params
            )
        
        total_days = len(simulation_results["debug_results"]) if simulation_results["debug_results"] else 0
        rebalance_days = len([r for r in simulation_results["debug_results"] if r["should_rebalance"]]) if simulation_results["debug_results"] else 0
        
        return JSONResponse(content={
            "success": True,
            "debug_simulation": simulation_results,
            "message": f"Debug simulation completed for {total_days} days with {rebalance_days} rebalance events"
        })
        
    except Exception as e:
        logger.error(f"❌ Error in debug simulation: {e}")
        raise HTTPException(status_code=500, detail=f"Debug simulation failed: {str(e)}")

@app.post("/api/simulation/estimate-charges")
async def estimate_simulation_charges(params: SimulationParams):
    """Estimate total charges for a simulation run"""
    try:
        logger.info(f"🧮 Estimating charges for strategy {params.strategy_id}")
        
        # Calculate simulation duration
        start_date = datetime.strptime(params.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(params.end_date, "%Y-%m-%d")
        simulation_days = (end_date - start_date).days
        
        # Initialize brokerage calculator
        calculator = BrokerageCalculator(
            default_exchange=params.exchange,
            custom_brokerage_rate=params.custom_brokerage_rate
        )
        
        # Estimate annual charge impact
        charge_estimate = calculator.estimate_annual_charge_impact(
            portfolio_value=params.portfolio_base_value,
            rebalance_frequency=params.rebalance_frequency,
            average_portfolio_churn=params.portfolio_turnover_estimate
        )
        
        # Adjust for actual simulation period
        simulation_years = simulation_days / 365.0
        estimated_total_charges = charge_estimate["charge_breakdown"]["total"] * simulation_years
        
        # Get charge rate information
        charge_info = calculator.get_charge_rates_info()
        
        response = {
            "success": True,
            "simulation_params": {
                "portfolio_value": params.portfolio_base_value,
                "rebalance_frequency": params.rebalance_frequency,
                "simulation_days": simulation_days,
                "simulation_years": round(simulation_years, 2),
                "exchange": params.exchange,
                "custom_brokerage_rate": params.custom_brokerage_rate,
                "portfolio_turnover_estimate": params.portfolio_turnover_estimate
            },
            "charge_estimate": {
                "total_estimated_charges": round(estimated_total_charges, 2),
                "estimated_charge_percentage": round((estimated_total_charges / params.portfolio_base_value) * 100, 3),
                "annual_charge_percentage": round(charge_estimate["impact_metrics"]["annual_charge_percentage"], 3),
                "monthly_charge_percentage": round(charge_estimate["impact_metrics"]["monthly_charge_percentage"], 4),
                "charge_per_rebalance": round(charge_estimate["impact_metrics"]["charge_per_rebalance"], 2),
                "breakdown": {
                    "stt": round(charge_estimate["charge_breakdown"]["stt"] * simulation_years, 2),
                    "transaction_charges": round(charge_estimate["charge_breakdown"]["transaction_charges"] * simulation_years, 2),
                    "sebi_charges": round(charge_estimate["charge_breakdown"]["sebi_charges"] * simulation_years, 2),
                    "stamp_duty": round(charge_estimate["charge_breakdown"]["stamp_duty"] * simulation_years, 2),
                    "brokerage": round(charge_estimate["charge_breakdown"]["brokerage"] * simulation_years, 2),
                    "gst": round(charge_estimate["charge_breakdown"]["gst"] * simulation_years, 2)
                }
            },
            "comparison": {
                "without_charges_final_value": params.portfolio_base_value,  # This would need actual simulation
                "with_charges_final_value": params.portfolio_base_value - estimated_total_charges,
                "impact_on_returns": round((estimated_total_charges / params.portfolio_base_value) * 100, 3)
            },
            "charge_rates": charge_info["charge_rates"],
            "rate_descriptions": charge_info["rate_descriptions"]
        }
        
        logger.info(f"📊 Charge estimation completed: {response['charge_estimate']['estimated_charge_percentage']:.3f}% of portfolio")
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"❌ Error estimating charges: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to estimate charges: {str(e)}")

@app.get("/api/simulation/charge-rates")
async def get_charge_rates():
    """Get current Indian equity delivery charge rates"""
    try:
        calculator = BrokerageCalculator()
        charge_info = calculator.get_charge_rates_info()
        
        return JSONResponse(content={
            "success": True,
            "charge_rates": charge_info["charge_rates"],
            "rate_descriptions": charge_info["rate_descriptions"],
            "configuration": charge_info["configuration"],
            "examples": {
                "buy_1_lakh_nse": calculate_single_trade_charges(100000, "BUY", "NSE"),
                "sell_1_lakh_nse": calculate_single_trade_charges(100000, "SELL", "NSE"),
                "buy_1_lakh_bse": calculate_single_trade_charges(100000, "BUY", "BSE"),
                "sell_1_lakh_bse": calculate_single_trade_charges(100000, "SELL", "BSE")
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting charge rates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get charge rates: {str(e)}")

@app.post("/api/simulation/download-tradebook")
async def download_tradebook(request: dict):
    """Generate and download PDF tradebook for simulation results"""
    try:
        from tradebook_pdf_generator import generate_tradebook_pdf
        
        logger.info("📄 Generating PDF tradebook download")
        
        # Extract simulation results and strategy name from request
        simulation_results = request.get("simulation_results", {})
        strategy_name = request.get("strategy_name", "strategy_report")
        
        # Debug: Log the data structure being received
        logger.info(f"🔍 Debug - Summary data: {simulation_results.get('summary', 'No summary')}")
        logger.info(f"🔍 Debug - Final portfolio value: {simulation_results.get('final_portfolio_value', 'No final value')}")
        logger.info(f"🔍 Debug - Benchmark data: {simulation_results.get('final_benchmark_value', 'No benchmark')}")
        
        if not simulation_results:
            raise HTTPException(status_code=400, detail="Simulation results required")
        
        # Generate PDF
        pdf_bytes = generate_tradebook_pdf(simulation_results, strategy_name)
        
        # Create filename
        safe_strategy_name = "".join(c for c in strategy_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_strategy_name}_tradebook.pdf"
        
        # Return PDF as streaming response
        pdf_stream = io.BytesIO(pdf_bytes)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'application/pdf'
        }
        
        logger.info(f"✅ PDF tradebook generated successfully: {filename} ({len(pdf_bytes)} bytes)")
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type='application/pdf',
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"❌ Error generating PDF tradebook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate tradebook: {str(e)}")

async def calculate_stock_momentum(symbol: str, current_date: str, price_data_history: dict, 
                                   indicator_data_history: dict = None, method: str = "20_day_return") -> float:
    """Calculate momentum score for a stock based on historical performance"""
    try:
        current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
        
        # Get lookback period based on method
        if method == "price_roc_66d":
            lookback_days = 90  # 66 trading days + buffer
            required_days = 66
        elif method == "price_roc_222d":
            lookback_days = 300  # 222 trading days + buffer
            required_days = 222
        else:
            lookback_days = 30  # 20-22 trading days + buffer
            required_days = 20
        
        start_date = current_date_obj - timedelta(days=lookback_days)
        
        # Get price history for this symbol
        symbol_prices = []
        for date_str, prices in price_data_history.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if start_date <= date_obj <= current_date_obj and symbol in prices:
                symbol_prices.append({
                    "date": date_obj,
                    "close": prices[symbol]["close_price"]
                })
        
        # Sort by date
        symbol_prices.sort(key=lambda x: x["date"])
        
        if len(symbol_prices) < 2:
            return 0.0  # No momentum if insufficient data
        
        current_price = symbol_prices[-1]["close"]
        
        if method == "20_day_return":
            # Simple 20-day return (or available period)
            if len(symbol_prices) >= 20:
                lookback_price = symbol_prices[-20]["close"]
            else:
                lookback_price = symbol_prices[0]["close"]
            
            if lookback_price > 0:
                return ((current_price / lookback_price) - 1) * 100  # Return as percentage
            return 0.0
        
        elif method == "price_roc_66d":
            # 66-day price momentum
            if len(symbol_prices) >= 66:
                lookback_price = symbol_prices[-66]["close"]
            else:
                lookback_price = symbol_prices[0]["close"]
            
            if lookback_price > 0:
                return ((current_price / lookback_price) - 1) * 100
            return 0.0
        
        elif method == "price_roc_222d":
            # 222-day price momentum
            if len(symbol_prices) >= 222:
                lookback_price = symbol_prices[-222]["close"]
            else:
                lookback_price = symbol_prices[0]["close"]
            
            if lookback_price > 0:
                return ((current_price / lookback_price) - 1) * 100
            return 0.0
            
        elif method == "risk_adjusted":
            # Risk-adjusted return (Sharpe-like calculation)
            if len(symbol_prices) < 5:
                return 0.0
            
            # Calculate daily returns
            daily_returns = []
            for i in range(1, len(symbol_prices)):
                prev_price = symbol_prices[i-1]["close"]
                curr_price = symbol_prices[i]["close"]
                if prev_price > 0:
                    daily_return = (curr_price / prev_price) - 1
                    daily_returns.append(daily_return)
            
            if not daily_returns:
                return 0.0
                
            # Calculate mean and std of returns
            if len(daily_returns) > 0:
                mean_return = sum(daily_returns) / len(daily_returns)
                variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
                std_return = variance ** 0.5
                
                # Risk-adjusted score (annualized)
                if std_return > 0:
                    sharpe_like = (mean_return / std_return) * (252 ** 0.5)  # Annualized
                    return sharpe_like * 100  # Scale for comparison
                return mean_return * 100
            else:
                return 0.0
            
        elif method == "technical":
            # Technical momentum combining price and trend
            if len(symbol_prices) < 10:
                return 0.0
                
            # Calculate 10-day and 20-day moving averages
            prices_10 = symbol_prices[-10:] if len(symbol_prices) >= 10 else symbol_prices
            prices_20 = symbol_prices[-20:] if len(symbol_prices) >= 20 else symbol_prices
            
            if len(prices_10) > 0 and len(prices_20) > 0:
                ma_10 = sum(p["close"] for p in prices_10) / len(prices_10)
                ma_20 = sum(p["close"] for p in prices_20) / len(prices_20)
                
                # Price momentum (current vs 20-day average)
                price_momentum = ((current_price / ma_20) - 1) * 100 if ma_20 > 0 else 0
                
                # Trend momentum (10-day MA vs 20-day MA)
                trend_momentum = ((ma_10 / ma_20) - 1) * 100 if ma_20 > 0 else 0
            else:
                price_momentum = 0
                trend_momentum = 0
            
            # Combined score
            return (price_momentum + trend_momentum) / 2
        
        elif method in ["truevx_roc", "short_mean_roc", "mid_mean_roc", "long_mean_roc", "stock_score_roc"]:
            # Indicator-based momentum (requires indicator_data_history)
            if not indicator_data_history:
                logger.warning(f"⚠️ No indicator data for {method} on symbol {symbol}")
                return 0.0
            
            # Get indicator history for this symbol (22 trading days lookback)
            indicator_records = []
            for date_str in sorted(indicator_data_history.keys()):
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                if date_obj <= current_date_obj and symbol in indicator_data_history[date_str]:
                    indicator_records.append({
                        "date": date_obj,
                        "data": indicator_data_history[date_str][symbol]
                    })
            
            # Sort by date and get most recent records
            indicator_records.sort(key=lambda x: x["date"], reverse=True)
            
            logger.info(f"📊 {symbol}: Found {len(indicator_records)} indicator records for {method}")
            
            if len(indicator_records) <= 22:
                logger.warning(f"⚠️ {symbol}: Not enough indicator data ({len(indicator_records)} records, need > 22)")
                return 0.0  # Not enough data
            
            # Current (most recent) and past (22 days ago)
            current_indicators = indicator_records[0]["data"]
            past_indicators = indicator_records[22]["data"]
            
            # Extract values with NaN handling (convert None to 0)
            def safe_get(data, key):
                val = data.get(key)
                return val if val is not None else 0
            
            if method == "truevx_roc":
                current_val = safe_get(current_indicators, "truevx_score")
                past_val = safe_get(past_indicators, "truevx_score")
                if past_val > 0:
                    return ((current_val - past_val) / past_val) * 100
                return 0.0
            
            elif method == "short_mean_roc":
                current_val = safe_get(current_indicators, "mean_short")
                past_val = safe_get(past_indicators, "mean_short")
                if past_val > 0:
                    return ((current_val - past_val) / past_val) * 100
                return 0.0
            
            elif method == "mid_mean_roc":
                current_val = safe_get(current_indicators, "mean_mid")
                past_val = safe_get(past_indicators, "mean_mid")
                if past_val > 0:
                    return ((current_val - past_val) / past_val) * 100
                return 0.0
            
            elif method == "long_mean_roc":
                current_val = safe_get(current_indicators, "mean_long")
                past_val = safe_get(past_indicators, "mean_long")
                if past_val > 0:
                    return ((current_val - past_val) / past_val) * 100
                return 0.0
            
            elif method == "stock_score_roc":
                # Calculate StockScore for both periods
                current_truevx = safe_get(current_indicators, "truevx_score")
                current_short = safe_get(current_indicators, "mean_short")
                current_mid = safe_get(current_indicators, "mean_mid")
                current_long = safe_get(current_indicators, "mean_long")
                current_score = (0.1 * current_truevx + 0.2 * current_short + 
                               0.3 * current_mid + 0.4 * current_long)
                
                past_truevx = safe_get(past_indicators, "truevx_score")
                past_short = safe_get(past_indicators, "mean_short")
                past_mid = safe_get(past_indicators, "mean_mid")
                past_long = safe_get(past_indicators, "mean_long")
                past_score = (0.1 * past_truevx + 0.2 * past_short + 
                            0.3 * past_mid + 0.4 * past_long)
                
                if past_score > 0:
                    return ((current_score - past_score) / past_score) * 100
                return 0.0
        
        return 0.0
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculating momentum for {symbol}: {e}")
        return 0.0

async def select_top_stocks_by_momentum(qualified_stocks: list, current_holdings: dict, 
                                price_data_history: dict, indicator_data_history: dict,
                                current_date: str, max_holdings: int, 
                                momentum_method: str = "20_day_return") -> tuple:
    """
    Select top stocks based on momentum ranking when portfolio limit is exceeded
    Returns: (selected_stocks, added_stocks, removed_stocks)
    """
    try:
        # If we're under the limit, no need to rank
        total_candidates = len(qualified_stocks) + len(current_holdings)
        if total_candidates <= max_holdings:
            # Add all qualified stocks that aren't already held
            new_stocks = [stock for stock in qualified_stocks 
                         if stock["symbol"] not in current_holdings]
            return qualified_stocks, new_stocks, []
        
        # Get all candidate stocks (current holdings + newly qualified)
        all_candidates = []
        
        # Add current holdings with their momentum scores
        for symbol in current_holdings.keys():
            momentum = await calculate_stock_momentum(
                symbol, current_date, price_data_history, indicator_data_history, momentum_method
            )
            all_candidates.append({
                "symbol": symbol,
                "momentum_score": momentum,
                "is_current_holding": True,
                "truevx_score": 0  # Will be updated if in qualified_stocks
            })
            logger.info(f"🔍 Momentum ({momentum_method}) for {symbol} (holding): {momentum:.2f}")
        
        # Add newly qualified stocks
        for stock in qualified_stocks:
            symbol = stock["symbol"]
            if symbol not in current_holdings:
                momentum = await calculate_stock_momentum(
                    symbol, current_date, price_data_history, indicator_data_history, momentum_method
                )
                all_candidates.append({
                    "symbol": symbol,
                    "momentum_score": momentum,
                    "is_current_holding": False,
                    "truevx_score": stock.get("truevx_score", 0)
                })
                logger.info(f"🔍 Momentum ({momentum_method}) for {symbol} (new): {momentum:.2f}")
            else:
                # Update truevx_score for existing holdings
                for candidate in all_candidates:
                    if candidate["symbol"] == symbol:
                        candidate["truevx_score"] = stock.get("truevx_score", 0)
                        break
        
        # Sort by momentum score (descending - highest momentum first)
        all_candidates.sort(key=lambda x: x["momentum_score"], reverse=True)
        
        # Select top stocks up to max_holdings limit
        selected_candidates = all_candidates[:max_holdings]
        selected_symbols = {candidate["symbol"] for candidate in selected_candidates}
        
        # Determine added and removed stocks
        current_symbols = set(current_holdings.keys())
        added_stocks = [candidate["symbol"] for candidate in selected_candidates 
                       if candidate["symbol"] not in current_symbols]
        removed_stocks = [symbol for symbol in current_symbols 
                         if symbol not in selected_symbols]
        
        # Convert selected candidates back to qualified_stocks format
        selected_stocks = []
        for candidate in selected_candidates:
            # Find the original stock data or create it
            original_stock = None
            for stock in qualified_stocks:
                if stock["symbol"] == candidate["symbol"]:
                    original_stock = stock
                    break
            
            if original_stock:
                selected_stocks.append(original_stock)
            else:
                # For existing holdings that remain selected
                selected_stocks.append({
                    "symbol": candidate["symbol"],
                    "truevx_score": candidate["truevx_score"],
                    "momentum_score": candidate["momentum_score"]
                })
        
        logger.info(f"🎯 Portfolio limit applied: {len(all_candidates)} candidates → {len(selected_stocks)} selected")
        logger.info(f"📈 Added: {added_stocks}")
        logger.info(f"📉 Removed: {removed_stocks}")
        
        return selected_stocks, added_stocks, removed_stocks
        
    except Exception as e:
        logger.error(f"❌ Error in momentum selection: {e}")
        # Fallback: just take first max_holdings qualified stocks
        limited_stocks = qualified_stocks[:max_holdings]
        new_stocks = [stock for stock in limited_stocks 
                     if stock["symbol"] not in current_holdings]
        return limited_stocks, new_stocks, []

async def run_strategy_simulation_debug(data_manager, strategy, universe_symbols, params):
    """Debug version of simulation with extensive logging"""
    try:
        logger.info(f"🔍 DEBUG: Starting simulation with {len(universe_symbols)} symbols")
        indicators_coll = data_manager.db[data_manager.indicators_collection]
        
        # Parse date range
        start_date = datetime.strptime(params.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(params.end_date, "%Y-%m-%d")
        
        # Get indicator data (simplified for debug)
        indicator_query = {
            "indicator_type": "truevx",
            "symbol": {"$in": universe_symbols},
            "date": {"$gte": start_date, "$lte": end_date}
        }
        
        indicator_data = {}
        cursor = indicators_coll.find(indicator_query).sort("date", 1)
        for doc in cursor:
            date_str = doc["date"].strftime('%Y-%m-%d')
            if date_str not in indicator_data:
                indicator_data[date_str] = {}
            
            indicator_data[date_str][doc["symbol"]] = {
                "symbol": doc["symbol"],
                "truevx_score": doc["data"].get("truevx_score") or 0,
                "mean_short": doc["data"].get("mean_short") or 0,
                "mean_mid": doc["data"].get("mean_mid") or 0,
                "mean_long": doc["data"].get("mean_long") or 0
            }
        
        # Get price data
        from stock_data_manager import StockDataManager
        price_data = {}
        
        async with StockDataManager() as stock_manager:
            for symbol in universe_symbols:
                symbol_prices = await stock_manager.get_price_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    limit=10000,  # Increased limit for full date range
                    sort_order=1
                )
                
                for record in symbol_prices:
                    date_str = record.date.strftime('%Y-%m-%d')
                    if date_str not in price_data:
                        price_data[date_str] = {}
                    
                    price_data[date_str][symbol] = {
                        "symbol": symbol,
                        "close_price": float(record.close_price),
                    }
        
        # Initialize simulation
        portfolio_value = params.portfolio_base_value
        current_holdings = {}
        debug_results = []
        
        # Get trading dates
        dates = sorted(set(indicator_data.keys()) & set(price_data.keys()))
        rebalance_dates = get_rebalance_dates(dates, params.rebalance_frequency, params.rebalance_date)
        
        logger.info(f"🧪 DEBUG: Processing {len(dates)} dates")
        logger.info(f"🧪 DEBUG: Rebalance dates: {list(rebalance_dates)}")
        
        for i, date_str in enumerate(dates):
            logger.info(f"\n📅 DEBUG DAY {i+1}: {date_str}")
            
            day_indicators = indicator_data.get(date_str, {})
            day_prices = price_data.get(date_str, {})
            
            logger.info(f"📊 Available indicators: {len(day_indicators)}, Available prices: {len(day_prices)}")
            if day_indicators:
                sample_symbol = list(day_indicators.keys())[0]
                logger.info(f"📈 Sample indicator data for {sample_symbol}: {day_indicators[sample_symbol]}")
            
            if not day_indicators or not day_prices:
                logger.info(f"⚠️ No data for {date_str}, skipping")
                continue
            
            # Log strategy rules for debugging
            logger.info(f"📋 Strategy rules: {strategy['rules']}")
            
            # Apply strategy rules
            qualified_stocks = apply_strategy_rules(day_indicators, strategy["rules"])
            qualified_symbols = [stock["symbol"] for stock in qualified_stocks]
            
            logger.info(f"🎯 Qualified stocks: {qualified_symbols} (from {len(day_indicators)} available)")
            
            # Check if rebalancing
            should_rebalance = (params.rebalance_frequency == "dynamic" or 
                              date_str in rebalance_dates or 
                              i == 0)
            
            logger.info(f"🔄 Should rebalance: {should_rebalance}")
            
            if should_rebalance:
                current_portfolio_value = calculate_current_portfolio_value(current_holdings, day_prices)
                logger.info(f"💰 Current portfolio value: ₹{current_portfolio_value:,.2f}")
                
                # Log detailed holdings
                logger.info(f"📊 Current holdings ({len(current_holdings)}):")
                for symbol, holding in current_holdings.items():
                    if symbol in day_prices:
                        price = day_prices[symbol]["close_price"]
                        value = holding["shares"] * price
                        logger.info(f"  • {symbol}: {holding['shares']:.2f} @ ₹{price:.2f} = ₹{value:,.2f}")
                
                # Simple rebalancing for debug (no momentum for clarity)
                if i == 0:
                    rebalance_value = params.portfolio_base_value
                else:
                    rebalance_value = current_portfolio_value
                
                # Apply momentum-based portfolio limit selection (same as actual simulation)
                selected_stocks, momentum_added, momentum_removed = await select_top_stocks_by_momentum(
                    qualified_stocks=qualified_stocks,
                    current_holdings=current_holdings,
                    price_data_history=price_data,
                    indicator_data_history=indicator_data,
                    current_date=date_str,
                    max_holdings=params.max_holdings,
                    momentum_method=params.momentum_ranking
                )
                
                # Update symbols list to only selected stocks
                selected_symbols = [stock["symbol"] for stock in selected_stocks]
                
                logger.info(f"💵 Rebalance value: ₹{rebalance_value:,.2f}")
                logger.info(f"📊 Selected {len(selected_symbols)}/{len(qualified_symbols)} stocks by momentum")
                
                # Clear holdings and rebuild
                current_holdings = {}
                
                # Equal weight allocation among selected momentum stocks
                if selected_symbols:
                    allocation_per_stock = rebalance_value / len(selected_symbols)
                    logger.info(f"📊 Allocation per stock: ₹{allocation_per_stock:,.2f}")
                    
                    for symbol in selected_symbols:
                        if symbol in day_prices:
                            price = day_prices[symbol]["close_price"]
                            shares = allocation_per_stock / price
                            current_holdings[symbol] = {
                                "shares": shares,
                                "avg_price": price
                            }
                            logger.info(f"  📈 Bought {symbol}: {shares:.2f} shares @ ₹{price:.2f}")
                
                # Recalculate portfolio value
                new_portfolio_value = calculate_current_portfolio_value(current_holdings, day_prices)
                logger.info(f"✅ New portfolio value: ₹{new_portfolio_value:,.2f}")
                portfolio_value = new_portfolio_value
            else:
                # Just update portfolio value
                if current_holdings:
                    portfolio_value = calculate_current_portfolio_value(current_holdings, day_prices)
                    logger.info(f"📊 Updated portfolio value: ₹{portfolio_value:,.2f}")
            
            # Create debug result
            debug_results.append({
                "date": date_str,
                "day_number": i + 1,
                "portfolio_value": portfolio_value,
                "should_rebalance": should_rebalance,
                "qualified_stocks": qualified_symbols,
                "holdings_count": len(current_holdings),
                "holdings_detail": [
                    {
                        "symbol": symbol,
                        "shares": holding["shares"],
                        "price": day_prices.get(symbol, {}).get("close_price", 0),
                        "value": holding["shares"] * day_prices.get(symbol, {}).get("close_price", 0)
                    }
                    for symbol, holding in current_holdings.items()
                    if symbol in day_prices
                ]
            })
        
        return {
            "params": params.dict(),
            "debug_results": debug_results,
            "summary": {
                "total_days": len(debug_results),
                "rebalance_days": len([r for r in debug_results if r["should_rebalance"]]),
                "final_value": debug_results[-1]["portfolio_value"] if debug_results else 0
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Debug simulation error: {e}")
        raise

async def rebalance_portfolio_with_charges(current_holdings: dict, 
                                         selected_symbols: list,
                                         day_prices: dict,
                                         available_capital: float,
                                         params,
                                         holding_periods: dict = None) -> dict:
    """
    Rebalance portfolio accounting for transaction charges
    
    Args:
        current_holdings: Current portfolio holdings {symbol: {"shares": float, "avg_price": float}}
        selected_symbols: List of symbols to hold in the new portfolio
        day_prices: Current day prices {symbol: {"close_price": float, ...}}
        available_capital: Available capital for rebalancing
        params: Simulation parameters including brokerage settings
        
    Returns:
        Dictionary with new holdings, charges, and trade details
    """
    try:
        # Initialize brokerage calculator
        calculator = BrokerageCalculator(
            default_exchange=params.exchange,
            custom_brokerage_rate=params.custom_brokerage_rate
        )
        
        rebalance_result = {
            "new_holdings": {},
            "total_buy_charges": 0.0,
            "total_sell_charges": 0.0,
            "net_capital_used": 0.0,
            "charge_breakdown": {},
            "trade_details": [],
            "sell_proceeds": 0.0,
            "remaining_cash": 0.0
        }
        
        # Phase 1: Calculate sell transactions and charges
        sell_trades = []
        total_sell_proceeds = 0.0
        
        for symbol, holding in current_holdings.items():
            if symbol not in selected_symbols and symbol in day_prices:
                # Create sell trade
                sell_trade = {
                    "symbol": symbol,
                    "quantity": holding["shares"],
                    "price": day_prices[symbol]["close_price"]
                }
                sell_trades.append(sell_trade)
        
        # Calculate sell charges if there are sell trades
        if sell_trades:
            sell_result = calculator.calculate_portfolio_rebalance_charges(sell_trades, [])
            rebalance_result["total_sell_charges"] = sell_result["total_sell_charges"]
            rebalance_result["sell_proceeds"] = sell_result["net_sell_proceeds"]
            total_sell_proceeds = sell_result["net_sell_proceeds"]
            
            # Add sell trade details
            for trade_detail in sell_result["sell_trades"]:
                rebalance_result["trade_details"].append(trade_detail)
        
        # Phase 2: Calculate available capital for purchases
        total_available = available_capital + total_sell_proceeds
        
        # Phase 3: Calculate buy transactions with iterative charge adjustment
        if selected_symbols:
            # Get prices for selected symbols
            valid_symbols = [symbol for symbol in selected_symbols if symbol in day_prices]
            
            if valid_symbols:
                if params.rebalance_type == "skewed" and holding_periods is not None:
                    # Use skewed allocation based on holding periods
                    skewed_allocations = calculate_skewed_allocation(
                        selected_symbols=valid_symbols,
                        holding_periods=holding_periods,
                        total_value=total_available
                    )
                    
                    # Estimate total buy charges for skewed allocation
                    estimated_buy_charges = 0.0
                    for symbol in valid_symbols:
                        allocation = skewed_allocations[symbol]
                        estimated_charges = calculator.calculate_transaction_charges(
                            trade_value=allocation,
                            trade_type="BUY"
                        )
                        estimated_buy_charges += estimated_charges.total_charges
                    
                    # Adjust allocations proportionally to account for charges
                    available_for_investment = max(0, total_available - estimated_buy_charges)
                    adjustment_factor = available_for_investment / total_available if total_available > 0 else 0
                    
                    # Create buy trades with skewed allocations
                    buy_trades = []
                    for symbol in valid_symbols:
                        if symbol in day_prices:
                            price = day_prices[symbol]["close_price"]
                            adjusted_allocation = skewed_allocations[symbol] * adjustment_factor
                            shares_to_buy = adjusted_allocation / price if price > 0 else 0
                            
                            if shares_to_buy > 0:
                                buy_trade = {
                                    "symbol": symbol,
                                    "quantity": shares_to_buy,
                                    "price": price
                                }
                                buy_trades.append(buy_trade)
                                
                else:
                    # Original equal allocation logic
                    if valid_symbols:  # Add check to prevent division by zero
                        # Initial allocation estimate (will be adjusted for charges)
                        initial_allocation_per_stock = total_available / len(valid_symbols)
                        
                        # Estimate total buy charges
                        estimated_buy_charges = 0.0
                        for symbol in valid_symbols:
                            estimated_charges = calculator.calculate_transaction_charges(
                                trade_value=initial_allocation_per_stock,
                                trade_type="BUY"
                            )
                            estimated_buy_charges += estimated_charges.total_charges
                        
                        # Adjust allocation to account for estimated charges
                        available_for_investment = max(0, total_available - estimated_buy_charges)
                        target_investment_per_stock = available_for_investment / len(valid_symbols) if valid_symbols else 0
                        
                        # Create buy trades
                        buy_trades = []
                        for symbol in valid_symbols:
                            if symbol in day_prices:
                                price = day_prices[symbol]["close_price"]
                                shares_to_buy = target_investment_per_stock / price if price > 0 else 0
                            
                            if shares_to_buy > 0:
                                buy_trade = {
                                    "symbol": symbol,
                                    "quantity": shares_to_buy,
                                    "price": price
                                }
                                buy_trades.append(buy_trade)
                    else:
                        # No valid symbols for allocation
                        logger.warning(f"⚠️  No valid symbols for charge-aware rebalancing")
                        buy_trades = []
                
                # Calculate actual buy charges
                if buy_trades:
                    buy_result = calculator.calculate_portfolio_rebalance_charges([], buy_trades)
                    rebalance_result["total_buy_charges"] = buy_result["total_buy_charges"]
                    rebalance_result["net_capital_used"] = buy_result["net_buy_cost"]
                    
                    # Add buy trade details
                    for trade_detail in buy_result["buy_trades"]:
                        rebalance_result["trade_details"].append(trade_detail)
                    
                    # Create new holdings
                    for trade in buy_trades:
                        symbol = trade["symbol"]
                        price = trade["price"]
                        shares = trade["quantity"]
                        
                        # Find the corresponding trade detail with charges
                        trade_charges = None
                        for detail in buy_result["buy_trades"]:
                            if detail["symbol"] == symbol:
                                trade_charges = detail["charges"]
                                break
                        
                        rebalance_result["new_holdings"][symbol] = {
                            "shares": shares,
                            "avg_price": price,
                            "total_cost": shares * price + (trade_charges["total_charges"] if trade_charges else 0)
                            # Removed cumulative_charges from individual holdings - this was causing inflation
                        }
        
        # Calculate remaining cash
        total_spent = rebalance_result["net_capital_used"]
        rebalance_result["remaining_cash"] = max(0, total_available - total_spent)
        
        # Aggregate charge breakdown with detailed components
        total_charges = rebalance_result["total_buy_charges"] + rebalance_result["total_sell_charges"]
        
        # Calculate detailed charge breakdown from trade details
        component_breakdown = {
            "stt": 0.0,
            "transaction_charges": 0.0,
            "sebi_charges": 0.0,
            "stamp_duty": 0.0,
            "brokerage": 0.0,
            "gst": 0.0
        }
        
        # Aggregate charges from all trade details
        for trade_detail in rebalance_result["trade_details"]:
            if "charges" in trade_detail:
                charges = trade_detail["charges"]
                component_breakdown["stt"] += charges.get("stt", 0.0)
                component_breakdown["transaction_charges"] += charges.get("transaction_charges", 0.0)
                component_breakdown["sebi_charges"] += charges.get("sebi_charges", 0.0)
                component_breakdown["stamp_duty"] += charges.get("stamp_duty", 0.0)
                component_breakdown["brokerage"] += charges.get("brokerage", 0.0)
                component_breakdown["gst"] += charges.get("gst", 0.0)
        
        rebalance_result["charge_breakdown"] = {
            "total_charges": total_charges,
            "buy_charges": rebalance_result["total_buy_charges"],
            "sell_charges": rebalance_result["total_sell_charges"],
            "net_impact": total_charges,
            "components": component_breakdown,
            "charge_rate_info": {
                "exchange": params.exchange,
                "custom_brokerage_rate": params.custom_brokerage_rate,
                "effective_charge_percent": (total_charges / available_capital * 100) if available_capital > 0 else 0
            }
        }
        
        logger.info(f"💰 Charge-aware rebalancing completed: Total charges = ₹{total_charges:,.2f}")
        logger.info(f"📊 Buy charges: ₹{rebalance_result['total_buy_charges']:,.2f}, Sell charges: ₹{rebalance_result['total_sell_charges']:,.2f}")
        logger.info(f"🏦 Remaining cash: ₹{rebalance_result['remaining_cash']:,.2f}")
        
        return rebalance_result
        
    except Exception as e:
        logger.error(f"❌ Error in charge-aware rebalancing: {e}")
        raise

def calculate_skewed_allocation(selected_symbols: list, 
                               holding_periods: dict, 
                               total_value: float) -> dict:
    """
    Calculate skewed allocation based on holding periods
    
    Args:
        selected_symbols: List of symbols to allocate to
        holding_periods: Dictionary of {symbol: consecutive_periods}
        total_value: Total value to allocate
        
    Returns:
        Dictionary of {symbol: allocation_amount}
    """
    if not selected_symbols:
        return {}
    
    # Calculate weights based on holding periods
    symbol_weights = {}
    total_weight = 0
    
    for symbol in selected_symbols:
        # Get holding period (0 for new stocks)
        periods_held = holding_periods.get(symbol, 0)
        
        # Calculate weight using exponential function
        # Formula: weight = 1 + (holding_periods * 0.3)
        # This gives: 0 periods = weight 1.0, 1 period = weight 1.3, 2 periods = weight 1.6, etc.
        weight = 1.0 + (periods_held * 0.3)
        
        symbol_weights[symbol] = weight
        total_weight += weight
    
    # Calculate allocation amounts
    allocations = {}
    if total_weight > 0:  # Check for division by zero
        for symbol in selected_symbols:
            weight_ratio = symbol_weights[symbol] / total_weight
            allocation = total_value * weight_ratio
            allocations[symbol] = allocation
    else:
        # If total_weight is 0, use equal allocation
        if selected_symbols:
            equal_allocation = total_value / len(selected_symbols)
            for symbol in selected_symbols:
                allocations[symbol] = equal_allocation
    
    logger.info(f"📊 Skewed allocation calculated:")
    for symbol in selected_symbols:
        periods = holding_periods.get(symbol, 0)
        weight = symbol_weights[symbol]
        allocation = allocations[symbol]
        logger.info(f"  📈 {symbol}: {periods} periods held, weight {weight:.1f}, allocation ₹{allocation:,.0f}")
    
    return allocations

async def run_strategy_simulation(data_manager, strategy, universe_symbols, params):
    """Execute the strategy simulation logic with daily rebalancing"""
    try:
        # Initialize cumulative charges at the start of each simulation
        # This fixes the bug where charges were persisting across API calls
        run_strategy_simulation.cumulative_charges = 0.0
        
        logger.info(f"🔍 Starting simulation with {len(universe_symbols)} symbols")
        indicators_coll = data_manager.db[data_manager.indicators_collection]
        
        # Parse date range
        start_date = datetime.strptime(params.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(params.end_date, "%Y-%m-%d")
        
        # Get all indicator data for the universe and date range
        indicator_query = {
            "indicator_type": "truevx",
            "symbol": {"$in": universe_symbols},
            "date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        # Process indicator data by date
        indicator_data = {}
        cursor = indicators_coll.find(indicator_query).sort("date", 1)
        for doc in cursor:
            date_str = doc["date"].strftime('%Y-%m-%d')
            if date_str not in indicator_data:
                indicator_data[date_str] = {}
            
            indicator_data[date_str][doc["symbol"]] = {
                "symbol": doc["symbol"],
                "truevx_score": doc["data"].get("truevx_score") or 0,
                "mean_short": doc["data"].get("mean_short") or 0,
                "mean_mid": doc["data"].get("mean_mid") or 0,
                "mean_long": doc["data"].get("mean_long") or 0
            }
        
        # Process price data by date using StockDataManager
        from stock_data_manager import StockDataManager
        price_data = {}
        
        logger.info(f"🔄 Loading price data for {len(universe_symbols)} symbols")
        
        async with StockDataManager() as stock_manager:
            for symbol in universe_symbols:
                symbol_prices = await stock_manager.get_price_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    limit=10000,  # Get sufficient data for the date range
                    sort_order=1   # Ascending order (oldest first)
                )
                
                logger.info(f"📈 Got {len(symbol_prices)} price records for {symbol}")
                
                for record in symbol_prices:
                    date_str = record.date.strftime('%Y-%m-%d')
                    if date_str not in price_data:
                        price_data[date_str] = {}
                    
                    price_data[date_str][symbol] = {
                        "symbol": symbol,
                        "close_price": float(record.close_price),
                        "open_price": float(record.open_price),
                        "high_price": float(record.high_price),
                        "low_price": float(record.low_price),
                        "volume": int(record.volume) if record.volume else 0
                    }
        
        logger.info(f"📊 Loaded price data for {len(price_data)} trading dates")
        
        # Initialize simulation state
        portfolio_value = params.portfolio_base_value
        current_holdings = {}  # {symbol: {"shares": float, "avg_price": float}}
        cash_balance = params.portfolio_base_value  # Track cash separately
        simulation_results = []
        prev_portfolio_value = portfolio_value
        
        # Initialize holding period tracking for skewed allocation
        holding_periods = {}  # {symbol: consecutive_rebalance_periods}
        rebalance_count = 0  # Track number of rebalances for logging
        
        # Initialize benchmark tracking
        benchmark_value = params.portfolio_base_value  # Start with same base value
        prev_benchmark_close = None
        
        # Get benchmark data for comparison
        if params.benchmark_symbol:
            benchmark_symbol = params.benchmark_symbol
        elif params.universe == "NIFTY50":
            benchmark_symbol = "Nifty 50"
        elif params.universe == "NIFTY100":
            benchmark_symbol = "Nifty 100"  # Assuming this exists
        elif params.universe == "NIFTY500":
            benchmark_symbol = "Nifty 500"
        else:
            benchmark_symbol = "Nifty 50"  # Default fallback
            
        benchmark_prices = {}
        
        logger.info(f"📊 Loading benchmark data for {benchmark_symbol}")
        
        async with StockDataManager() as stock_manager:
            benchmark_data = await stock_manager.get_price_data(
                symbol=benchmark_symbol,
                start_date=start_date,
                end_date=end_date,
                limit=10000,
                sort_order=1
            )
            
            for record in benchmark_data:
                date_str = record.date.strftime('%Y-%m-%d')
                benchmark_prices[date_str] = float(record.close_price)
        
        logger.info(f"📈 Loaded benchmark data for {len(benchmark_prices)} trading dates")
        
        # Get all trading dates where we have both indicator and price data
        dates = sorted(set(indicator_data.keys()) & set(price_data.keys()))
        rebalance_dates = get_rebalance_dates(dates, params.rebalance_frequency, params.rebalance_date)
        
        logger.info(f"📅 Processing {len(dates)} trading days: {dates[:5]}...{dates[-5:] if len(dates) > 5 else ''}")
        logger.info(f"📊 Sample price data for first date: {list(price_data.get(dates[0], {}).keys())[:3] if dates else 'No dates'}")
        
        for i, date_str in enumerate(dates):
            day_indicators = indicator_data.get(date_str, {})
            day_prices = price_data.get(date_str, {})
            
            # Skip if no data for this day
            if not day_indicators or not day_prices:
                continue
            
            # Apply strategy rules to filter qualified stocks
            qualified_stocks = apply_strategy_rules(day_indicators, strategy["rules"])
            qualified_symbols = [stock["symbol"] for stock in qualified_stocks]
            
            # Track additions and exits
            new_added = []
            exited = []
            exited_details = []  # Initialize detailed exit tracking
            
            # Rebalance portfolio if needed (dynamic = daily, else use schedule)
            should_rebalance = (params.rebalance_frequency == "dynamic" or 
                              date_str in rebalance_dates or 
                              i == 0)  # Always rebalance on first day
            
            if should_rebalance:
                rebalance_reason = "First day" if i == 0 else ("Dynamic" if params.rebalance_frequency == "dynamic" else "Scheduled")
                logger.info(f"📅 {rebalance_reason} rebalancing triggered on {date_str}")
            
            if should_rebalance :
                # Calculate current portfolio value before rebalancing
                current_portfolio_value = calculate_current_portfolio_value(current_holdings, day_prices, cash_balance)
                prev_holdings = current_holdings.copy()

                # Use current portfolio value (preserve capital) or base value on first day
                if i == 0:  # First day
                    rebalance_value = params.portfolio_base_value
                else:
                    # Use current portfolio value to preserve capital - don't amplify
                    rebalance_value = current_portfolio_value
                    # Safety floor to prevent portfolio from going to zero
                    rebalance_value = max(rebalance_value, params.portfolio_base_value * 0.01)
                
                logger.info(f"🔄 Rebalancing on {date_str}: Current Value = ₹{current_portfolio_value:,.2f}, Rebalance Value = ₹{rebalance_value:,.2f}")
                
                # Log portfolio before rebalancing
                logger.info(f"📊 BEFORE Rebalancing: {len(current_holdings)} holdings worth ₹{current_portfolio_value:,.2f}")
                for symbol, holding in current_holdings.items():
                    if symbol in day_prices:
                        current_price = day_prices[symbol]["close_price"]
                        market_value = holding["shares"] * current_price
                        logger.info(f"  📈 {symbol}: {holding['shares']:.2f} shares @ ₹{current_price:.2f} = ₹{market_value:,.2f}")
                
                # Apply momentum-based portfolio limit selection
                selected_stocks, momentum_added, momentum_removed = await select_top_stocks_by_momentum(
                    qualified_stocks=qualified_stocks,
                    current_holdings=current_holdings,
                    price_data_history=price_data,
                    indicator_data_history=indicator_data,
                    current_date=date_str,
                    max_holdings=params.max_holdings,
                    momentum_method=params.momentum_ranking
                )
                
                # Update symbols list to only selected stocks
                selected_symbols = [stock["symbol"] for stock in selected_stocks]
                
                # Track additions and exits based on momentum selection
                new_added = momentum_added
                # Start with momentum-based exits (just symbol names)
                exited_symbols = list(momentum_removed) if momentum_removed else []
                
                # Calculate exit details for ALL stocks that will be removed BEFORE deleting them
                for symbol in list(current_holdings.keys()):
                    if symbol not in selected_symbols:
                        # Calculate exit performance before deleting
                        holding = current_holdings[symbol]
                        if symbol in day_prices:
                            current_price = day_prices[symbol]["close_price"]
                            exit_pnl = (current_price - holding["avg_price"]) * holding["shares"]
                            exit_pnl_percent = ((current_price / holding["avg_price"]) - 1) * 100 if holding["avg_price"] > 0 else 0
                            
                            exit_details = {
                                "symbol": symbol,
                                "company_name": symbol,  # TODO: Get from company mapping
                                "quantity": holding["shares"],
                                "avg_price": holding["avg_price"],
                                "exit_price": current_price,
                                "pnl": exit_pnl,
                                "pnl_percent": exit_pnl_percent,
                                "sector": "Unknown"  # TODO: Get from mapping
                            }
                            exited_details.append(exit_details)
                            logger.info(f"📤 Exit details calculated for {symbol}: {exit_pnl_percent:.2f}% P&L")
                        
                        # Add to exit symbols list if not already there
                        if symbol not in exited_symbols:
                            exited_symbols.append(symbol)
                
                # Now remove the holdings and add cash from sales
                for symbol in list(current_holdings.keys()):
                    if symbol not in selected_symbols:
                        # Calculate sale proceeds before deleting holding
                        if symbol in day_prices:
                            holding = current_holdings[symbol]
                            sale_price = day_prices[symbol]["close_price"]
                            sale_proceeds = holding["shares"] * sale_price
                            cash_balance += sale_proceeds
                            logger.info(f"💰 Sold {symbol}: {holding['shares']:.2f} shares @ ₹{sale_price:.2f} = ₹{sale_proceeds:,.2f}")
                        
                        del current_holdings[symbol]
                
                # Set the final exited list
                exited = exited_symbols
                
                # Initialize daily charges tracking
                daily_charges = {"total_charges": 0.0, "buy_charges": 0.0, "sell_charges": 0.0, "charge_breakdown": {}}
                rebalance_trade_details = []
                
                # Choose rebalancing method based on brokerage settings
                if params.include_brokerage:
                    # Use charge-aware rebalancing
                    logger.info(f"💰 Using charge-aware rebalancing with {params.exchange} exchange")
                    
                    rebalance_result = await rebalance_portfolio_with_charges(
                        current_holdings=current_holdings,
                        selected_symbols=selected_symbols,
                        day_prices=day_prices,
                        available_capital=rebalance_value,
                        params=params,
                        holding_periods=holding_periods
                    )
                    
                    # Update holdings with charge tracking
                    current_holdings = rebalance_result["new_holdings"]
                    
                    # Track daily charges
                    daily_charges = rebalance_result["charge_breakdown"]
                    rebalance_trade_details = rebalance_result["trade_details"]
                    
                    # Adjust portfolio value for charges (charges are already deducted in rebalance logic)
                    new_portfolio_value = calculate_current_portfolio_value(current_holdings, day_prices, 0)
                    cash_balance = rebalance_result["remaining_cash"]  # Update cash balance from rebalancing
                    new_portfolio_value += cash_balance
                    
                    logger.info(f"💰 Rebalancing with charges: Total charges = ₹{daily_charges['total_charges']:,.2f}")
                    logger.info(f"📊 Buy charges: ₹{daily_charges['buy_charges']:,.2f}, Sell charges: ₹{daily_charges['sell_charges']:,.2f}")
                    logger.info(f"🏦 Remaining cash: ₹{rebalance_result['remaining_cash']:,.2f}")
                    
                else:
                    # Rebalancing without brokerage charges
                    if selected_symbols:
                        if params.rebalance_type == "skewed":
                            # Skewed allocation based on holding periods
                            logger.info(f"📊 Using skewed allocation based on holding periods")
                            skewed_allocations = calculate_skewed_allocation(
                                selected_symbols=selected_symbols,
                                holding_periods=holding_periods,
                                total_value=cash_balance  # Use available cash
                            )
                            
                            # Clear current holdings for fresh allocation
                            current_holdings = {}
                            total_invested = 0
                            
                            # Apply skewed allocations
                            for symbol in selected_symbols:
                                if symbol in day_prices:
                                    allocation_amount = skewed_allocations[symbol]
                                    price = day_prices[symbol]["close_price"]
                                    target_shares = allocation_amount / price
                                    investment_amount = target_shares * price
                                    
                                    current_holdings[symbol] = {
                                        "shares": target_shares,
                                        "avg_price": price
                                    }
                                    
                                    total_invested += investment_amount
                                    logger.info(f"📈 Skewed buy {symbol}: {target_shares:.2f} shares @ ₹{price:.2f} = ₹{investment_amount:,.2f}")
                            
                            # Update cash balance after purchases
                            cash_balance -= total_invested
                            logger.info(f"💵 Cash remaining after skewed allocation: ₹{cash_balance:,.2f}")
                                    
                        else:
                            # Original equal weight allocation
                            if selected_symbols:  # Add check to prevent division by zero
                                # Use available cash for investments
                                available_cash = cash_balance
                                target_value_per_stock = available_cash / len(selected_symbols)
                                
                                logger.info(f"💰 Equal allocation (no charges): ₹{target_value_per_stock:,.2f} per stock across {len(selected_symbols)} stocks")
                                logger.info(f"💵 Available cash for investment: ₹{available_cash:,.2f}")
                                
                                # Clear current holdings for fresh allocation
                                current_holdings = {}
                                total_invested = 0
                                
                                # Rebalance all holdings to equal weights
                                for symbol in selected_symbols:
                                    if symbol in day_prices:
                                        price = day_prices[symbol]["close_price"]
                                        target_shares = target_value_per_stock / price
                                        investment_amount = target_shares * price
                                        
                                        current_holdings[symbol] = {
                                            "shares": target_shares,
                                            "avg_price": price
                                        }
                                        
                                        total_invested += investment_amount
                                        logger.info(f"📈 Bought {symbol}: {target_shares:.2f} shares @ ₹{price:.2f} = ₹{investment_amount:,.2f}")
                                
                                # Update cash balance after purchases
                                cash_balance -= total_invested
                                logger.info(f"💵 Cash remaining after purchases: ₹{cash_balance:,.2f}")
                            else:
                                logger.warning(f"⚠️  No stocks selected for rebalancing on {date_str}, keeping previous holdings")
                                current_holdings = prev_holdings
                    else:
                        current_holdings = prev_holdings
                    
                    # Recalculate portfolio value after rebalancing
                    new_portfolio_value = calculate_current_portfolio_value(current_holdings, day_prices, cash_balance)
                
                # Log portfolio after rebalancing
                logger.info(f"📊 AFTER Rebalancing: {len(current_holdings)} holdings worth ₹{new_portfolio_value:,.2f}")
                for symbol, holding in current_holdings.items():
                    if symbol in day_prices:
                        current_price = day_prices[symbol]["close_price"]
                        market_value = holding["shares"] * current_price
                        logger.info(f"  📈 {symbol}: {holding['shares']:.2f} shares @ ₹{current_price:.2f} = ₹{market_value:,.2f}")
                
                logger.info(f"✅ Rebalancing complete: ₹{current_portfolio_value:,.2f} → ₹{new_portfolio_value:,.2f}")
                portfolio_value = new_portfolio_value
                
                # Update holding periods after rebalancing
                rebalance_count += 1
                logger.info(f"📊 Updating holding periods after rebalance #{rebalance_count}")
                
                # Increment holding periods for stocks that remain in portfolio
                new_holding_periods = {}
                for symbol in selected_symbols:
                    if symbol in holding_periods:
                        # Stock was already held, increment its period
                        new_holding_periods[symbol] = holding_periods[symbol] + 1
                        logger.info(f"  📈 {symbol}: holding period {holding_periods[symbol]} → {new_holding_periods[symbol]}")
                    else:
                        # New stock, start with 0 periods
                        new_holding_periods[symbol] = 0
                        logger.info(f"  🆕 {symbol}: new stock, holding period = 0")
                
                # Replace holding_periods with updated values
                holding_periods = new_holding_periods
            else:
                if current_holdings:
                    # Just update portfolio value based on price changes
                    portfolio_value = calculate_current_portfolio_value(current_holdings, day_prices, cash_balance)
                else:
                    # No holdings, portfolio value is just cash
                    portfolio_value = cash_balance 

            # Calculate day PnL
            day_pnl = portfolio_value - prev_portfolio_value
            prev_portfolio_value = portfolio_value
            
            # Calculate benchmark value
            current_benchmark_close = benchmark_prices.get(date_str)
            if current_benchmark_close is not None:
                if prev_benchmark_close is not None:
                    # Calculate benchmark daily return and apply to benchmark value
                    benchmark_return = (current_benchmark_close / prev_benchmark_close) - 1
                    benchmark_value = benchmark_value * (1 + benchmark_return)
                else:
                    # First day - initialize
                    benchmark_value = params.portfolio_base_value
                
                prev_benchmark_close = current_benchmark_close
            else:
                logger.warning(f"⚠️ No benchmark data for {date_str}, using previous value")
            
            # Create holdings list for frontend
            holdings_list = []
            total_portfolio_value = portfolio_value  # Use current portfolio value for weight calculation
            
            for symbol, holding in current_holdings.items():
                if symbol in day_prices:
                    current_price = day_prices[symbol]["close_price"]
                    market_value = holding["shares"] * current_price
                    pnl = (current_price - holding["avg_price"]) * holding["shares"]
                    pnl_percent = ((current_price / holding["avg_price"]) - 1) * 100 if holding["avg_price"] > 0 else 0
                    
                    # Calculate portfolio weight percentage
                    weight_percent = (market_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
                    
                    # Get holding period and allocation weight
                    holding_periods_count = holding_periods.get(symbol, 0)
                    allocation_weight = 1.0 + (holding_periods_count * 0.3)
                    
                    holding_info = {
                        "symbol": symbol,
                        "company_name": symbol,  # TODO: Get from company mapping
                        "quantity": holding["shares"],
                        "avg_price": holding["avg_price"],
                        "current_price": current_price,
                        "market_value": market_value,
                        "pnl": pnl,
                        "pnl_percent": pnl_percent,
                        "sector": "Unknown",  # TODO: Get from mapping
                        "weight": weight_percent,  # Portfolio weight percentage
                        "holding_periods": holding_periods_count,  # Number of consecutive periods held
                        "allocation_weight": allocation_weight  # Skewed allocation weight
                    }
                    
                    # Add charge tracking if available
                    if "total_cost" in holding:
                        holding_info["total_cost"] = holding["total_cost"]
                    # Removed cumulative_charges aggregation from individual holdings
                    
                    holdings_list.append(holding_info)
            
            # Sort holdings by allocation weight (descending) for skewed rebalancing display
            if params.rebalance_type == "skewed":
                holdings_list.sort(key=lambda x: x["allocation_weight"], reverse=True)
            else:
                # For equal weight, sort by market value (descending)
                holdings_list.sort(key=lambda x: x["market_value"], reverse=True)
            
            # Track cumulative charges
            if not hasattr(run_strategy_simulation, 'cumulative_charges'):
                run_strategy_simulation.cumulative_charges = 0.0
            
            if should_rebalance and params.include_brokerage:
                run_strategy_simulation.cumulative_charges += daily_charges.get("total_charges", 0.0)
            
            # Sanitize trade details for JSON serialization
            sanitized_trade_details = []
            if should_rebalance and rebalance_trade_details:
                for trade in rebalance_trade_details:
                    sanitized_trade = {}
                    for key, value in trade.items():
                        if isinstance(value, datetime):
                            sanitized_trade[key] = value.isoformat()
                        elif hasattr(value, '__dict__'):
                            # Handle nested objects (like TransactionCharges)
                            sanitized_nested = {}
                            for nested_key, nested_value in value.__dict__.items():
                                if isinstance(nested_value, datetime):
                                    sanitized_nested[nested_key] = nested_value.isoformat()
                                else:
                                    sanitized_nested[nested_key] = nested_value
                            sanitized_trade[key] = sanitized_nested
                        else:
                            sanitized_trade[key] = value
                    sanitized_trade_details.append(sanitized_trade)
            
            # Create day result with enhanced charge tracking
            day_result = {
                "date": date_str,
                "portfolio_value": portfolio_value,
                "benchmark_value": benchmark_value,
                "holdings": holdings_list,
                "new_added": new_added,
                "exited": exited,
                "exited_details": exited_details,
                "cash": cash_balance,  # Actual cash balance
                "total_pnl": portfolio_value - params.portfolio_base_value,
                "day_pnl": day_pnl,
                "benchmark_price": current_benchmark_close or 0,
                
                # Enhanced charge tracking
                "daily_charges": daily_charges if should_rebalance else {"total_charges": 0.0, "buy_charges": 0.0, "sell_charges": 0.0},
                "cumulative_charges": getattr(run_strategy_simulation, 'cumulative_charges', 0.0),
                "charge_impact_percent": (getattr(run_strategy_simulation, 'cumulative_charges', 0.0) / params.portfolio_base_value) * 100,
                "trade_details": sanitized_trade_details,
                "brokerage_enabled": params.include_brokerage,
                "exchange_used": params.exchange if params.include_brokerage else None
            }
            
            # Debug logging for exit details
            if exited_details:
                logger.info(f"📤 Day {date_str}: Created {len(exited_details)} exit details for symbols: {[e['symbol'] for e in exited_details]}")
            elif exited:
                logger.info(f"⚠️ Day {date_str}: Have {len(exited)} exits but no exit details: {exited}")
            
            simulation_results.append(day_result)
        
        # Calculate comprehensive summary statistics with charge analytics
        final_portfolio_value = portfolio_value
        total_return = (final_portfolio_value / params.portfolio_base_value - 1) * 100 if params.portfolio_base_value > 0 else 0
        benchmark_return = (benchmark_value / params.portfolio_base_value - 1) * 100 if params.portfolio_base_value > 0 else 0
        
        # Calculate cumulative charge impact
        total_cumulative_charges = getattr(run_strategy_simulation, 'cumulative_charges', 0.0)
        charge_impact_percent = (total_cumulative_charges / params.portfolio_base_value) * 100
        
        # Calculate theoretical return without charges (approximate)
        theoretical_value_without_charges = final_portfolio_value + total_cumulative_charges
        theoretical_return_without_charges = (theoretical_value_without_charges / params.portfolio_base_value - 1) * 100
        
        # Calculate max drawdown
        peak_value = params.portfolio_base_value
        max_drawdown = 0
        drawdown_details = []
        for result in simulation_results:
            peak_value = max(peak_value, result["portfolio_value"])
            drawdown = (result["portfolio_value"] / peak_value - 1) * 100
            max_drawdown = min(max_drawdown, drawdown)
            drawdown_details.append({
                "date": result["date"],
                "portfolio_value": result["portfolio_value"],
                "peak_value": peak_value,
                "drawdown_percent": drawdown
            })
        
        # Calculate rebalance statistics
        rebalance_events = [result for result in simulation_results if result["daily_charges"]["total_charges"] > 0]
        total_rebalances = len(rebalance_events)
        avg_rebalance_cost = (total_cumulative_charges / total_rebalances) if total_rebalances > 0 else 0
        
        # Calculate charge breakdown analytics
        charge_analytics = {
            "total_cumulative_charges": round(total_cumulative_charges, 2),
            "charge_impact_percent": round(charge_impact_percent, 4),
            "total_rebalances": total_rebalances,
            "avg_cost_per_rebalance": round(avg_rebalance_cost, 2),
            "charge_drag_on_returns": round(theoretical_return_without_charges - total_return, 4),
            "theoretical_return_without_charges": round(theoretical_return_without_charges, 2),
            "charge_as_percent_of_final_value": round((total_cumulative_charges / final_portfolio_value) * 100, 4) if final_portfolio_value > 0 else 0
        }
        
        # Enhanced charge breakdown by components (aggregate from all rebalances)
        if params.include_brokerage and rebalance_events:
            aggregate_breakdown = {
                "total_buy_charges": 0.0,
                "total_sell_charges": 0.0,
                "stt_total": 0.0,
                "transaction_charges_total": 0.0,
                "sebi_charges_total": 0.0,
                "stamp_duty_total": 0.0,
                "brokerage_total": 0.0,
                "gst_total": 0.0
            }
            
            # Aggregate charges from all trade details
            for result in simulation_results:
                if result["trade_details"]:
                    for trade in result["trade_details"]:
                        if "charges" in trade and isinstance(trade["charges"], dict):
                            charges = trade["charges"]
                            aggregate_breakdown["stt_total"] += charges.get("stt", 0.0)
                            aggregate_breakdown["transaction_charges_total"] += charges.get("transaction_charges", 0.0)
                            aggregate_breakdown["sebi_charges_total"] += charges.get("sebi_charges", 0.0)
                            aggregate_breakdown["stamp_duty_total"] += charges.get("stamp_duty", 0.0)
                            aggregate_breakdown["brokerage_total"] += charges.get("brokerage", 0.0)
                            aggregate_breakdown["gst_total"] += charges.get("gst", 0.0)
                
                aggregate_breakdown["total_buy_charges"] += result["daily_charges"].get("buy_charges", 0.0)
                aggregate_breakdown["total_sell_charges"] += result["daily_charges"].get("sell_charges", 0.0)
            
            charge_analytics["component_breakdown"] = {
                "stt": round(aggregate_breakdown["stt_total"], 2),
                "transaction_charges": round(aggregate_breakdown["transaction_charges_total"], 2),
                "sebi_charges": round(aggregate_breakdown["sebi_charges_total"], 2),
                "stamp_duty": round(aggregate_breakdown["stamp_duty_total"], 2),
                "brokerage": round(aggregate_breakdown["brokerage_total"], 2),
                "gst": round(aggregate_breakdown["gst_total"], 2),
                "total_buy_charges": round(aggregate_breakdown["total_buy_charges"], 2),
                "total_sell_charges": round(aggregate_breakdown["total_sell_charges"], 2)
            }
        
        # Calculate performance metrics
        daily_returns = []
        for i in range(1, len(simulation_results)):
            prev_portfolio_value = simulation_results[i-1]["portfolio_value"]
            curr_portfolio_value = simulation_results[i]["portfolio_value"]
            
            if prev_portfolio_value > 0:
                daily_return = (curr_portfolio_value / prev_portfolio_value) - 1
                daily_returns.append(daily_return)
            else:
                # Skip this calculation if previous value is 0
                logger.warning(f"⚠️ Skipping daily return calculation: previous portfolio value is 0 on day {i-1}")
                continue
        
        # Calculate Sharpe ratio (assuming 6% risk-free rate)
        if daily_returns:
            import numpy as np
            daily_returns_array = np.array(daily_returns)
            avg_daily_return = np.mean(daily_returns_array)
            daily_volatility = np.std(daily_returns_array)
            
            # Annualize metrics (assuming 252 trading days)
            annual_return = (1 + avg_daily_return) ** 252 - 1
            annual_volatility = daily_volatility * np.sqrt(252)
            
            # Calculate Sharpe ratio with 6% risk-free rate
            risk_free_rate = 0.06
            sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Sanitize all results for JSON serialization
        sanitized_results = sanitize_for_json({
            "params": params.dict(),
            "benchmark_symbol": benchmark_symbol,
            "results": simulation_results,
            "charge_analytics": charge_analytics,
            "summary": {
                "total_return": round(total_return, 2),
                "benchmark_return": round(benchmark_return, 2),
                "alpha": round(total_return - benchmark_return, 2),
                "max_drawdown": round(max_drawdown, 2),
                "sharpe_ratio": round(sharpe_ratio, 3),
                "total_trades": total_rebalances,
                "brokerage_enabled": params.include_brokerage,
                "exchange": params.exchange if params.include_brokerage else None,
                "theoretical_return_without_charges": round(theoretical_return_without_charges, 2) if params.include_brokerage else None,
                "charge_impact": round(charge_impact_percent, 4) if params.include_brokerage else 0
            }
        })
        
        return sanitized_results
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"❌ Error in simulation logic: {e}")
        logger.error(f"❌ Full traceback: {error_details}")
        raise

def apply_strategy_rules(day_indicators, rules):
    """Apply strategy rules to filter qualified stocks"""
    qualified_stocks = []
    
    for symbol, stock_data in day_indicators.items():
        qualifies = True
        
        for rule in rules:
            metric_value = stock_data.get(rule["metric"]) or 0  # Handle None values
            threshold = rule["threshold"]
            operator = rule["operator"]
            
            if operator == ">" and not (metric_value > threshold):
                qualifies = False
                break
            elif operator == "<" and not (metric_value < threshold):
                qualifies = False
                break
            elif operator == ">=" and not (metric_value >= threshold):
                qualifies = False
                break
            elif operator == "<=" and not (metric_value <= threshold):
                qualifies = False
                break
            elif operator == "==" and not (metric_value == threshold):
                qualifies = False
                break
            elif operator == "!=" and not (metric_value != threshold):
                qualifies = False
                break
        
        if qualifies:
            qualified_stocks.append(stock_data)
    
    return qualified_stocks

def calculate_current_portfolio_value(current_holdings, day_prices, cash_balance=0):
    """Calculate current portfolio value based on current prices plus cash"""
    total_value = 0
    
    # Calculate value of stock holdings
    for symbol, holding in current_holdings.items():
        if symbol in day_prices:
            current_price = day_prices[symbol]["close_price"]
            market_value = holding["shares"] * current_price
            total_value += market_value
    
    # Add cash balance
    total_value += cash_balance
    
    return total_value

def get_rebalance_dates(dates, frequency, date_type):
    """Generate rebalance dates based on frequency and date type"""
    rebalance_dates = set()
    
    if frequency == "monthly":
        # Group dates by month
        monthly_groups = {}
        for date_str in dates:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = (date_obj.year, date_obj.month)
            if month_key not in monthly_groups:
                monthly_groups[month_key] = []
            monthly_groups[month_key].append(date_str)
        
        # Select date based on date_type
        for month_key in sorted(monthly_groups.keys()):
            month_dates = sorted(monthly_groups[month_key])
            if date_type == "first":
                rebalance_dates.add(month_dates[0])
            elif date_type == "last":
                rebalance_dates.add(month_dates[-1])
            elif date_type == "mid":
                mid_index = len(month_dates) // 2
                rebalance_dates.add(month_dates[mid_index])
                
    elif frequency == "weekly":
        # Group dates by week
        weekly_groups = {}
        for date_str in dates:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            week_key = (date_obj.year, date_obj.isocalendar()[1])
            if week_key not in weekly_groups:
                weekly_groups[week_key] = []
            weekly_groups[week_key].append(date_str)
        
        # Select date based on date_type
        for week_key in sorted(weekly_groups.keys()):
            week_dates = sorted(weekly_groups[week_key])
            if date_type == "first":
                rebalance_dates.add(week_dates[0])
            elif date_type == "last":
                rebalance_dates.add(week_dates[-1])
            elif date_type == "mid":
                mid_index = len(week_dates) // 2
                rebalance_dates.add(week_dates[mid_index])
                
    elif frequency == "quarterly":
        # Group dates by quarter
        quarterly_groups = {}
        for date_str in dates:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            # Calculate quarter: Q1 (1-3), Q2 (4-6), Q3 (7-9), Q4 (10-12)
            quarter = (date_obj.month - 1) // 3 + 1
            quarter_key = (date_obj.year, quarter)
            if quarter_key not in quarterly_groups:
                quarterly_groups[quarter_key] = []
            quarterly_groups[quarter_key].append(date_str)
        
        # Select date based on date_type
        for quarter_key in sorted(quarterly_groups.keys()):
            quarter_dates = sorted(quarterly_groups[quarter_key])
            if date_type == "first":
                rebalance_dates.add(quarter_dates[0])
            elif date_type == "last":
                rebalance_dates.add(quarter_dates[-1])
            elif date_type == "mid":
                mid_index = len(quarter_dates) // 2
                rebalance_dates.add(quarter_dates[mid_index])
    
    return rebalance_dates

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=False)
