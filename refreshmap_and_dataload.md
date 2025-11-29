# RefreshMap and DataLoad Guide

## Overview
This guide covers the process of refreshing symbol mappings and loading historical stock data using the DataLoadManagement CLI tool. The process involves mapping index constituent symbols to NSE scrip codes and downloading comprehensive historical price data.

## Prerequisites

### 1. Environment Setup
```bash
# Ensure you're in the project directory
cd /media/guru/Data/workspace/market-hunt

# Activate virtual environment
source .venv/bin/activate

# Verify services are running
ps aux | grep -E "(streamlit|api_server)" | grep -v grep
```

### 2. Database Requirements
- MongoDB running on localhost:27017
- Database: `market_hunt`
- Required collections: `index_meta`, `symbol_mappings`

### 3. Data Prerequisites
- Index constituent data should be loaded in `index_meta` collection
- Use URL Management system to process index URLs before running this guide

## DataLoadManagement CLI Overview

### Available Commands
```bash
# View all available commands
python DataLoadManagement.py --help

# Key commands:
# - refresh-mappings: Map symbols to NSE scrip codes
# - download-index: Download historical data for entire index
# - download-stock: Download data for individual stock
# - show-stats: Show system statistics
# - check-gaps: Analyze data gaps without downloading
```

## Step-by-Step Process

### Step 1: Refresh Symbol Mappings

**Purpose:** Map index constituent symbols to NSE scrip codes

```bash
source .venv/bin/activate && python DataLoadManagement.py refresh-mappings
```

**What it does:**
- Reads symbols from `index_meta` collection
- Fetches latest NSE equity masters (3000+ symbols)
- Maps index symbols to NSE scrip codes
- Updates `symbol_mappings` collection

**Expected Output:**
```
✅ Symbol mapping refresh completed successfully!
   Total Symbols Processed: 1,408
   Successfully Mapped: 507
   Unmapped Symbols: 0
   New Mappings Created: 0
   Updated Existing: 507
```

### Step 2: Verify Available Indexes

Check what indexes are available for data loading:

```bash
# Check database for exact index names
mongosh --eval "db = db.getSiblingDB('market_hunt'); db.index_meta.distinct('index_name')"
```

**Expected indexes:**
- MARKET INDEXES
- NIFTY 500
- NIFTY 200
- NIFTY100
- NIFTY150
- NIFTY50
- NIFTYMID150
- NIFTYSMALL250

### Step 3: Force Load Historical Data

#### For NIFTY 500 Index

```bash
source .venv/bin/activate && python DataLoadManagement.py download-index "NIFTY 500" --force-refresh --max-concurrent 3
```

**Parameters:**
- `--force-refresh`: Re-download even if recent data exists
- `--max-concurrent 3`: Use 3 parallel downloads for stability

**Expected Results:**
- Total stocks: 501
- Success rate: ~99.8% (500/501)
- Date range: 2005-01-01 to current date
- Duration: ~45-60 minutes depending on network

#### For MARKET INDEXES

```bash
source .venv/bin/activate && python DataLoadManagement.py download-index "MARKET INDEXES" --force-refresh --max-concurrent 3
```

**Expected Results:**
- Total indexes: 6 (Nifty 50, Nifty 500, Nifty Bank, Nifty IT, 100 EQL Wgt, 50 EQL Wgt)
- Success rate: 100% (6/6)
- Date range: 2005-01-01 to current date
- Duration: ~5-10 minutes

## Data Storage Structure

### Database Collections

#### 1. symbol_mappings
```javascript
{
  "symbol": "RELIANCE",
  "scrip_code": "2885",
  "company_name": "Reliance Industries Ltd.",
  "index_names": ["NIFTY 50", "NIFTY 500"],
  "industry": "Oil Gas & Consumable Fuels"
}
```

#### 2. prices_YYYY_YYYY (Partitioned by 5-year periods)
```javascript
{
  "symbol": "RELIANCE",
  "date": "2025-09-03",
  "open": 2850.00,
  "high": 2875.00,
  "low": 2840.00,
  "close": 2860.00,
  "volume": 5000000,
  "scrip_code": "2885"
}
```

**Partition Examples:**
- `prices_2005` (2005-2009)
- `prices_2010` (2010-2014)
- `prices_2015` (2015-2019)
- `prices_2020` (2020-2024)
- `prices_2025` (2025-2029)

#### 3. stock_metadata
- Processing timestamps
- Data quality metrics
- Coverage statistics

#### 4. data_processing_logs
- Download activity logs
- Error tracking
- Performance metrics

## Monitoring and Verification

### 1. Check Progress During Download
```bash
# Monitor logs in another terminal
tail -f backend.log

# Check system statistics
source .venv/bin/activate && python DataLoadManagement.py show-stats
```

### 2. Verify Data Quality
```bash
# Check gaps for specific stock
source .venv/bin/activate && python DataLoadManagement.py check-gaps RELIANCE

# Check database record counts
mongosh --eval "
db = db.getSiblingDB('market_hunt');
db.symbol_mappings.countDocuments();
db.prices_2020.countDocuments();
"
```

### 3. Sample Data Verification
```bash
# Check recent data for a symbol
mongosh --eval "
db = db.getSiblingDB('market_hunt');
db.prices_2025.find({symbol: 'RELIANCE'}).sort({date: -1}).limit(5);
"
```

## Troubleshooting

### Common Issues

#### 1. Symbol Mapping Failures
```bash
# Symptom: Low mapping success rate
# Solution: Check index_meta data quality
mongosh --eval "db = db.getSiblingDB('market_hunt'); db.index_meta.findOne()"
```

#### 2. Network Timeout Errors
```bash
# Symptom: Connection failures during download
# Solution: Reduce concurrent downloads
python DataLoadManagement.py download-index "INDEX_NAME" --max-concurrent 1
```

#### 3. Database Connection Issues
```bash
# Check MongoDB status
sudo systemctl status mongod

# Check database connectivity
mongosh --eval "db.adminCommand('ismaster')"
```

#### 4. Incomplete Downloads
```bash
# Check and resume specific symbols
python DataLoadManagement.py download-stock SYMBOL_NAME --force-refresh

# Check data gaps
python DataLoadManagement.py check-gaps SYMBOL_NAME
```

## Performance Optimization

### 1. Concurrent Downloads
- **Conservative:** `--max-concurrent 1` (slow but stable)
- **Balanced:** `--max-concurrent 3` (recommended)
- **Aggressive:** `--max-concurrent 5` (faster but may cause timeouts)

### 2. Memory Management
```bash
# Monitor system resources
htop

# Check MongoDB memory usage
mongosh --eval "db.serverStatus().mem"
```

### 3. Network Considerations
- Stable internet connection required
- NSE rate limiting may apply
- Peak hours may have slower response times

## Maintenance Schedule

### Daily
- Monitor data freshness in frontend
- Check for failed downloads in logs

### Weekly
```bash
# Update recent data
python DataLoadManagement.py download-index "NIFTY 500" --start-date $(date -d '7 days ago' +%Y-%m-%d)
```

### Monthly
```bash
# Full refresh of symbol mappings
python DataLoadManagement.py refresh-mappings

# Update all index data
python DataLoadManagement.py download-index "NIFTY 500" --force-refresh
```

## Success Metrics

### Symbol Mapping
- ✅ **Target:** 99%+ mapping success rate
- ✅ **Achieved:** 507/507 (100%) unique symbols mapped

### Data Loading
- ✅ **Target:** 99%+ download success rate
- ✅ **Achieved:** NIFTY 500: 500/501 (99.8%), MARKET INDEXES: 6/6 (100%)

### Data Coverage
- ✅ **Target:** 2005-present with 99%+ trading day coverage
- ✅ **Achieved:** 20+ years of historical data with 99.8% coverage

## Advanced Usage

### Custom Date Ranges
```bash
# Download specific date range
python DataLoadManagement.py download-stock RELIANCE --start-date 2020-01-01 --end-date 2023-12-31
```

### Industry-Based Downloads
```bash
# Download all stocks in an industry
python DataLoadManagement.py download-industry "Information Technology"
```

### Bulk Operations
```bash
# Delete and reload specific index (use with caution)
python DataLoadManagement.py delete-index "TEST_INDEX" --force
python DataLoadManagement.py download-index "TEST_INDEX" --force-refresh
```

## Integration with Frontend

After successful data loading:

1. **Frontend Dashboard:** Shows updated statistics
2. **Stock Data Status:** Displays data freshness
3. **Gap Analysis:** Highlights missing data periods
4. **Performance Metrics:** Shows data coverage percentages

## Security Considerations

1. **Database Access:** Ensure MongoDB is properly secured
2. **API Limits:** Respect NSE API rate limits
3. **Data Integrity:** Verify data quality after bulk operations
4. **Backup Strategy:** Regular database backups recommended

## Conclusion

This guide provides a comprehensive approach to refreshing symbol mappings and loading historical stock data. The process is designed to be robust, scalable, and maintainable for long-term operation of the Market Hunt system.

**Next Steps:**
1. Set up automated daily data refresh
2. Implement monitoring alerts for data quality
3. Create data backup and recovery procedures
4. Develop custom indicators and analysis tools

---

**Last Updated:** September 3, 2025  
**Tested On:** Market Hunt v1.0.0  
**Database:** MongoDB market_hunt  
**Environment:** Ubuntu Linux with Python 3.13
