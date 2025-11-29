import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pymongo
from pymongo import MongoClient, DESCENDING
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Stock Screener - Market Hunt",
    page_icon="📊",
    layout="wide"
)

# MongoDB connection
@st.cache_resource(ttl=3600)  # Cache for 1 hour
def get_mongo_client():
    """Create and cache MongoDB client"""
    try:
        client = MongoClient("mongodb://localhost:27017/")
        logger.info("MongoDB client created successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        st.error(f"Failed to connect to MongoDB: {e}")
        return None

# Get the MongoDB client
mongo_client = get_mongo_client()

# Connect to the database
if mongo_client:
    db = mongo_client["market_hunt"]
    logger.info("Connected to 'market_hunt' database")
else:
    st.error("Failed to connect to MongoDB. Please check if MongoDB is running.")
    st.stop()

# Page title
st.title("Stock Screener")
st.markdown("### Consolidated Stock Indicators and Performance")

# Explanation of the page
st.info("""
This page displays a consolidated view of stocks with their latest indicator scores, current prices, and multiple rate of change (ROC) periods.
Use the filters to narrow down the stocks by index, industry, or indicator scores.
The performance filter lets you select the ROC lookback period (22, 66, or 222 days) and top N stocks with the highest ROC values.
""")

# Function to get available indices
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_available_indices():
    """Get list of available indices in the database"""
    try:
        indices = []
        cursor = db.index_meta.aggregate([
            {"$group": {"_id": "$index_name", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 10}}},  # Only indices with > 10 stocks
            {"$sort": {"_id": 1}}
        ])
        
        for doc in cursor:
            indices.append(doc["_id"])
        
        if not indices:  # Fallback if no indices found
            indices = ["NIFTY50", "NIFTY100", "NIFTY500"]
            
        return indices
    except Exception as e:
        logger.error(f"Error getting available indices: {e}")
        return ["NIFTY50", "NIFTY100", "NIFTY500"]  # Default fallback

# Function to get available industries
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_available_industries():
    """Get list of available industries in the database"""
    try:
        industries = []
        cursor = db.symbol_mappings.aggregate([
            {"$group": {"_id": "$industry", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$ne": None}}},  # Exclude null industries
            {"$sort": {"_id": 1}}
        ])
        
        for doc in cursor:
            industries.append(doc["_id"])
            
        return industries
    except Exception as e:
        logger.error(f"Error getting available industries: {e}")
        return []

# Function to get stocks by index
def get_stocks_by_index(index_name):
    """
    Get list of stock symbols that belong to a specific index
    
    Args:
        index_name: Name of the index (e.g., "NIFTY50")
        
    Returns:
        List of stock symbols in the index
    """
    try:
        stocks = []
        cursor = db.index_meta.find({"index_name": index_name}, {"Symbol": 1})
        
        for doc in cursor:
            stocks.append(doc["Symbol"])
            
        return stocks
    except Exception as e:
        logger.error(f"Error getting stocks by index {index_name}: {e}")
        return []

# Function to get stock metadata
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_stock_metadata(symbols=None):
    """
    Get metadata for stocks (name, industry, etc.)
    
    Args:
        symbols: Optional list of symbols to filter by (if None, get all)
        
    Returns:
        Dictionary mapping symbols to their metadata
    """
    try:
        metadata = {}
        query = {}
        
        if symbols:
            query["symbol"] = {"$in": symbols}
            
        cursor = db.symbol_mappings.find(query)
        
        for doc in cursor:
            symbol = doc["symbol"]
            metadata[symbol] = {
                "name": doc.get("company_name", symbol),
                "industry": doc.get("industry", "Unknown"),
                "index_names": doc.get("index_names", [])
            }
            
        return metadata
    except Exception as e:
        logger.error(f"Error getting stock metadata: {e}")
        return {}

# Function to get the latest indicator data
@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_latest_indicator_data():
    """
    Get the latest indicator data for all stocks from the indicators collection
    Returns a dictionary mapping symbols to their latest indicator data
    """
    try:
        # Find the most recent date in the indicators collection
        latest_date_record = db.indicators.find_one(
            {"indicator_type": "truevx"},
            sort=[("date", DESCENDING)]
        )
        
        if not latest_date_record:
            logger.error("No indicator data found")
            return {}
            
        latest_date = latest_date_record["date"]
        logger.info(f"Latest indicator data date: {latest_date}")
        
        # Query for all stocks on the latest date
        cursor = db.indicators.find({
            "indicator_type": "truevx",
            "date": latest_date
        })
        
        # Create a dictionary of symbol -> indicator data
        indicators_data = {}
        for doc in cursor:
            symbol = doc["symbol"]
            indicators_data[symbol] = {
                "date": doc["date"],
                "truevx_score": doc["data"].get("truevx_score", 0),
                "mean_short": doc["data"].get("mean_short", 0),
                "mean_mid": doc["data"].get("mean_mid", 0),
                "mean_long": doc["data"].get("mean_long", 0)
            }
            
        logger.info(f"Retrieved indicator data for {len(indicators_data)} stocks")
        return indicators_data
        
    except Exception as e:
        logger.error(f"Error retrieving indicator data: {e}")
        st.error(f"Error retrieving indicator data: {e}")
        return {}

# Function to get the most recent price data for stocks
@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_current_prices(symbols):
    """
    Get the current price for a list of stock symbols
    
    Args:
        symbols: List of stock symbols
        
    Returns:
        Dictionary mapping symbols to their current price
    """
    try:
        price_data = {}
        # Get the current year for the partitioned collection
        current_year = datetime.now().year
        partition_start = (current_year // 5) * 5
        partition_end = partition_start + 4
        collection_name = f"prices_{partition_start}_{partition_end}"
        
        for symbol in symbols:
            # Get the most recent price for each symbol
            price_record = db[collection_name].find_one(
                {"symbol": symbol},
                sort=[("date", DESCENDING)]
            )
            
            if price_record:
                price_data[symbol] = {
                    "date": price_record["date"],
                    "close_price": price_record["close_price"]
                }
        
        logger.info(f"Retrieved current prices for {len(price_data)} stocks")
        return price_data
        
    except Exception as e:
        logger.error(f"Error retrieving current prices: {e}")
        st.error(f"Error retrieving current prices: {e}")
        return {}

# Function to calculate 20-day Rate of Change (ROC)
@st.cache_data(ttl=1800)  # Cache for 30 minutes
def calculate_roc(symbols, days=20):
    """
    Calculate Rate of Change (ROC) for a list of stock symbols
    
    Args:
        symbols: List of stock symbols
        days: Number of days for ROC calculation (default: 20)
        
    Returns:
        Dictionary mapping symbols to their ROC values
    """
    try:
        roc_data = {}
        
        # Determine which partitions we need to query based on the days
        current_year = datetime.now().year
        
        # For longer periods, we might need multiple partitions
        partitions_to_check = []
        
        if days <= 365:  # Within 1 year, check current and previous partition
            # Current partition
            current_partition_start = (current_year // 5) * 5
            current_partition_end = current_partition_start + 4
            partitions_to_check.append(f"prices_{current_partition_start}_{current_partition_end}")
            
            # Previous partition (for data spanning across years)
            prev_partition_start = current_partition_start - 5
            prev_partition_end = prev_partition_start + 4
            partitions_to_check.append(f"prices_{prev_partition_start}_{prev_partition_end}")
        else:
            # For very long periods, check more partitions
            for year_offset in range(0, (days // 365) + 2):
                partition_year = current_year - (year_offset * 5)
                partition_start = (partition_year // 5) * 5
                partition_end = partition_start + 4
                partitions_to_check.append(f"prices_{partition_start}_{partition_end}")
        
        for symbol in symbols:
            recent_prices = []
            
            # Query each partition and collect prices
            for collection_name in partitions_to_check:
                try:
                    prices_from_partition = list(db[collection_name].find(
                        {"symbol": symbol},
                        sort=[("date", DESCENDING)],
                        limit=days + 50  # Get extra to ensure we have enough after combining
                    ))
                    recent_prices.extend(prices_from_partition)
                except Exception as e:
                    # Partition might not exist, continue with next one
                    continue
            
            # Sort all prices by date (most recent first) and remove duplicates
            seen_dates = set()
            unique_prices = []
            for price in sorted(recent_prices, key=lambda x: x["date"], reverse=True):
                date_key = price["date"]
                if date_key not in seen_dates:
                    seen_dates.add(date_key)
                    unique_prices.append(price)
                    
            recent_prices = unique_prices[:days+1]  # Take only what we need
            
            if len(recent_prices) > days:  # Ensure we have enough data points
                current_price = recent_prices[0]["close_price"]
                past_price = recent_prices[days]["close_price"]
                
                if past_price > 0:  # Avoid division by zero
                    roc = ((current_price - past_price) / past_price) * 100
                    roc_data[symbol] = round(roc, 2)
                else:
                    roc_data[symbol] = 0
            else:
                # Not enough data points
                roc_data[symbol] = None
        
        logger.info(f"Calculated {days}-day ROC for {len(roc_data)} stocks")
        return roc_data
        
    except Exception as e:
        logger.error(f"Error calculating ROC: {e}")
        st.error(f"Error calculating ROC: {e}")
        return {}

# Function to get historical indicator data for ROC calculation
@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_historical_indicator_data(symbols, days_back=22):
    """
    Get historical indicator data for ROC calculation
    
    Args:
        symbols: List of stock symbols
        days_back: Number of days of historical data to fetch
        
    Returns:
        Dictionary mapping symbols to list of historical indicator data
    """
    try:
        historical_data = {}
        
        # Get the date range we need
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back + 30)  # Extra buffer for trading days
        
        for symbol in symbols:
            # Query indicators collection for this symbol's history
            cursor = db.indicators.find(
                {
                    "indicator_type": "truevx",
                    "symbol": symbol,
                    "date": {"$gte": start_date, "$lte": end_date}
                },
                sort=[("date", DESCENDING)]
            ).limit(days_back + 10)  # Get extra to ensure we have enough trading days
            
            # Collect historical records
            records = []
            for doc in cursor:
                # Handle None values from database - convert to 0
                data = doc.get("data", {})
                records.append({
                    "date": doc["date"],
                    "truevx_score": data.get("truevx_score") or 0,
                    "mean_short": data.get("mean_short") or 0,
                    "mean_mid": data.get("mean_mid") or 0,
                    "mean_long": data.get("mean_long") or 0
                })
            
            # Sort by date (most recent first)
            records.sort(key=lambda x: x["date"], reverse=True)
            historical_data[symbol] = records
        
        logger.info(f"Retrieved historical indicator data for {len(historical_data)} stocks")
        return historical_data
        
    except Exception as e:
        logger.error(f"Error retrieving historical indicator data: {e}")
        st.error(f"Error retrieving historical indicator data: {e}")
        return {}

# Function to calculate indicator ROC
@st.cache_data(ttl=1800)  # Cache for 30 minutes
def calculate_indicator_roc(symbols, historical_data, days=22):
    """
    Calculate Rate of Change (ROC) for indicator scores
    
    Args:
        symbols: List of stock symbols
        historical_data: Historical indicator data from get_historical_indicator_data()
        days: Number of days for ROC calculation (default: 22)
        
    Returns:
        Dictionary mapping symbols to their indicator ROC values
        Each symbol has: truevx_roc, short_roc, mid_roc, long_roc, stock_score_roc
    """
    try:
        indicator_roc_data = {}
        
        for symbol in symbols:
            if symbol not in historical_data:
                continue
                
            records = historical_data[symbol]
            
            # Need at least days+1 records for ROC calculation
            if len(records) <= days:
                indicator_roc_data[symbol] = {
                    "truevx_roc": None,
                    "short_roc": None,
                    "mid_roc": None,
                    "long_roc": None,
                    "stock_score_roc": None
                }
                continue
            
            # Get current (most recent) values
            current = records[0]
            # Get past values (days ago)
            past = records[days]
            
            # Calculate ROC for each indicator
            roc_values = {}
            
            # TrueVX ROC
            past_truevx = past["truevx_score"] if past["truevx_score"] is not None else 0
            current_truevx = current["truevx_score"] if current["truevx_score"] is not None else 0
            if past_truevx > 0:
                roc_values["truevx_roc"] = round(
                    ((current_truevx - past_truevx) / past_truevx) * 100, 2
                )
            else:
                roc_values["truevx_roc"] = None
            
            # Short Mean ROC
            past_short = past["mean_short"] if past["mean_short"] is not None else 0
            current_short = current["mean_short"] if current["mean_short"] is not None else 0
            if past_short > 0:
                roc_values["short_roc"] = round(
                    ((current_short - past_short) / past_short) * 100, 2
                )
            else:
                roc_values["short_roc"] = None
            
            # Mid Mean ROC
            past_mid = past["mean_mid"] if past["mean_mid"] is not None else 0
            current_mid = current["mean_mid"] if current["mean_mid"] is not None else 0
            if past_mid > 0:
                roc_values["mid_roc"] = round(
                    ((current_mid - past_mid) / past_mid) * 100, 2
                )
            else:
                roc_values["mid_roc"] = None
            
            # Long Mean ROC
            past_long = past["mean_long"] if past["mean_long"] is not None else 0
            current_long = current["mean_long"] if current["mean_long"] is not None else 0
            if past_long > 0:
                roc_values["long_roc"] = round(
                    ((current_long - past_long) / past_long) * 100, 2
                )
            else:
                roc_values["long_roc"] = None
            
            # StockScore ROC (composite) - use the safe values we already extracted
            current_stock_score = (0.1 * current_truevx + 0.2 * current_short + 
                                   0.3 * current_mid + 0.4 * current_long)
            past_stock_score = (0.1 * past_truevx + 0.2 * past_short + 
                               0.3 * past_mid + 0.4 * past_long)
            
            if past_stock_score > 0:
                roc_values["stock_score_roc"] = round(
                    ((current_stock_score - past_stock_score) / past_stock_score) * 100, 2
                )
            else:
                roc_values["stock_score_roc"] = None
            
            indicator_roc_data[symbol] = roc_values
        
        logger.info(f"Calculated {days}-day indicator ROC for {len(indicator_roc_data)} stocks")
        return indicator_roc_data
        
    except Exception as e:
        logger.error(f"Error calculating indicator ROC: {e}")
        st.error(f"Error calculating indicator ROC: {e}")
        return {}

# Show a loading message while we set up the page
with st.spinner('Loading stock data...'):
    # Get the latest indicator data
    indicator_data = get_latest_indicator_data()
    
    if not indicator_data:
        st.error("No indicator data available. Please check the database connection.")
        st.stop()
    
    # Get list of symbols from indicator data
    symbols = list(indicator_data.keys())
    
    # Get current prices for these symbols
    price_data = get_current_prices(symbols)
    
    # Get stock metadata
    stock_metadata = get_stock_metadata(symbols)
    
    # Get available indices and industries for filtering
    available_indices = get_available_indices()
    available_industries = get_available_industries()
    
    logger.info(f"Loaded data for {len(indicator_data)} stocks")

# Create filter UI in the sidebar
st.sidebar.title("Filters")

# Index filter
selected_index = st.sidebar.selectbox(
    "Select Index",
    ["All"] + available_indices,
    index=0,
    help="Filter stocks by index membership"
)

# Industry filter
selected_industry = st.sidebar.selectbox(
    "Select Industry",
    ["All"] + available_industries,
    index=0,
    help="Filter stocks by industry"
)

# Advanced filters
st.sidebar.subheader("Advanced Filters")
with st.sidebar.expander("Score Filters", expanded=False):
    min_truevx = st.slider("Min TrueVX Score", 0, 100, 90)
    min_short_mean = st.slider("Min Short Mean", 0, 100, 81)
    min_mid_mean = st.slider("Min Mid Mean", 0, 100, 61)
    min_long_mean = st.slider("Min Long Mean", 0, 100, 50)
    
with st.sidebar.expander("Performance Filters", expanded=False):
    # ROC criteria selector
    roc_criteria = st.selectbox(
        "Top N Filter Criteria",
        options=[
            "Price ROC (22-day)",
            "Price ROC (66-day)",
            "Price ROC (222-day)",
            "TrueVX ROC (22-day)",
            "Short Mean ROC (22-day)",
            "Mid Mean ROC (22-day)",
            "Long Mean ROC (22-day)",
            "StockScore ROC (22-day)"
        ],
        index=0,
        help="Select which ROC metric to use for filtering top N stocks"
    )
    
    # Top N stocks by selected ROC criteria
    top_n_roc = st.slider(
        f"Top N Stocks by {roc_criteria}", 
        min_value=1,
        max_value=len(symbols) if symbols else 500,
        value=len(symbols) if symbols else 500,
        help=f"Select top N stocks with highest {roc_criteria} values"
    )

# Calculate ROC for multiple periods (after sidebar is defined)
roc_data_22d = calculate_roc(symbols, days=22)
roc_data_66d = calculate_roc(symbols, days=66) 
roc_data_222d = calculate_roc(symbols, days=222)

# Get historical indicator data for indicator ROC calculation
historical_indicator_data = get_historical_indicator_data(symbols, days_back=22)

# Calculate indicator ROC (22-day)
indicator_roc_data = calculate_indicator_roc(symbols, historical_indicator_data, days=22)

# Helper function to get ROC value based on selected criteria
def get_roc_value(symbol, criteria):
    """Get ROC value for a symbol based on selected criteria"""
    if criteria == "Price ROC (22-day)":
        return roc_data_22d.get(symbol, None)
    elif criteria == "Price ROC (66-day)":
        return roc_data_66d.get(symbol, None)
    elif criteria == "Price ROC (222-day)":
        return roc_data_222d.get(symbol, None)
    elif criteria == "TrueVX ROC (22-day)":
        return indicator_roc_data.get(symbol, {}).get("truevx_roc", None)
    elif criteria == "Short Mean ROC (22-day)":
        return indicator_roc_data.get(symbol, {}).get("short_roc", None)
    elif criteria == "Mid Mean ROC (22-day)":
        return indicator_roc_data.get(symbol, {}).get("mid_roc", None)
    elif criteria == "Long Mean ROC (22-day)":
        return indicator_roc_data.get(symbol, {}).get("long_roc", None)
    elif criteria == "StockScore ROC (22-day)":
        return indicator_roc_data.get(symbol, {}).get("stock_score_roc", None)
    return None

# Apply filters to get the final list of symbols to display
filtered_symbols = symbols.copy()

# Apply index filter
if selected_index != "All":
    index_stocks = get_stocks_by_index(selected_index)
    filtered_symbols = [s for s in filtered_symbols if s in index_stocks]

# Apply industry filter
if selected_industry != "All":
    filtered_symbols = [
        s for s in filtered_symbols 
        if s in stock_metadata and stock_metadata[s].get("industry") == selected_industry
    ]
    
# Apply advanced score filters
filtered_symbols = [
    s for s in filtered_symbols
    if (s in indicator_data and
        indicator_data[s].get("truevx_score", 0) >= min_truevx and
        indicator_data[s].get("mean_short", 0) >= min_short_mean and
        indicator_data[s].get("mean_mid", 0) >= min_mid_mean and
        indicator_data[s].get("mean_long", 0) >= min_long_mean)
]

# Apply top N ROC filter
# Sort ALL filtered symbols by selected ROC criteria in descending order (None values go to the end)
def roc_sort_key(symbol):
    roc_value = get_roc_value(symbol, roc_criteria)
    if roc_value is None:
        return -float('inf')  # Put None values at the end
    return roc_value

sorted_by_roc = sorted(filtered_symbols, key=roc_sort_key, reverse=True)
# Take top N symbols based on selected ROC criteria (up to the number that have valid ROC values)
filtered_symbols = sorted_by_roc[:top_n_roc]

# Create a DataFrame with StockScore for ALL stocks (before filtering)
all_stock_data = []
for symbol in symbols:
    # Skip if missing data (check basic required data only)
    if symbol not in indicator_data or symbol not in price_data:
        continue
        
    # Get stock metadata
    metadata = stock_metadata.get(symbol, {})
    name = metadata.get("name", symbol)
    industry = metadata.get("industry", "Unknown")
    
    # Get indicator scores
    truevx_score = indicator_data[symbol].get("truevx_score", 0)
    mean_short = indicator_data[symbol].get("mean_short", 0)
    mean_mid = indicator_data[symbol].get("mean_mid", 0)
    mean_long = indicator_data[symbol].get("mean_long", 0)
    
    # Calculate StockScore = 0.1*TrueValueX + 0.2*Mean_Short + 0.3*Mean_Mid + 0.4*Mean_Long
    stock_score = (0.1 * truevx_score + 0.2 * mean_short + 0.3 * mean_mid + 0.4 * mean_long)
    
    # Get current price
    current_price = price_data.get(symbol, {}).get("close_price", 0)
    
    # Get ROC values for all periods (price ROC)
    roc_22d = roc_data_22d.get(symbol, None)
    roc_66d = roc_data_66d.get(symbol, None)
    roc_222d = roc_data_222d.get(symbol, None)
    
    # Get indicator ROC values (22-day)
    ind_roc = indicator_roc_data.get(symbol, {})
    truevx_roc = ind_roc.get("truevx_roc", None)
    short_roc = ind_roc.get("short_roc", None)
    mid_roc = ind_roc.get("mid_roc", None)
    long_roc = ind_roc.get("long_roc", None)
    stock_score_roc = ind_roc.get("stock_score_roc", None)
    
    # Add to all stock data
    all_stock_data.append({
        "Symbol": symbol,
        "Name": name,
        "Industry": industry,
        "TrueVX Score": round(truevx_score, 2),
        "Short Mean": round(mean_short, 2),
        "Mid Mean": round(mean_mid, 2),
        "Long Mean": round(mean_long, 2),
        "StockScore": round(stock_score, 2),
        "Current Price": round(current_price, 2),
        "22-Day ROC (%)": roc_22d,
        "66-Day ROC (%)": roc_66d,
        "222-Day ROC (%)": roc_222d,
        "TrueVX ROC (22d)": truevx_roc,
        "Short ROC (22d)": short_roc,
        "Mid ROC (22d)": mid_roc,
        "Long ROC (22d)": long_roc,
        "StockScore ROC (22d)": stock_score_roc
    })

# Create DataFrame for all stocks and calculate industry_mean_all
all_df = pd.DataFrame(all_stock_data)
industry_mean_all = all_df.groupby('Industry')['StockScore'].mean().to_dict()

# Create a DataFrame from the filtered data
data_rows = []
for symbol in filtered_symbols:
    # Find the stock in all_stock_data
    stock_data_row = next((row for row in all_stock_data if row["Symbol"] == symbol), None)
    if stock_data_row:
        data_rows.append(stock_data_row)

# Create DataFrame and sort by selected ROC criteria in descending order
df = pd.DataFrame(data_rows)

# Map criteria to column name for sorting
criterion_column_map = {
    "Price ROC (22-day)": "22-Day ROC (%)",
    "Price ROC (66-day)": "66-Day ROC (%)",
    "Price ROC (222-day)": "222-Day ROC (%)",
    "TrueVX ROC (22-day)": "TrueVX ROC (22d)",
    "Short Mean ROC (22-day)": "Short ROC (22d)",
    "Mid Mean ROC (22-day)": "Mid ROC (22d)",
    "Long Mean ROC (22-day)": "Long ROC (22d)",
    "StockScore ROC (22-day)": "StockScore ROC (22d)"
}

sort_column = criterion_column_map[roc_criteria]
df = df.sort_values(by=sort_column, ascending=False)

# Display count of stocks and note about ROC sorting
st.write(f"Displaying {len(data_rows)} stocks")
if top_n_roc < len(symbols):
    st.write(f"Showing top {top_n_roc} stocks by {roc_criteria} (sorted in descending order)")
else:
    st.write(f"Showing all stocks (sorted by {roc_criteria} in descending order)")

# Display metrics at the top
if data_rows:
    # Calculate average metrics - Scores
    avg_stock_score = df["StockScore"].mean()
    avg_truevx = df["TrueVX Score"].mean()
    avg_short_mean = df["Short Mean"].mean()
    avg_mid_mean = df["Mid Mean"].mean()
    avg_long_mean = df["Long Mean"].mean()
    
    # Calculate average metrics - Price ROC
    avg_price_roc_22d = df["22-Day ROC (%)"].mean()
    avg_price_roc_66d = df["66-Day ROC (%)"].mean()
    avg_price_roc_222d = df["222-Day ROC (%)"].mean()
    
    # Calculate average metrics - Indicator ROC
    avg_truevx_roc = df["TrueVX ROC (22d)"].mean()
    avg_short_roc = df["Short ROC (22d)"].mean()
    avg_mid_roc = df["Mid ROC (22d)"].mean()
    avg_long_roc = df["Long ROC (22d)"].mean()
    avg_score_roc = df["StockScore ROC (22d)"].mean()
    
    # Selected ROC average
    avg_selected_roc = df[sort_column].mean()
    
    # Determine CSS classes for color coding
    price_roc_22d_class = 'positive' if avg_price_roc_22d > 0 else 'negative'
    price_roc_66d_class = 'positive' if avg_price_roc_66d > 0 else 'negative'
    price_roc_222d_class = 'positive' if avg_price_roc_222d > 0 else 'negative'
    truevx_roc_class = 'positive' if avg_truevx_roc > 0 else 'negative'
    short_roc_class = 'positive' if avg_short_roc > 0 else 'negative'
    mid_roc_class = 'positive' if avg_mid_roc > 0 else 'negative'
    long_roc_class = 'positive' if avg_long_roc > 0 else 'negative'
    score_roc_class = 'positive' if avg_score_roc > 0 else 'negative'
    selected_roc_class = 'positive' if avg_selected_roc > 0 else 'negative'
    
    # Create compact metric display with sections
    st.markdown("""
    <style>
    .metric-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid #00d4ff;
        box-shadow: 0 4px 6px rgba(0, 212, 255, 0.1);
    }
    .metric-section {
        margin-bottom: 10px;
    }
    .metric-title {
        color: #00d4ff;
        font-size: 14px;
        font-weight: bold;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
    }
    .metric-item {
        background: rgba(0, 212, 255, 0.05);
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 3px solid #00d4ff;
    }
    .metric-label {
        color: #888;
        font-size: 11px;
        margin-bottom: 2px;
    }
    .metric-value {
        color: #fff;
        font-size: 16px;
        font-weight: bold;
    }
    .metric-value.positive {
        color: #00ff88;
    }
    .metric-value.negative {
        color: #ff4444;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Build the metrics HTML - using string concatenation to avoid f-string issues
    metrics_html = '<div class="metric-container">'
    
    # Score Metrics Section
    metrics_html += '<div class="metric-section">'
    metrics_html += '<div class="metric-title">📊 Average Indicator Scores</div>'
    metrics_html += '<div class="metric-grid">'
    metrics_html += f'<div class="metric-item"><div class="metric-label">StockScore</div><div class="metric-value">{avg_stock_score:.2f}</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">TrueVX</div><div class="metric-value">{avg_truevx:.2f}</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">Short Mean</div><div class="metric-value">{avg_short_mean:.2f}</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">Mid Mean</div><div class="metric-value">{avg_mid_mean:.2f}</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">Long Mean</div><div class="metric-value">{avg_long_mean:.2f}</div></div>'
    metrics_html += '</div></div>'
    
    # Price ROC Section
    metrics_html += '<div class="metric-section">'
    metrics_html += '<div class="metric-title">💹 Average Price ROC (Momentum)</div>'
    metrics_html += '<div class="metric-grid">'
    metrics_html += f'<div class="metric-item"><div class="metric-label">22-Day ROC</div><div class="metric-value {price_roc_22d_class}">{avg_price_roc_22d:+.2f}%</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">66-Day ROC</div><div class="metric-value {price_roc_66d_class}">{avg_price_roc_66d:+.2f}%</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">222-Day ROC</div><div class="metric-value {price_roc_222d_class}">{avg_price_roc_222d:+.2f}%</div></div>'
    metrics_html += '</div></div>'
    
    # Indicator ROC Section
    metrics_html += '<div class="metric-section">'
    metrics_html += '<div class="metric-title">🚀 Average Indicator ROC (22-Day Fundamental Momentum)</div>'
    metrics_html += '<div class="metric-grid">'
    metrics_html += f'<div class="metric-item"><div class="metric-label">TrueVX ROC</div><div class="metric-value {truevx_roc_class}">{avg_truevx_roc:+.2f}%</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">Short ROC</div><div class="metric-value {short_roc_class}">{avg_short_roc:+.2f}%</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">Mid ROC</div><div class="metric-value {mid_roc_class}">{avg_mid_roc:+.2f}%</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">Long ROC</div><div class="metric-value {long_roc_class}">{avg_long_roc:+.2f}%</div></div>'
    metrics_html += f'<div class="metric-item"><div class="metric-label">Score ROC</div><div class="metric-value {score_roc_class}">{avg_score_roc:+.2f}%</div></div>'
    metrics_html += '</div></div>'
    
    # Selected Filter Highlight
    metrics_html += '<div class="metric-section">'
    metrics_html += f'<div class="metric-title">🎯 Selected Filter: {roc_criteria}</div>'
    metrics_html += '<div class="metric-grid">'
    metrics_html += f'<div class="metric-item" style="border-left-color: #ffd700; background: rgba(255, 215, 0, 0.1);"><div class="metric-label">Average Value</div><div class="metric-value {selected_roc_class}" style="font-size: 20px;">{avg_selected_roc:+.2f}%</div></div>'
    metrics_html += '</div></div>'
    
    metrics_html += '</div>'
    
    st.markdown(metrics_html, unsafe_allow_html=True)


# Display the data as a sortable table
if not data_rows:
    st.warning("No stocks match the selected filters.")
else:
    # Function to generate color based on value
    def get_color_for_value(val, min_val, max_val):
        """Generate color gradient from dark red (negative) to dark green (positive)"""
        if val is None or pd.isna(val):
            return ''
        
        if val == 0:
            return 'background-color: #2b2b2b; color: white'
        
        if val > 0:
            # Positive values: Light green to Dark green
            if max_val > 0:
                intensity = min(abs(val) / max_val, 1.0)
            else:
                intensity = 0.5
            
            # RGB gradient from light green (144,238,144) to dark green (0,100,0)
            r = int(144 - (144 * intensity))
            g = int(238 - (138 * intensity))
            b = int(144 - (144 * intensity))
            return f'background-color: rgb({r},{g},{b}); color: white'
        else:
            # Negative values: Light red to Dark red
            if min_val < 0:
                intensity = min(abs(val) / abs(min_val), 1.0)
            else:
                intensity = 0.5
            
            # RGB gradient from light red (255,182,193) to dark red (139,0,0)
            r = int(255 - (116 * intensity))
            g = int(182 - (182 * intensity))
            b = int(193 - (193 * intensity))
            return f'background-color: rgb({r},{g},{b}); color: white'
    
    # Apply styling to ROC columns
    def style_roc_columns(row):
        """Apply color gradient styling to ROC columns for each row"""
        styles = [''] * len(row)
        
        roc_columns = [
            "22-Day ROC (%)", "66-Day ROC (%)", "222-Day ROC (%)",
            "TrueVX ROC (22d)", "Short ROC (22d)", "Mid ROC (22d)", 
            "Long ROC (22d)", "StockScore ROC (22d)"
        ]
        
        for col in roc_columns:
            if col in df.columns:
                col_idx = df.columns.get_loc(col)
                # Get min and max for this column (excluding None values)
                col_values = df[col].dropna()
                if len(col_values) > 0:
                    min_val = col_values.min()
                    max_val = col_values.max()
                    styles[col_idx] = get_color_for_value(row[col], min_val, max_val)
        
        return styles
    
    # Apply styling and display
    styled_df = df.style.apply(style_roc_columns, axis=1)
    
    st.dataframe(
        styled_df,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol"),
            "Name": st.column_config.TextColumn("Name"),
            "Industry": st.column_config.TextColumn("Industry"),
            "StockScore": st.column_config.NumberColumn(
                "StockScore",
                format="%.2f",
                help="Composite Score: 0.1*TrueVX + 0.2*Short + 0.3*Mid + 0.4*Long"
            ),
            "TrueVX Score": st.column_config.NumberColumn(
                "TrueVX Score",
                format="%.2f",
                help="TrueValueX Score (0-100)"
            ),
            "Short Mean": st.column_config.NumberColumn(
                "Short Mean",
                format="%.2f",
                help="Short-term (22-period) mean"
            ),
            "Mid Mean": st.column_config.NumberColumn(
                "Mid Mean",
                format="%.2f",
                help="Mid-term (66-period) mean"
            ),
            "Long Mean": st.column_config.NumberColumn(
                "Long Mean",
                format="%.2f",
                help="Long-term (222-period) mean"
            ),
            "Current Price": st.column_config.NumberColumn(
                "Price (₹)",
                format="%.2f"
            ),
            "22-Day ROC (%)": st.column_config.NumberColumn(
                "Price ROC 22d (%)",
                format="%.2f",
                help="22-day price rate of change"
            ),
            "66-Day ROC (%)": st.column_config.NumberColumn(
                "Price ROC 66d (%)",
                format="%.2f",
                help="66-day price rate of change"
            ),
            "222-Day ROC (%)": st.column_config.NumberColumn(
                "Price ROC 222d (%)",
                format="%.2f",
                help="222-day price rate of change"
            ),
            "TrueVX ROC (22d)": st.column_config.NumberColumn(
                "TrueVX ROC (%)",
                format="%.2f",
                help="22-day TrueVX score rate of change"
            ),
            "Short ROC (22d)": st.column_config.NumberColumn(
                "Short ROC (%)",
                format="%.2f",
                help="22-day Short Mean rate of change"
            ),
            "Mid ROC (22d)": st.column_config.NumberColumn(
                "Mid ROC (%)",
                format="%.2f",
                help="22-day Mid Mean rate of change"
            ),
            "Long ROC (22d)": st.column_config.NumberColumn(
                "Long ROC (%)",
                format="%.2f",
                help="22-day Long Mean rate of change"
            ),
            "StockScore ROC (22d)": st.column_config.NumberColumn(
                "Score ROC (%)",
                format="%.2f",
                help="22-day StockScore rate of change"
            )
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Add download button
    csv = df.to_csv(index=False).encode('utf-8')
    current_date = datetime.now().strftime("%Y%m%d")
    
    # Create a clean filename from criteria
    criteria_clean = roc_criteria.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "")
    
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name=f"stock_indicators_{criteria_clean}_{current_date}.csv",
        mime="text/csv",
        help="Download the displayed data as a CSV file"
    )
    
    # Industry Bubble Chart Section
    st.markdown("---")
    
    # Create industry-level aggregation for bubble chart
    if not data_rows:
        st.warning("No data available for bubble chart visualization.")
    else:
        try:
            import altair as alt
            import math
            
            # For filtered stocks, compute count_filtered and mean_filtered per industry
            filtered_industry_metrics = df.groupby('Industry').agg({
                'StockScore': 'mean',
                'Symbol': 'count'
            }).reset_index()
            filtered_industry_metrics.columns = ['Industry', 'mean_filtered', 'count_filtered']
            
            # Compute max_count (use 1 if all zero to avoid div-by-zero)
            max_count = filtered_industry_metrics['count_filtered'].max()
            if max_count == 0:
                max_count = 1
            
            # Create final table with all required metrics
            bubble_data = []
            for industry in filtered_industry_metrics['Industry']:
                # Get metrics from filtered data
                filtered_row = filtered_industry_metrics[filtered_industry_metrics['Industry'] == industry].iloc[0]
                count_filtered = filtered_row['count_filtered']
                mean_filtered = filtered_row['mean_filtered']
                
                # Get industry_mean_all (from unfiltered data)
                industry_mean_all_val = industry_mean_all.get(industry, 0)
                
                # Compute normalized_strength = industry_mean_all * sqrt(count_filtered / max_count)
                normalized_strength = industry_mean_all_val * math.sqrt(count_filtered / max_count)
                
                bubble_data.append({
                    'Industry': industry,
                    'industry_mean_all': round(industry_mean_all_val, 2),
                    'count_filtered': int(count_filtered),
                    'mean_filtered': round(mean_filtered, 2),
                    'normalized_strength': round(normalized_strength, 2)
                })
            
            # Create DataFrame for bubble chart
            bubble_df = pd.DataFrame(bubble_data)
            
            # Validate bubble_df data
            if bubble_df.empty:
                st.warning("No bubble chart data generated.")
            else:
                # Clean the data - ensure no NaN or infinite values
                bubble_df = bubble_df.replace([np.inf, -np.inf], np.nan).dropna()
                
                # Create stock names list for each industry (sorted by StockScore desc)
                industry_stocks = {}
                for industry in bubble_df['Industry']:
                    industry_df = df[df['Industry'] == industry].sort_values('StockScore', ascending=False)
                    stock_list = []
                    for _, row in industry_df.iterrows():
                        stock_list.append(f"{row['Symbol']} ({row['StockScore']:.1f})")
                    industry_stocks[industry] = " | ".join(stock_list[:10])  # Limit to top 10 stocks
                
                # Add stock names to bubble_df
                bubble_df['Top_Stocks'] = bubble_df['Industry'].map(industry_stocks)
            
                # Check if we have valid data for visualization
                if bubble_df.empty:
                    st.warning("No industry data available for bubble chart.")
                else:
                    # Create futuristic bubble chart with advanced styling
                    # Base chart with main bubbles - enhanced for stronger futuristic look
                    base_bubbles = alt.Chart(bubble_df).mark_circle(
                        stroke='#00FFFF',  # Cyan glow effect
                        strokeWidth=6,
                        opacity=1.0,
                        fillOpacity=0.9
                    ).encode(
                        x=alt.X('Industry:N', 
                               title='Industry Sectors',
                               sort='-y',
                               axis=alt.Axis(
                                   labelAngle=-45,
                                   labelFontSize=12,
                                   titleFontSize=14,
                                   grid=False
                               )),
                        y=alt.Y('normalized_strength:Q', 
                               title='Performance Strength',
                               scale=alt.Scale(zero=False, padding=0.15),
                               axis=alt.Axis(
                                   labelFontSize=12,
                                   titleFontSize=14,
                                   grid=True,
                                   gridOpacity=0.3
                               )),
                        size=alt.Size('count_filtered:Q',
                                     scale=alt.Scale(range=[800, 3000], type='sqrt'),
                                     legend=None),
                        color=alt.Color('normalized_strength:Q',
                                       scale=alt.Scale(
                                           range=['#CC0000', '#FF6B00', '#FFAA00', '#FFD700', '#66FF66', '#00CC00', '#008800'],
                                           domain=[bubble_df['normalized_strength'].min(), bubble_df['normalized_strength'].max()]
                                       ),
                                       title='Performance Metrics',
                                       legend=alt.Legend(
                                           orient='right',
                                           titleFontSize=14,
                                           labelFontSize=11
                                       )),
                        tooltip=[
                            alt.Tooltip('Industry:N', title='🏭 Industry Sector'),
                            alt.Tooltip('count_filtered:Q', title='📊 Stock Count', format='.0f'),
                            alt.Tooltip('mean_filtered:Q', title='⚡ Performance Strength', format='.2f'),
                            alt.Tooltip('Top_Stocks:N', title='⭐ Top Performers')
                        ]
                    )
                    
                    # Enhanced outer glow effect layer for stronger futuristic appearance
                    glow_layer = alt.Chart(bubble_df).mark_circle(
                        stroke='#00FFFF',
                        strokeWidth=10,
                        strokeOpacity=0.6,
                        fillOpacity=0.15,
                        fill='#00FFFF'
                    ).encode(
                        x=alt.X('Industry:N', sort='-y'),
                        y=alt.Y('normalized_strength:Q'),
                        size=alt.Size('count_filtered:Q',
                                     scale=alt.Scale(range=[1000, 3500], type='sqrt'),
                                     legend=None)
                    )
                    
                    # Secondary inner glow for enhanced effect
                    secondary_glow = alt.Chart(bubble_df).mark_circle(
                        stroke='#80FFFF',
                        strokeWidth=5,
                        strokeOpacity=0.8,
                        fillOpacity=0.25,
                        fill='#40FFFF'
                    ).encode(
                        x=alt.X('Industry:N', sort='-y'),
                        y=alt.Y('normalized_strength:Q'),
                        size=alt.Size('count_filtered:Q',
                                     scale=alt.Scale(range=[600, 2400], type='sqrt'),
                                     legend=None)
                    )
                    
                    # Inner core highlights
                    core_layer = alt.Chart(bubble_df).mark_circle(
                        stroke='none',
                        fillOpacity=0.9
                    ).encode(
                        x=alt.X('Industry:N', sort='-y'),
                        y=alt.Y('normalized_strength:Q'),
                        size=alt.Size('count_filtered:Q',
                                     scale=alt.Scale(range=[200, 800], type='sqrt'),
                                     legend=None),
                        color=alt.Color('normalized_strength:Q',
                                       scale=alt.Scale(
                                           range=['#FFFFFF', '#FFFF80', '#80FFFF'],
                                           domain=[bubble_df['normalized_strength'].min(), bubble_df['normalized_strength'].max()]
                                       ),
                                       legend=None)
                    )
                    
                    # Combine layers for enhanced futuristic effect
                    bubble_chart = (glow_layer + secondary_glow + base_bubbles + core_layer).resolve_scale(
                        color='independent',
                        size='independent'
                    ).properties(
                        width=1000,
                        height=700,
                        background='#1E1E1E'  # Dark futuristic background
                    )
                    
                    # Display the bubble chart with enhanced spacing
                    st.markdown("")  # Add space before chart
                    st.altair_chart(bubble_chart, use_container_width=True)
                    st.markdown("")  # Add space after chart
                    
                    # Display the data table
                    st.subheader("Industry Performance Metrics")
                    st.dataframe(
                        bubble_df[['Industry', 'industry_mean_all', 'count_filtered', 'mean_filtered', 'normalized_strength']],
                        column_config={
                            "Industry": st.column_config.TextColumn("Industry Sector"),
                            "industry_mean_all": st.column_config.NumberColumn(
                                "Overall Score",
                                format="%.2f",
                                help="Mean performance for all stocks in industry"
                            ),
                            "count_filtered": st.column_config.NumberColumn(
                                "Stock Count",
                                format="%d",
                                help="Number of stocks in industry after applying filters"
                            ),
                            "mean_filtered": st.column_config.NumberColumn(
                                "Performance Strength",
                                format="%.2f", 
                                help="Mean performance for filtered stocks in industry"
                            ),
                            "normalized_strength": st.column_config.NumberColumn(
                                "Strength Index",
                                format="%.2f",
                                help="Normalized performance strength metric"
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Add Group by Index analysis
                    st.markdown("### � Filtered Stocks by Index")
                    
                    # Calculate index distribution for filtered stocks only
                    if data_rows:
                        total_filtered = len(data_rows)
                        
                        # Get index information for filtered symbols
                        filtered_symbols = [row["Symbol"] for row in data_rows]
                        stock_metadata = get_stock_metadata(filtered_symbols)
                        
                        # Use sets to track stocks per index
                        nifty50_stocks = set()
                        nifty100_stocks = set()
                        niftymid150_stocks = set()
                        niftysmall250_stocks = set()
                        
                        # Debug: collect all unique index names to understand the data structure
                        all_index_names = set()
                        
                        for row in data_rows:
                            symbol = row["Symbol"]
                            metadata = stock_metadata.get(symbol, {})
                            index_names = metadata.get("index_names", [])
                            
                            # Add to debug collection
                            all_index_names.update(index_names)
                            
                            # Check each index membership with more precise matching
                            for index_name in index_names:
                                index_clean = index_name.upper().strip().replace(" ", "").replace("-", "").replace("_", "")
                                
                                # More precise matching - look for exact index names
                                if index_clean == 'NIFTY50' or index_clean == 'NIFTY_50':
                                    nifty50_stocks.add(symbol)
                                elif index_clean == 'NIFTY100' or index_clean == 'NIFTY_100':
                                    nifty100_stocks.add(symbol)
                                elif 'NIFTYMIDCAP150' in index_clean or 'NIFTY_MIDCAP_150' in index_clean or (index_clean.startswith('NIFTY') and 'MID' in index_clean and '150' in index_clean):
                                    niftymid150_stocks.add(symbol)
                                elif 'NIFTYSMALLCAP250' in index_clean or 'NIFTY_SMALLCAP_250' in index_clean or (index_clean.startswith('NIFTY') and 'SMALL' in index_clean and '250' in index_clean):
                                    niftysmall250_stocks.add(symbol)
                        
                        # Calculate counts with proper logic:
                        # NIFTY100 should exclude stocks already in NIFTY50 to avoid duplication
                        nifty100_exclusive = nifty100_stocks - nifty50_stocks
                        
                        index_counts = {
                            'NIFTY50': len(nifty50_stocks),
                            'NIFTY100': len(nifty100_exclusive),  # Only NIFTY100 stocks not in NIFTY50
                            'NIFTYMID150': len(niftymid150_stocks),
                            'NIFTYSMALL250': len(niftysmall250_stocks)
                        }
                        
                        # Debug information - show what index names were found
                        with st.expander("🔍 Debug: Index Names Found in Database", expanded=False):
                            st.write("**Unique index names in the database:**")
                            for idx_name in sorted(all_index_names):
                                st.write(f"- `{idx_name}`")
                        
                        # Create display columns
                        col1, col2, col3, col4 = st.columns(4)
                        
                        # Define index display info
                        index_info = {
                            'NIFTY50': {'col': col1, 'icon': '🏆', 'color': '#FFD700'},
                            'NIFTY100': {'col': col2, 'icon': '📈', 'color': '#00FF7F'},
                            'NIFTYMID150': {'col': col3, 'icon': '⚖️', 'color': '#87CEEB'},
                            'NIFTYSMALL250': {'col': col4, 'icon': '💎', 'color': '#FF69B4'}
                        }
                        
                        # Get stock details for each index
                        index_stock_details = {
                            'NIFTY50': [(symbol, next((row['StockScore'] for row in data_rows if row['Symbol'] == symbol), 0)) for symbol in nifty50_stocks],
                            'NIFTY100': [(symbol, next((row['StockScore'] for row in data_rows if row['Symbol'] == symbol), 0)) for symbol in nifty100_exclusive],
                            'NIFTYMID150': [(symbol, next((row['StockScore'] for row in data_rows if row['Symbol'] == symbol), 0)) for symbol in niftymid150_stocks],
                            'NIFTYSMALL250': [(symbol, next((row['StockScore'] for row in data_rows if row['Symbol'] == symbol), 0)) for symbol in niftysmall250_stocks]
                        }
                        
                        # Display each index's statistics with hover details
                        for index_name, info in index_info.items():
                            count = index_counts.get(index_name, 0)
                            percentage = (count / total_filtered * 100) if total_filtered > 0 else 0
                            stock_details = index_stock_details.get(index_name, [])
                            
                            with info['col']:
                                # Create hover tooltip content
                                if stock_details:
                                    # Sort stocks by score (descending)
                                    sorted_stocks = sorted(stock_details, key=lambda x: x[1], reverse=True)
                                    stock_list = ""
                                    for symbol, score in sorted_stocks[:10]:  # Show top 10
                                        stock_list += f"• {symbol}: {score:.2f}\\n"
                                    if len(sorted_stocks) > 10:
                                        stock_list += f"... and {len(sorted_stocks) - 10} more"
                                    
                                    tooltip_text = f"Top stocks in {index_name}:\\n{stock_list}"
                                else:
                                    tooltip_text = f"No stocks found in {index_name}"
                                
                                # Create the card with hover effect
                                st.markdown(f"""
                                <div title="{tooltip_text}" style="
                                    background: linear-gradient(135deg, #1E1E1E 0%, #2D2D2D 100%);
                                    border: 2px solid {info['color']};
                                    border-radius: 10px;
                                    padding: 15px;
                                    text-align: center;
                                    margin: 10px 0;
                                    cursor: pointer;
                                    transition: all 0.3s ease;
                                " onmouseover="this.style.boxShadow='0 0 20px {info['color']}50'; this.style.transform='scale(1.02)'" 
                                  onmouseout="this.style.boxShadow='none'; this.style.transform='scale(1)'">
                                    <h4 style="color: {info['color']}; margin: 0;">
                                        {info['icon']} {index_name}
                                    </h4>
                                    <p style="color: #FFFFFF; font-size: 24px; font-weight: bold; margin: 10px 0;">
                                        {count}
                                    </p>
                                    <p style="color: {info['color']}; font-size: 18px; margin: 0;">
                                        {percentage:.1f}%
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Add expandable section for detailed stock list
                                if count > 0:
                                    with st.expander(f"📋 View {index_name} stocks ({count})", expanded=False):
                                        if stock_details:
                                            sorted_stocks = sorted(stock_details, key=lambda x: x[1], reverse=True)
                                            
                                            # Create a mini dataframe for better display
                                            stock_df = pd.DataFrame(sorted_stocks, columns=['Symbol', 'StockScore'])
                                            stock_df = stock_df.reset_index(drop=True)
                                            stock_df.index += 1  # Start index from 1
                                            
                                            st.dataframe(
                                                stock_df,
                                                column_config={
                                                    "Symbol": st.column_config.TextColumn("Stock Symbol"),
                                                    "StockScore": st.column_config.NumberColumn("Score", format="%.2f")
                                                },
                                                use_container_width=True,
                                                hide_index=False
                                            )
                        
                        # Summary section
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, #0F0F23 0%, #1A1A2E 100%);
                            border: 1px solid #00FFFF;
                            border-radius: 10px;
                            padding: 15px;
                            margin: 20px 0;
                            text-align: center;
                        ">
                            <h5 style="color: #00FFFF; margin: 0;">
                                📊 Total Filtered Stocks: <span style="color: #FFFFFF;">{total_filtered}</span>
                            </h5>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No filtered stocks available for index analysis.")
            
        except Exception as e:
            st.error(f"Error creating bubble chart visualization: {e}")
            logger.error(f"Bubble chart visualization error: {e}")
    
    # Industry Sector Deep Dive Section
    st.markdown("---")
    st.markdown("## 🏭 Industry Sector Analysis")
    st.markdown("### Deep dive into filtered stocks grouped by industry sectors")
    
    if data_rows:
        try:
            # Group stocks by industry
            industry_groups = df.groupby('Industry')
            
            # Calculate comprehensive industry-level metrics
            industry_analysis = []
            for industry, group in industry_groups:
                # Count metrics
                stock_count = len(group)
                
                # Score averages
                avg_stock_score = group['StockScore'].mean()
                avg_truevx = group['TrueVX Score'].mean()
                avg_short = group['Short Mean'].mean()
                avg_mid = group['Mid Mean'].mean()
                avg_long = group['Long Mean'].mean()
                
                # Price ROC averages
                avg_price_roc_22d = group['22-Day ROC (%)'].mean()
                avg_price_roc_66d = group['66-Day ROC (%)'].mean()
                avg_price_roc_222d = group['222-Day ROC (%)'].mean()
                
                # Indicator ROC averages
                avg_truevx_roc = group['TrueVX ROC (22d)'].mean()
                avg_short_roc = group['Short ROC (22d)'].mean()
                avg_mid_roc = group['Mid ROC (22d)'].mean()
                avg_long_roc = group['Long ROC (22d)'].mean()
                avg_score_roc = group['StockScore ROC (22d)'].mean()
                
                # Top performers in this industry
                top_stock = group.nlargest(1, 'StockScore')
                top_stock_name = top_stock['Symbol'].values[0] if len(top_stock) > 0 else 'N/A'
                top_stock_score = top_stock['StockScore'].values[0] if len(top_stock) > 0 else 0
                
                # Best momentum stock (by selected criteria)
                best_momentum_stock = group.nlargest(1, sort_column)
                best_momentum_name = best_momentum_stock['Symbol'].values[0] if len(best_momentum_stock) > 0 else 'N/A'
                best_momentum_value = best_momentum_stock[sort_column].values[0] if len(best_momentum_stock) > 0 else 0
                
                industry_analysis.append({
                    'Industry': industry,
                    'Stock Count': stock_count,
                    'Avg StockScore': round(avg_stock_score, 2),
                    'Avg TrueVX': round(avg_truevx, 2),
                    'Avg Short': round(avg_short, 2),
                    'Avg Mid': round(avg_mid, 2),
                    'Avg Long': round(avg_long, 2),
                    'Avg Price ROC 22d': round(avg_price_roc_22d, 2),
                    'Avg Price ROC 66d': round(avg_price_roc_66d, 2),
                    'Avg Price ROC 222d': round(avg_price_roc_222d, 2),
                    'Avg TrueVX ROC': round(avg_truevx_roc, 2),
                    'Avg Short ROC': round(avg_short_roc, 2),
                    'Avg Mid ROC': round(avg_mid_roc, 2),
                    'Avg Long ROC': round(avg_long_roc, 2),
                    'Avg Score ROC': round(avg_score_roc, 2),
                    'Top Stock': f"{top_stock_name} ({top_stock_score:.1f})",
                    'Best Momentum': f"{best_momentum_name} ({best_momentum_value:.1f}%)"
                })
            
            # Create industry analysis DataFrame
            industry_df = pd.DataFrame(industry_analysis)
            industry_df = industry_df.sort_values('Avg StockScore', ascending=False)
            
            # Display industry summary cards
            st.markdown("#### 📊 Industry Performance Metrics")
            
            # Top 3 industries by average StockScore
            top_3_industries = industry_df.head(3)
            
            col1, col2, col3 = st.columns(3)
            
            for idx, (col, (_, row)) in enumerate(zip([col1, col2, col3], top_3_industries.iterrows())):
                with col:
                    # Medal colors
                    colors = ['#FFD700', '#C0C0C0', '#CD7F32']  # Gold, Silver, Bronze
                    medals = ['🥇', '🥈', '🥉']
                    
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #1E1E1E 0%, #2D2D2D 100%);
                        border: 3px solid {colors[idx]};
                        border-radius: 15px;
                        padding: 20px;
                        text-align: center;
                        box-shadow: 0 0 15px {colors[idx]}50;
                    ">
                        <h2 style="color: {colors[idx]}; margin: 0;">
                            {medals[idx]} #{idx + 1}
                        </h2>
                        <h3 style="color: #FFFFFF; margin: 10px 0;">
                            {row['Industry']}
                        </h3>
                        <p style="color: #00FFFF; font-size: 14px; margin: 5px 0;">
                            📈 Avg Score: <span style="color: #FFFFFF; font-weight: bold;">{row['Avg StockScore']}</span>
                        </p>
                        <p style="color: #FFD700; font-size: 14px; margin: 5px 0;">
                            🔥 Stocks: <span style="color: #FFFFFF; font-weight: bold;">{row['Stock Count']}</span>
                        </p>
                        <p style="color: #90EE90; font-size: 13px; margin: 5px 0;">
                            ⚡ Momentum: <span style="color: #FFFFFF; font-weight: bold;">{row['Avg Score ROC']}%</span>
                        </p>
                        <p style="color: #FFA500; font-size: 12px; margin: 5px 0; font-style: italic;">
                            👑 {row['Top Stock']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("")  # Spacing
            
            # Summary comparison table
            st.markdown("#### 📊 Complete Industry Comparison Table")
            
            # Display the full industry comparison with all metrics
            st.dataframe(
                industry_df,
                column_config={
                    "Industry": st.column_config.TextColumn("Industry Sector", width="medium"),
                    "Stock Count": st.column_config.NumberColumn("Stocks", format="%d"),
                    "Avg StockScore": st.column_config.NumberColumn("Avg Score", format="%.2f"),
                    "Avg TrueVX": st.column_config.NumberColumn("TrueVX", format="%.2f"),
                    "Avg Short": st.column_config.NumberColumn("Short", format="%.2f"),
                    "Avg Mid": st.column_config.NumberColumn("Mid", format="%.2f"),
                    "Avg Long": st.column_config.NumberColumn("Long", format="%.2f"),
                    "Avg Price ROC 22d": st.column_config.NumberColumn("P-ROC 22d", format="%.2f%%"),
                    "Avg Price ROC 66d": st.column_config.NumberColumn("P-ROC 66d", format="%.2f%%"),
                    "Avg Price ROC 222d": st.column_config.NumberColumn("P-ROC 222d", format="%.2f%%"),
                    "Avg TrueVX ROC": st.column_config.NumberColumn("TVX ROC", format="%.2f%%"),
                    "Avg Short ROC": st.column_config.NumberColumn("S-ROC", format="%.2f%%"),
                    "Avg Mid ROC": st.column_config.NumberColumn("M-ROC", format="%.2f%%"),
                    "Avg Long ROC": st.column_config.NumberColumn("L-ROC", format="%.2f%%"),
                    "Avg Score ROC": st.column_config.NumberColumn("Score ROC", format="%.2f%%"),
                    "Top Stock": st.column_config.TextColumn("Best Stock"),
                    "Best Momentum": st.column_config.TextColumn("Best Momentum")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Download industry analysis
            industry_csv = industry_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Industry Analysis CSV",
                data=industry_csv,
                file_name=f"industry_analysis_{criteria_clean}_{current_date}.csv",
                mime="text/csv",
                help="Download the industry-level analysis as a CSV file"
            )
            
        except Exception as e:
            st.error(f"Error creating industry analysis: {e}")
            logger.error(f"Industry analysis error: {e}")
    else:
        st.info("No data available for industry analysis. Please adjust your filters.")
    
    # Industry Heatmap Section
    st.markdown("---")
    st.markdown("## 🔥 Industry Distribution Heatmap")
    st.markdown("### Percentage weightage of each industry in filtered stocks")
    
    if data_rows:
        try:
            # Calculate industry distribution
            industry_counts = df['Industry'].value_counts()
            total_stocks = len(df)
            
            # Calculate percentages
            industry_percentages = (industry_counts / total_stocks * 100).round(2)
            
            # Create heatmap data
            heatmap_data = pd.DataFrame({
                'Industry': industry_percentages.index,
                'Percentage': industry_percentages.values,
                'Stock Count': industry_counts.values
            }).sort_values('Percentage', ascending=False)
            
            # Determine number of rows and columns for grid layout
            total_industries = len(heatmap_data)
            cols_per_row = 5  # 5 industries per row for better visibility
            
            # Create the heatmap grid
            st.markdown("""
            <style>
            .heatmap-grid {
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 15px;
                margin: 20px 0;
            }
            .heatmap-cell {
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                transition: all 0.3s ease;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                border: 2px solid transparent;
            }
            .heatmap-cell:hover {
                transform: scale(1.05);
                box-shadow: 0 8px 12px rgba(0, 0, 0, 0.5);
                border-color: #00d4ff;
            }
            .heatmap-industry {
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 10px;
                word-wrap: break-word;
            }
            .heatmap-percentage {
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;
                margin: 10px 0;
            }
            .heatmap-count {
                font-size: 12px;
                color: #dddddd;
                margin-top: 5px;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Generate color based on percentage
            def get_heatmap_color(percentage):
                """Generate heatmap color from blue (low) to red (high)"""
                if percentage >= 15:
                    # Very high: Dark Red
                    return '#8B0000'
                elif percentage >= 10:
                    # High: Red
                    return '#DC143C'
                elif percentage >= 7:
                    # Medium-High: Orange Red
                    return '#FF4500'
                elif percentage >= 5:
                    # Medium: Orange
                    return '#FF8C00'
                elif percentage >= 3:
                    # Medium-Low: Yellow Orange
                    return '#FFA500'
                elif percentage >= 2:
                    # Low: Light Green
                    return '#32CD32'
                else:
                    # Very Low: Light Blue
                    return '#4169E1'
            
            # Build heatmap HTML using string concatenation
            heatmap_html = '<div class="heatmap-grid">'
            
            for idx, row in heatmap_data.iterrows():
                industry = row['Industry']
                percentage = row['Percentage']
                count = row['Stock Count']
                bg_color = get_heatmap_color(percentage)
                
                heatmap_html += f'<div class="heatmap-cell" style="background: linear-gradient(135deg, {bg_color} 0%, {bg_color}CC 100%);">'
                heatmap_html += f'<div class="heatmap-industry">{industry}</div>'
                heatmap_html += f'<div class="heatmap-percentage">{percentage:.1f}%</div>'
                heatmap_html += f'<div class="heatmap-count">{count} stocks</div>'
                heatmap_html += '</div>'
            
            heatmap_html += '</div>'
            
            st.markdown(heatmap_html, unsafe_allow_html=True)
            
            st.markdown("")  # Spacing
            
            # Interactive industry selection using expandable sections
            st.markdown("#### 🔍 Click on an Industry to View Details")
            
            # Pre-calculate all metrics for color coding comparison
            all_industry_metrics = []
            for idx, row in heatmap_data.iterrows():
                industry = row['Industry']
                industry_stocks = df[df['Industry'] == industry]
                all_industry_metrics.append({
                    'industry': industry,
                    'avg_score': industry_stocks['StockScore'].mean(),
                    'avg_truevx': industry_stocks['TrueVX Score'].mean(),
                    'avg_price_roc': industry_stocks['22-Day ROC (%)'].mean(),
                    'avg_score_roc': industry_stocks['StockScore ROC (22d)'].mean()
                })
            
            # Calculate min/max for color coding
            all_scores = [m['avg_score'] for m in all_industry_metrics]
            all_truevx = [m['avg_truevx'] for m in all_industry_metrics]
            all_price_roc = [m['avg_price_roc'] for m in all_industry_metrics]
            all_score_roc = [m['avg_score_roc'] for m in all_industry_metrics]
            
            min_score, max_score = min(all_scores), max(all_scores)
            min_truevx, max_truevx = min(all_truevx), max(all_truevx)
            min_price_roc, max_price_roc = min(all_price_roc), max(all_price_roc)
            min_score_roc, max_score_roc = min(all_score_roc), max(all_score_roc)
            
            # Helper function to get color for metric value
            def get_metric_color(value, min_val, max_val):
                """Generate color from red (low) to green (high)"""
                if max_val == min_val:
                    return '#888888'  # Gray for no variation
                
                # Normalize to 0-1
                normalized = (value - min_val) / (max_val - min_val)
                
                if normalized >= 0.8:
                    return '#00FF00'  # Bright Green
                elif normalized >= 0.6:
                    return '#7FFF00'  # Light Green
                elif normalized >= 0.4:
                    return '#FFD700'  # Gold
                elif normalized >= 0.2:
                    return '#FFA500'  # Orange
                else:
                    return '#FF4500'  # Red Orange
            
            # Add custom CSS for industry expander headers
            st.markdown("""
            <style>
            .industry-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border-radius: 8px;
                margin: 5px 0;
            }
            .industry-name {
                flex: 1;
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
            }
            .industry-metrics {
                display: flex;
                gap: 15px;
                align-items: center;
            }
            .metric-badge {
                padding: 4px 10px;
                border-radius: 5px;
                font-size: 13px;
                font-weight: 600;
                white-space: nowrap;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Create expandable sections for each industry
            for idx, row in heatmap_data.iterrows():
                industry = row['Industry']
                percentage = row['Percentage']
                count = row['Stock Count']
                bg_color = get_heatmap_color(percentage)
                
                # Get stocks for this industry
                industry_stocks = df[df['Industry'] == industry].sort_values('StockScore', ascending=False)
                
                # Calculate key metrics to display in header
                avg_score = industry_stocks['StockScore'].mean()
                avg_truevx = industry_stocks['TrueVX Score'].mean()
                avg_price_roc = industry_stocks['22-Day ROC (%)'].mean()
                avg_score_roc = industry_stocks['StockScore ROC (22d)'].mean()
                
                # Get colors for each metric
                score_color = get_metric_color(avg_score, min_score, max_score)
                truevx_color = get_metric_color(avg_truevx, min_truevx, max_truevx)
                price_roc_color = get_metric_color(avg_price_roc, min_price_roc, max_price_roc)
                score_roc_color = get_metric_color(avg_score_roc, min_score_roc, max_score_roc)
                
                # Create two-column layout: industry info on left, metrics on right
                header_col1, header_col2 = st.columns([2, 3])
                
                with header_col1:
                    st.markdown(f"### 🏭 {industry}")
                    st.caption(f"{percentage:.1f}% ({count} stocks)")
                
                with header_col2:
                    badge_col1, badge_col2, badge_col3, badge_col4 = st.columns(4)
                    
                    with badge_col1:
                        st.markdown(
                            f'<div style="background-color: {score_color}; color: #000; padding: 8px; '
                            f'border-radius: 5px; text-align: center; font-weight: 600; font-size: 13px;">'
                            f'Score<br>{avg_score:.2f}</div>',
                            unsafe_allow_html=True
                        )
                    
                    with badge_col2:
                        st.markdown(
                            f'<div style="background-color: {truevx_color}; color: #000; padding: 8px; '
                            f'border-radius: 5px; text-align: center; font-weight: 600; font-size: 13px;">'
                            f'TrueVX<br>{avg_truevx:.2f}</div>',
                            unsafe_allow_html=True
                        )
                    
                    with badge_col3:
                        st.markdown(
                            f'<div style="background-color: {price_roc_color}; color: #000; padding: 8px; '
                            f'border-radius: 5px; text-align: center; font-weight: 600; font-size: 13px;">'
                            f'P-ROC<br>{avg_price_roc:+.2f}%</div>',
                            unsafe_allow_html=True
                        )
                    
                    with badge_col4:
                        st.markdown(
                            f'<div style="background-color: {score_roc_color}; color: #000; padding: 8px; '
                            f'border-radius: 5px; text-align: center; font-weight: 600; font-size: 13px;">'
                            f'S-ROC<br>{avg_score_roc:+.2f}%</div>',
                            unsafe_allow_html=True
                        )
                
                # Expander for detailed stock list
                with st.expander("📋 View detailed stock list", expanded=False):
                    # Display key metrics for this industry
                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                    
                    with metric_col1:
                        avg_score = industry_stocks['StockScore'].mean()
                        st.metric("Avg StockScore", f"{avg_score:.2f}")
                    
                    with metric_col2:
                        avg_truevx = industry_stocks['TrueVX Score'].mean()
                        st.metric("Avg TrueVX", f"{avg_truevx:.2f}")
                    
                    with metric_col3:
                        avg_price_roc = industry_stocks['22-Day ROC (%)'].mean()
                        st.metric("Avg Price ROC 22d", f"{avg_price_roc:+.2f}%")
                    
                    with metric_col4:
                        avg_score_roc = industry_stocks['StockScore ROC (22d)'].mean()
                        st.metric("Avg Score ROC", f"{avg_score_roc:+.2f}%")
                    
                    # Display stocks table
                    st.markdown("##### 📋 Stocks in this Industry")
                    
                    # Create a compact view with key metrics
                    display_cols = ['Symbol', 'Name', 'StockScore', 'TrueVX Score', 
                                  '22-Day ROC (%)', 'TrueVX ROC (22d)', 'StockScore ROC (22d)']
                    industry_stocks_display = industry_stocks[display_cols].copy()
                    
                    # Apply styling to this mini table
                    def style_mini_table(row):
                        styles = [''] * len(row)
                        roc_cols_mini = ['22-Day ROC (%)', 'TrueVX ROC (22d)', 'StockScore ROC (22d)']
                        
                        for col in roc_cols_mini:
                            if col in industry_stocks_display.columns:
                                col_idx = industry_stocks_display.columns.get_loc(col)
                                col_values = industry_stocks_display[col].dropna()
                                if len(col_values) > 0:
                                    min_val = col_values.min()
                                    max_val = col_values.max()
                                    styles[col_idx] = get_color_for_value(row[col], min_val, max_val)
                        return styles
                    
                    styled_industry_df = industry_stocks_display.style.apply(style_mini_table, axis=1)
                    
                    st.dataframe(
                        styled_industry_df,
                        column_config={
                            "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                            "Name": st.column_config.TextColumn("Company", width="medium"),
                            "StockScore": st.column_config.NumberColumn("Score", format="%.2f"),
                            "TrueVX Score": st.column_config.NumberColumn("TrueVX", format="%.2f"),
                            "22-Day ROC (%)": st.column_config.NumberColumn("Price ROC", format="%.2f"),
                            "TrueVX ROC (22d)": st.column_config.NumberColumn("TrueVX ROC", format="%.2f"),
                            "StockScore ROC (22d)": st.column_config.NumberColumn("Score ROC", format="%.2f")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
            
            # Summary statistics
            st.markdown("---")
            st.markdown("#### 📈 Distribution Summary")
            
            summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
            
            with summary_col1:
                st.metric(
                    "Total Industries",
                    total_industries,
                    help="Number of different industries in filtered stocks"
                )
            
            with summary_col2:
                top_industry = heatmap_data.iloc[0]['Industry']
                top_percentage = heatmap_data.iloc[0]['Percentage']
                st.metric(
                    "Top Industry",
                    f"{top_percentage:.1f}%",
                    delta=top_industry,
                    help="Industry with highest concentration"
                )
            
            with summary_col3:
                avg_percentage = heatmap_data['Percentage'].mean()
                st.metric(
                    "Average Weight",
                    f"{avg_percentage:.1f}%",
                    help="Average percentage per industry"
                )
            
            with summary_col4:
                # Calculate concentration (% of stocks in top 3 industries)
                top_3_concentration = heatmap_data.head(3)['Percentage'].sum()
                st.metric(
                    "Top 3 Concentration",
                    f"{top_3_concentration:.1f}%",
                    help="Percentage of stocks in top 3 industries"
                )
            
            # Detailed table
            st.markdown("#### 📋 Detailed Distribution Table")
            
            st.dataframe(
                heatmap_data,
                column_config={
                    "Industry": st.column_config.TextColumn("Industry Sector", width="large"),
                    "Percentage": st.column_config.NumberColumn(
                        "Weight (%)",
                        format="%.2f%%",
                        help="Percentage of filtered stocks in this industry"
                    ),
                    "Stock Count": st.column_config.NumberColumn(
                        "Stocks",
                        format="%d",
                        help="Number of stocks in this industry"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Download heatmap data
            heatmap_csv = heatmap_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Industry Distribution CSV",
                data=heatmap_csv,
                file_name=f"industry_distribution_{criteria_clean}_{current_date}.csv",
                mime="text/csv",
                help="Download the industry distribution data as a CSV file"
            )
            
        except Exception as e:
            st.error(f"Error creating industry heatmap: {e}")
            logger.error(f"Industry heatmap error: {e}")
    else:
        st.info("No data available for industry heatmap. Please adjust your filters.")