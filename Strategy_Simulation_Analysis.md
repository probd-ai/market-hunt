# Strategy Simulation Engine - Deep Technical Analysis

*Last Updated: September 1, 2025*  
*Status: Production Ready - Complete Backtesting System*

## 🎯 Overview
The Strategy Simulation Engine (`/api/simulation/run`) is a sophisticated backtesting system that evaluates trading strategies based on TrueValueX technical indicators. It simulates real-world portfolio management with advanced features like momentum ranking, rebalancing schedules, and comprehensive performance tracking.

## 📊 System Architecture

### Core Components
1. **Strategy Definition System** - Rule-based strategy configuration
2. **Data Management Layer** - Historical price & indicator data handling
3. **Portfolio Management Engine** - Position sizing and rebalancing logic
4. **Momentum Ranking System** - Stock selection optimization
5. **Performance Analytics** - Comprehensive metrics calculation

---

## 🔧 API Endpoint Structure

### Main Simulation Endpoint
```
POST /api/simulation/run
```

### Request Parameters (SimulationParams)
```python
class SimulationParams(BaseModel):
    strategy_id: str                    # References saved strategy
    portfolio_base_value: float = 100000 # Starting capital (₹1 Lakh default)
    rebalance_frequency: str = "monthly" # 'monthly', 'weekly', 'dynamic'
    rebalance_date: str = "first"       # 'first', 'last', 'mid' of period
    universe: str = "NIFTY50"          # 'NIFTY50', 'NIFTY100', 'NIFTY500'
    benchmark_symbol: Optional[str] = None # Custom benchmark override
    max_holdings: int = 50              # Portfolio size limit
    momentum_ranking: str = "20_day_return" # Stock selection method
    start_date: str                     # Simulation start (YYYY-MM-DD)
    end_date: str                       # Simulation end (YYYY-MM-DD)
```

---

## 🧠 Strategy Definition System

### Strategy Rules Structure
```python
class StrategyRule(BaseModel):
    id: str           # Unique rule identifier
    metric: str       # TrueValueX metrics: 'truevx_score', 'mean_short', 'mean_mid', 'mean_long'
    operator: str     # Comparison: '>', '<', '>=', '<=', '==', '!='
    threshold: float  # Threshold value for filtering
    name: str         # Human-readable rule name
```

### Example Strategy
```json
{
  "name": "High TrueVX + Strong Short Term",
  "description": "Select stocks with TrueVX > 70 and short-term momentum > 50",
  "rules": [
    {
      "id": "rule_1",
      "metric": "truevx_score",
      "operator": ">",
      "threshold": 70.0,
      "name": "High TrueVX Score"
    },
    {
      "id": "rule_2", 
      "metric": "mean_short",
      "operator": ">",
      "threshold": 50.0,
      "name": "Strong Short-Term Trend"
    }
  ]
}
```

---

## 🎲 Data Loading & Processing Pipeline

### Phase 1: Indicator Data Loading
```python
# Query TrueValueX indicators for universe symbols
indicator_query = {
    "indicator_type": "truevx",
    "symbol": {"$in": universe_symbols},
    "date": {"$gte": start_date, "$lte": end_date}
}

# Organize data by trading date
indicator_data = {
    "2024-01-01": {
        "RELIANCE": {
            "truevx_score": 75.2,
            "mean_short": 67.8,
            "mean_mid": 72.1,
            "mean_long": 68.9
        },
        "TCS": {...}
    }
}
```

### Phase 2: Price Data Loading
```python
# Load historical price data for all universe symbols
async with StockDataManager() as stock_manager:
    for symbol in universe_symbols:
        symbol_prices = await stock_manager.get_price_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=10000,
            sort_order=1  # Ascending (oldest first)
        )
```

### Phase 3: Benchmark Data Loading
```python
# Determine benchmark symbol based on universe
if params.universe == "NIFTY50":
    benchmark_symbol = "Nifty 50"
elif params.universe == "NIFTY100":
    benchmark_symbol = "Nifty 100"
else:
    benchmark_symbol = "Nifty 500"
```

---

## ⚡ Strategy Rule Application Engine

### Rule Evaluation Logic
```python
def apply_strategy_rules(day_indicators, rules):
    """Apply strategy rules to filter qualified stocks"""
    qualified_stocks = []
    
    for symbol, stock_data in day_indicators.items():
        qualifies = True
        
        for rule in rules:
            metric_value = stock_data.get(rule["metric"]) or 0
            threshold = rule["threshold"]
            operator = rule["operator"]
            
            # Evaluate rule condition
            if operator == ">" and not (metric_value > threshold):
                qualifies = False
                break
            elif operator == "<" and not (metric_value < threshold):
                qualifies = False
                break
            # ... other operators
        
        if qualifies:
            qualified_stocks.append(stock_data)
    
    return qualified_stocks
```

### Daily Processing Flow
1. **Load Indicators** - Get TrueValueX data for current date
2. **Apply Rules** - Filter stocks meeting strategy criteria
3. **Check Rebalancing** - Determine if portfolio adjustment needed
4. **Select Stocks** - Apply momentum ranking if over portfolio limit
5. **Execute Trades** - Update positions and calculate P&L

---

## 🎯 Momentum Ranking System

### Three Momentum Methods

#### 1. 20-Day Return Method
```python
if method == "20_day_return":
    if len(symbol_prices) >= 20:
        lookback_price = symbol_prices[-20]["close"]
    else:
        lookback_price = symbol_prices[0]["close"]
    
    if lookback_price > 0:
        return ((current_price / lookback_price) - 1) * 100
```

#### 2. Risk-Adjusted Method (Sharpe-like)
```python
elif method == "risk_adjusted":
    # Calculate daily returns
    daily_returns = []
    for i in range(1, len(symbol_prices)):
        daily_return = (curr_price / prev_price) - 1
        daily_returns.append(daily_return)
    
    # Risk-adjusted score
    mean_return = sum(daily_returns) / len(daily_returns)
    std_return = calculate_std(daily_returns)
    
    if std_return > 0:
        sharpe_like = (mean_return / std_return) * (252 ** 0.5)
        return sharpe_like * 100
```

#### 3. Technical Method (MA-based)
```python
elif method == "technical":
    # Calculate moving averages
    ma_10 = sum(prices_10) / len(prices_10)
    ma_20 = sum(prices_20) / len(prices_20)
    
    # Price momentum vs MA
    price_momentum = ((current_price / ma_20) - 1) * 100
    
    # Trend momentum (MA crossover)
    trend_momentum = ((ma_10 / ma_20) - 1) * 100
    
    # Combined score
    return (price_momentum + trend_momentum) / 2
```

### Portfolio Limit Application
```python
async def select_top_stocks_by_momentum(qualified_stocks, current_holdings, 
                                      price_data_history, current_date, 
                                      max_holdings, momentum_method):
    # If under limit, add all qualified stocks
    total_candidates = len(qualified_stocks) + len(current_holdings)
    if total_candidates <= max_holdings:
        return qualified_stocks, new_stocks, []
    
    # Calculate momentum for all candidates
    all_candidates = []
    
    # Current holdings + newly qualified stocks
    for symbol in current_holdings.keys():
        momentum = await calculate_stock_momentum(...)
        all_candidates.append({
            "symbol": symbol,
            "momentum_score": momentum,
            "is_current_holding": True
        })
    
    # Sort by momentum (highest first)
    all_candidates.sort(key=lambda x: x["momentum_score"], reverse=True)
    
    # Select top N stocks
    selected_candidates = all_candidates[:max_holdings]
    
    return selected_stocks, added_stocks, removed_stocks
```

---

## 💰 Portfolio Management Engine

### Initialization
```python
portfolio_value = params.portfolio_base_value  # ₹100,000
current_holdings = {}  # {symbol: {"shares": float, "avg_price": float}}
benchmark_value = params.portfolio_base_value
```

### Rebalancing Logic

#### Rebalancing Triggers
1. **First Day** - Always rebalance
2. **Scheduled** - Monthly/Weekly based on `rebalance_frequency`
3. **Dynamic** - Daily rebalancing (if `rebalance_frequency == "dynamic"`)

#### Rebalancing Process
```python
if should_rebalance:
    # 1. Calculate current portfolio value
    current_portfolio_value = calculate_current_portfolio_value(current_holdings, day_prices)
    
    # 2. Determine rebalance amount
    if i == 0:  # First day
        rebalance_value = params.portfolio_base_value
    else:
        # Use current value (preserve capital - don't amplify)
        rebalance_value = current_portfolio_value
        # Safety floor (prevent portfolio going to zero)
        rebalance_value = max(rebalance_value, params.portfolio_base_value * 0.01)
    
    # 3. Apply momentum-based selection
    selected_stocks, momentum_added, momentum_removed = await select_top_stocks_by_momentum(...)
    
    # 4. Calculate exit details BEFORE deleting holdings
    for symbol in list(current_holdings.keys()):
        if symbol not in selected_symbols:
            holding = current_holdings[symbol]
            current_price = day_prices[symbol]["close_price"]
            exit_pnl = (current_price - holding["avg_price"]) * holding["shares"]
            exit_pnl_percent = ((current_price / holding["avg_price"]) - 1) * 100
            
            exited_details.append({
                "symbol": symbol,
                "quantity": holding["shares"],
                "avg_price": holding["avg_price"],
                "exit_price": current_price,
                "pnl": exit_pnl,
                "pnl_percent": exit_pnl_percent
            })
    
    # 5. Equal weight allocation
    if selected_symbols:
        target_value_per_stock = rebalance_value / len(selected_symbols)
        
        for symbol in selected_symbols:
            price = day_prices[symbol]["close_price"]
            target_shares = target_value_per_stock / price
            
            current_holdings[symbol] = {
                "shares": target_shares,
                "avg_price": price
            }
```

### Daily Value Calculation
```python
def calculate_current_portfolio_value(current_holdings, day_prices):
    """Calculate current portfolio value based on current prices"""
    total_value = 0
    
    for symbol, holding in current_holdings.items():
        if symbol in day_prices:
            current_price = day_prices[symbol]["close_price"]
            market_value = holding["shares"] * current_price
            total_value += market_value
    
    return total_value
```

---

## 📈 Benchmark Tracking

### Benchmark Value Calculation
```python
# Calculate benchmark daily return
if current_benchmark_close is not None and prev_benchmark_close is not None:
    benchmark_return = (current_benchmark_close / prev_benchmark_close) - 1
    benchmark_value = benchmark_value * (1 + benchmark_return)
```

### Performance Metrics
```python
# Calculate summary statistics
total_return = (portfolio_value / params.portfolio_base_value - 1) * 100
benchmark_return = (benchmark_value / params.portfolio_base_value - 1) * 100
alpha = total_return - benchmark_return

# Calculate maximum drawdown
peak_value = params.portfolio_base_value
max_drawdown = 0
for result in simulation_results:
    peak_value = max(peak_value, result["portfolio_value"])
    drawdown = (result["portfolio_value"] / peak_value - 1) * 100
    max_drawdown = min(max_drawdown, drawdown)
```

---

## 📊 Daily Result Structure

### Daily Portfolio Snapshot
```python
day_result = {
    "date": "2024-01-15",
    "portfolio_value": 105000.50,
    "benchmark_value": 102000.25,
    "holdings": [
        {
            "symbol": "RELIANCE",
            "company_name": "Reliance Industries",
            "quantity": 125.50,
            "avg_price": 2450.00,
            "current_price": 2500.00,
            "market_value": 313750.00,
            "pnl": 6275.00,
            "pnl_percent": 2.04,
            "sector": "Oil & Gas"
        }
    ],
    "new_added": ["INFY", "HDFC"],
    "exited": ["WIPRO"],
    "exited_details": [
        {
            "symbol": "WIPRO",
            "quantity": 200.00,
            "avg_price": 425.00,
            "exit_price": 445.00,
            "pnl": 4000.00,
            "pnl_percent": 4.71
        }
    ],
    "cash": 0,  # Fully invested strategy
    "total_pnl": 5000.50,
    "day_pnl": 1250.25,
    "benchmark_price": 22150.75
}
```

---

## 🔄 Rebalancing Schedule System

### Rebalancing Date Generation
```python
def get_rebalance_dates(dates, frequency, date_type):
    """Generate rebalance dates based on frequency and date type"""
    rebalance_dates = set()
    
    if frequency == "monthly":
        current_month = None
        for date_str in dates:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if current_month != date_obj.month:
                current_month = date_obj.month
                rebalance_dates.add(date_str)  # First trading day of month
                
    elif frequency == "weekly":
        current_week = None
        for date_str in dates:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            week_num = date_obj.isocalendar()[1]
            if current_week != week_num:
                current_week = week_num
                rebalance_dates.add(date_str)  # First trading day of week
    
    return rebalance_dates
```

---

## 🎯 Key Simulation Features

### 1. Capital Preservation
- **Problem**: Avoid value amplification on rebalancing
- **Solution**: Use current portfolio value, not base value for subsequent rebalances
- **Implementation**: `rebalance_value = current_portfolio_value` (except first day)

### 2. Exit Performance Tracking
- **Feature**: Calculate P&L for exited stocks before deletion
- **Data Captured**: Entry price, exit price, quantity, P&L percentage
- **Timing**: Calculated before holdings are removed from portfolio

### 3. Equal Weight Strategy
- **Method**: `target_value_per_stock = rebalance_value / len(selected_symbols)`
- **Implementation**: All selected stocks get equal allocation
- **Advantage**: Prevents concentration risk

### 4. Momentum-Based Selection
- **Trigger**: When qualified stocks exceed `max_holdings` limit
- **Methods**: 20-day return, risk-adjusted, technical analysis
- **Process**: Rank all candidates (current + new) by momentum, select top N

---

## 📋 Performance Summary Structure

```python
{
    "params": {SimulationParams},
    "benchmark_symbol": "Nifty 50",
    "results": [daily_results],
    "summary": {
        "total_return": 25.6,           # Portfolio return %
        "benchmark_return": 18.3,       # Benchmark return %
        "alpha": 7.3,                   # Outperformance
        "max_drawdown": -12.4,          # Maximum drawdown %
        "sharpe_ratio": 1.2,            # Risk-adjusted return
        "total_trades": 12              # Number of rebalance events
    }
}
```

---

## ⚠️ Known Issues & Limitations

### 1. Debug vs Production Discrepancy
- **Issue**: Debug simulation returns differ from actual simulation
- **Root Cause**: Debug function missing `calculate_current_portfolio_value()` logic
- **Impact**: Debug shows 36.51% vs actual 56.65% returns
- **Status**: Identified, requires alignment between debug/actual functions

### 2. Company Metadata Missing
- **Current**: Using symbol as company name
- **Needed**: Integration with symbol mapping collection
- **Impact**: Frontend displays "RELIANCE" instead of "Reliance Industries"

### 3. Sector Information Missing
- **Current**: All stocks show "Unknown" sector
- **Needed**: Integration with industry/sector mapping
- **Impact**: Limited analytical capabilities by sector

---

## 🔧 Potential Improvements

### 1. Transaction Costs
- **Current**: Zero transaction costs assumed
- **Enhancement**: Add brokerage, STT, taxes
- **Implementation**: Deduct costs on each trade

### 2. Slippage Modeling
- **Current**: Assumes perfect execution at closing prices
- **Enhancement**: Add price impact modeling
- **Implementation**: Apply slippage percentage based on volume

### 3. Risk Management
- **Current**: No position limits beyond portfolio size
- **Enhancement**: Add sector limits, volatility controls
- **Implementation**: Additional constraints in stock selection

### 4. Advanced Rebalancing
- **Current**: Simple equal weight allocation
- **Enhancement**: Risk-parity, momentum-weighted, volatility-based
- **Implementation**: Pluggable allocation strategies

### 5. Multi-Strategy Support
- **Current**: Single strategy per simulation
- **Enhancement**: Strategy blending and rotation
- **Implementation**: Strategy weight allocation system

---

## 🏗️ Technical Architecture

### Database Collections Used
1. **`simulation_strategies`** - Saved strategy definitions
2. **`indicators`** - TrueValueX indicator data
3. **`prices_YYYY_YYYY`** - Historical price data (partitioned)
4. **`index_meta`** - Index constituent mappings
5. **`symbol_mappings`** - Symbol metadata and mappings

### External Dependencies
1. **`StockDataManager`** - Price data retrieval
2. **`IndicatorDataManager`** - Indicator data access
3. **`NSEDataClient`** - Real-time data fetching

### Performance Considerations
- **Async Operations**: All database calls are asynchronous
- **Batch Loading**: Price data loaded in bulk per symbol
- **Index Usage**: Optimized MongoDB queries with proper indexing
- **Memory Management**: Data processed date-by-date to manage memory

---

## 📝 Usage Example

```python
# Strategy Definition
strategy = {
    "name": "TrueVX High Momentum",
    "rules": [
        {"metric": "truevx_score", "operator": ">", "threshold": 75},
        {"metric": "mean_short", "operator": ">", "threshold": 60}
    ]
}

# Simulation Parameters
params = {
    "strategy_id": "strategy_12345",
    "portfolio_base_value": 1000000,
    "rebalance_frequency": "monthly",
    "universe": "NIFTY50",
    "max_holdings": 15,
    "momentum_ranking": "risk_adjusted",
    "start_date": "2023-01-01",
    "end_date": "2024-12-31"
}

# Execute Simulation
result = await run_simulation(params)
```

This simulation would:
1. Select NIFTY50 stocks with TrueVX > 75 and short-term mean > 60
2. Limit portfolio to 15 best momentum stocks
3. Rebalance monthly with equal weights
4. Track performance vs Nifty 50 benchmark
5. Return comprehensive daily portfolio snapshots and summary metrics

---

*This analysis provides a complete understanding of the Strategy Simulation Engine's inner workings, enabling informed modifications and enhancements.*

---

# 💰 Brokerage Charges Implementation Plan

*Added: September 1, 2025*  
*Status: Implementation Plan - Ready for Development*

## 🎯 Overview
This section outlines the comprehensive implementation plan for adding realistic Indian equity delivery brokerage charges to the simulation engine. The charges will be calculated per transaction and deducted from the portfolio value to provide accurate backtesting results.

## 📊 Indian Equity Delivery Charges Structure

### Charge Components
```python
INDIAN_EQUITY_CHARGES = {
    "brokerage": 0.0,                    # ₹0 for delivery trades
    "stt_buy": 0.001,                    # 0.1% on buy
    "stt_sell": 0.001,                   # 0.1% on sell  
    "transaction_charges_nse": 0.0000297, # 0.00297% NSE
    "transaction_charges_bse": 0.0000375, # 0.00375% BSE
    "gst_rate": 0.18,                    # 18% on applicable charges
    "sebi_charges": 0.000001,            # ₹10 per crore (0.0001%)
    "stamp_duty": 0.00015                # 0.015% on buy side only
}
```

### Calculation Formula
```python
def calculate_transaction_charges(trade_value: float, trade_type: str, exchange: str = "NSE") -> dict:
    """
    Calculate all charges for a single transaction
    
    Args:
        trade_value: Total transaction value (price * quantity)
        trade_type: "BUY" or "SELL"
        exchange: "NSE" or "BSE" (default NSE)
    
    Returns:
        Dictionary with breakdown of all charges
    """
    charges = {}
    
    # 1. Brokerage (Zero for delivery)
    charges["brokerage"] = 0.0
    
    # 2. STT (0.1% on both buy & sell)
    charges["stt"] = trade_value * 0.001
    
    # 3. Transaction Charges (Exchange dependent)
    if exchange == "NSE":
        charges["transaction_charges"] = trade_value * 0.0000297
    else:  # BSE
        charges["transaction_charges"] = trade_value * 0.0000375
    
    # 4. SEBI Charges (₹10 per crore)
    charges["sebi_charges"] = trade_value * 0.000001
    
    # 5. Stamp Duty (0.015% on buy side only)
    if trade_type == "BUY":
        charges["stamp_duty"] = trade_value * 0.00015
    else:
        charges["stamp_duty"] = 0.0
    
    # 6. GST (18% on brokerage + SEBI + transaction charges)
    taxable_amount = (charges["brokerage"] + 
                     charges["sebi_charges"] + 
                     charges["transaction_charges"])
    charges["gst"] = taxable_amount * 0.18
    
    # 7. Total charges
    charges["total_charges"] = sum(charges.values())
    
    # 8. Net trade value (for buy: trade_value + charges, for sell: trade_value - charges)
    if trade_type == "BUY":
        charges["net_trade_value"] = trade_value + charges["total_charges"]
    else:
        charges["net_trade_value"] = trade_value - charges["total_charges"]
    
    return charges
```

## 🔧 Implementation Strategy

### Phase 1: Data Structure Updates

#### 1. Update SimulationParams Model
```python
class SimulationParams(BaseModel):
    # ... existing fields ...
    include_brokerage: bool = True          # Enable/disable brokerage calculation
    exchange: str = "NSE"                   # Default exchange for charges
    brokerage_rate: float = 0.0             # Custom brokerage rate override
```

#### 2. Update Holdings Structure
```python
# Enhanced holdings structure with cost tracking
current_holdings = {
    "symbol": {
        "shares": float,
        "avg_price": float,
        "total_cost": float,                # Including purchase charges
        "cumulative_charges": float,        # Total charges paid for this holding
        "purchase_dates": list,             # Track multiple purchase dates
        "charge_breakdown": dict            # Detailed charge history
    }
}
```

#### 3. Update Daily Result Structure
```python
day_result = {
    # ... existing fields ...
    "daily_charges": {
        "total_buy_charges": float,
        "total_sell_charges": float,
        "charge_breakdown": {
            "stt": float,
            "transaction_charges": float,
            "sebi_charges": float,
            "stamp_duty": float,
            "gst": float,
            "total": float
        }
    },
    "cumulative_charges": float,            # Total charges to date
    "net_portfolio_value": float,           # Portfolio value after charges
    "charge_impact_percent": float          # Charges as % of portfolio
}
```

### Phase 2: Core Functions Implementation

#### 1. Transaction Charge Calculator
```python
def calculate_transaction_charges(trade_value: float, trade_type: str, 
                                 exchange: str = "NSE", 
                                 custom_brokerage: float = 0.0) -> dict:
    """
    Calculate comprehensive transaction charges for Indian equity delivery
    """
    charges = {
        "trade_value": trade_value,
        "trade_type": trade_type,
        "exchange": exchange
    }
    
    # Brokerage (typically zero for delivery, but allow custom)
    charges["brokerage"] = trade_value * custom_brokerage
    
    # STT (Securities Transaction Tax) - 0.1% on buy & sell
    charges["stt"] = trade_value * 0.001
    
    # Exchange Transaction Charges
    if exchange.upper() == "NSE":
        charges["transaction_charges"] = trade_value * 0.0000297
    elif exchange.upper() == "BSE":
        charges["transaction_charges"] = trade_value * 0.0000375
    else:
        charges["transaction_charges"] = trade_value * 0.0000297  # Default to NSE
    
    # SEBI Charges (₹10 per crore = 0.0001%)
    charges["sebi_charges"] = trade_value * 0.000001
    
    # Stamp Duty (0.015% on buy side only)
    charges["stamp_duty"] = trade_value * 0.00015 if trade_type == "BUY" else 0.0
    
    # GST (18% on brokerage + SEBI + transaction charges)
    taxable_base = (charges["brokerage"] + 
                   charges["sebi_charges"] + 
                   charges["transaction_charges"])
    charges["gst"] = taxable_base * 0.18
    
    # Calculate totals
    charges["total_charges"] = (charges["brokerage"] + 
                               charges["stt"] + 
                               charges["transaction_charges"] + 
                               charges["sebi_charges"] + 
                               charges["stamp_duty"] + 
                               charges["gst"])
    
    # Net amount (what actually gets debited/credited)
    if trade_type == "BUY":
        charges["net_amount"] = trade_value + charges["total_charges"]
    else:  # SELL
        charges["net_amount"] = trade_value - charges["total_charges"]
    
    return charges
```

#### 2. Portfolio Rebalancing with Charges
```python
async def rebalance_portfolio_with_charges(current_holdings: dict, 
                                         selected_symbols: list,
                                         day_prices: dict,
                                         available_capital: float,
                                         params: SimulationParams) -> dict:
    """
    Rebalance portfolio accounting for transaction charges
    """
    rebalance_result = {
        "new_holdings": {},
        "total_buy_charges": 0.0,
        "total_sell_charges": 0.0,
        "net_capital_used": 0.0,
        "charge_breakdown": {},
        "trade_details": []
    }
    
    # Phase 1: Calculate sell transactions and charges
    total_sell_proceeds = 0.0
    for symbol, holding in current_holdings.items():
        if symbol not in selected_symbols:
            # Sell this holding
            sell_value = holding["shares"] * day_prices[symbol]["close_price"]
            sell_charges = calculate_transaction_charges(
                trade_value=sell_value,
                trade_type="SELL",
                exchange=params.exchange,
                custom_brokerage=params.brokerage_rate if params.brokerage_rate > 0 else 0.0
            )
            
            net_proceeds = sell_charges["net_amount"]  # sell_value - charges
            total_sell_proceeds += net_proceeds
            rebalance_result["total_sell_charges"] += sell_charges["total_charges"]
            
            # Track sell transaction
            rebalance_result["trade_details"].append({
                "type": "SELL",
                "symbol": symbol,
                "quantity": holding["shares"],
                "price": day_prices[symbol]["close_price"],
                "gross_value": sell_value,
                "charges": sell_charges["total_charges"],
                "net_value": net_proceeds,
                "charge_breakdown": sell_charges
            })
    
    # Phase 2: Calculate available capital for purchases
    total_available = available_capital + total_sell_proceeds
    
    # Phase 3: Calculate buy transactions with iterative charge adjustment
    if selected_symbols:
        # Initial allocation (will be adjusted for charges)
        target_gross_per_stock = total_available / len(selected_symbols)
        
        total_buy_charges_estimated = 0.0
        for symbol in selected_symbols:
            if symbol in day_prices:
                # Estimate charges for this allocation
                estimated_charges = calculate_transaction_charges(
                    trade_value=target_gross_per_stock,
                    trade_type="BUY",
                    exchange=params.exchange,
                    custom_brokerage=params.brokerage_rate if params.brokerage_rate > 0 else 0.0
                )
                total_buy_charges_estimated += estimated_charges["total_charges"]
        
        # Adjust allocation to account for charges
        available_for_investment = total_available - total_buy_charges_estimated
        target_investment_per_stock = available_for_investment / len(selected_symbols)
        
        # Execute buy transactions
        for symbol in selected_symbols:
            if symbol in day_prices:
                price = day_prices[symbol]["close_price"]
                
                # Calculate shares we can buy with available investment amount
                shares_to_buy = target_investment_per_stock / price
                actual_investment = shares_to_buy * price
                
                # Calculate actual charges
                buy_charges = calculate_transaction_charges(
                    trade_value=actual_investment,
                    trade_type="BUY",
                    exchange=params.exchange,
                    custom_brokerage=params.brokerage_rate if params.brokerage_rate > 0 else 0.0
                )
                
                total_cost = buy_charges["net_amount"]  # investment + charges
                
                # Update holdings
                rebalance_result["new_holdings"][symbol] = {
                    "shares": shares_to_buy,
                    "avg_price": price,
                    "total_cost": total_cost,
                    "cumulative_charges": buy_charges["total_charges"],
                    "charge_breakdown": buy_charges
                }
                
                rebalance_result["total_buy_charges"] += buy_charges["total_charges"]
                rebalance_result["net_capital_used"] += total_cost
                
                # Track buy transaction
                rebalance_result["trade_details"].append({
                    "type": "BUY",
                    "symbol": symbol,
                    "quantity": shares_to_buy,
                    "price": price,
                    "gross_value": actual_investment,
                    "charges": buy_charges["total_charges"],
                    "net_cost": total_cost,
                    "charge_breakdown": buy_charges
                })
    
    # Aggregate charge breakdown
    rebalance_result["charge_breakdown"] = {
        "total_charges": rebalance_result["total_buy_charges"] + rebalance_result["total_sell_charges"],
        "buy_charges": rebalance_result["total_buy_charges"],
        "sell_charges": rebalance_result["total_sell_charges"],
        "net_impact": rebalance_result["total_buy_charges"] + rebalance_result["total_sell_charges"]
    }
    
    return rebalance_result
```

### Phase 3: Integration Points

#### 1. Modified Rebalancing Logic
```python
# In run_strategy_simulation function, replace the equal weight rebalancing section:

if should_rebalance:
    # ... existing code for qualification and selection ...
    
    if params.include_brokerage:
        # Use charge-aware rebalancing
        rebalance_result = await rebalance_portfolio_with_charges(
            current_holdings=current_holdings,
            selected_symbols=selected_symbols,
            day_prices=day_prices,
            available_capital=rebalance_value,
            params=params
        )
        
        # Update holdings with charge tracking
        current_holdings = rebalance_result["new_holdings"]
        
        # Deduct total charges from portfolio value
        portfolio_value = rebalance_value - rebalance_result["charge_breakdown"]["total_charges"]
        
        # Track daily charges
        daily_charges = rebalance_result["charge_breakdown"]
        
        logger.info(f"💰 Rebalancing with charges: Total charges = ₹{daily_charges['total_charges']:,.2f}")
        logger.info(f"📊 Buy charges: ₹{daily_charges['buy_charges']:,.2f}, Sell charges: ₹{daily_charges['sell_charges']:,.2f}")
        
    else:
        # Original logic without charges
        # ... existing equal weight allocation code ...
        daily_charges = {"total_charges": 0.0, "buy_charges": 0.0, "sell_charges": 0.0}
```

#### 2. Updated Daily Result Creation
```python
# Enhanced day result with charge tracking
day_result = {
    "date": date_str,
    "portfolio_value": portfolio_value,
    "benchmark_value": benchmark_value,
    "holdings": holdings_list,
    "new_added": new_added,
    "exited": exited,
    "exited_details": exited_details,
    "cash": remaining_cash,  # Track remaining cash after charges
    "total_pnl": portfolio_value - params.portfolio_base_value,
    "day_pnl": day_pnl,
    "benchmark_price": current_benchmark_close or 0,
    
    # New charge tracking fields
    "daily_charges": daily_charges if should_rebalance else {"total_charges": 0.0},
    "cumulative_charges": cumulative_charges_to_date,
    "net_portfolio_value": portfolio_value,  # Already adjusted for charges
    "charge_impact_percent": (cumulative_charges_to_date / params.portfolio_base_value) * 100,
    "trade_details": rebalance_result.get("trade_details", []) if should_rebalance else []
}
```

## 📊 Expected Impact Analysis

### Charge Impact Estimation
```python
def estimate_charge_impact(portfolio_value: float, rebalance_frequency: str, 
                          max_holdings: int, simulation_days: int) -> dict:
    """
    Estimate the total impact of charges on portfolio performance
    """
    
    # Estimate number of rebalance events
    if rebalance_frequency == "monthly":
        rebalance_events = simulation_days / 22  # ~22 trading days per month
    elif rebalance_frequency == "weekly":
        rebalance_events = simulation_days / 5   # 5 trading days per week
    else:  # dynamic
        rebalance_events = simulation_days
    
    # Estimate turnover per rebalance (assume 50% portfolio churn)
    average_turnover_per_rebalance = portfolio_value * 0.5
    total_turnover = average_turnover_per_rebalance * rebalance_events
    
    # Calculate estimated charges
    estimated_charges = {
        "stt": total_turnover * 0.001,                    # 0.1% STT
        "transaction_charges": total_turnover * 0.0000297, # NSE charges
        "sebi_charges": total_turnover * 0.000001,         # SEBI charges
        "stamp_duty": (total_turnover * 0.5) * 0.00015,   # 50% is buys, 0.015% stamp duty
        "gst": 0.0  # Calculated separately
    }
    
    # GST on applicable charges
    taxable_amount = (estimated_charges["transaction_charges"] + 
                     estimated_charges["sebi_charges"])  # No brokerage for delivery
    estimated_charges["gst"] = taxable_amount * 0.18
    
    estimated_charges["total"] = sum(estimated_charges.values())
    estimated_charges["impact_percent"] = (estimated_charges["total"] / portfolio_value) * 100
    
    return {
        "rebalance_events": int(rebalance_events),
        "total_turnover": total_turnover,
        "estimated_charges": estimated_charges,
        "annual_charge_rate": (estimated_charges["total"] / portfolio_value) * (365 / simulation_days) * 100
    }
```

### Typical Charge Impact
For a ₹10 lakh portfolio with monthly rebalancing over 1 year:
- **Estimated Turnover**: ₹60 lakhs (50% churn × 12 months)
- **Total Charges**: ~₹7,200 (0.12% of turnover)
- **Annual Impact**: ~0.72% of portfolio value
- **Breakdown**:
  - STT: ₹6,000 (0.1%)
  - Transaction Charges: ₹178 (0.00297%)
  - SEBI Charges: ₹60 (₹10 per crore)
  - Stamp Duty: ₹450 (0.015% on buys only)
  - GST: ₹43 (18% on applicable charges)

## 🔧 Implementation Checklist

### Backend Changes Required

1. **✅ Data Models Update**
   - [ ] Add `include_brokerage` to SimulationParams
   - [ ] Add `exchange` selection to SimulationParams  
   - [ ] Add `brokerage_rate` override to SimulationParams
   - [ ] Enhance holdings structure with cost tracking
   - [ ] Update daily result structure with charge fields

2. **✅ Core Functions**
   - [ ] Implement `calculate_transaction_charges()` function
   - [ ] Implement `rebalance_portfolio_with_charges()` function
   - [ ] Implement `estimate_charge_impact()` helper function
   - [ ] Update `calculate_current_portfolio_value()` to handle charges

3. **✅ Integration Points**
   - [ ] Modify rebalancing logic in `run_strategy_simulation()`
   - [ ] Update daily result creation with charge tracking
   - [ ] Add cumulative charge tracking across simulation
   - [ ] Implement charge impact reporting in summary

4. **✅ API Endpoints**
   - [ ] Add charge estimation endpoint `/api/simulation/estimate-charges`
   - [ ] Update strategy CRUD endpoints for charge parameters
   - [ ] Enhance simulation results with charge breakdown

### Frontend Changes Required

1. **✅ Strategy Configuration**
   - [ ] Add brokerage toggle in strategy setup
   - [ ] Add exchange selection (NSE/BSE)
   - [ ] Add custom brokerage rate input
   - [ ] Add charge impact estimation display

2. **✅ Results Visualization**
   - [ ] Add charge breakdown in simulation results
   - [ ] Show cumulative charges over time
   - [ ] Display charge impact percentage
   - [ ] Add gross vs net performance comparison

3. **✅ Analytics Enhancement**
   - [ ] Charge impact charts (daily/cumulative)
   - [ ] Performance comparison (with/without charges)
   - [ ] Trade-by-trade charge breakdown
   - [ ] Charge efficiency metrics

## 📈 Testing Strategy

### Unit Tests
1. **Transaction Charge Calculator**
   - Test all charge components individually
   - Verify GST calculation accuracy
   - Test edge cases (zero brokerage, different exchanges)

2. **Portfolio Rebalancing**
   - Test charge-adjusted allocation logic
   - Verify capital preservation with charges
   - Test partial rebalancing scenarios

### Integration Tests
1. **End-to-End Simulation**
   - Compare results with/without charges
   - Verify charge accumulation over time
   - Test different rebalancing frequencies

2. **Performance Impact**
   - Benchmark calculation speed with charges
   - Memory usage analysis
   - Database impact assessment

### Validation Tests
1. **Real-World Validation**
   - Compare with actual brokerage statements
   - Verify charge calculation accuracy
   - Test with different portfolio sizes

## 🎯 Implementation Priority

### Phase 1 (High Priority)
1. Core charge calculation functions
2. Basic integration with rebalancing logic
3. Simple charge tracking in results

### Phase 2 (Medium Priority)
1. Advanced charge breakdown and reporting
2. Frontend visualization enhancements
3. Performance optimization

### Phase 3 (Future Enhancement)
1. Multiple brokerage models (different brokers)
2. Intraday trading charge support
3. Options/futures charge calculation

---

*This comprehensive implementation plan ensures accurate and realistic backtesting results by incorporating all Indian equity delivery charges into the simulation engine.*
