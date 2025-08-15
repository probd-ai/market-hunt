# URL Management System - Market Hunt

## 🚀 Getting Started

### Prerequisites
- MongoDB installed and running
- Python 3.13 with virtual environment configured
- FastAPI backend service running (recommended)
- Required packages installed (requests, pandas, pymongo, beautifulsoup4, streamlit)

### System Overview
The URL management system allows you to:
- Add multiple CSV data source URLs
- Automatically extract index names from URLs
- Manage URL configurations through web interfaces (Streamlit + Next.js)
- Process data from multiple sources simultaneously
- Track download history and error status
- Integrate with modern FastAPI backend for real-time operations

## 📝 Quick Start Steps

### Option 1: Modern Next.js Interface (Recommended)
```bash
# Start FastAPI backend
cd /media/guru/Data/workspace/market_hunt
source .venv/bin/activate
uvicorn api_server:app --host 0.0.0.0 --port 3001 --reload

# Start Next.js frontend (in separate terminal)
cd /media/guru/Data/workspace/market_hunt/frontend
npm run dev -- --port 3000
```
Access at: http://localhost:3000

### Option 2: Legacy Streamlit Interface
```bash
cd /media/guru/Data/workspace/market_hunt
./.venv/bin/python -m streamlit run streamlit_url_manager.py --server.port 8501
```
Access at: http://localhost:8501

### 2. Add Your First URL

#### Using Next.js Interface (Modern)
1. Go to http://localhost:3000
2. Navigate to "URLs" tab
3. Fill in the form:
   - **URL**: Enter the CSV download URL (e.g., `https://niftyindices.com/IndexConstituent/ind_nifty50list.csv`)
   - **Index Name**: Leave empty for auto-extraction or specify manually (e.g., "NIFTY 50")
   - **Description**: Brief description of the data source
   - **Tags**: Comma-separated tags for categorization
   - **Active**: Check to include in bulk operations
4. Click "Add URL"

#### Using Streamlit Interface (Legacy)
1. Go to the "URL Management" tab
2. Fill in the same form fields as above
3. Click "Add URL"

### 3. Process Data
- **Modern Interface**: Use "Refresh Data" button in Dashboard or process specific URLs in URLs management
- **Legacy Interface**: Use "Process All Active" or "Process Selected" options
- Data is automatically stored in MongoDB collection `index_meta`
- Real-time progress tracking and error reporting

### 4. View Results
- **Modern Interface**: Go to Dashboard for overview, or Indexes/Industries tabs for detailed exploration
- **Legacy Interface**: Go to "Data Overview" tab to see loaded data statistics
- Check document counts and last update timestamps
- View index-wise breakdown with interactive charts

## � API Integration

### FastAPI Endpoints (Modern Backend)
The system now provides comprehensive REST API endpoints:

```bash
# URL Management
GET    /api/urls                    # List all URLs
POST   /api/urls                    # Create new URL
PUT    /api/urls/{url_id}          # Update existing URL
DELETE /api/urls/{url_id}          # Delete URL

# Data Processing
POST   /api/process                 # Process URLs and download data
GET    /api/data                    # Get data overview
GET    /api/data/index/{index_name} # Get companies for specific index

# System Health
GET    /api/health                  # System status monitoring
```

### API Usage Examples
```python
import requests

# Add a URL via API
response = requests.post("http://localhost:3001/api/urls", json={
    "url": "https://example.com/data.csv",
    "index_name": "MY INDEX",
    "description": "Custom data source",
    "tags": ["custom", "test"],
    "is_active": True
})

# Process all active URLs
response = requests.post("http://localhost:3001/api/process")
```

## 🛠️ Command Line Usage

### Add URLs Programmatically
```python
from url_manager import URLManager

manager = URLManager()
manager.connect_to_mongodb()

# Add a new URL
success, message = manager.add_url(
    url="https://example.com/data.csv",
    index_name="MY INDEX",  # Optional - will auto-extract if not provided
    description="My custom data source",
    tags=["custom", "test"],
    is_active=True
)

print(f"Add URL: {success} - {message}")
```

### Load Data Programmatically
```python
from generic_data_loader import GenericIndexDataLoader

loader = GenericIndexDataLoader()
loader.connect_to_mongodb()

# Process all active URLs
success = loader.process_all_active_urls()

# Or process specific URL IDs
success = loader.process_specific_urls(['url_id_1', 'url_id_2'])

# Get statistics
stats = loader.get_collection_stats()
print(stats)
```

## 🔧 Auto Index Name Extraction

The system automatically extracts index names from URLs using these patterns:

| URL Pattern | Extracted Name |
|-------------|----------------|
| `ind_nifty50list.csv` | NIFTY50 |
| `ind_nifty100list.csv` | NIFTY100 |
| `sensex30.csv` | SENSEX30 |
| `bse500.csv` | BSE500 |
| `nifty-next-50.csv` | NIFTY |
| `midcap_index.csv` | MIDCAP INDEX |

## 🏗️ System Architecture

```
┌─────────────────┐    HTTP API    ┌─────────────────┐    MongoDB    ┌─────────────────┐
│   Next.js       │ ──────────────► │   FastAPI       │ ──────────────► │   MongoDB       │
│   Frontend      │    Port 3001   │   Backend       │   Port 27017  │   Database      │
│   Port 3000     │ ◄────────────── │   Port 3001     │ ◄────────────── │   market_hunt   │
└─────────────────┘    JSON Data    └─────────────────┘    Collections └─────────────────┘
        │                                   │
        │                                   │
        ▼                                   ▼
┌─────────────────┐                ┌─────────────────┐
│   Streamlit     │                │   Python        │
│   Legacy UI     │                │   Data Loaders  │
│   Port 8501     │                │   & URL Manager │
└─────────────────┘                └─────────────────┘
```

## 📊 MongoDB Collections

### Integration with Stock Data System
The URL management system now seamlessly integrates with the Stock Data Management System:
- URLs provide index composition data for symbol mapping
- Stock system uses index_meta collection for NSE symbol matching
- Dual data sources: CSV files (index composition) + NSE APIs (price data)
- Unified database with proper data relationships

### `index_meta` - Actual Data
Stores the downloaded CSV data with metadata:
- Company details (Name, Symbol, Industry, ISIN)
- Data source tracking (URL, timestamp)
- Index classification

### `index_meta_csv_urls` - URL Configurations
Stores URL management information:
- URL and validation status
- Download history and error tracking
- Categorization (tags, description)
- Active/inactive status

## 🚨 Troubleshooting

### Common Issues

1. **URL Validation Failed**
   - Check if the URL is accessible
   - Verify it returns CSV data
   - Ensure proper Content-Type headers

2. **Data Loading Failed**
   - Check MongoDB connection
   - Verify CSV format compatibility
   - Review error logs in the web interface

3. **Auto-extraction Not Working**
   - Manually specify index name when adding URL
   - Check if URL pattern matches extraction rules

### Error Tracking
- All errors are logged in the URL configuration
- Check "URL Details" section for last error messages
- Use the verification script for comprehensive testing

## 🧪 Testing the System

Run the comprehensive verification script:
```bash
./.venv/bin/python system_verification.py
```

This will test:
- URL management functionality
- Data loading system
- Auto index name extraction
- End-to-end integration
- Generate system report

## 📈 Best Practices

1. **URL Management**
   - Use descriptive names for indices
   - Add meaningful tags for categorization
   - Test URLs before marking as active

2. **Data Processing**
   - Process data during off-peak hours for large datasets
   - Monitor download counts and errors
   - Review data quality after each load

3. **Monitoring**
   - Check system statistics regularly
   - Export URL configurations as backup
   - Review error logs for failed downloads

## 🔗 Supported URL Types

- Direct CSV download links
- Pages with CSV download buttons
- NIFTY indices CSV files
- Custom CSV endpoints
- Any URL returning CSV data with proper headers

The system uses intelligent link discovery to find CSV downloads on pages that don't directly point to CSV files.

---

**Need Help?** 
- **Modern Interface**: Check the Dashboard and navigation for intuitive usage
- **Legacy Interface**: Check the "Help" tab in the Streamlit interface
- **API Documentation**: Visit http://localhost:3001/docs for comprehensive API reference
- **Stock Data Integration**: See `Stock_Data_Management_System.md` for stock-specific features

**Last Updated**: August 15, 2025  
**Status**: Production Ready - Dual interface support with modern Next.js frontend and legacy Streamlit interface
