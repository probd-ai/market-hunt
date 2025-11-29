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
    page_title="Enhanced Stock Screener - Market Hunt",
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
st.title("Enhanced Stock Screener")
st.markdown("### Advanced Range-Based Stock Filtering")

# Explanation of the page
st.info("""
This enhanced screener displays a consolidated view of stocks with their latest indicator scores, current prices, and 20-day rate of change (ROC).
**Key Enhancement**: The Score Filters now support both minimum and maximum ranges for all four parameters, allowing more precise filtering.
Use the filters to narrow down stocks by index, industry, or specific score ranges.
The performance filter lets you select the top N stocks with the highest ROC values.
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
        # Get the current year for the partitioned collection
        current_year = datetime.now().year
        partition_start = (current_year // 5) * 5
        partition_end = partition_start + 4
        collection_name = f"prices_{partition_start}_{partition_end}"
        
        for symbol in symbols:
            # Get the most recent price and the price from 'days' ago
            recent_prices = list(db[collection_name].find(
                {"symbol": symbol},
                sort=[("date", DESCENDING)],
                limit=days+1  # Get one more than needed to ensure we have enough
            ))
            
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
    
    # Calculate 20-day ROC for these symbols
    roc_data = calculate_roc(symbols, days=20)
    
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

# Enhanced Advanced filters with min/max ranges
st.sidebar.subheader("Advanced Filters")
with st.sidebar.expander("🎯 Enhanced Score Filters", expanded=True):
    st.markdown("**Set Min-Max ranges for all parameters:**")
    
    # Get min/max values from the data for better slider initialization
    if indicator_data:
        all_truevx = [data.get("truevx_score", 0) for data in indicator_data.values()]
        all_short = [data.get("mean_short", 0) for data in indicator_data.values()]
        all_mid = [data.get("mean_mid", 0) for data in indicator_data.values()]
        all_long = [data.get("mean_long", 0) for data in indicator_data.values()]
        
        # Calculate actual min/max from data
        truevx_min, truevx_max = int(min(all_truevx)), int(max(all_truevx))
        short_min, short_max = int(min(all_short)), int(max(all_short))
        mid_min, mid_max = int(min(all_mid)), int(max(all_mid))
        long_min, long_max = int(min(all_long)), int(max(all_long))
    else:
        # Fallback values
        truevx_min, truevx_max = 0, 100
        short_min, short_max = 0, 100
        mid_min, mid_max = 0, 100
        long_min, long_max = 0, 100
    
    # TrueVX Score Range
    st.markdown("**🔥 TrueVX Score Range:**")
    truevx_range = st.slider(
        "TrueVX Score (Min - Max)",
        min_value=truevx_min,
        max_value=truevx_max,
        value=(90, truevx_max),
        help="Select the minimum and maximum TrueVX Score range"
    )
    
    # Short Mean Range
    st.markdown("**⚡ Short Mean Range:**")
    short_range = st.slider(
        "Short Mean (Min - Max)",
        min_value=short_min,
        max_value=short_max,
        value=(81, short_max),
        help="Select the minimum and maximum Short Mean range"
    )
    
    # Mid Mean Range
    st.markdown("**🎯 Mid Mean Range:**")
    mid_range = st.slider(
        "Mid Mean (Min - Max)",
        min_value=mid_min,
        max_value=mid_max,
        value=(61, mid_max),
        help="Select the minimum and maximum Mid Mean range"
    )
    
    # Long Mean Range
    st.markdown("**📈 Long Mean Range:**")
    long_range = st.slider(
        "Long Mean (Min - Max)",
        min_value=long_min,
        max_value=long_max,
        value=(50, long_max),
        help="Select the minimum and maximum Long Mean range"
    )
    
with st.sidebar.expander("Performance Filters", expanded=False):
    # Replace min/max ROC with Top N stocks by ROC
    top_n_roc = st.slider(
        "Top N Stocks by ROC", 
        min_value=1,
        max_value=len(symbols) if symbols else 500,
        value=len(symbols) if symbols else 500,
        help="Select top N stocks with highest ROC values"
    )

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
    
# Apply enhanced score filters with min/max ranges
filtered_symbols = [
    s for s in filtered_symbols
    if (s in indicator_data and
        truevx_range[0] <= indicator_data[s].get("truevx_score", 0) <= truevx_range[1] and
        short_range[0] <= indicator_data[s].get("mean_short", 0) <= short_range[1] and
        mid_range[0] <= indicator_data[s].get("mean_mid", 0) <= mid_range[1] and
        long_range[0] <= indicator_data[s].get("mean_long", 0) <= long_range[1])
]

# Apply top N ROC filter
valid_symbols = [s for s in filtered_symbols if s in roc_data and roc_data[s] is not None]
# Sort symbols by ROC in descending order
sorted_by_roc = sorted(valid_symbols, key=lambda s: roc_data.get(s, -float('inf')), reverse=True)
# Take top N symbols based on ROC
filtered_symbols = sorted_by_roc[:top_n_roc]

# Create a DataFrame with StockScore for ALL stocks (before filtering)
all_stock_data = []
for symbol in symbols:
    # Skip if missing data
    if symbol not in indicator_data or symbol not in price_data or symbol not in roc_data:
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
    
    # Calculate StockScore = 0.3*TrueValueX + 0.2*Mean_Short + 0.25*Mean_Mid + 0.25*Mean_Long
    stock_score = (0.3 * truevx_score + 0.2 * mean_short + 0.25 * mean_mid + 0.25 * mean_long)
    
    # Get current price
    current_price = price_data.get(symbol, {}).get("close_price", 0)
    
    # Get 20-day ROC
    roc_20d = roc_data.get(symbol, None)
    
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
        "20-Day ROC (%)": roc_20d
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

# Create DataFrame and sort by ROC in descending order
df = pd.DataFrame(data_rows)
df = df.sort_values(by="20-Day ROC (%)", ascending=False)

# Display enhanced filter summary
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 🎯 **Active Filter Summary**")
    filter_summary = f"""
    **Index:** {selected_index} | **Industry:** {selected_industry}
    
    **Score Ranges Applied:**
    - 🔥 TrueVX: {truevx_range[0]} - {truevx_range[1]}
    - ⚡ Short Mean: {short_range[0]} - {short_range[1]}  
    - 🎯 Mid Mean: {mid_range[0]} - {mid_range[1]}
    - 📈 Long Mean: {long_range[0]} - {long_range[1]}
    """
    st.markdown(filter_summary)
    
with col2:
    st.metric(
        "Filtered Results", 
        f"{len(data_rows)} stocks",
        delta=f"-{len(symbols) - len(data_rows)} from total",
        delta_color="normal"
    )

# Display count of stocks and note about ROC sorting
st.write(f"Displaying {len(data_rows)} stocks")
if top_n_roc < len(symbols):
    st.write(f"Showing top {top_n_roc} stocks by 20-day ROC (sorted in descending order)")
else:
    st.write("Showing all stocks (sorted by 20-day ROC in descending order)")

# Display metrics at the top
if data_rows:
    # Calculate average metrics
    avg_stock_score = df["StockScore"].mean()
    avg_truevx = df["TrueVX Score"].mean()
    avg_short_mean = df["Short Mean"].mean()
    avg_mid_mean = df["Mid Mean"].mean()
    avg_long_mean = df["Long Mean"].mean()
    avg_roc = df["20-Day ROC (%)"].mean()
    
    # Display metrics in columns
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric(
            "Avg StockScore", 
            f"{avg_stock_score:.2f}", 
            delta=None
        )
    
    with col2:
        st.metric(
            "Avg TrueVX Score", 
            f"{avg_truevx:.2f}", 
            delta=None
        )
    
    with col3:
        st.metric(
            "Avg Short Mean", 
            f"{avg_short_mean:.2f}", 
            delta=None
        )
    
    with col4:
        st.metric(
            "Avg Mid Mean", 
            f"{avg_mid_mean:.2f}", 
            delta=None
        )
    
    with col5:
        st.metric(
            "Avg Long Mean", 
            f"{avg_long_mean:.2f}", 
            delta=None
        )
    
    with col6:
        st.metric(
            "Avg 20-Day ROC", 
            f"{avg_roc:.2f}%", 
            delta=None,
            delta_color="normal"
        )

# Display the data as a sortable table
if not data_rows:
    st.warning("No stocks match the selected filters.")
else:
    # Add styling to the table
    st.dataframe(
        df,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol"),
            "Name": st.column_config.TextColumn("Name"),
            "Industry": st.column_config.TextColumn("Industry"),
            "StockScore": st.column_config.NumberColumn(
                "StockScore",
                format="%.2f",
                help="Composite Score: 0.3*TrueVX + 0.2*Short + 0.25*Mid + 0.25*Long"
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
                help="Long-term (66-period) mean"
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
            "20-Day ROC (%)": st.column_config.NumberColumn(
                "20-Day ROC (%)",
                format="%.2f"
            )
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Add download button
    csv = df.to_csv(index=False).encode('utf-8')
    current_date = datetime.now().strftime("%Y%m%d")
    
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name=f"enhanced_stock_screener_{current_date}.csv",
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
                    st.markdown("### 📊 Filtered Stocks by Index")
                    
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