#!/usr/bin/env python3
"""
Brokerage Calculator for Indian Equity Delivery Trades
Handles comprehensive charge calculation including STT, transaction charges, SEBI charges, stamp duty, and GST
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TransactionCharges:
    """Data class for transaction charges breakdown"""
    trade_value: float
    trade_type: str  # "BUY" or "SELL"
    exchange: str    # "NSE" or "BSE"
    
    # Individual charge components
    brokerage: float = 0.0
    stt: float = 0.0
    transaction_charges: float = 0.0
    sebi_charges: float = 0.0
    stamp_duty: float = 0.0
    gst: float = 0.0
    
    # Totals
    total_charges: float = 0.0
    net_amount: float = 0.0  # trade_value ± total_charges
    
    # Metadata
    calculation_timestamp: Optional[datetime] = None

@dataclass
class TradeDetails:
    """Data class for individual trade details"""
    trade_id: str
    symbol: str
    trade_type: str  # "BUY" or "SELL"
    quantity: float
    price: float
    gross_value: float
    charges: TransactionCharges
    net_value: float
    timestamp: datetime

class BrokerageCalculator:
    """
    Comprehensive brokerage calculator for Indian equity delivery trades
    """
    
    # Indian equity delivery charge rates
    CHARGE_RATES = {
        "stt_rate": 0.001,           # 0.1% on buy & sell
        "nse_transaction_rate": 0.0000297,  # 0.00297% of turnover
        "bse_transaction_rate": 0.0000375,  # 0.00375% of turnover
        "sebi_rate": 0.000001,       # ₹10 per crore (0.0001% of turnover)
        "stamp_duty_rate": 0.00015,  # 0.015% on buy side only
        "gst_rate": 0.18,            # 18% on applicable charges
        "default_brokerage": 0.0     # ₹0 for delivery trades
    }
    
    def __init__(self, default_exchange: str = "NSE", custom_brokerage_rate: float = 0.0):
        """
        Initialize brokerage calculator
        
        Args:
            default_exchange: Default exchange for calculations ("NSE" or "BSE")
            custom_brokerage_rate: Custom brokerage rate (as decimal, e.g., 0.001 for 0.1%)
        """
        self.default_exchange = default_exchange.upper()
        self.custom_brokerage_rate = custom_brokerage_rate
        
        logger.info(f"🧮 BrokerageCalculator initialized - Exchange: {self.default_exchange}, Custom Brokerage: {custom_brokerage_rate*100:.3f}%")
    
    def calculate_transaction_charges(self, 
                                    trade_value: float, 
                                    trade_type: str, 
                                    exchange: Optional[str] = None) -> TransactionCharges:
        """
        Calculate comprehensive transaction charges for a single trade
        
        Args:
            trade_value: Total transaction value (price * quantity)
            trade_type: "BUY" or "SELL"
            exchange: Exchange for the trade ("NSE" or "BSE"). Uses default if None.
            
        Returns:
            TransactionCharges object with detailed breakdown
        """
        try:
            # Validate inputs
            if trade_value <= 0:
                raise ValueError(f"Trade value must be positive, got: {trade_value}")
            
            trade_type = trade_type.upper()
            if trade_type not in ["BUY", "SELL"]:
                raise ValueError(f"Trade type must be 'BUY' or 'SELL', got: {trade_type}")
            
            exchange = (exchange or self.default_exchange).upper()
            if exchange not in ["NSE", "BSE"]:
                raise ValueError(f"Exchange must be 'NSE' or 'BSE', got: {exchange}")
            
            # Initialize charges object
            charges = TransactionCharges(
                trade_value=trade_value,
                trade_type=trade_type,
                exchange=exchange,
                calculation_timestamp=datetime.now()
            )
            
            # 1. Brokerage (typically ₹0 for delivery, but allow custom)
            charges.brokerage = trade_value * (self.custom_brokerage_rate or self.CHARGE_RATES["default_brokerage"])
            
            # 2. STT (Securities Transaction Tax) - 0.1% on buy & sell
            charges.stt = trade_value * self.CHARGE_RATES["stt_rate"]
            
            # 3. Exchange Transaction Charges
            if exchange == "NSE":
                charges.transaction_charges = trade_value * self.CHARGE_RATES["nse_transaction_rate"]
            else:  # BSE
                charges.transaction_charges = trade_value * self.CHARGE_RATES["bse_transaction_rate"]
            
            # 4. SEBI Charges (₹10 per crore = 0.0001%)
            charges.sebi_charges = trade_value * self.CHARGE_RATES["sebi_rate"]
            
            # 5. Stamp Duty (0.015% on buy side only)
            if trade_type == "BUY":
                charges.stamp_duty = trade_value * self.CHARGE_RATES["stamp_duty_rate"]
            else:
                charges.stamp_duty = 0.0
            
            # 6. GST (18% on brokerage + SEBI + transaction charges)
            taxable_base = (charges.brokerage + 
                           charges.sebi_charges + 
                           charges.transaction_charges)
            charges.gst = taxable_base * self.CHARGE_RATES["gst_rate"]
            
            # 7. Calculate totals
            charges.total_charges = (charges.brokerage + 
                                   charges.stt + 
                                   charges.transaction_charges + 
                                   charges.sebi_charges + 
                                   charges.stamp_duty + 
                                   charges.gst)
            
            # 8. Net amount (what actually gets debited/credited)
            if trade_type == "BUY":
                charges.net_amount = trade_value + charges.total_charges
            else:  # SELL
                charges.net_amount = trade_value - charges.total_charges
            
            logger.debug(f"💰 Calculated charges for {trade_type} ₹{trade_value:,.2f} on {exchange}: Total charges = ₹{charges.total_charges:.2f}")
            
            return charges
            
        except Exception as e:
            logger.error(f"❌ Error calculating transaction charges: {e}")
            raise
    
    def calculate_portfolio_rebalance_charges(self, 
                                            sell_trades: List[Dict[str, Any]], 
                                            buy_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate total charges for a complete portfolio rebalance
        
        Args:
            sell_trades: List of sell trade dictionaries with keys: symbol, quantity, price
            buy_trades: List of buy trade dictionaries with keys: symbol, quantity, price
            
        Returns:
            Dictionary with comprehensive charge breakdown and trade details
        """
        try:
            rebalance_result = {
                "sell_trades": [],
                "buy_trades": [],
                "total_sell_charges": 0.0,
                "total_buy_charges": 0.0,
                "total_charges": 0.0,
                "total_sell_value": 0.0,
                "total_buy_value": 0.0,
                "net_sell_proceeds": 0.0,
                "net_buy_cost": 0.0,
                "charge_breakdown": {
                    "brokerage": 0.0,
                    "stt": 0.0,
                    "transaction_charges": 0.0,
                    "sebi_charges": 0.0,
                    "stamp_duty": 0.0,
                    "gst": 0.0
                }
            }
            
            # Process sell trades
            for trade in sell_trades:
                trade_value = trade["quantity"] * trade["price"]
                charges = self.calculate_transaction_charges(trade_value, "SELL")
                
                trade_detail = TradeDetails(
                    trade_id=f"SELL_{trade['symbol']}_{datetime.now().timestamp()}",
                    symbol=trade["symbol"],
                    trade_type="SELL",
                    quantity=trade["quantity"],
                    price=trade["price"],
                    gross_value=trade_value,
                    charges=charges,
                    net_value=charges.net_amount,
                    timestamp=datetime.now()
                )
                
                rebalance_result["sell_trades"].append(asdict(trade_detail))
                rebalance_result["total_sell_charges"] += charges.total_charges
                rebalance_result["total_sell_value"] += trade_value
                rebalance_result["net_sell_proceeds"] += charges.net_amount
                
                # Aggregate charge components
                rebalance_result["charge_breakdown"]["brokerage"] += charges.brokerage
                rebalance_result["charge_breakdown"]["stt"] += charges.stt
                rebalance_result["charge_breakdown"]["transaction_charges"] += charges.transaction_charges
                rebalance_result["charge_breakdown"]["sebi_charges"] += charges.sebi_charges
                rebalance_result["charge_breakdown"]["stamp_duty"] += charges.stamp_duty
                rebalance_result["charge_breakdown"]["gst"] += charges.gst
            
            # Process buy trades
            for trade in buy_trades:
                trade_value = trade["quantity"] * trade["price"]
                charges = self.calculate_transaction_charges(trade_value, "BUY")
                
                trade_detail = TradeDetails(
                    trade_id=f"BUY_{trade['symbol']}_{datetime.now().timestamp()}",
                    symbol=trade["symbol"],
                    trade_type="BUY",
                    quantity=trade["quantity"],
                    price=trade["price"],
                    gross_value=trade_value,
                    charges=charges,
                    net_value=charges.net_amount,
                    timestamp=datetime.now()
                )
                
                rebalance_result["buy_trades"].append(asdict(trade_detail))
                rebalance_result["total_buy_charges"] += charges.total_charges
                rebalance_result["total_buy_value"] += trade_value
                rebalance_result["net_buy_cost"] += charges.net_amount
                
                # Aggregate charge components
                rebalance_result["charge_breakdown"]["brokerage"] += charges.brokerage
                rebalance_result["charge_breakdown"]["stt"] += charges.stt
                rebalance_result["charge_breakdown"]["transaction_charges"] += charges.transaction_charges
                rebalance_result["charge_breakdown"]["sebi_charges"] += charges.sebi_charges
                rebalance_result["charge_breakdown"]["stamp_duty"] += charges.stamp_duty
                rebalance_result["charge_breakdown"]["gst"] += charges.gst
            
            # Calculate totals
            rebalance_result["total_charges"] = rebalance_result["total_sell_charges"] + rebalance_result["total_buy_charges"]
            
            logger.info(f"💰 Portfolio rebalance charges calculated: Sell charges = ₹{rebalance_result['total_sell_charges']:,.2f}, Buy charges = ₹{rebalance_result['total_buy_charges']:,.2f}")
            logger.info(f"📊 Total charges = ₹{rebalance_result['total_charges']:,.2f}")
            
            return rebalance_result
            
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio rebalance charges: {e}")
            raise
    
    def estimate_annual_charge_impact(self, 
                                    portfolio_value: float, 
                                    rebalance_frequency: str, 
                                    average_portfolio_churn: float = 0.5) -> Dict[str, Any]:
        """
        Estimate annual charge impact for a given portfolio and rebalancing strategy
        
        Args:
            portfolio_value: Portfolio value in ₹
            rebalance_frequency: "monthly", "weekly", or "daily"
            average_portfolio_churn: Average percentage of portfolio that changes per rebalance (0.0-1.0)
            
        Returns:
            Dictionary with annual charge impact estimation
        """
        try:
            # Determine rebalancing frequency
            if rebalance_frequency.lower() == "monthly":
                rebalances_per_year = 12
            elif rebalance_frequency.lower() == "weekly":
                rebalances_per_year = 52
            elif rebalance_frequency.lower() == "daily":
                rebalances_per_year = 252  # Trading days
            else:
                raise ValueError(f"Unknown rebalance frequency: {rebalance_frequency}")
            
            # Calculate annual turnover
            turnover_per_rebalance = portfolio_value * average_portfolio_churn
            annual_turnover = turnover_per_rebalance * rebalances_per_year
            
            # Estimate charges (assuming equal buy/sell split)
            buy_turnover = annual_turnover * 0.5
            sell_turnover = annual_turnover * 0.5
            
            # Calculate charge components
            total_stt = annual_turnover * self.CHARGE_RATES["stt_rate"]
            total_transaction_charges = annual_turnover * self.CHARGE_RATES["nse_transaction_rate"]  # Using NSE rates
            total_sebi_charges = annual_turnover * self.CHARGE_RATES["sebi_rate"]
            total_stamp_duty = buy_turnover * self.CHARGE_RATES["stamp_duty_rate"]  # Only on buys
            total_brokerage = annual_turnover * (self.custom_brokerage_rate or self.CHARGE_RATES["default_brokerage"])
            
            # GST on applicable charges
            taxable_base = total_brokerage + total_sebi_charges + total_transaction_charges
            total_gst = taxable_base * self.CHARGE_RATES["gst_rate"]
            
            # Total annual charges
            total_annual_charges = (total_stt + total_transaction_charges + total_sebi_charges + 
                                  total_stamp_duty + total_brokerage + total_gst)
            
            impact_analysis = {
                "portfolio_value": portfolio_value,
                "rebalance_frequency": rebalance_frequency,
                "rebalances_per_year": rebalances_per_year,
                "average_portfolio_churn": average_portfolio_churn,
                "annual_turnover": annual_turnover,
                "charge_breakdown": {
                    "stt": total_stt,
                    "transaction_charges": total_transaction_charges,
                    "sebi_charges": total_sebi_charges,
                    "stamp_duty": total_stamp_duty,
                    "brokerage": total_brokerage,
                    "gst": total_gst,
                    "total": total_annual_charges
                },
                "impact_metrics": {
                    "annual_charge_percentage": (total_annual_charges / portfolio_value) * 100,
                    "monthly_charge_percentage": (total_annual_charges / portfolio_value / 12) * 100,
                    "charge_per_rebalance": total_annual_charges / rebalances_per_year,
                    "charge_per_lakh_portfolio": (total_annual_charges / portfolio_value) * 100000
                }
            }
            
            logger.info(f"📊 Annual charge impact estimated: {impact_analysis['impact_metrics']['annual_charge_percentage']:.2f}% of portfolio value")
            
            return impact_analysis
            
        except Exception as e:
            logger.error(f"❌ Error estimating annual charge impact: {e}")
            raise
    
    def get_charge_rates_info(self) -> Dict[str, Any]:
        """
        Get information about current charge rates and calculator configuration
        
        Returns:
            Dictionary with charge rates and configuration info
        """
        return {
            "charge_rates": self.CHARGE_RATES.copy(),
            "configuration": {
                "default_exchange": self.default_exchange,
                "custom_brokerage_rate": self.custom_brokerage_rate,
                "custom_brokerage_percentage": self.custom_brokerage_rate * 100
            },
            "rate_descriptions": {
                "stt_rate": "Securities Transaction Tax - 0.1% on buy & sell",
                "nse_transaction_rate": "NSE Transaction Charges - 0.00297% of turnover",
                "bse_transaction_rate": "BSE Transaction Charges - 0.00375% of turnover",
                "sebi_rate": "SEBI Charges - ₹10 per crore (0.0001% of turnover)",
                "stamp_duty_rate": "Stamp Duty - 0.015% on buy side only",
                "gst_rate": "GST - 18% on (brokerage + SEBI + transaction charges)",
                "default_brokerage": "Default Brokerage - ₹0 for delivery trades"
            }
        }

# Helper functions for easy usage
def calculate_single_trade_charges(trade_value: float, 
                                 trade_type: str, 
                                 exchange: str = "NSE", 
                                 custom_brokerage: float = 0.0) -> Dict[str, Any]:
    """
    Quick function to calculate charges for a single trade
    
    Args:
        trade_value: Total transaction value
        trade_type: "BUY" or "SELL"
        exchange: "NSE" or "BSE"
        custom_brokerage: Custom brokerage rate (as decimal)
        
    Returns:
        Dictionary with charge breakdown (JSON-serializable)
    """
    calculator = BrokerageCalculator(exchange, custom_brokerage)
    charges = calculator.calculate_transaction_charges(trade_value, trade_type, exchange)
    
    # Convert to dict and handle datetime serialization
    charges_dict = asdict(charges)
    if charges_dict.get('calculation_timestamp'):
        charges_dict['calculation_timestamp'] = charges_dict['calculation_timestamp'].isoformat()
    
    return charges_dict

def estimate_portfolio_charges(portfolio_value: float, 
                             rebalance_frequency: str = "monthly", 
                             portfolio_churn: float = 0.5) -> Dict[str, Any]:
    """
    Quick function to estimate annual charges for a portfolio
    
    Args:
        portfolio_value: Portfolio value in ₹
        rebalance_frequency: "monthly", "weekly", or "daily"
        portfolio_churn: Average portfolio turnover per rebalance (0.0-1.0)
        
    Returns:
        Dictionary with annual charge impact analysis
    """
    calculator = BrokerageCalculator()
    return calculator.estimate_annual_charge_impact(portfolio_value, rebalance_frequency, portfolio_churn)

# Example usage and testing
if __name__ == "__main__":
    # Test the brokerage calculator
    calculator = BrokerageCalculator()
    
    # Test single trade
    print("🧪 Testing single trade calculation...")
    trade_charges = calculator.calculate_transaction_charges(100000, "BUY", "NSE")
    print(f"Buy ₹1,00,000 on NSE: Total charges = ₹{trade_charges.total_charges:.2f}")
    print(f"Breakdown: STT=₹{trade_charges.stt:.2f}, Transaction=₹{trade_charges.transaction_charges:.2f}, Stamp=₹{trade_charges.stamp_duty:.2f}")
    
    # Test portfolio rebalance
    print("\n🧪 Testing portfolio rebalance calculation...")
    sell_trades = [{"symbol": "RELIANCE", "quantity": 100, "price": 2500}]
    buy_trades = [{"symbol": "TCS", "quantity": 50, "price": 3600}]
    
    rebalance_result = calculator.calculate_portfolio_rebalance_charges(sell_trades, buy_trades)
    print(f"Rebalance charges: ₹{rebalance_result['total_charges']:.2f}")
    
    # Test annual impact estimation
    print("\n🧪 Testing annual impact estimation...")
    impact = calculator.estimate_annual_charge_impact(1000000, "monthly", 0.5)
    print(f"Annual impact for ₹10L portfolio with monthly rebalancing: {impact['impact_metrics']['annual_charge_percentage']:.2f}%")
