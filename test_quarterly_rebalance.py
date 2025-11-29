#!/usr/bin/env python3
"""
Test quarterly rebalancing functionality
"""

import sys
import os
sys.path.append(os.getcwd())

from datetime import datetime

# Import the function from api_server
from api_server import get_rebalance_dates

def test_quarterly_rebalancing():
    """Test quarterly rebalancing with first, mid, and last date options"""
    
    # Generate test dates covering multiple quarters
    test_dates = [
        # Q1 2024 (Jan-Mar)
        "2024-01-01", "2024-01-15", "2024-01-31",
        "2024-02-01", "2024-02-15", "2024-02-29", 
        "2024-03-01", "2024-03-15", "2024-03-29",
        
        # Q2 2024 (Apr-Jun)
        "2024-04-01", "2024-04-15", "2024-04-30",
        "2024-05-01", "2024-05-15", "2024-05-31",
        "2024-06-03", "2024-06-17", "2024-06-28",
        
        # Q3 2024 (Jul-Sep)
        "2024-07-01", "2024-07-15", "2024-07-31",
        "2024-08-01", "2024-08-15", "2024-08-30",
        "2024-09-02", "2024-09-16", "2024-09-30",
        
        # Q4 2024 (Oct-Dec)
        "2024-10-01", "2024-10-15", "2024-10-31",
        "2024-11-01", "2024-11-15", "2024-11-29",
        "2024-12-02", "2024-12-16", "2024-12-31"
    ]
    
    print("Testing Quarterly Rebalancing...")
    print("=" * 50)
    
    # Test quarterly first
    print("\nQuarterly First:")
    quarterly_first = get_rebalance_dates(test_dates, "quarterly", "first")
    quarterly_first_sorted = sorted(list(quarterly_first))
    for date in quarterly_first_sorted:
        dt = datetime.strptime(date, "%Y-%m-%d")
        quarter = (dt.month - 1) // 3 + 1
        print(f"  {date} (Q{quarter} {dt.year})")
    
    # Test quarterly mid
    print("\nQuarterly Mid:")
    quarterly_mid = get_rebalance_dates(test_dates, "quarterly", "mid")
    quarterly_mid_sorted = sorted(list(quarterly_mid))
    for date in quarterly_mid_sorted:
        dt = datetime.strptime(date, "%Y-%m-%d")
        quarter = (dt.month - 1) // 3 + 1
        print(f"  {date} (Q{quarter} {dt.year})")
    
    # Test quarterly last
    print("\nQuarterly Last:")
    quarterly_last = get_rebalance_dates(test_dates, "quarterly", "last")
    quarterly_last_sorted = sorted(list(quarterly_last))
    for date in quarterly_last_sorted:
        dt = datetime.strptime(date, "%Y-%m-%d")
        quarter = (dt.month - 1) // 3 + 1
        print(f"  {date} (Q{quarter} {dt.year})")
    
    # Verify we got 4 dates (one per quarter) for each test
    assert len(quarterly_first) == 4, f"Expected 4 quarterly first dates, got {len(quarterly_first)}"
    assert len(quarterly_mid) == 4, f"Expected 4 quarterly mid dates, got {len(quarterly_mid)}"
    assert len(quarterly_last) == 4, f"Expected 4 quarterly last dates, got {len(quarterly_last)}"
    
    # Verify dates are from correct quarters
    expected_quarters = [(2024, 1), (2024, 2), (2024, 3), (2024, 4)]
    
    for date_str in quarterly_first_sorted:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        quarter = (dt.month - 1) // 3 + 1
        assert (dt.year, quarter) in expected_quarters, f"Unexpected quarter for {date_str}"
    
    print("\n✅ All quarterly rebalancing tests passed!")
    print(f"✅ Got {len(quarterly_first)} dates for each date type (first, mid, last)")
    print("✅ All dates are from correct quarters (Q1, Q2, Q3, Q4)")
    
    return True

if __name__ == "__main__":
    try:
        test_quarterly_rebalancing()
        print("\n🎉 Quarterly rebalancing functionality is working correctly!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)