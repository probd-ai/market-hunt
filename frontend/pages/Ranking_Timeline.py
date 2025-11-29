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
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Ranking Timeline - Market Hunt",
    page_icon="⏱️",
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
<div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
            padding: 30px; border-radius: 15px; margin-bottom: 20px;">
    <h1 style="color: white; text-align: center; margin: 0;">
        ⏱️ Ranking Timeline Viewer
    </h1>
    <p style="color: #f0f0f0; text-align: center; margin-top: 10px; font-size: 18px;">
        Watch How Stock Rankings Evolve Over Time
    </p>
</div>
""", unsafe_allow_html=True)

# Explanation
st.info("""
**🎬 What This Dashboard Does:**

This time-lapse viewer shows how stock rankings change over time based on **Momentum Divergence Scoring**:
- 🎯 **Select Date Range**: Choose your analysis period (from/to dates)
- ▶️ **Play Time-lapse**: Watch rankings evolve day-by-day
- 📊 **Track Movement**: See which stocks climb or fall in rankings
- 🎨 **Visual Highlights**: Color-coded ranking changes (gainers/losers)
- 📈 **Statistics**: Daily ranking volatility and momentum shifts
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
def get_indicators_for_date(symbols, target_date):
    """
    Get indicator data for a specific date
    
    Args:
        symbols: List of symbols
        target_date: Target date
        
    Returns:
        DataFrame with indicator values for that date
    """
    try:
        data_list = []
        
        # Query for specific date
        for symbol in symbols:
            doc = db.indicators.find_one(
                {
                    "indicator_type": "truevx",
                    "symbol": symbol,
                    "date": {"$lte": target_date}
                },
                sort=[("date", DESCENDING)]
            )
            
            if doc:
                indicator_data = doc.get("data", {})
                data_list.append({
                    "symbol": symbol,
                    "date": doc["date"],
                    "truevx_score": indicator_data.get("truevx_score") or 0,
                    "mean_short": indicator_data.get("mean_short") or 0,
                    "mean_mid": indicator_data.get("mean_mid") or 0,
                    "mean_long": indicator_data.get("mean_long") or 0
                })
        
        if not data_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(data_list)
        return df
        
    except Exception as e:
        logger.error(f"Error getting indicators for date {target_date}: {e}")
        return pd.DataFrame()

def calculate_ranking_for_date(df, metadata):
    """
    Calculate momentum divergence ranking for a specific date
    
    Args:
        df: DataFrame with indicator values
        metadata: Stock metadata dict
        
    Returns:
        DataFrame with rankings
    """
    if df.empty:
        return pd.DataFrame()
    
    # Add company name
    df['company'] = df['symbol'].map(lambda x: metadata.get(x, {}).get('name', x))
    df['industry'] = df['symbol'].map(lambda x: metadata.get(x, {}).get('industry', 'Unknown'))
    
    # Calculate Average baseline
    df['average'] = (df['mean_long'] + df['mean_mid'] + df['mean_short']) / 3
    
    # Calculate Deviations
    df['dev_long'] = df['mean_long'] - df['average']
    df['dev_mid'] = df['mean_mid'] - df['average']
    df['dev_short'] = df['mean_short'] - df['average']
    
    # Calculate weighted Score
    df['score'] = (0.2 * df['dev_long'] + 
                   0.3 * df['dev_mid'] + 
                   0.5 * df['dev_short'])
    
    # Add Rank (1 = strongest)
    df['rank'] = df['score'].rank(ascending=False, method='first').astype(int)
    
    # Sort by Rank
    df = df.sort_values('rank')
    
    return df

@st.cache_data(ttl=1800)
def get_ranking_timeline(symbols, start_date, end_date, metadata):
    """
    Get rankings for each day in the date range
    
    Args:
        symbols: List of symbols
        start_date: Start date
        end_date: End date
        metadata: Stock metadata dict
        
    Returns:
        Dict mapping date -> ranking DataFrame
    """
    timeline = {}
    current_date = start_date
    
    with st.spinner(f"Loading rankings from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}..."):
        progress_bar = st.progress(0)
        total_days = (end_date - start_date).days + 1
        day_count = 0
        
        while current_date <= end_date:
            # Get indicators for this date
            df = get_indicators_for_date(symbols, current_date)
            
            if not df.empty:
                # Calculate rankings
                ranking_df = calculate_ranking_for_date(df, metadata)
                timeline[current_date] = ranking_df
            
            current_date += timedelta(days=1)
            day_count += 1
            progress_bar.progress(day_count / total_days)
        
        progress_bar.empty()
    
    logger.info(f"Retrieved rankings for {len(timeline)} dates")
    return timeline

def create_ranking_table_html(df, prev_df=None, show_top_n=50):
    """
    Create HTML table showing rankings with movement indicators
    
    Args:
        df: Current ranking DataFrame
        prev_df: Previous ranking DataFrame (to show movement)
        show_top_n: Number of top stocks to show
        
    Returns:
        HTML string
    """
    if df.empty:
        return "<p>No data available</p>"
    
    # Create rank change mapping if previous data exists
    rank_changes = {}
    if prev_df is not None and not prev_df.empty:
        prev_ranks = dict(zip(prev_df['symbol'], prev_df['rank']))
        for _, row in df.iterrows():
            symbol = row['symbol']
            current_rank = row['rank']
            if symbol in prev_ranks:
                prev_rank = prev_ranks[symbol]
                rank_changes[symbol] = prev_rank - current_rank  # Positive = moved up
    
    html = '<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 14px;">'
    
    # Header
    html += '<thead><tr style="background-color: #1a1a2e; color: white;">'
    headers = ['Rank', 'Movement', 'Symbol', 'Company', 'Long', 'Mid', 'Short', 'Score']
    for header in headers:
        html += f'<th style="padding: 10px; border: 1px solid #444; text-align: left;">{header}</th>'
    html += '</tr></thead><tbody>'
    
    # Data rows
    for idx, (_, row) in enumerate(df.head(show_top_n).iterrows()):
        html += '<tr style="border-bottom: 1px solid #444;">'
        
        symbol = row['symbol']
        rank = int(row['rank'])
        
        # Rank column
        rank_style = "padding: 8px; border: 1px solid #444; font-weight: bold;"
        if rank <= 10:
            rank_style += " background-color: #ffd700; color: black;"  # Gold
        elif rank <= 25:
            rank_style += " background-color: #c0c0c0; color: black;"  # Silver
        elif rank <= 50:
            rank_style += " background-color: #cd7f32; color: white;"  # Bronze
        html += f'<td style="{rank_style}">#{rank}</td>'
        
        # Movement column
        movement_style = "padding: 8px; border: 1px solid #444; text-align: center; font-weight: bold;"
        movement_text = "-"
        if symbol in rank_changes:
            change = rank_changes[symbol]
            if change > 0:
                movement_style += " background-color: #00aa00; color: white;"
                movement_text = f"↑ {change}"
            elif change < 0:
                movement_style += " background-color: #aa0000; color: white;"
                movement_text = f"↓ {abs(change)}"
            else:
                movement_style += " color: #888;"
                movement_text = "="
        html += f'<td style="{movement_style}">{movement_text}</td>'
        
        # Symbol
        html += f'<td style="padding: 8px; border: 1px solid #444; font-weight: bold;">{symbol}</td>'
        
        # Company
        company = row['company']
        html += f'<td style="padding: 8px; border: 1px solid #444;">{company}</td>'
        
        # Long, Mid, Short with color coding
        for col in ['mean_long', 'mean_mid', 'mean_short']:
            val = row[col]
            cell_style = "padding: 8px; border: 1px solid #444;"
            
            if val >= 80:
                cell_style += " background-color: #00ff00; color: black; font-weight: bold;"
            elif val >= 60:
                cell_style += " background-color: #7fff00; color: black; font-weight: bold;"
            elif val >= 40:
                cell_style += " background-color: #ffff00; color: black; font-weight: bold;"
            elif val >= 20:
                cell_style += " background-color: #ffa500; color: black;"
            else:
                cell_style += " background-color: #ff4500; color: white;"
            
            html += f'<td style="{cell_style}">{val:.2f}</td>'
        
        # Score
        score = row['score']
        score_style = "padding: 8px; border: 1px solid #444;"
        if score > 5:
            score_style += " background-color: #00ff00; color: black; font-weight: bold;"
        elif score > 2:
            score_style += " background-color: #7fff00; color: black; font-weight: bold;"
        elif score > 0:
            score_style += " background-color: #90ee90; color: black;"
        elif score > -2:
            score_style += " background-color: #ffcccb; color: black;"
        elif score > -5:
            score_style += " background-color: #ff6b6b; color: white;"
        else:
            score_style += " background-color: #ff0000; color: white; font-weight: bold;"
        
        html += f'<td style="{score_style}">{score:.3f}</td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    return html

# Sidebar filters
st.sidebar.header("📊 Timeline Filters")

# Index selection
available_indices = get_available_indices()
selected_index = st.sidebar.selectbox(
    "Select Index",
    options=available_indices,
    index=available_indices.index("NIFTY50") if "NIFTY50" in available_indices else 0
)

# Date range selection
st.sidebar.markdown("### 📅 Date Range")

col1, col2 = st.sidebar.columns(2)

# Default: last 30 days
default_end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
default_start = default_end - timedelta(days=30)

with col1:
    start_date = st.date_input(
        "From Date",
        value=default_start,
        max_value=datetime.now()
    )

with col2:
    end_date = st.date_input(
        "To Date",
        value=default_end,
        max_value=datetime.now()
    )

# Convert to datetime
start_date = datetime.combine(start_date, datetime.min.time())
end_date = datetime.combine(end_date, datetime.min.time())

# Validate date range
if start_date >= end_date:
    st.error("❌ Start date must be before end date!")
    st.stop()

# Display options
st.sidebar.markdown("### 🎨 Display Options")

show_top_n = st.sidebar.slider(
    "Show Top N Stocks",
    min_value=10,
    max_value=100,
    value=50,
    step=10
)

playback_speed = st.sidebar.slider(
    "Playback Speed (seconds per frame)",
    min_value=0.1,
    max_value=2.0,
    value=0.5,
    step=0.1
)

# Load data
st.markdown("---")
st.markdown("## 📊 Data Loading")

# Get stocks for selected index
stocks = get_stocks_by_index(selected_index)
if not stocks:
    st.error(f"No stocks found for index {selected_index}")
    st.stop()

st.success(f"✅ Found {len(stocks)} stocks in {selected_index}")

# Get metadata
metadata = get_stock_metadata(stocks)

# Get ranking timeline
timeline = get_ranking_timeline(stocks, start_date, end_date, metadata)

if not timeline:
    st.warning("⚠️ No data available for the selected date range")
    st.stop()

st.success(f"✅ Loaded rankings for {len(timeline)} trading days")

# Timeline player
st.markdown("---")
st.markdown("## ⏯️ Timeline Player")

# Control buttons
col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

with col1:
    play_button = st.button("▶️ Play", use_container_width=True)

with col2:
    pause_button = st.button("⏸️ Pause", use_container_width=True)

with col3:
    reset_button = st.button("⏮️ Reset", use_container_width=True)

# Initialize session state
if 'timeline_index' not in st.session_state:
    st.session_state.timeline_index = 0

if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False

# Handle button clicks
if reset_button:
    st.session_state.timeline_index = 0
    st.session_state.is_playing = False

if play_button:
    st.session_state.is_playing = True

if pause_button:
    st.session_state.is_playing = False

# Timeline slider
timeline_dates = sorted(timeline.keys())
max_index = len(timeline_dates) - 1

timeline_index = st.slider(
    "Select Date",
    min_value=0,
    max_value=max_index,
    value=st.session_state.timeline_index,
    format=""
)

st.session_state.timeline_index = timeline_index

# Display current date
current_date = timeline_dates[timeline_index]
st.markdown(f"### 📅 Viewing: **{current_date.strftime('%A, %B %d, %Y')}**")

# Get current and previous data
current_df = timeline[current_date]
prev_df = None
if timeline_index > 0:
    prev_date = timeline_dates[timeline_index - 1]
    prev_df = timeline[prev_date]

# Display ranking table
st.markdown("### 🏆 Rankings")
st.markdown(create_ranking_table_html(current_df, prev_df, show_top_n), unsafe_allow_html=True)

# Statistics
st.markdown("---")
st.markdown("### 📊 Daily Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    top_score = current_df.iloc[0]['score']
    top_symbol = current_df.iloc[0]['symbol']
    st.metric("🥇 Top Score", f"{top_score:.3f}", delta=top_symbol)

with col2:
    avg_score = current_df['score'].mean()
    st.metric("📊 Average Score", f"{avg_score:.3f}")

with col3:
    positive_count = (current_df['score'] > 0).sum()
    st.metric("✅ Positive Scores", positive_count)

with col4:
    if prev_df is not None:
        # Calculate ranking volatility
        rank_changes_count = sum(1 for s in current_df['symbol'] if s in prev_df['symbol'].values)
        st.metric("🔄 Tracked Stocks", rank_changes_count)
    else:
        st.metric("🔄 Tracked Stocks", len(current_df))

# Movement analysis
if prev_df is not None and not prev_df.empty:
    st.markdown("---")
    st.markdown("### 📈 Movement Analysis")
    
    # Calculate movements
    prev_ranks = dict(zip(prev_df['symbol'], prev_df['rank']))
    movements = []
    
    for _, row in current_df.iterrows():
        symbol = row['symbol']
        current_rank = row['rank']
        if symbol in prev_ranks:
            prev_rank = prev_ranks[symbol]
            change = prev_rank - current_rank
            if change != 0:
                movements.append({
                    'symbol': symbol,
                    'company': row['company'],
                    'current_rank': current_rank,
                    'prev_rank': prev_rank,
                    'change': change
                })
    
    if movements:
        movements_df = pd.DataFrame(movements)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top gainers
            st.markdown("#### 🚀 Top Gainers")
            gainers = movements_df[movements_df['change'] > 0].nlargest(10, 'change')
            if not gainers.empty:
                for _, row in gainers.iterrows():
                    st.markdown(f"**{row['symbol']}** ({row['company'][:30]}): #{row['prev_rank']} → #{row['current_rank']} 🔥 +{row['change']}")
            else:
                st.info("No gainers today")
        
        with col2:
            # Top losers
            st.markdown("#### 📉 Top Losers")
            losers = movements_df[movements_df['change'] < 0].nsmallest(10, 'change')
            if not losers.empty:
                for _, row in losers.iterrows():
                    st.markdown(f"**{row['symbol']}** ({row['company'][:30]}): #{row['prev_rank']} → #{row['current_rank']} ❄️ {row['change']}")
            else:
                st.info("No losers today")

# Auto-play functionality
if st.session_state.is_playing:
    if st.session_state.timeline_index < max_index:
        time.sleep(playback_speed)
        st.session_state.timeline_index += 1
        st.rerun()
    else:
        st.session_state.is_playing = False
        st.success("✅ Timeline playback completed!")

# Top Rank Persistence Analysis
st.markdown("---")
st.markdown("## 🎯 Top Rank Persistence Analysis")

st.info("""
**📊 Understanding Ranking Stability:**

This analysis shows how long stocks **stay in top rankings** after appearing there:
- Pick top N stocks on each date
- Track how many days they remain in top 10, 15, 20 ranges
- Helps identify **consistent winners** vs **flash-in-the-pan** stocks
""")

# Analysis parameters
col1, col2, col3 = st.columns(3)

with col1:
    initial_top_n = st.selectbox(
        "Initial Selection (Top N)",
        options=[3, 5, 10, 15, 20],
        index=1  # Default: Top 5
    )

with col2:
    track_ranges = st.multiselect(
        "Track Persistence in Ranges",
        options=[5, 10, 15, 20, 25, 30],
        default=[10, 15, 20]
    )

with col3:
    min_days_required = st.slider(
        "Minimum Days to Analyze",
        min_value=3,
        max_value=min(30, len(timeline_dates)),
        value=min(7, len(timeline_dates))
    )

if track_ranges and len(timeline_dates) >= min_days_required:
    
    @st.cache_data(ttl=1800)
    def analyze_ranking_persistence(timeline_dict, timeline_dates_list, top_n, ranges, min_days):
        """
        Analyze how long top-N stocks persist in various ranking ranges
        
        Args:
            timeline_dict: Dict mapping date -> ranking DataFrame
            timeline_dates_list: Sorted list of dates
            top_n: Number of top stocks to track from each date
            ranges: List of ranking ranges to track (e.g., [10, 15, 20])
            min_days: Minimum days required after selection to track
            
        Returns:
            DataFrame with persistence statistics
        """
        persistence_records = []
        
        # For each date (except last min_days)
        for i in range(len(timeline_dates_list) - min_days):
            selection_date = timeline_dates_list[i]
            selection_df = timeline_dict[selection_date]
            
            # Get top N stocks on this date
            top_stocks = selection_df.head(top_n)['symbol'].tolist()
            
            # Track each stock's persistence
            for stock in top_stocks:
                stock_data = selection_df[selection_df['symbol'] == stock].iloc[0]
                initial_rank = int(stock_data['rank'])
                
                # Initialize persistence counters for each range
                persistence_days = {range_val: 0 for range_val in ranges}
                consecutive_days = {range_val: 0 for range_val in ranges}
                max_consecutive = {range_val: 0 for range_val in ranges}
                
                # Look forward in time
                for j in range(i + 1, len(timeline_dates_list)):
                    future_date = timeline_dates_list[j]
                    future_df = timeline_dict[future_date]
                    
                    # Find this stock in future ranking
                    stock_future = future_df[future_df['symbol'] == stock]
                    
                    if not stock_future.empty:
                        future_rank = int(stock_future.iloc[0]['rank'])
                        
                        # Check each range
                        for range_val in ranges:
                            if future_rank <= range_val:
                                persistence_days[range_val] += 1
                                consecutive_days[range_val] += 1
                                max_consecutive[range_val] = max(max_consecutive[range_val], consecutive_days[range_val])
                            else:
                                consecutive_days[range_val] = 0
                    else:
                        # Stock not in rankings (broke persistence)
                        for range_val in ranges:
                            consecutive_days[range_val] = 0
                
                # Days available for tracking
                days_available = len(timeline_dates_list) - i - 1
                
                # Record persistence data
                record = {
                    'selection_date': selection_date,
                    'symbol': stock,
                    'company': stock_data['company'],
                    'initial_rank': initial_rank,
                    'days_tracked': days_available
                }
                
                for range_val in ranges:
                    record[f'days_in_top_{range_val}'] = persistence_days[range_val]
                    record[f'pct_in_top_{range_val}'] = (persistence_days[range_val] / days_available * 100) if days_available > 0 else 0
                    record[f'max_consecutive_top_{range_val}'] = max_consecutive[range_val]
                
                persistence_records.append(record)
        
        return pd.DataFrame(persistence_records)
    
    # Run analysis
    with st.spinner("🔍 Analyzing ranking persistence..."):
        persistence_df = analyze_ranking_persistence(
            timeline, 
            timeline_dates, 
            initial_top_n, 
            sorted(track_ranges),
            min_days_required
        )
    
    if not persistence_df.empty:
        st.success(f"✅ Analyzed {len(persistence_df)} stock selections across {len(timeline_dates)} dates")
        
        # Overall Statistics
        st.markdown("### 📊 Overall Persistence Statistics")
        st.markdown(f"**Analysis:** Top {initial_top_n} stocks selected on each date")
        
        # Create summary metrics
        metric_cols = st.columns(len(track_ranges))
        
        for idx, range_val in enumerate(sorted(track_ranges)):
            with metric_cols[idx]:
                avg_days = persistence_df[f'days_in_top_{range_val}'].mean()
                avg_pct = persistence_df[f'pct_in_top_{range_val}'].mean()
                avg_consecutive = persistence_df[f'max_consecutive_top_{range_val}'].mean()
                
                st.metric(
                    f"📍 Top {range_val} Range",
                    f"{avg_days:.1f} days",
                    delta=f"{avg_pct:.1f}% retention"
                )
                st.caption(f"Avg max streak: {avg_consecutive:.1f} days")
        
        # Detailed breakdown by stock
        st.markdown("---")
        st.markdown("### 🏆 Top Performing Stocks (by persistence)")
        
        # Calculate composite persistence score
        score_components = [f'pct_in_top_{r}' for r in sorted(track_ranges)]
        persistence_df['composite_score'] = persistence_df[score_components].mean(axis=1)
        
        # Group by stock and calculate averages
        stock_summary = persistence_df.groupby(['symbol', 'company']).agg({
            'initial_rank': 'mean',
            'days_tracked': 'mean',
            'composite_score': 'mean',
            **{f'days_in_top_{r}': 'mean' for r in sorted(track_ranges)},
            **{f'pct_in_top_{r}': 'mean' for r in sorted(track_ranges)},
            **{f'max_consecutive_top_{r}': 'mean' for r in sorted(track_ranges)}
        }).reset_index()
        
        # Sort by composite score
        stock_summary = stock_summary.sort_values('composite_score', ascending=False)
        
        # Display top stocks table
        st.markdown("#### 🌟 Most Persistent Stocks")
        
        # Create display DataFrame
        display_cols = ['symbol', 'company', 'initial_rank', 'composite_score']
        for range_val in sorted(track_ranges):
            display_cols.extend([
                f'days_in_top_{range_val}',
                f'pct_in_top_{range_val}',
                f'max_consecutive_top_{range_val}'
            ])
        
        top_persistent = stock_summary.head(20).copy()
        top_persistent['initial_rank'] = top_persistent['initial_rank'].round(1)
        top_persistent['composite_score'] = top_persistent['composite_score'].round(1)
        
        for range_val in sorted(track_ranges):
            top_persistent[f'days_in_top_{range_val}'] = top_persistent[f'days_in_top_{range_val}'].round(1)
            top_persistent[f'pct_in_top_{range_val}'] = top_persistent[f'pct_in_top_{range_val}'].round(1)
            top_persistent[f'max_consecutive_top_{range_val}'] = top_persistent[f'max_consecutive_top_{range_val}'].round(1)
        
        # Rename columns for display
        rename_dict = {
            'symbol': 'Symbol',
            'company': 'Company',
            'initial_rank': 'Avg Initial Rank',
            'composite_score': 'Persistence Score'
        }
        
        for range_val in sorted(track_ranges):
            rename_dict[f'days_in_top_{range_val}'] = f'Days in Top{range_val}'
            rename_dict[f'pct_in_top_{range_val}'] = f'% in Top{range_val}'
            rename_dict[f'max_consecutive_top_{range_val}'] = f'Max Streak (Top{range_val})'
        
        display_df = top_persistent[display_cols].rename(columns=rename_dict)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600
        )
        
        # Visualization: Persistence comparison
        st.markdown("---")
        st.markdown("### 📊 Persistence Visualization")
        
        # Box plot showing distribution of persistence across ranges
        fig_persistence = go.Figure()
        
        for range_val in sorted(track_ranges):
            fig_persistence.add_trace(go.Box(
                y=persistence_df[f'pct_in_top_{range_val}'],
                name=f'Top {range_val}',
                marker_color=f'rgb({50 + range_val * 3}, {150 - range_val * 2}, {200})'
            ))
        
        fig_persistence.update_layout(
            title=f"Distribution of Persistence (% days in range) - Top {initial_top_n} Stocks",
            yaxis_title="Percentage of Days in Range (%)",
            xaxis_title="Ranking Range",
            template="plotly_dark",
            height=500,
            showlegend=True
        )
        
        st.plotly_chart(fig_persistence, use_container_width=True)
        
        # Top stocks persistence chart
        st.markdown("#### 📈 Top 10 Most Persistent Stocks")
        
        fig_top_stocks = go.Figure()
        
        top_10_stocks = stock_summary.head(10)
        
        for range_val in sorted(track_ranges):
            fig_top_stocks.add_trace(go.Bar(
                name=f'Top {range_val}',
                x=top_10_stocks['symbol'],
                y=top_10_stocks[f'pct_in_top_{range_val}'],
                text=top_10_stocks[f'pct_in_top_{range_val}'].round(1),
                textposition='auto',
            ))
        
        fig_top_stocks.update_layout(
            title="Persistence Comparison Across Ranking Ranges",
            xaxis_title="Stock Symbol",
            yaxis_title="Percentage of Days in Range (%)",
            barmode='group',
            template="plotly_dark",
            height=500,
            showlegend=True
        )
        
        st.plotly_chart(fig_top_stocks, use_container_width=True)
        
        # Key insights
        st.markdown("---")
        st.markdown("### 💡 Key Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏅 Best Performers")
            best_stock = stock_summary.iloc[0]
            st.success(f"""
            **{best_stock['symbol']}** ({best_stock['company']})
            - Persistence Score: {best_stock['composite_score']:.1f}%
            - Avg Initial Rank: #{best_stock['initial_rank']:.1f}
            """)
            
            for range_val in sorted(track_ranges):
                pct = best_stock[f'pct_in_top_{range_val}']
                days = best_stock[f'days_in_top_{range_val}']
                st.write(f"• Top {range_val}: {pct:.1f}% ({days:.1f} days avg)")
        
        with col2:
            st.markdown("#### 📉 Volatility Indicator")
            avg_top_range = sorted(track_ranges)[0]
            volatility = persistence_df[f'pct_in_top_{avg_top_range}'].std()
            
            if volatility < 20:
                stability = "🟢 High Stability"
                message = "Top stocks tend to remain stable"
            elif volatility < 40:
                stability = "🟡 Moderate Stability"
                message = "Some movement in rankings"
            else:
                stability = "🔴 High Volatility"
                message = "Rankings change frequently"
            
            st.info(f"""
            **{stability}**
            
            Standard Deviation: {volatility:.1f}%
            
            {message}
            """)
        
        # Download persistence data
        st.markdown("---")
        persistence_csv = persistence_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Persistence Analysis CSV",
            data=persistence_csv,
            file_name=f"ranking_persistence_top{initial_top_n}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ Not enough data for persistence analysis")
else:
    st.info("👆 Select tracking ranges and ensure sufficient days in timeline")

# Download timeline data
st.markdown("---")
st.markdown("## 💾 Export Data")

# Prepare full timeline CSV
all_timeline_data = []
for date, df in timeline.items():
    df_copy = df.copy()
    df_copy['date'] = date
    all_timeline_data.append(df_copy)

if all_timeline_data:
    full_timeline_df = pd.concat(all_timeline_data, ignore_index=True)
    timeline_cols = ['date', 'rank', 'symbol', 'company', 'industry', 'mean_long', 'mean_mid', 'mean_short', 'score']
    
    timeline_csv = full_timeline_df[timeline_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Full Timeline CSV",
        data=timeline_csv,
        file_name=f"ranking_timeline_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    <p>🎯 Market Hunt - Ranking Timeline Viewer</p>
    <p>Track momentum divergence rankings across time</p>
</div>
""", unsafe_allow_html=True)
