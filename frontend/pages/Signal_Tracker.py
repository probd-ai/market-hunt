import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pymongo
from pymongo import MongoClient, DESCENDING, ASCENDING
import logging
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Signal Tracker - Market Hunt",
    page_icon="🎯",
    layout="wide"
)

# MongoDB connection
@st.cache_resource(ttl=3600)
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

mongo_client = get_mongo_client()

if mongo_client:
    db = mongo_client["market_hunt"]
    logger.info("Connected to 'market_hunt' database")
else:
    st.error("Failed to connect to MongoDB. Please check if MongoDB is running.")
    st.stop()

# Page title with styling
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 30px; border-radius: 15px; margin-bottom: 20px;">
    <h1 style="color: white; text-align: center; margin: 0;">
        🎯 Signal Tracker Dashboard
    </h1>
    <p style="color: #f0f0f0; text-align: center; margin-top: 10px; font-size: 18px;">
        Track Threshold Crossings & Signal Timeline Analysis
    </p>
</div>
""", unsafe_allow_html=True)

# Explanation
st.info("""
**📊 What This Dashboard Does:**

This dashboard tracks when stocks cross critical threshold levels (20, 40, 60, 80) for each indicator:
- **TrueVX Score**
- **Short Mean** (22-period)
- **Mid Mean** (66-period)  
- **Long Mean** (222-period)

Instead of just showing current values, it reveals:
- 📅 **Days Since Crossing**: How many days ago the stock crossed each threshold
- 📈 **Crossing Direction**: Whether it crossed above (bullish) or below (bearish)
- 🎨 **Visual Timeline**: Color-coded heatmaps showing signal freshness
- 📊 **Signal Strength**: Recent crossings = stronger signals
""")

# Utility Functions
@st.cache_data(ttl=3600)
def get_available_indices():
    """Get list of available indices"""
    try:
        indices = []
        cursor = db.index_meta.aggregate([
            {"$group": {"_id": "$index_name", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 10}}},
            {"$sort": {"_id": 1}}
        ])
        for doc in cursor:
            indices.append(doc["_id"])
        return indices if indices else ["NIFTY50", "NIFTY100", "NIFTY500"]
    except Exception as e:
        logger.error(f"Error getting indices: {e}")
        return ["NIFTY50", "NIFTY100", "NIFTY500"]

@st.cache_data(ttl=3600)
def get_available_industries():
    """Get list of available industries"""
    try:
        industries = []
        cursor = db.symbol_mappings.aggregate([
            {"$group": {"_id": "$industry", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$ne": None}}},
            {"$sort": {"_id": 1}}
        ])
        for doc in cursor:
            industries.append(doc["_id"])
        return industries
    except Exception as e:
        logger.error(f"Error getting industries: {e}")
        return []

def get_stocks_by_index(index_name):
    """Get stocks in a specific index"""
    try:
        stocks = []
        cursor = db.index_meta.find({"index_name": index_name}, {"Symbol": 1})
        for doc in cursor:
            stocks.append(doc["Symbol"])
        return stocks
    except Exception as e:
        logger.error(f"Error getting stocks by index: {e}")
        return []

@st.cache_data(ttl=3600)
def get_stock_metadata(symbols=None):
    """Get stock metadata"""
    try:
        metadata = {}
        query = {"symbol": {"$in": symbols}} if symbols else {}
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
        logger.error(f"Error getting metadata: {e}")
        return {}

@st.cache_data(ttl=1800)
def get_historical_indicators(symbols, days_back=90):
    """
    Get historical indicator data for threshold crossing analysis
    
    Args:
        symbols: List of symbols
        days_back: Number of days to look back
        
    Returns:
        Dict mapping symbol -> list of historical records sorted by date (newest first)
    """
    try:
        historical_data = {}
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for symbol in symbols:
            cursor = db.indicators.find(
                {
                    "indicator_type": "truevx",
                    "symbol": symbol,
                    "date": {"$gte": start_date, "$lte": end_date}
                },
                sort=[("date", DESCENDING)]
            )
            
            records = []
            for doc in cursor:
                data = doc.get("data", {})
                records.append({
                    "date": doc["date"],
                    "truevx_score": data.get("truevx_score") or 0,
                    "mean_short": data.get("mean_short") or 0,
                    "mean_mid": data.get("mean_mid") or 0,
                    "mean_long": data.get("mean_long") or 0
                })
            
            # Sort by date (newest first)
            records.sort(key=lambda x: x["date"], reverse=True)
            historical_data[symbol] = records
        
        logger.info(f"Retrieved historical data for {len(historical_data)} stocks")
        return historical_data
        
    except Exception as e:
        logger.error(f"Error getting historical indicators: {e}")
        return {}

def analyze_threshold_crossings(historical_records, thresholds=[20, 40, 60, 80]):
    """
    Analyze when indicators crossed threshold levels
    
    Args:
        historical_records: List of historical indicator records (sorted newest first)
        thresholds: List of threshold levels to check
        
    Returns:
        Dict with crossing analysis for each indicator
    """
    if not historical_records or len(historical_records) < 2:
        return None
    
    indicators = ["truevx_score", "mean_short", "mean_mid", "mean_long"]
    results = {}
    
    for indicator in indicators:
        results[indicator] = {}
        current_value = historical_records[0][indicator]
        
        for threshold in thresholds:
            crossing_info = {
                "days_since_cross": None,
                "direction": None,  # "above" or "below"
                "crossed": False,
                "current_above": current_value >= threshold
            }
            
            # Look back through history to find crossing
            for i in range(len(historical_records) - 1):
                current = historical_records[i][indicator]
                previous = historical_records[i + 1][indicator]
                
                # Check for crossing
                crossed_above = previous < threshold <= current
                crossed_below = previous >= threshold > current
                
                if crossed_above or crossed_below:
                    crossing_info["days_since_cross"] = i
                    crossing_info["direction"] = "above" if crossed_above else "below"
                    crossing_info["crossed"] = True
                    break
            
            results[indicator][threshold] = crossing_info
    
    return results

def get_signal_strength_color(days_since_cross, direction):
    """
    Get color based on signal strength (recent crossings = stronger)
    
    Args:
        days_since_cross: Days since crossing (None if never crossed)
        direction: "above" or "below"
        
    Returns:
        Color code for display
    """
    if days_since_cross is None:
        return "#2b2b2b"  # Dark gray - no recent crossing
    
    if direction == "above":
        # Green gradient - darker = more recent
        if days_since_cross <= 3:
            return "#00ff00"  # Bright green - very recent bullish
        elif days_since_cross <= 7:
            return "#32cd32"  # Medium green
        elif days_since_cross <= 14:
            return "#228b22"  # Forest green
        elif days_since_cross <= 30:
            return "#006400"  # Dark green
        else:
            return "#003300"  # Very dark green - old signal
    else:  # below
        # Red gradient - darker = more recent
        if days_since_cross <= 3:
            return "#ff0000"  # Bright red - very recent bearish
        elif days_since_cross <= 7:
            return "#dc143c"  # Crimson
        elif days_since_cross <= 14:
            return "#8b0000"  # Dark red
        elif days_since_cross <= 30:
            return "#660000"  # Darker red
        else:
            return "#330000"  # Very dark red - old signal

# Sidebar Filters
st.sidebar.title("🎛️ Filters")

# Basic Filters
selected_index = st.sidebar.selectbox(
    "📊 Select Index",
    ["All"] + get_available_indices(),
    index=0
)

selected_industry = st.sidebar.selectbox(
    "🏭 Select Industry",
    ["All"] + get_available_industries(),
    index=0
)

# Threshold Selection
st.sidebar.subheader("🎯 Threshold Configuration")
selected_thresholds = st.sidebar.multiselect(
    "Select Thresholds to Track",
    options=[20, 40, 60, 80],
    default=[40, 60, 80],
    help="Select which threshold levels to analyze for crossings"
)

# Indicator Selection
st.sidebar.subheader("📈 Indicators to Track")
track_truevx = st.sidebar.checkbox("TrueVX Score", value=True)
track_short = st.sidebar.checkbox("Short Mean", value=True)
track_mid = st.sidebar.checkbox("Mid Mean", value=True)
track_long = st.sidebar.checkbox("Long Mean", value=True)

# Lookback Period
lookback_days = st.sidebar.slider(
    "📅 Lookback Period (Days)",
    min_value=30,
    max_value=180,
    value=90,
    step=10,
    help="How far back to search for threshold crossings"
)

# Signal Recency Filter
st.sidebar.subheader("⚡ Signal Recency Filter")
max_days_since_cross = st.sidebar.slider(
    "Max Days Since Crossing",
    min_value=1,
    max_value=90,
    value=30,
    help="Only show stocks that crossed within this many days"
)

crossing_direction_filter = st.sidebar.selectbox(
    "Crossing Direction",
    options=["All", "Above Only (Bullish)", "Below Only (Bearish)"],
    index=0
)

# Load Data
with st.spinner("🔄 Loading stock data and analyzing threshold crossings..."):
    # Get all stocks from indicators
    latest_indicators = list(db.indicators.find(
        {"indicator_type": "truevx"},
        sort=[("date", DESCENDING)],
        limit=1
    ))
    
    if not latest_indicators:
        st.error("No indicator data found!")
        st.stop()
    
    latest_date = latest_indicators[0]["date"]
    
    # Get all symbols for latest date
    all_symbols_cursor = db.indicators.find(
        {"indicator_type": "truevx", "date": latest_date},
        {"symbol": 1}
    )
    symbols = [doc["symbol"] for doc in all_symbols_cursor]
    
    # Apply index filter
    if selected_index != "All":
        index_stocks = get_stocks_by_index(selected_index)
        symbols = [s for s in symbols if s in index_stocks]
    
    # Get metadata for industry filter
    stock_metadata = get_stock_metadata(symbols)
    
    # Apply industry filter
    if selected_industry != "All":
        symbols = [
            s for s in symbols
            if s in stock_metadata and stock_metadata[s].get("industry") == selected_industry
        ]
    
    if not symbols:
        st.warning("No stocks match the selected filters.")
        st.stop()
    
    # Get historical data for threshold analysis
    historical_data = get_historical_indicators(symbols, days_back=lookback_days)
    
    # Analyze threshold crossings for each stock
    st.write(f"📊 Analyzing {len(symbols)} stocks for threshold crossings...")
    
    crossing_analysis = {}
    for symbol in symbols:
        if symbol in historical_data and historical_data[symbol]:
            analysis = analyze_threshold_crossings(
                historical_data[symbol],
                thresholds=selected_thresholds
            )
            if analysis:
                crossing_analysis[symbol] = analysis

# Create results table
st.markdown("---")
st.markdown("## 📋 Threshold Crossing Results")

if not crossing_analysis:
    st.warning("No crossing data available for selected stocks and time period.")
    st.stop()

# Build display data
display_data = []

for symbol, analysis in crossing_analysis.items():
    metadata = stock_metadata.get(symbol, {})
    
    # Get current values (from most recent record)
    current_record = historical_data[symbol][0]
    
    row = {
        "Symbol": symbol,
        "Company": metadata.get("name", symbol),
        "Industry": metadata.get("industry", "Unknown"),
        "Current TrueVX": round(current_record["truevx_score"], 2),
        "Current Short": round(current_record["mean_short"], 2),
        "Current Mid": round(current_record["mean_mid"], 2),
        "Current Long": round(current_record["mean_long"], 2)
    }
    
    # Add crossing data for each indicator and threshold
    indicator_names = {
        "truevx_score": "TrueVX",
        "mean_short": "Short",
        "mean_mid": "Mid",
        "mean_long": "Long"
    }
    
    # Track if stock has any recent crossings (for filtering)
    has_recent_crossing = False
    
    for indicator_key, indicator_label in indicator_names.items():
        # Skip if indicator not selected
        if indicator_key == "truevx_score" and not track_truevx:
            continue
        if indicator_key == "mean_short" and not track_short:
            continue
        if indicator_key == "mean_mid" and not track_mid:
            continue
        if indicator_key == "mean_long" and not track_long:
            continue
        
        for threshold in selected_thresholds:
            crossing_info = analysis[indicator_key][threshold]
            days = crossing_info["days_since_cross"]
            direction = crossing_info["direction"]
            
            # Check for recency filter
            if days is not None and days <= max_days_since_cross:
                # Check direction filter
                if crossing_direction_filter == "All":
                    has_recent_crossing = True
                elif crossing_direction_filter == "Above Only (Bullish)" and direction == "above":
                    has_recent_crossing = True
                elif crossing_direction_filter == "Below Only (Bearish)" and direction == "below":
                    has_recent_crossing = True
            
            col_name = f"{indicator_label}_{threshold}"
            
            if days is None:
                row[col_name] = "No Signal"
                row[f"{col_name}_days"] = 999  # For sorting
                row[f"{col_name}_dir"] = None
            else:
                dir_symbol = "↑" if direction == "above" else "↓"
                row[col_name] = f"{days}d {dir_symbol}"
                row[f"{col_name}_days"] = days
                row[f"{col_name}_dir"] = direction
    
    # Only add if has recent crossing (based on filters)
    if has_recent_crossing:
        display_data.append(row)

if not display_data:
    st.warning(f"No stocks found with crossings in the last {max_days_since_cross} days matching your filters.")
    st.stop()

# Create DataFrame
df = pd.DataFrame(display_data)

# Display count
st.write(f"### 🎯 Found {len(df)} stocks with recent threshold crossings")

# Summary Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_stocks = len(df)
    st.metric("📊 Total Stocks", total_stocks)

with col2:
    # Count stocks with very recent crossings (< 7 days)
    very_recent = sum(
        1 for _, row in df.iterrows()
        if any(
            row.get(f"{ind}_{th}_days", 999) <= 7
            for ind in ["TrueVX", "Short", "Mid", "Long"]
            for th in selected_thresholds
            if f"{ind}_{th}_days" in row
        )
    )
    st.metric("🔥 Hot Signals (<7d)", very_recent)

with col3:
    # Count bullish crossings (above)
    bullish = sum(
        1 for _, row in df.iterrows()
        if any(
            row.get(f"{ind}_{th}_dir") == "above" and row.get(f"{ind}_{th}_days", 999) <= max_days_since_cross
            for ind in ["TrueVX", "Short", "Mid", "Long"]
            for th in selected_thresholds
            if f"{ind}_{th}_dir" in row
        )
    )
    st.metric("📈 Bullish Signals", bullish, delta="Above")

with col4:
    # Count bearish crossings (below)
    bearish = sum(
        1 for _, row in df.iterrows()
        if any(
            row.get(f"{ind}_{th}_dir") == "below" and row.get(f"{ind}_{th}_days", 999) <= max_days_since_cross
            for ind in ["TrueVX", "Short", "Mid", "Long"]
            for th in selected_thresholds
            if f"{ind}_{th}_dir" in row
        )
    )
    st.metric("📉 Bearish Signals", bearish, delta="Below", delta_color="inverse")

# Detailed Table View
st.markdown("---")
st.markdown("## 📊 Detailed Crossing Data")

# Prepare display columns - Always show Current Long, Mid, Short
display_cols = ["Symbol", "Company", "Industry", "Current Long", "Current Mid", "Current Short"]

# Add Current TrueVX if tracked
if track_truevx:
    display_cols.insert(3, "Current TrueVX")  # Add after Industry

# Add crossing columns grouped by threshold (20, 40, 60, 80)
# Each threshold group will have Long, Mid, Short (and TrueVX if tracked)
sorted_thresholds = sorted(selected_thresholds)

for threshold in sorted_thresholds:
    # For each threshold, add columns in order: Long, Mid, Short, TrueVX
    for indicator in ["Long", "Mid", "Short", "TrueVX"]:
        if (indicator == "TrueVX" and track_truevx) or \
           (indicator == "Short" and track_short) or \
           (indicator == "Mid" and track_mid) or \
           (indicator == "Long" and track_long):
            col_name = f"{indicator}_{threshold}"
            if col_name in df.columns:
                display_cols.append(col_name)

# Sort by Current Long (descending - highest first)
df = df.sort_values("Current Long", ascending=False)

# Function to apply color to individual cells
def highlight_crossing_cells(val, col_name):
    """Color code crossing cells based on direction and recency"""
    if col_name not in df.columns:
        return ''
    
    # Check if this is a crossing column
    if any(col_name.startswith(f"{ind}_") for ind in ["TrueVX", "Short", "Mid", "Long"]):
        # Get the corresponding direction and days columns
        days_col = f"{col_name}_days"
        dir_col = f"{col_name}_dir"
        
        # Find the row for this value
        matching_rows = df[df[col_name] == val]
        if len(matching_rows) > 0:
            row = matching_rows.iloc[0]
            
            if days_col in df.columns and dir_col in df.columns:
                days = row.get(days_col, 999)
                direction = row.get(dir_col)
                
                if days < 999 and direction:
                    # Color based on direction and recency
                    if direction == "above":
                        # Green gradient - brighter for more recent
                        if days <= 3:
                            return "background-color: #00ff00; color: black; font-weight: bold"
                        elif days <= 7:
                            return "background-color: #32cd32; color: black; font-weight: bold"
                        elif days <= 14:
                            return "background-color: #228b22; color: white"
                        elif days <= 30:
                            return "background-color: #006400; color: white"
                        else:
                            return "background-color: #003300; color: #aaa"
                    else:  # below
                        # Red gradient - brighter for more recent
                        if days <= 3:
                            return "background-color: #ff0000; color: white; font-weight: bold"
                        elif days <= 7:
                            return "background-color: #dc143c; color: white; font-weight: bold"
                        elif days <= 14:
                            return "background-color: #8b0000; color: white"
                        elif days <= 30:
                            return "background-color: #660000; color: white"
                        else:
                            return "background-color: #330000; color: #aaa"
    
    return ''

# Create styled dataframe using HTML
def create_colored_html_table():
    """Create HTML table with color coding"""
    html = '<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 14px;">'
    
    # Header row
    html += '<thead><tr style="background-color: #1a1a2e; color: white;">'
    for col in display_cols:
        # Format header names
        if "@" in col or "_" in col:
            header = col.replace("_", "@") if any(col.startswith(f"{ind}_") for ind in ["TrueVX", "Short", "Mid", "Long"]) else col
        else:
            header = col
        html += f'<th style="padding: 10px; border: 1px solid #444; text-align: left;">{header}</th>'
    html += '</tr></thead><tbody>'
    
    # Data rows
    for idx, row in df.iterrows():
        html += '<tr style="border-bottom: 1px solid #444;">'
        for col in display_cols:
            value = row.get(col, "")
            
            # Get color styling
            style = "padding: 8px; border: 1px solid #444;"
            
            # Color code Current value columns (0-100 scale)
            if col in ["Current TrueVX", "Current Short", "Current Mid", "Current Long"]:
                try:
                    val = float(value)
                    # Color gradient from red (0) to yellow (50) to green (100)
                    if val >= 80:
                        style += " background-color: #00ff00; color: black; font-weight: bold;"  # Bright green
                    elif val >= 60:
                        style += " background-color: #7fff00; color: black; font-weight: bold;"  # Chartreuse
                    elif val >= 40:
                        style += " background-color: #ffff00; color: black; font-weight: bold;"  # Yellow
                    elif val >= 20:
                        style += " background-color: #ffa500; color: black;"  # Orange
                    else:
                        style += " background-color: #ff4500; color: white;"  # Red-orange
                except (ValueError, TypeError):
                    pass
            
            # Color code crossing columns based on direction and recency
            elif any(col.startswith(f"{ind}_") for ind in ["TrueVX", "Short", "Mid", "Long"]):
                days_col = f"{col}_days"
                dir_col = f"{col}_dir"
                
                if days_col in df.columns and dir_col in df.columns:
                    days = row.get(days_col, 999)
                    direction = row.get(dir_col)
                    
                    if days < 999 and direction:
                        if direction == "above":
                            if days <= 3:
                                style += " background-color: #00ff00; color: black; font-weight: bold;"
                            elif days <= 7:
                                style += " background-color: #32cd32; color: black; font-weight: bold;"
                            elif days <= 14:
                                style += " background-color: #228b22; color: white;"
                            elif days <= 30:
                                style += " background-color: #006400; color: white;"
                            else:
                                style += " background-color: #003300; color: #aaa;"
                        else:  # below
                            if days <= 3:
                                style += " background-color: #ff0000; color: white; font-weight: bold;"
                            elif days <= 7:
                                style += " background-color: #dc143c; color: white; font-weight: bold;"
                            elif days <= 14:
                                style += " background-color: #8b0000; color: white;"
                            elif days <= 30:
                                style += " background-color: #660000; color: white;"
                            else:
                                style += " background-color: #330000; color: #aaa;"
            
            html += f'<td style="{style}">{value}</td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    return html

# Display colored table
st.markdown(create_colored_html_table(), unsafe_allow_html=True)

# Download button
csv_data = df[display_cols].to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Signal Data CSV",
    data=csv_data,
    file_name=f"signal_tracker_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

# Momentum Divergence Ranking
st.markdown("---")
st.markdown("## 🚀 Momentum Divergence Ranking")
st.info("""
**Ranking Methodology:**
- Calculates average baseline from Long, Mid, Short values
- Measures deviation of each timeframe from baseline
- Applies weighted scoring: Short (50%), Mid (30%), Long (20%)
- Higher score = stronger short-term momentum divergence from baseline
""")

# Create ranking dataframe
ranking_df = df.copy()

# Calculate Average baseline
ranking_df['Average'] = (ranking_df['Current Long'] + ranking_df['Current Mid'] + ranking_df['Current Short']) / 3

# Calculate Deviations
ranking_df['DevLong'] = ranking_df['Current Long'] - ranking_df['Average']
ranking_df['DevMid'] = ranking_df['Current Mid'] - ranking_df['Average']
ranking_df['DevShort'] = ranking_df['Current Short'] - ranking_df['Average']

# Calculate weighted Score
ranking_df['Score'] = (0.2 * ranking_df['DevLong'] + 
                       0.3 * ranking_df['DevMid'] + 
                       0.5 * ranking_df['DevShort'])

# Add Rank (1 = strongest)
ranking_df['Rank'] = ranking_df['Score'].rank(ascending=False, method='first').astype(int)

# Sort by Rank
ranking_df = ranking_df.sort_values('Rank')

# Create HTML table for momentum ranking
def create_momentum_ranking_table():
    """Create styled HTML table for momentum ranking"""
    html = '<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 14px;">'
    
    # Header
    html += '<thead><tr style="background-color: #1a1a2e; color: white;">'
    headers = ['Rank', 'Symbol', 'Company', 'Industry', 'Current Long', 'Current Mid', 'Current Short', 
               'Average', 'DevLong', 'DevMid', 'DevShort', 'Score']
    for header in headers:
        html += f'<th style="padding: 10px; border: 1px solid #444; text-align: left;">{header}</th>'
    html += '</tr></thead><tbody>'
    
    # Data rows - show top 100
    for idx, (_, row) in enumerate(ranking_df.head(100).iterrows()):
        html += '<tr style="border-bottom: 1px solid #444;">'
        
        for col in headers:
            if col not in ranking_df.columns:
                continue
                
            value = row[col]
            style = "padding: 8px; border: 1px solid #444;"
            
            # Rank coloring
            if col == 'Rank':
                rank = int(value)
                if rank <= 10:
                    style += " background-color: #ffd700; color: black; font-weight: bold;"  # Gold
                elif rank <= 25:
                    style += " background-color: #c0c0c0; color: black; font-weight: bold;"  # Silver
                elif rank <= 50:
                    style += " background-color: #cd7f32; color: white; font-weight: bold;"  # Bronze
                else:
                    style += " font-weight: bold;"
                value = f"#{rank}"
            
            # Current value coloring (0-100 scale)
            elif col in ['Current Long', 'Current Mid', 'Current Short', 'Average']:
                try:
                    val = float(value)
                    if val >= 80:
                        style += " background-color: #00ff00; color: black; font-weight: bold;"
                    elif val >= 60:
                        style += " background-color: #7fff00; color: black; font-weight: bold;"
                    elif val >= 40:
                        style += " background-color: #ffff00; color: black; font-weight: bold;"
                    elif val >= 20:
                        style += " background-color: #ffa500; color: black;"
                    else:
                        style += " background-color: #ff4500; color: white;"
                    value = f"{val:.2f}"
                except:
                    pass
            
            # Deviation coloring (positive = green, negative = red)
            elif col in ['DevLong', 'DevMid', 'DevShort']:
                try:
                    val = float(value)
                    if val > 5:
                        style += " background-color: #00aa00; color: white; font-weight: bold;"
                    elif val > 0:
                        style += " background-color: #006600; color: white;"
                    elif val < -5:
                        style += " background-color: #aa0000; color: white; font-weight: bold;"
                    elif val < 0:
                        style += " background-color: #660000; color: white;"
                    value = f"{val:+.2f}"
                except:
                    pass
            
            # Score coloring (gradient based on value)
            elif col == 'Score':
                try:
                    val = float(value)
                    if val > 5:
                        style += " background-color: #00ff00; color: black; font-weight: bold;"
                    elif val > 2:
                        style += " background-color: #7fff00; color: black; font-weight: bold;"
                    elif val > 0:
                        style += " background-color: #90ee90; color: black;"
                    elif val > -2:
                        style += " background-color: #ffcccb; color: black;"
                    elif val > -5:
                        style += " background-color: #ff6b6b; color: white;"
                    else:
                        style += " background-color: #ff0000; color: white; font-weight: bold;"
                    value = f"{val:.3f}"
                except:
                    pass
            
            html += f'<td style="{style}">{value}</td>'
        
        html += '</tr>'
    
    html += '</tbody></table></div>'
    return html

# Display ranking table
st.markdown("### 📊 Top 100 Stocks by Momentum Divergence")
st.markdown(create_momentum_ranking_table(), unsafe_allow_html=True)

# Summary statistics
st.markdown("### 📈 Ranking Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    top_score = ranking_df.iloc[0]['Score']
    top_symbol = ranking_df.iloc[0]['Symbol']
    st.metric("🥇 Top Score", f"{top_score:.3f}", delta=top_symbol)

with col2:
    avg_score = ranking_df['Score'].mean()
    st.metric("📊 Average Score", f"{avg_score:.3f}")

with col3:
    positive_count = (ranking_df['Score'] > 0).sum()
    st.metric("✅ Positive Scores", positive_count)

with col4:
    negative_count = (ranking_df['Score'] < 0).sum()
    st.metric("❌ Negative Scores", negative_count)

# Distribution chart
st.markdown("### 📊 Score Distribution")

fig_score = go.Figure()

fig_score.add_trace(go.Histogram(
    x=ranking_df['Score'],
    nbinsx=40,
    marker_color='#667eea',
    name='Score Distribution'
))

fig_score.update_layout(
    title="Distribution of Momentum Divergence Scores",
    xaxis_title="Score",
    yaxis_title="Number of Stocks",
    template="plotly_dark",
    height=400
)

st.plotly_chart(fig_score, use_container_width=True)

# Download ranking
ranking_cols = ['Rank', 'Symbol', 'Company', 'Industry', 'Current Long', 'Current Mid', 'Current Short',
                'Average', 'DevLong', 'DevMid', 'DevShort', 'Score']
ranking_csv = ranking_df[ranking_cols].to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Momentum Ranking CSV",
    data=ranking_csv,
    file_name=f"momentum_ranking_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

# Signal Distribution Analysis
st.markdown("---")
st.markdown("## 📈 Signal Distribution Analysis")

tab1, tab2, tab3 = st.tabs(["📊 By Indicator", "🎯 By Threshold", "🏭 By Industry"])

with tab1:
    st.markdown("### Crossing Distribution by Indicator")
    
    # Count crossings per indicator
    indicator_counts = {}
    for indicator in ["TrueVX", "Short", "Mid", "Long"]:
        if (indicator == "TrueVX" and not track_truevx) or \
           (indicator == "Short" and not track_short) or \
           (indicator == "Mid" and not track_mid) or \
           (indicator == "Long" and not track_long):
            continue
        
        count = 0
        for threshold in selected_thresholds:
            col_name = f"{indicator}_{threshold}_days"
            if col_name in df.columns:
                count += (df[col_name] <= max_days_since_cross).sum()
        
        indicator_counts[indicator] = count
    
    if indicator_counts:
        fig_ind = go.Figure(data=[
            go.Bar(
                x=list(indicator_counts.keys()),
                y=list(indicator_counts.values()),
                marker_color=['#667eea', '#764ba2', '#f093fb', '#4facfe'],
                text=list(indicator_counts.values()),
                textposition='auto'
            )
        ])
        
        fig_ind.update_layout(
            title="Number of Recent Crossings by Indicator",
            xaxis_title="Indicator",
            yaxis_title="Number of Crossings",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig_ind, use_container_width=True)

with tab2:
    st.markdown("### Crossing Distribution by Threshold")
    
    # Count crossings per threshold
    threshold_counts = {}
    for threshold in selected_thresholds:
        count = 0
        for indicator in ["TrueVX", "Short", "Mid", "Long"]:
            col_name = f"{indicator}_{threshold}_days"
            if col_name in df.columns:
                count += (df[col_name] <= max_days_since_cross).sum()
        
        threshold_counts[threshold] = count
    
    if threshold_counts:
        fig_thresh = go.Figure(data=[
            go.Bar(
                x=list(threshold_counts.keys()),
                y=list(threshold_counts.values()),
                marker_color=['#ff6b6b', '#feca57', '#48dbfb', '#1dd1a1'],
                text=list(threshold_counts.values()),
                textposition='auto'
            )
        ])
        
        fig_thresh.update_layout(
            title="Number of Recent Crossings by Threshold Level",
            xaxis_title="Threshold Level",
            yaxis_title="Number of Crossings",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig_thresh, use_container_width=True)

with tab3:
    st.markdown("### 🏭 Detailed Industry Analysis")
    
    # Build comprehensive industry analysis
    industry_analysis = []
    
    for industry in df['Industry'].unique():
        industry_df = df[df['Industry'] == industry]
        total_stocks = len(industry_df)
        
        # Count crossings by direction
        above_count = 0
        below_count = 0
        above_days_list = []
        below_days_list = []
        
        # Analyze all crossing columns
        for _, row in industry_df.iterrows():
            for indicator in ["TrueVX", "Short", "Mid", "Long"]:
                for threshold in selected_thresholds:
                    days_col = f"{indicator}_{threshold}_days"
                    dir_col = f"{indicator}_{threshold}_dir"
                    
                    if days_col in df.columns and dir_col in df.columns:
                        days = row.get(days_col, 999)
                        direction = row.get(dir_col)
                        
                        if days < 999 and direction:
                            if direction == "above":
                                above_count += 1
                                above_days_list.append(days)
                            else:
                                below_count += 1
                                below_days_list.append(days)
        
        # Calculate averages
        avg_above_days = round(np.mean(above_days_list), 1) if above_days_list else 0
        avg_below_days = round(np.mean(below_days_list), 1) if below_days_list else 0
        
        # Calculate percentages (out of total stocks for this industry)
        total_crossings = above_count + below_count
        above_pct = round((above_count / total_crossings * 100), 1) if total_crossings > 0 else 0
        below_pct = round((below_count / total_crossings * 100), 1) if total_crossings > 0 else 0
        
        industry_analysis.append({
            'Industry': industry,
            'Total Stocks': total_stocks,
            'Above Crossings': above_count,
            'Below Crossings': below_count,
            'Above %': above_pct,
            'Below %': below_pct,
            'Avg Days (Above)': avg_above_days,
            'Avg Days (Below)': avg_below_days,
            'Net Signal': above_count - below_count
        })
    
    # Create DataFrame
    industry_df_analysis = pd.DataFrame(industry_analysis)
    industry_df_analysis = industry_df_analysis.sort_values('Total Stocks', ascending=False)
    
    # Display summary cards for top 3 industries
    st.markdown("#### 🎯 Top Industries by Stock Count")
    
    top_3 = industry_df_analysis.head(3)
    col1, col2, col3 = st.columns(3)
    
    for idx, (col, (_, row)) in enumerate(zip([col1, col2, col3], top_3.iterrows())):
        with col:
            medal = ['🥇', '🥈', '🥉'][idx]
            net_signal = row['Net Signal']
            signal_color = '#00ff00' if net_signal > 0 else '#ff0000' if net_signal < 0 else '#888888'
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1E1E1E 0%, #2D2D2D 100%);
                border: 3px solid {signal_color};
                border-radius: 15px;
                padding: 20px;
                text-align: center;
            ">
                <h2 style="color: {signal_color}; margin: 0;">{medal}</h2>
                <h3 style="color: #FFFFFF; margin: 10px 0;">{row['Industry']}</h3>
                <p style="color: #00FFFF; font-size: 14px; margin: 5px 0;">
                    📊 Stocks: <span style="color: #FFFFFF; font-weight: bold;">{row['Total Stocks']}</span>
                </p>
                <p style="color: #90EE90; font-size: 13px; margin: 5px 0;">
                    ↑ Above: <span style="color: #FFFFFF;">{row['Above %']:.1f}%</span> ({row['Above Crossings']} signals, {row['Avg Days (Above)']}d avg)
                </p>
                <p style="color: #FF6B6B; font-size: 13px; margin: 5px 0;">
                    ↓ Below: <span style="color: #FFFFFF;">{row['Below %']:.1f}%</span> ({row['Below Crossings']} signals, {row['Avg Days (Below)']}d avg)
                </p>
                <p style="color: {signal_color}; font-size: 16px; margin: 10px 0; font-weight: bold;">
                    Net: {net_signal:+d}
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("")
    
    # Detailed table
    st.markdown("#### 📊 Complete Industry Breakdown")
    
    st.dataframe(
        industry_df_analysis,
        column_config={
            "Industry": st.column_config.TextColumn("Industry Sector", width="medium"),
            "Total Stocks": st.column_config.NumberColumn("Stocks", format="%d"),
            "Above %": st.column_config.NumberColumn("🟢 Above %", format="%.1f%%", help="Percentage of bullish crossings"),
            "Below %": st.column_config.NumberColumn("🔴 Below %", format="%.1f%%", help="Percentage of bearish crossings"),
            "Above Crossings": st.column_config.NumberColumn("Above Count", format="%d", help="Number of bullish crossings"),
            "Below Crossings": st.column_config.NumberColumn("Below Count", format="%d", help="Number of bearish crossings"),
            "Avg Days (Above)": st.column_config.NumberColumn("Avg Days ↑", format="%.1f", help="Average days since above crossings"),
            "Avg Days (Below)": st.column_config.NumberColumn("Avg Days ↓", format="%.1f", help="Average days since below crossings"),
            "Net Signal": st.column_config.NumberColumn("Net Signal", format="%+d", help="Above crossings - Below crossings")
        },
        hide_index=True,
        use_container_width=True,
        height=400
    )
    
    # Visualization - Bar chart with percentages
    st.markdown("#### 📈 Industry Signal Comparison (% Distribution)")
    
    fig_industry = go.Figure()
    
    # Add above crossings percentage
    fig_industry.add_trace(go.Bar(
        name='Above %',
        x=industry_df_analysis['Industry'],
        y=industry_df_analysis['Above %'],
        marker_color='#00ff00',
        text=industry_df_analysis.apply(lambda row: f"{row['Above %']:.1f}%<br>({row['Above Crossings']})", axis=1),
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>Above: %{y:.1f}%<br>Count: %{customdata}<extra></extra>',
        customdata=industry_df_analysis['Above Crossings']
    ))
    
    # Add below crossings percentage
    fig_industry.add_trace(go.Bar(
        name='Below %',
        x=industry_df_analysis['Industry'],
        y=industry_df_analysis['Below %'],
        marker_color='#ff0000',
        text=industry_df_analysis.apply(lambda row: f"{row['Below %']:.1f}%<br>({row['Below Crossings']})", axis=1),
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>Below: %{y:.1f}%<br>Count: %{customdata}<extra></extra>',
        customdata=industry_df_analysis['Below Crossings']
    ))
    
    fig_industry.update_layout(
        title="Bullish vs Bearish Signal Distribution by Industry (%)",
        xaxis_title="Industry",
        yaxis_title="Percentage (%)",
        barmode='group',
        xaxis_tickangle=-45,
        template="plotly_dark",
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig_industry, use_container_width=True)
    
    # Average days comparison
    st.markdown("#### ⏱️ Average Days Since Crossing by Industry")
    
    fig_days = go.Figure()
    
    fig_days.add_trace(go.Bar(
        name='Avg Days (Above)',
        x=industry_df_analysis['Industry'],
        y=industry_df_analysis['Avg Days (Above)'],
        marker_color='#32cd32',
        text=industry_df_analysis['Avg Days (Above)'].apply(lambda x: f"{x:.1f}d"),
        textposition='auto',
    ))
    
    fig_days.add_trace(go.Bar(
        name='Avg Days (Below)',
        x=industry_df_analysis['Industry'],
        y=industry_df_analysis['Avg Days (Below)'],
        marker_color='#dc143c',
        text=industry_df_analysis['Avg Days (Below)'].apply(lambda x: f"{x:.1f}d"),
        textposition='auto',
    ))
    
    fig_days.update_layout(
        title="Signal Freshness: Average Days Since Crossing",
        xaxis_title="Industry",
        yaxis_title="Average Days",
        barmode='group',
        xaxis_tickangle=-45,
        template="plotly_dark",
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig_days, use_container_width=True)

# Stock Detail View
st.markdown("---")
st.markdown("## 🔍 Individual Stock Analysis")

selected_stock = st.selectbox(
    "Select a stock to view detailed crossing timeline:",
    options=df["Symbol"].tolist(),
    format_func=lambda x: f"{x} - {stock_metadata.get(x, {}).get('name', x)}"
)

if selected_stock and selected_stock in historical_data:
    st.markdown(f"### 📊 {selected_stock} - {stock_metadata.get(selected_stock, {}).get('name', selected_stock)}")
    
    stock_history = historical_data[selected_stock]
    
    # Create time series plot
    dates = [record["date"] for record in reversed(stock_history)]
    
    fig_timeline = make_subplots(
        rows=2, cols=2,
        subplot_titles=("TrueVX Score", "Short Mean", "Mid Mean", "Long Mean"),
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    indicators_plot = [
        ("truevx_score", "TrueVX Score", 1, 1),
        ("mean_short", "Short Mean", 1, 2),
        ("mean_mid", "Mid Mean", 2, 1),
        ("mean_long", "Long Mean", 2, 2)
    ]
    
    for ind_key, ind_name, row, col in indicators_plot:
        values = [record[ind_key] for record in reversed(stock_history)]
        
        # Add main line
        fig_timeline.add_trace(
            go.Scatter(
                x=dates,
                y=values,
                name=ind_name,
                mode='lines',
                line=dict(color='#667eea', width=2),
                showlegend=False
            ),
            row=row, col=col
        )
        
        # Add threshold lines
        for threshold in selected_thresholds:
            fig_timeline.add_hline(
                y=threshold,
                line_dash="dash",
                line_color="rgba(255, 255, 255, 0.3)",
                annotation_text=f"{threshold}",
                annotation_position="right",
                row=row, col=col
            )
    
    fig_timeline.update_layout(
        title=f"Indicator Timeline for {selected_stock}",
        template="plotly_dark",
        height=700,
        showlegend=False
    )
    
    fig_timeline.update_xaxes(title_text="Date")
    fig_timeline.update_yaxes(title_text="Score")
    
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Show crossing details
    if selected_stock in crossing_analysis:
        st.markdown("#### 🎯 Threshold Crossing Details")
        
        crossing_details = []
        analysis = crossing_analysis[selected_stock]
        
        for indicator_key, indicator_label in [
            ("truevx_score", "TrueVX"),
            ("mean_short", "Short Mean"),
            ("mean_mid", "Mid Mean"),
            ("mean_long", "Long Mean")
        ]:
            for threshold in selected_thresholds:
                info = analysis[indicator_key][threshold]
                
                crossing_details.append({
                    "Indicator": indicator_label,
                    "Threshold": threshold,
                    "Days Since Cross": str(info["days_since_cross"]) if info["days_since_cross"] is not None else "No Signal",
                    "Direction": "↑ Above" if info["direction"] == "above" else "↓ Below" if info["direction"] else "—",
                    "Current Above": "✓" if info["current_above"] else "✗"
                })
        
        crossing_df = pd.DataFrame(crossing_details)
        
        st.dataframe(
            crossing_df,
            column_config={
                "Indicator": st.column_config.TextColumn("Indicator"),
                "Threshold": st.column_config.NumberColumn("Threshold Level"),
                "Days Since Cross": st.column_config.TextColumn("Days Since Crossing"),
                "Direction": st.column_config.TextColumn("Cross Direction"),
                "Current Above": st.column_config.TextColumn("Currently Above Threshold")
            },
            hide_index=True,
            use_container_width=True
        )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    <p>🎯 Signal Tracker Dashboard | Market Hunt Analytics</p>
    <p style="font-size: 12px;">Threshold crossing analysis based on historical indicator data</p>
</div>
""", unsafe_allow_html=True)
