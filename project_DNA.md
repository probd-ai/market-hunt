# Project DNA - Market Hunt

*Last Updated: 2025-08-19*  
*Status: **PRODUCTION READY** - Complete market research system with historical data coverage*

## 🎯 Project Purpose
Market research and analysis application focusing on Indian stock market data. Provides comprehensive historical stock data management with NSE API integration, gap analysis, and multi-level data operations.

## 🏗️ System Architecture

```
┌─────────────────┐    HTTP API    ┌─────────────────┐    MongoDB    ┌─────────────────┐
│   Next.js       │ ──────────────► │   FastAPI       │ ──────────────► │   MongoDB       │
│   Frontend      │    Port 3001   │   Backend       │   Port 27017  │   Database      │
│   Port 3000     │ ◄────────────── │   Port 3001     │ ◄────────────── │   market_hunt   │
└─────────────────┘                └─────────────────┘                └─────────────────┘
        │                                   │
        └── CLI Tools ──────────────────────┘
```

## 🛠️ Tech Stack
- **Backend**: Python 3.13 (venv environment)
- **Database**: MongoDB 7.0  
- **Frontend**: Next.js 15.4.6
- **CLI Tools**: Custom Python CLI for data management
- **APIs**: NSE India integration for real-time data

## 📊 Core Data Collections

### `symbol_mappings` - NSE Symbol Mapping
```json
{
  "_id": "symbol",
  "symbol": "string",
  "company_name": "string", 
  "industry": "string",
  "index_names": ["array"],
  "nse_scrip_code": integer,
  "nse_symbol": "string",
  "match_confidence": float
}
```

### `prices_YYYY_YYYY` - Historical Price Data (5-Year Partitions)
```json
{
  "_id": "scripcode_YYYYMMDD",
  "scrip_code": integer,
  "symbol": "string",
  "date": DateTime,
  "open_price": float,
  "high_price": float, 
  "low_price": float,
  "close_price": float,
  "volume": integer,
  "value": float
}
```

### `index_meta` - Company Data
```json
{
  "_id": ObjectId,
  "Company Name": "string",
  "Industry": "string",
  "Symbol": "string", 
  "ISIN Code": "string",
  "index_name": "string"
}
```

## 🔧 CLI Tools

### DataLoadManagement CLI (`DataLoadManagement.py`)
**Purpose**: Production-ready historical stock data management with intelligent gap analysis

**Key Commands**:
```bash
# Symbol Operations
python DataLoadManagement.py refresh-mappings
python DataLoadManagement.py symbol-info SYMBOL
python DataLoadManagement.py download-stock SYMBOL [--force-refresh]
python DataLoadManagement.py check-gaps SYMBOL

# Index/Industry Operations  
python DataLoadManagement.py download-index "INDEX_NAME" [--max-concurrent 5]
python DataLoadManagement.py download-industry "INDUSTRY_NAME" [--max-concurrent 5]
python DataLoadManagement.py list-indices
python DataLoadManagement.py list-industries

# System Management
python DataLoadManagement.py show-stats
python DataLoadManagement.py update-gap-status [--max-concurrent 5]
python DataLoadManagement.py delete-stock SYMBOL --confirm
```

**Key Features**:
- **Intelligent Gap Analysis**: Compares NSE trading days with database coverage
- **Concurrent Processing**: Parallel downloads with configurable limits
- **5-Year Partitioning**: Automatic data distribution across time-based collections
- **Smart Processing**: Only downloads when gaps exist (unless forced)
- **Real-time Validation**: Live NSE API validation

### IndexManagement CLI (`IndexManagement.py`)
**Purpose**: Manages market index constituent data URLs and CSV processing

**Key Commands**:
```bash
# URL Management
python IndexManagement.py add-url URL --index-name NAME --description DESC
python IndexManagement.py list-urls
python IndexManagement.py process-all

# System Info
python IndexManagement.py show-stats
```

## 🚀 API Endpoints (FastAPI - Port 3001)

### Stock Data Management
- `GET /api/stock/mappings` - Get symbol mappings
- `POST /api/stock/mappings/refresh` - Refresh mappings
- `GET /api/stock/data/{symbol}` - Get historical price data
- `POST /api/stock/download` - Download historical data
- `GET /api/stock/statistics` - Get system statistics

### Data Overview
- `GET /api/data` - System overview
- `GET /api/data/index/{index_name}` - Index companies
- `GET /api/industries` - Industry statistics
- `GET /api/industries/{industry_name}` - Industry companies

### URL Management
- `GET /api/urls` - List all URLs
- `POST /api/urls` - Create URL
- `PUT /api/urls/{url_id}` - Update URL
- `DELETE /api/urls/{url_id}` - Delete URL

## 📱 Frontend (Next.js - Port 3000)

### Key Pages
- `/` - Dashboard with real-time metrics
- `/urls` - URL management interface
- `/data-load` - Stock data management with gap analysis
- `/indexes` - Index exploration with multi-level navigation
- `/industries` - Industry analysis

### Key Components
- **DataLoadManagement**: Gap analysis, batch operations, progress tracking
- **Interactive Dashboards**: Real-time charts and statistics
- **CRUD Interfaces**: Complete data management capabilities

## 🗄️ Current Data Status
- **205 Symbols**: Complete symbol mappings with NSE integration
- **22,567+ Records**: Historical trading data across major indices
- **5 Market Indices**: MARKET INDEXES with 100% coverage
- **200 Individual Stocks**: NIFTY 200 with complete historical data
- **Zero Data Gaps**: 100% coverage validation completed

## 💡 Key System Features

### Intelligence & Automation
- **Gap Analysis Engine**: Smart comparison between NSE data and database
- **Concurrent Processing**: Parallel operations with progress tracking  
- **Data Partitioning**: 5-year collections for scalability
- **Real-time Validation**: Live NSE API integration
- **Smart Recommendations**: Actionable guidance based on data analysis

### Production Features
- **Error Recovery**: Comprehensive error handling and retry logic
- **Audit Logging**: Complete operation tracking in `data_processing_logs`
- **Safety Features**: Confirmation-required operations
- **Performance Optimization**: Efficient database queries and API usage
- **Scalable Architecture**: Ready for enterprise-level data volumes

## 🔄 Typical Workflows

### Initial Setup
1. Use IndexManagement CLI to configure data sources
2. Run `refresh-mappings` to create symbol-to-NSE mappings
3. Download historical data using `download-index` or `download-stock`

### Daily Operations  
1. Run `update-gap-status` to check data freshness
2. Use `download-stock` for individual updates
3. Monitor via web dashboard or `show-stats`

### Analysis & Research
1. Access data via REST API endpoints
2. Use frontend dashboard for visualization
3. Export data for external analysis tools

## 🌐 Access Points
- **Frontend**: http://localhost:3000
- **API**: http://localhost:3001
- **API Docs**: http://localhost:3001/docs
- **Repository**: https://github.com/probd-ai/market_hunt.git

## 📋 Dependencies
**Backend**: `fastapi`, `uvicorn`, `pymongo`, `requests`, `pandas`, `beautifulsoup4`
**Frontend**: `next`, `react`, `typescript`, `tailwindcss`, `@tanstack/react-query`

---

*This system provides complete historical stock data management for the Indian market with intelligent gap analysis, concurrent processing, and production-ready architecture.*
