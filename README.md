# Market Hunt - Stock Data Management System

A comprehensive market research and analysis platform focusing on Indian stock market data, featuring real-time data management, industry analytics, and URL-based data synchronization.

## 🚀 Features

### ✅ **Production Ready Components**
- **Stock Data Management**: Complete CRUD operations for stock market data
- **URL Management**: Configure and manage data source URLs with cascading delete
- **Industry Analytics**: Real-time aggregation of companies by industry and index
- **Index Analytics**: Comprehensive analysis across NIFTY indices
- **Data Synchronization**: Automated data fetching from configured URLs
- **Cascading Operations**: Data consistency maintained across all operations

### 📊 **Analytics Dashboard**
- **Industries Overview**: Company distribution across 18+ industries
- **Index Management**: NIFTY 50, NIFTY 100, NIFTY 200 data management
- **Real-time Statistics**: Live company counts and industry metrics
- **Data Integrity**: Consistent data across all views and operations

## 🛠 Tech Stack

### Backend
- **Python 3.13** with virtual environment
- **FastAPI** for REST API endpoints
- **MongoDB** for data persistence
- **PyMongo** for database operations
- **Uvicorn** ASGI server with auto-reload

### Frontend
- **Next.js 14** with TypeScript
- **Tailwind CSS** for styling
- **React** components with modern hooks
- **API Integration** with comprehensive error handling

## 📁 Project Structure

```
market_hunt/
├── Backend (Python)
│   ├── api_server.py              # FastAPI main server
│   ├── stock_data_manager.py      # Core data management
│   ├── url_manager.py             # URL configuration management
│   ├── nse_data_client.py         # NSE data fetching
│   ├── generic_data_loader.py     # Generic CSV data loader
│   └── system_verification.py    # System health checks
├── Frontend (Next.js)
│   ├── src/app/                   # App router pages
│   ├── src/components/            # Reusable components
│   ├── src/lib/                   # API client and utilities
│   └── src/types/                 # TypeScript type definitions
├── Documentation/
│   ├── project_DNA.md             # Project architecture and fixes
│   ├── Stock_Data_Management_System.md
│   └── URL_Management_System.md
└── Configuration
    ├── requirements.txt           # Python dependencies
    └── .gitignore                # Git ignore rules
```

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- MongoDB running on localhost:27017
- Node.js 18+ (for frontend)

### Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
nohup python -m uvicorn api_server:app --host 0.0.0.0 --port 3001 --reload > api_server.log 2>&1 &
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Database Setup
MongoDB should be running on `mongodb://localhost:27017/`
- Database: `market_hunt`
- Collections: `index_meta`, `index_meta_csv_urls`

## 📡 API Endpoints

### URL Management
- `GET /api/urls` - List all configured URLs
- `POST /api/urls` - Add new URL configuration
- `DELETE /api/urls/manage?id={url_id}` - Delete URL (with cascading delete)

### Data Operations
- `POST /api/download` - Download and sync stock data
- `GET /api/data/index/{index_name}` - Get companies by index
- `GET /api/data/index/{index_name}/industries` - Get industry breakdown by index

### Analytics
- `GET /api/industries` - Industries overview with statistics
- `GET /api/industries/{industry_name}` - Companies in specific industry
- `GET /api/indexes` - Available indices summary

## 🔧 Key Features

### Cascading Delete
When a URL configuration is deleted, all associated stock data is automatically removed to maintain data consistency.

### Industry Aggregation
Real-time aggregation shows accurate company counts and index associations across all industries.

### Error Handling
Comprehensive error handling with detailed logging and user-friendly error messages.

### Data Validation
Input validation and data integrity checks across all operations.

## 📈 Recent Fixes & Improvements

### Industry Count Bug Fix (2025-08-15)
- **Problem**: Industries showing incorrect index counts
- **Solution**: Fixed MongoDB aggregation pipeline to collect all indices per industry
- **Result**: Accurate statistics across all analytics views

### Cascading Delete Implementation (2025-08-15)
- **Problem**: Orphaned data after URL deletion
- **Solution**: Enhanced delete operations to remove associated data
- **Result**: Complete data consistency maintained

### URL Management Parameter Fix (2025-08-15)
- **Problem**: DELETE requests failing due to parameter mismatch
- **Solution**: Corrected frontend-backend parameter mapping
- **Result**: Fully functional URL management

## 🧪 Testing

### System Verification
```bash
python system_verification.py
```

### API Testing
```bash
# Test industries endpoint
curl -s "http://localhost:3001/api/industries" | jq '.industry_stats[0]'

# Test URL management
curl -s "http://localhost:3001/api/urls"
```

## 📝 Development Notes

- Server runs with `nohup` for persistent execution
- Auto-reload enabled for development
- Comprehensive logging to `api_server.log`
- MongoDB aggregation optimized for performance
- Frontend API client with proper error handling

## 🤝 Contributing

This project follows an iterative development approach with user feedback integration. Each component is developed based on evolving requirements and real-world usage patterns.

## 📞 Support

For technical issues or feature requests, refer to the `project_DNA.md` file for detailed implementation notes and recent fixes.
