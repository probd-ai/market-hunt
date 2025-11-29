"""
Test script to verify rebalance date selection logic
"""
from datetime import datetime

def get_rebalance_dates(dates, frequency, date_type):
    """Generate rebalance dates based on frequency and date type"""
    rebalance_dates = set()
    
    if frequency == "monthly":
        # Group dates by month
        monthly_groups = {}
        for date_str in dates:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = (date_obj.year, date_obj.month)
            if month_key not in monthly_groups:
                monthly_groups[month_key] = []
            monthly_groups[month_key].append(date_str)
        
        # Select date based on date_type
        for month_key in sorted(monthly_groups.keys()):
            month_dates = sorted(monthly_groups[month_key])
            if date_type == "first":
                rebalance_dates.add(month_dates[0])
            elif date_type == "last":
                rebalance_dates.add(month_dates[-1])
            elif date_type == "mid":
                mid_index = len(month_dates) // 2
                rebalance_dates.add(month_dates[mid_index])
                
    elif frequency == "weekly":
        # Group dates by week
        weekly_groups = {}
        for date_str in dates:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            week_key = (date_obj.year, date_obj.isocalendar()[1])
            if week_key not in weekly_groups:
                weekly_groups[week_key] = []
            weekly_groups[week_key].append(date_str)
        
        # Select date based on date_type
        for week_key in sorted(weekly_groups.keys()):
            week_dates = sorted(weekly_groups[week_key])
            if date_type == "first":
                rebalance_dates.add(week_dates[0])
            elif date_type == "last":
                rebalance_dates.add(week_dates[-1])
            elif date_type == "mid":
                mid_index = len(week_dates) // 2
                rebalance_dates.add(week_dates[mid_index])
    
    return rebalance_dates

def test_monthly_rebalancing():
    """Test monthly rebalancing with different date types"""
    # Sample dates spanning 2 months with trading days
    test_dates = [
        # January 2025
        "2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08",
        "2025-01-09", "2025-01-10", "2025-01-13", "2025-01-14", "2025-01-15",
        "2025-01-16", "2025-01-17", "2025-01-20", "2025-01-21", "2025-01-22",
        "2025-01-23", "2025-01-24", "2025-01-27", "2025-01-28", "2025-01-29",
        "2025-01-30", "2025-01-31",
        # February 2025
        "2025-02-03", "2025-02-04", "2025-02-05", "2025-02-06", "2025-02-07",
        "2025-02-10", "2025-02-11", "2025-02-12", "2025-02-13", "2025-02-14",
        "2025-02-17", "2025-02-18", "2025-02-19", "2025-02-20", "2025-02-21",
        "2025-02-24", "2025-02-25", "2025-02-26", "2025-02-27", "2025-02-28"
    ]
    
    print("=" * 60)
    print("MONTHLY REBALANCING TEST")
    print("=" * 60)
    
    # Test first available date
    first_dates = sorted(get_rebalance_dates(test_dates, "monthly", "first"))
    print("\n✅ FIRST AVAILABLE DATE:")
    for date in first_dates:
        print(f"   {date} (First trading day of month)")
    
    # Test mid period date
    mid_dates = sorted(get_rebalance_dates(test_dates, "monthly", "mid"))
    print("\n✅ MID PERIOD DATE:")
    for date in mid_dates:
        print(f"   {date} (Middle trading day of month)")
    
    # Test last available date
    last_dates = sorted(get_rebalance_dates(test_dates, "monthly", "last"))
    print("\n✅ LAST AVAILABLE DATE:")
    for date in last_dates:
        print(f"   {date} (Last trading day of month)")
    
    # Verification
    assert first_dates[0] == "2025-01-02", "January first date should be 2025-01-02"
    assert first_dates[1] == "2025-02-03", "February first date should be 2025-02-03"
    assert last_dates[0] == "2025-01-31", "January last date should be 2025-01-31"
    assert last_dates[1] == "2025-02-28", "February last date should be 2025-02-28"
    
    print("\n✅ All monthly rebalancing tests PASSED!")

def test_weekly_rebalancing():
    """Test weekly rebalancing with different date types"""
    # Sample dates spanning 3 weeks
    test_dates = [
        # Week 1 (starts Monday Jan 6)
        "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09", "2025-01-10",
        # Week 2 (starts Monday Jan 13)
        "2025-01-13", "2025-01-14", "2025-01-15", "2025-01-16", "2025-01-17",
        # Week 3 (starts Monday Jan 20)
        "2025-01-20", "2025-01-21", "2025-01-22", "2025-01-23", "2025-01-24"
    ]
    
    print("\n" + "=" * 60)
    print("WEEKLY REBALANCING TEST")
    print("=" * 60)
    
    # Test first available date
    first_dates = sorted(get_rebalance_dates(test_dates, "weekly", "first"))
    print("\n✅ FIRST AVAILABLE DATE:")
    for date in first_dates:
        print(f"   {date} (First trading day of week)")
    
    # Test mid period date
    mid_dates = sorted(get_rebalance_dates(test_dates, "weekly", "mid"))
    print("\n✅ MID PERIOD DATE:")
    for date in mid_dates:
        print(f"   {date} (Middle trading day of week)")
    
    # Test last available date
    last_dates = sorted(get_rebalance_dates(test_dates, "weekly", "last"))
    print("\n✅ LAST AVAILABLE DATE:")
    for date in last_dates:
        print(f"   {date} (Last trading day of week)")
    
    # Verification
    assert first_dates[0] == "2025-01-06", "Week 1 first date should be Monday"
    assert last_dates[0] == "2025-01-10", "Week 1 last date should be Friday"
    
    print("\n✅ All weekly rebalancing tests PASSED!")

if __name__ == "__main__":
    try:
        test_monthly_rebalancing()
        test_weekly_rebalancing()
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED - Rebalance date logic is working correctly!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
