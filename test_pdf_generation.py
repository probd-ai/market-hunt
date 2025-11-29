#!/usr/bin/env python3
"""
Test script for PDF tradebook generation
"""

import json
from datetime import datetime
from tradebook_pdf_generator import generate_tradebook_pdf

# Sample simulation results for testing
test_simulation_results = {
    "params": {
        "strategy_id": "test_strategy_123",
        "universe": "NIFTY100",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "portfolio_base_value": 1000000,
        "max_holdings": 10,
        "rebalance_frequency": "monthly",
        "rebalance_type": "equal_weight",
        "momentum_ranking": "20_day_return",
        "include_brokerage": True,
        "exchange": "NSE"
    },
    "final_portfolio_value": 1150000,
    "cumulative_charges": 5500,
    "charge_impact_percent": 0.55,
    "portfolio_history": [
        {"date": "2024-01-01", "portfolio_value": 1000000, "rebalanced": True},
        {"date": "2024-01-02", "portfolio_value": 1005000, "rebalanced": False},
        {"date": "2024-01-03", "portfolio_value": 1008000, "rebalanced": False},
        {"date": "2024-02-01", "portfolio_value": 1050000, "rebalanced": True},
        {"date": "2024-02-02", "portfolio_value": 1055000, "rebalanced": False},
        {"date": "2024-06-30", "portfolio_value": 1150000, "rebalanced": False}
    ],
    "trades": [
        {
            "date": "2024-01-01",
            "symbol": "RELIANCE",
            "action": "BUY",
            "quantity": 100,
            "price": 2500.00,
            "value": 250000,
            "pnl": 0
        },
        {
            "date": "2024-01-01",
            "symbol": "TCS",
            "action": "BUY",
            "quantity": 50,
            "price": 3600.00,
            "value": 180000,
            "pnl": 0
        },
        {
            "date": "2024-02-01",
            "symbol": "RELIANCE",
            "action": "SELL",
            "quantity": 100,
            "price": 2650.00,
            "value": 265000,
            "pnl": 15000
        },
        {
            "date": "2024-02-01",
            "symbol": "INFY",
            "action": "BUY",
            "quantity": 80,
            "price": 1400.00,
            "value": 112000,
            "pnl": 0
        }
    ]
}

def test_pdf_generation():
    """Test PDF generation with sample data"""
    try:
        print("🔄 Testing PDF tradebook generation...")
        
        # Generate PDF
        pdf_bytes = generate_tradebook_pdf(test_simulation_results, "Test_Strategy")
        
        # Save test PDF
        with open("test_tradebook.pdf", "wb") as f:
            f.write(pdf_bytes)
        
        print(f"✅ PDF generated successfully!")
        print(f"📄 File size: {len(pdf_bytes):,} bytes")
        print(f"💾 Saved as: test_tradebook.pdf")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pdf_generation()
    if success:
        print("\n🎉 PDF generation test completed successfully!")
    else:
        print("\n❌ PDF generation test failed!")
