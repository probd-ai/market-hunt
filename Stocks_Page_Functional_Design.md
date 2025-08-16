# 📊 Stocks Page - Functional Design Document

*Last Updated: 2025-08-16*  
*Status: Production Ready*

## 🎯 Overview

The `/stocks` page is the core data management interface for the Market Hunt platform, providing comprehensive stock price data loading, synchronization, and analysis capabilities. It serves as the primary control center for managing historical stock data across 200+ symbols from the Indian stock market (NSE).

## 🏗️ System Architecture

### **Frontend Stack:**
- **Framework**: Next.js 15.4.6 with React 19.1.0
- **State Management**: React Query (TanStack Query) for server state
- **UI Components**: Custom components with Tailwind CSS
- **Icons**: Heroicons v2

### **Backend Integration:**
- **API Server**: FastAPI on port 3001
- **Database**: MongoDB with 5-year partitioned collections
- **Data Source**: NSE India API for real-time stock data
- **Proxy Configuration**: Frontend (3000) → Backend (3001) seamless integration

## 📋 Core Features & Functionality

### **1. 📈 Statistics Dashboard**

#### **What it Does:**
Provides real-time overview of the entire stock data ecosystem with key performance indicators.

#### **How it Works:**
```typescript
// Fetches live statistics from backend
const { data: statistics } = useQuery({
  queryKey: ['stockStatistics'],
  queryFn: () => api.getStockDataStatistics(),
});
```

#### **Displayed Metrics:**
- **Total Price Records**: 761,834+ historical stock price entries
- **Symbols with Data**: 200 symbols with complete historical data
- **Total Symbols**: All mapped symbols available for download
- **Mapped Symbols**: Symbols with valid NSE mappings
- **Years of Data**: Historical coverage span (2005-2025)

#### **Technical Implementation:**
- Real-time data fetching with automatic updates
- Color-coded metrics (blue, green, purple, orange)
- Responsive grid layout (1-4 columns based on screen size)

---

### **2. 🔄 Progress Tracking System**

#### **What it Does:**
Provides real-time monitoring of background data loading operations with detailed progress information.

#### **How it Works:**
```typescript
// Polls progress updates every 2 seconds for active tasks
const { data: progressData } = useQuery({
  queryKey: ['taskProgress', activeTaskId],
  queryFn: () => api.getTaskProgress(activeTaskId),
  enabled: !!activeTaskId && showProgress,
  refetchInterval: 2000,
});
```

#### **Features:**
- **Real-time Progress Bar**: Visual completion percentage (0-100%)
- **Item Counter**: Shows "current_count / total_count" processing status
- **Current Item Display**: Shows which symbol is currently being processed
- **Status Indicators**: Running (blue), Completed (green), Failed (red)
- **Error Reporting**: Detailed error messages when operations fail
- **Auto-dismiss**: Progress panel closes automatically after completion

#### **User Experience:**
- Non-blocking UI during data loading
- Collapsible progress panel with close button
- Status messages and completion notifications
- Background task management with unique task IDs

---

### **3. 📊 Multi-Mode Data Loading System**

#### **What it Does:**
Sophisticated data loading interface supporting three distinct loading strategies and four sync modes.

#### **Loading Strategies:**

##### **A. Individual Symbol Loading**
- **Purpose**: Load data for specific stocks
- **Selection Method**: Intelligent symbol search with auto-complete
- **Implementation**: 
  ```typescript
  <SymbolSearch
    symbols={symbolMappings}
    onSelect={setDownloadSymbol}
    selectedSymbol={downloadSymbol}
  />
  ```

##### **B. Index-Based Loading**
- **Purpose**: Load all symbols in a stock index (NIFTY50, NIFTY100, etc.)
- **Selection Method**: Dropdown with dynamically populated indices
- **Scope**: Can load 50-200 symbols simultaneously

##### **C. Industry-Wide Loading**
- **Purpose**: Load all symbols in a specific industry sector
- **Selection Method**: Industry dropdown (Information Technology, Banking, etc.)
- **Scope**: Variable symbol count per industry

#### **Sync Modes:**

##### **1. Load & Sync Mode** (Green)
- **Purpose**: Smart incremental data loading
- **Behavior**: 
  - Detects earliest missing data year
  - Downloads only missing data (upsert operation)
  - Preserves existing data integrity
- **Use Case**: Adding new data without overwriting existing records

##### **2. Refresh Mode** (Yellow)
- **Purpose**: Complete data replacement
- **Behavior**:
  - Deletes all existing data for the symbol/period
  - Downloads complete historical data from 2005
  - Full replacement operation
- **Use Case**: Fixing corrupted data or ensuring complete refresh

##### **3. Delete Mode** (Red)
- **Purpose**: Data cleanup
- **Behavior**: Removes data for specified symbols and date range
- **Safety**: Requires user confirmation dialog
- **Use Case**: Removing unwanted or incorrect data

#### **Date Range Selection:**
- **Default Range**: 2020-01-01 to current date
- **Flexible Input**: HTML date pickers for start/end dates
- **Validation**: Ensures logical date sequences
- **Use Case**: Targeted data loading for specific periods

---

### **4. 🔍 Advanced Gap Analysis System**

#### **What it Does:**
Sophisticated data integrity analysis that discovers missing trading days and provides intelligent sync recommendations.

#### **How it Works:**
```typescript
const checkGapsMutation = useMutation({
  mutationFn: (request: GapAnalysisRequest) => api.checkDataGaps(request),
  onSuccess: (gaps: DataGapInfo[]) => {
    setDataGaps(gaps);
    setShowGaps(gaps.length > 0);
  },
});
```

#### **Analysis Types:**

##### **A. Complete Historical Analysis**
- **Scope**: Analyzes entire NSE data range (2005-present)
- **Process**: 
  1. Queries NSE to discover actual trading period for symbol
  2. Compares local database against NSE availability
  3. Identifies all missing trading days across 20+ years
- **Output**: Comprehensive gap report with yearly breakdown

##### **B. User Range Analysis**
- **Scope**: Analyzes only user-specified date range
- **Process**: Focuses on gaps within selected period
- **Output**: Targeted gap analysis for specific timeframe

#### **Gap Display Features:**

##### **Visual Gap Indicators:**
```tsx
// Color-coded gap warnings
<div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
  <h4 className="font-medium text-yellow-800">⚠️ Data Gaps for {symbol}</h4>
</div>
```

##### **Yearly Breakdown Grid:**
- Displays missing days per year (2005-2025)
- Color-coded severity indicators
- Scrollable grid for large gap datasets
- Focus on years with actual missing data

##### **Sync Recommendations:**
- **"Sync All Missing Data"**: Downloads complete historical gaps
- **"Sync Range Only"**: Downloads gaps in user's selected range
- **"Skip Symbol"**: Removes symbol from gap analysis

#### **Intelligent Discovery:**
- Automatically detects when symbols weren't trading in specific periods
- Provides realistic gap analysis accounting for market holidays
- Avoids false positives for non-trading periods

---

### **5. 🗂️ Symbol Mappings Management**

#### **What it Does:**
Comprehensive symbol database management with advanced filtering, status tracking, and bulk operations.

#### **Core Features:**

##### **A. Dynamic Filtering System**
```typescript
// Server-side filtering with real-time updates
const { data: symbolMappingsResponse } = useQuery({
  queryKey: ['symbolMappings', { 
    index_name: selectedIndex, 
    industry: selectedIndustry,
    symbol_filter: symbolFilter,
    mapped_only: mappedOnly 
  }],
  queryFn: () => api.getSymbolMappings({ /* filters */ }),
});
```

##### **Filter Options:**
- **Symbol/Company Search**: Real-time text search across symbol names and company names
- **Index Filter**: Filter by stock index (NIFTY50, NIFTY100, NIFTY200, MIDCAP50)
- **Industry Filter**: Filter by business sector (18+ industries available)
- **Mapping Status**: Show only symbols with valid NSE mappings
- **Clear All Filters**: One-click filter reset

##### **B. Symbol Status Tracking**
- **Data Status Indicators**: ✓ Up-to-date / ✗ Outdated / Unknown
- **Quality Scores**: 0-100% data quality with visual progress bars
- **Last Update Timestamps**: When symbol data was last refreshed
- **NSE Integration Status**: Valid scrip codes and mapping confidence

##### **C. Bulk Operations**
- **Refresh Mappings**: Updates all symbol-to-NSE mappings from source
- **Update Status**: Recalculates data quality scores for all symbols
- **Batch Loading**: Load data for multiple symbols simultaneously

#### **Table Features:**
- **Responsive Design**: Horizontal scroll on smaller screens
- **Multi-Index Display**: Symbols can belong to multiple indices
- **Action Buttons**: Per-symbol Load, Refresh, and Chart access
- **Color-coded Status**: Visual indicators for mapping and data quality

---

### **6. 🎛️ Control Interface Design**

#### **Selection Summary Panel:**
- **Symbol Count**: Shows number of symbols that will be affected
- **Date Range**: Displays selected time period in days
- **Current Selection**: Summary of selected symbol/index/industry
- **Action Preview**: Shows what operation will be performed

#### **Smart Validation:**
```typescript
const isFormValid = () => {
  if (loadMode === 'symbol') return !!downloadSymbol;
  if (loadMode === 'index') return !!selectedIndex;
  if (loadMode === 'industry') return !!selectedIndustry;
  return false;
};
```

#### **Error Handling:**
- Form validation before submission
- API error display with retry options
- Network failure recovery
- User-friendly error messages

---

## 🔗 API Integration Architecture

### **Endpoint Mapping:**
```typescript
// Frontend API calls → Backend endpoints
'/api/stock/statistics'     → FastAPI /api/stock/statistics
'/api/stock/mappings'       → FastAPI /api/stock/mappings
'/api/stock/download'       → FastAPI /api/stock/download
'/api/stock/gaps'           → FastAPI /api/stock/gaps
```

### **Data Flow:**
1. **Frontend Request** → Next.js API proxy
2. **Proxy Forward** → FastAPI backend (port 3001)
3. **Backend Processing** → MongoDB operations + NSE API calls
4. **Response Chain** → FastAPI → Next.js → Frontend UI

### **Background Task Management:**
```typescript
// Task creation and tracking
const loadDataMutation = useMutation({
  mutationFn: (request: DownloadStockDataRequest) => api.downloadStockData(request),
  onSuccess: (response) => {
    setActiveTaskId(response.task_id);  // Track background task
    setShowProgress(true);              // Show progress UI
  },
});
```

---

## 🎨 User Experience Design

### **Workflow Patterns:**

#### **Standard Data Loading Flow:**
1. Select loading mode (Symbol/Index/Industry)
2. Choose specific symbol/index/industry
3. Set date range (optional)
4. Select sync mode (Load/Refresh/Delete)
5. Click action button
6. Monitor real-time progress
7. Review completion status

#### **Gap Analysis Flow:**
1. Configure selection (symbol/index/industry)
2. Click "Complete Historical Gap Analysis"
3. Review discovered gaps by year
4. Choose sync strategy (All Missing / Range Only)
5. Execute data sync operation
6. Monitor progress and completion

#### **Symbol Management Flow:**
1. Apply filters (search, index, industry)
2. Review symbol mappings table
3. Perform individual symbol actions (Load/Refresh)
4. Monitor data quality scores
5. Update mappings when needed

### **Progressive Enhancement:**
- **Basic**: Core data loading functionality
- **Intermediate**: Gap analysis and smart sync
- **Advanced**: Bulk operations and real-time monitoring

### **Responsive Design:**
- **Mobile**: Single-column layout with collapsed panels
- **Tablet**: Two-column layout with optimized spacing
- **Desktop**: Full multi-column layout with all features visible

---

## 📊 Performance & Scalability

### **Frontend Optimization:**
- **React Query Caching**: Minimizes API calls with intelligent cache management
- **Debounced Search**: Reduces API calls during symbol filtering
- **Pagination**: Large datasets loaded in manageable chunks
- **Progressive Loading**: Non-blocking UI with background task processing

### **Backend Integration:**
- **Connection Pooling**: Efficient database connections
- **Partitioned Data**: 5-year MongoDB collections for optimal performance
- **Background Tasks**: Non-blocking operations with progress tracking
- **Error Recovery**: Retry mechanisms and graceful degradation

### **Real-world Performance:**
- **Symbol Mappings**: ~1 second load time for 200 symbols
- **Gap Analysis**: ~2-3 seconds for complete historical analysis
- **Data Loading**: Background processing with real-time progress
- **Database Queries**: Sub-second response times with proper indexing

---

## 🔒 Data Integrity & Validation

### **Duplicate Prevention:**
- Fixed partition query logic prevents duplicate records
- Unique constraints on symbol+date combinations
- Upsert operations maintain data consistency

### **Gap Analysis Accuracy:**
- Realistic trading day calculations accounting for Indian market holidays
- NSE source validation for accurate gap detection
- Coverage calculations show exactly 100% when data is complete

### **Error Handling:**
- Comprehensive validation at form level
- API error boundaries with user-friendly messages
- Network failure recovery with retry mechanisms
- Data corruption detection and reporting

---

## 🚀 Future Enhancement Opportunities

### **Near-term Improvements:**
1. **Batch Symbol Selection**: Multi-select checkboxes for symbol loading
2. **Scheduling System**: Automated data refresh scheduling
3. **Data Export**: Excel/CSV export functionality
4. **Advanced Charting**: Integrated price charts with technical indicators

### **Long-term Vision:**
1. **Real-time Data Feeds**: Live market data integration
2. **Portfolio Management**: Investment tracking and analysis
3. **Alert System**: Price-based and technical indicator notifications
4. **Machine Learning**: Predictive analytics and pattern recognition

---

## 📈 Success Metrics

### **Current System Performance:**
- **✅ 761,834+ Records**: Successfully managing large-scale historical data
- **✅ 200 Active Symbols**: Complete historical coverage across major stocks
- **✅ 0 Duplicates**: Data integrity maintained through all operations
- **✅ 20+ Years**: Historical data from 2005 to present
- **✅ Real-time Processing**: Background tasks with live progress tracking

### **User Experience Quality:**
- **✅ Sub-second Response**: Fast API calls and UI updates
- **✅ Intuitive Interface**: Clear workflow with progressive enhancement
- **✅ Error Recovery**: Robust error handling with user guidance
- **✅ Mobile Responsive**: Full functionality across all device types

---

*This functional design document serves as the definitive reference for the `/stocks` page functionality, covering all features, technical implementation, and user experience design patterns. The system is production-ready and actively managing 761K+ financial records with real-time processing capabilities.*
