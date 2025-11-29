# Indicator CLI Tool Documentation

## Overview
The Indicator CLI Tool (`indicator_cli.py`) provides a powerful command-line interface for calculating technical indicators directly, serving as an alternative to the web interface. This tool is designed for power users, automation scripts, and batch processing scenarios.

## Features

### ✅ **Core Capabilities**
- **Single Stock Calculation**: Calculate indicators for individual stocks
- **Multiple Stock Processing**: Batch process multiple stocks simultaneously
- **Bulk Universe Processing**: Process entire stock universes (NIFTY50, NIFTY100, NIFTY500)
- **Real-time Progress Monitoring**: Live progress updates during calculations
- **Data Export**: Export results to CSV or JSON formats
- **Job Status Tracking**: Monitor and check calculation job statuses
- **Stored Data Management**: List and view previously calculated indicators

### 🎯 **Supported Indicators**
- **TrueValueX**: Advanced ranking system with structural and trend analysis
- **Extensible Design**: Easy to add new indicators in the future

### 📊 **Output Formats**
- **CSV**: Spreadsheet-compatible format for analysis
- **JSON**: Machine-readable format for integration
- **Console**: Formatted table display for quick viewing

## Installation & Setup

### Prerequisites
```bash
# Ensure Python 3.13+ is installed
python --version

# Ensure MongoDB is running
systemctl status mongodb  # Linux
brew services list | grep mongodb  # macOS
```

### Dependencies
The CLI tool uses existing project modules:
- `indicator_data_manager.py` - Database operations
- `indicator_engine.py` - Calculation engine  
- `batch_indicator_processor.py` - Batch processing
- `stock_data_manager.py` - Stock data access

## Usage Examples

### 🔥 **Quick Start Examples**

#### Calculate TrueValueX for a Single Stock
```bash
# Basic calculation with default parameters
python indicator_cli.py calculate --symbol TCS --indicator truevx

# With custom date range
python indicator_cli.py calculate --symbol TCS --indicator truevx --start-date 2024-01-01 --end-date 2024-12-31

# With custom parameters
python indicator_cli.py calculate --symbol TCS --indicator truevx --s1 20 --m2 60 --l3 200
```

#### Calculate for Multiple Stocks
```bash
# Multiple stocks with comma separation
python indicator_cli.py calculate --symbols TCS,INFY,RELIANCE --indicator truevx

# Multiple stocks with custom parameters
python indicator_cli.py calculate --symbols TCS,INFY,RELIANCE --indicator truevx --s1 25 --m2 75 --l3 250
```

#### Bulk Processing
```bash
# Process entire NIFTY50 universe
python indicator_cli.py bulk --universe nifty50 --indicator truevx

# Process NIFTY100 with custom date range
python indicator_cli.py bulk --universe nifty100 --indicator truevx --start-date 2024-01-01 --end-date 2024-12-31

# Process NIFTY500 with custom parameters
python indicator_cli.py bulk --universe nifty500 --indicator truevx --s1 30 --m2 90 --l3 300
```

### 📋 **Data Management**

#### List Stored Indicators
```bash
# List all stored indicators
python indicator_cli.py list

# List indicators for specific symbol
python indicator_cli.py list --symbol TCS
```

#### Export Data
```bash
# Export to CSV (default format)
python indicator_cli.py export --symbol TCS --indicator truevx

# Export to JSON
python indicator_cli.py export --symbol TCS --indicator truevx --format json

# Export with custom filename
python indicator_cli.py export --symbol TCS --indicator truevx --output my_analysis.csv

# Export with date range filter
python indicator_cli.py export --symbol TCS --indicator truevx --start-date 2024-06-01 --end-date 2024-12-31
```

#### Check Job Status
```bash
# Check status of a calculation job
python indicator_cli.py status --job-id abc123-def456-ghi789
```

## Command Reference

### **calculate** - Calculate indicators
```bash
python indicator_cli.py calculate [OPTIONS]

Required (one of):
  --symbol SYMBOL         Single symbol to calculate
  --symbols SYMBOLS       Comma-separated list of symbols

Optional:
  --indicator {truevx}    Indicator type (default: truevx) 
  --base-symbol SYMBOL    Base symbol for comparison (default: Nifty 50)
  --s1 INT               S1 parameter (default: 22)
  --m2 INT               M2 parameter (default: 66) 
  --l3 INT               L3 parameter (default: 222)
  --start-date DATE      Start date YYYY-MM-DD (default: stock's first available date)
  --end-date DATE        End date YYYY-MM-DD (default: stock's last available date)
```

### **bulk** - Bulk calculate for universe
```bash
python indicator_cli.py bulk [OPTIONS]

Required:
  --universe {nifty50,nifty100,nifty500}  Stock universe

Optional:
  --indicator {truevx}    Indicator type (default: truevx)
  --s1 INT               S1 parameter (default: 22)
  --m2 INT               M2 parameter (default: 66)
  --l3 INT               L3 parameter (default: 222) 
  --start-date DATE      Start date YYYY-MM-DD
  --end-date DATE        End date YYYY-MM-DD
```

### **list** - List stored indicators
```bash
python indicator_cli.py list [OPTIONS]

Optional:
  --symbol SYMBOL        Filter by symbol
```

### **export** - Export indicator data
```bash
python indicator_cli.py export [OPTIONS]

Required:
  --symbol SYMBOL        Symbol to export

Optional:
  --indicator {truevx}   Indicator type (default: truevx)
  --base-symbol SYMBOL   Base symbol (default: Nifty 50)
  --format {csv,json}    Export format (default: csv)
  --output FILENAME      Output filename (auto-generated if not provided)
  --start-date DATE      Start date filter YYYY-MM-DD
  --end-date DATE        End date filter YYYY-MM-DD
```

### **status** - Check job status
```bash
python indicator_cli.py status [OPTIONS]

Required:
  --job-id JOB_ID       Job ID to check
```

## Advanced Usage Scenarios

### 🔄 **Automation Scripts**
```bash
#!/bin/bash
# Daily indicator calculation script

echo "Starting daily indicator calculations..."

# Calculate for top stocks
python indicator_cli.py calculate --symbols TCS,INFY,RELIANCE,HDFCBANK,ICICIBANK --indicator truevx

# Export latest data for analysis
python indicator_cli.py export --symbol TCS --indicator truevx --format csv --output daily_tcs.csv

echo "Daily calculations completed!"
```

### 📊 **Batch Analysis Workflow**
```bash
# 1. Calculate indicators for entire NIFTY50
python indicator_cli.py bulk --universe nifty50 --indicator truevx

# 2. List all calculated indicators
python indicator_cli.py list

# 3. Export data for top performers
python indicator_cli.py export --symbol TCS --indicator truevx --format json
python indicator_cli.py export --symbol INFY --indicator truevx --format json
```

### 🎯 **Custom Parameter Analysis**
```bash
# Test different parameter combinations
python indicator_cli.py calculate --symbol TCS --indicator truevx --s1 15 --m2 45 --l3 150
python indicator_cli.py calculate --symbol TCS --indicator truevx --s1 25 --m2 75 --l3 250  
python indicator_cli.py calculate --symbol TCS --indicator truevx --s1 30 --m2 90 --l3 300
```

## Output Examples

### Console Output - Calculation
```
============================================================
🎯 Calculating TRUEVX for TCS
============================================================
ℹ️  Fetching stock data for TCS...
ℹ️  Created calculation job: 12345678-1234-1234-1234-123456789012
ℹ️  Performing calculation...
✅ Successfully calculated and stored 365 data points
```

### Console Output - Progress Monitoring  
```
============================================================
🎯 Calculating TRUEVX for 5 symbols
============================================================
ℹ️  Symbols: TCS, INFY, RELIANCE, HDFCBANK, ICICIBANK
✅ Submitted batch job: 87654321-4321-4321-4321-210987654321
ℹ️  Monitoring progress...
📊 Progress: 60.0% - Status: running
✅ Batch calculation completed successfully!
```

### Console Output - List Indicators
```
============================================================
🎯 Stored Indicators  
============================================================

Symbol     Indicator  Base Symbol     Points   Last Updated         Latest Score
-------------------------------------------------------------------------------------
TCS        truevx     Nifty 50        365      2024-12-31          67.45
INFY       truevx     Nifty 50        365      2024-12-31          72.18
RELIANCE   truevx     Nifty 50        365      2024-12-31          58.92

✅ Found 3 stored indicators
```

### CSV Export Format
```csv
date,truevx_score,mean_short,mean_mid,mean_long,structural_score,trend_score
2024-01-01,65.5,62.1,64.8,66.2,0.75,0.82
2024-01-02,66.2,62.8,65.1,66.5,0.76,0.83
2024-01-03,64.9,61.5,64.2,66.0,0.74,0.81
```

### JSON Export Format
```json
[
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
```

## Error Handling

### Common Errors and Solutions

#### **Connection Error**
```
❌ Failed to connect to MongoDB: Connection refused
```
**Solution**: Ensure MongoDB is running
```bash
sudo systemctl start mongodb  # Linux
brew services start mongodb   # macOS
```

#### **Symbol Not Found**
```
❌ No data found for symbol: INVALID
```
**Solution**: Use valid NSE symbols (TCS, INFY, RELIANCE, etc.)

#### **Invalid Date Format**
```
❌ Invalid date format. Use YYYY-MM-DD
```
**Solution**: Use correct date format: `--start-date 2024-01-01`

#### **Missing Job ID**
```
❌ Job not found
```
**Solution**: Use valid job ID returned from calculation commands

## Performance Considerations

### **Optimization Tips**
1. **Batch Processing**: Use `--symbols` for multiple stocks instead of separate commands
2. **Date Ranges**: Specify reasonable date ranges to avoid excessive data processing
3. **Universe Processing**: Use bulk commands for large-scale calculations
4. **Progress Monitoring**: CLI provides real-time progress for long-running jobs

### **Resource Usage**
- **Memory**: ~100MB for typical calculations
- **CPU**: Utilizes multiple cores for batch processing
- **Database**: Efficient indexes for fast data retrieval
- **Network**: Minimal - only local MongoDB connections

## Integration with Existing System

### **Web Interface Alternative**
The CLI tool provides identical functionality to the web interface:
- ✅ Same calculation engine (`indicator_engine.py`)
- ✅ Same data storage (`indicator_data_manager.py`) 
- ✅ Same batch processing (`batch_indicator_processor.py`)
- ✅ Same job tracking and progress monitoring
- ✅ Same TrueValueX parameters and output format

### **Data Compatibility**
- **Shared Database**: CLI and web interface use the same MongoDB collections
- **Interchangeable Results**: Data calculated via CLI appears in web interface and vice versa
- **Consistent Format**: Same indicator output structure across both interfaces

## Troubleshooting

### **Debug Mode**
Enable detailed logging:
```bash
export PYTHONPATH=/path/to/market-hunt
python -u indicator_cli.py calculate --symbol TCS --indicator truevx
```

### **Verbose Output**
Check calculation logs:
```bash
tail -f backend.log  # If backend server is running
```

### **Database Verification**
Check stored data:
```bash
python indicator_cli.py list --symbol TCS
```

## Future Enhancements

### **Planned Features**
- [ ] Real-time calculation streaming
- [ ] Email notifications for completed jobs
- [ ] Slack/Teams integration for alerts
- [ ] Advanced filtering and search capabilities
- [ ] Custom indicator plugin system
- [ ] Performance benchmarking tools

### **Extensibility**
The CLI tool is designed for easy extension:
- **New Indicators**: Add to `supported_indicators` in `IndicatorEngine`
- **New Export Formats**: Extend `export_data()` method
- **New Commands**: Add subparsers in `create_parser()`
- **Custom Parameters**: Extend argument parsing for new indicators

## Support

For issues, questions, or feature requests:
1. Check this documentation first
2. Review project DNA (`project_DNA.md`) for system context
3. Check backend logs for detailed error information
4. Use `--help` flag for command-specific guidance

## Conclusion

The Indicator CLI Tool provides a robust, efficient alternative to the web interface for technical indicator calculations. It's particularly valuable for:

- **Power Users**: Who prefer command-line interfaces
- **Automation**: Scheduled calculations and batch processing
- **Integration**: Embedding in larger analysis workflows
- **Development**: Testing and debugging indicator calculations
- **Production**: High-volume, unattended processing scenarios

The tool maintains full compatibility with the existing web system while providing the speed and flexibility that command-line users expect.