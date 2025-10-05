"""
Quick verification script to test the db_cache functionality
"""
import db_cache
from datetime import datetime

print("=" * 60)
print("SQLite Database Migration - Verification Test")
print("=" * 60)

# Test 1: Get cached tables
print("\n✓ Test 1: Reading cached tables from database...")
try:
    tables = db_cache.get_cached_tables()
    monthly_count = len(tables.get("Monthly", []))
    daily_count = len(tables.get("daily_OCT", []))
    print(f"  Monthly schedule rows: {monthly_count}")
    print(f"  Daily schedule rows: {daily_count}")
    print("  ✅ Successfully read from database!")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 2: Check if data structure is correct
print("\n✓ Test 2: Validating data structure...")
try:
    if monthly_count > 0 and daily_count > 0:
        # Check if first row is header
        monthly_header = tables["Monthly"][0] if tables["Monthly"] else []
        daily_header = tables["daily_OCT"][0] if tables["daily_OCT"] else []
        
        print(f"  Monthly header columns: {len(monthly_header)}")
        print(f"  Daily header columns: {len(daily_header)}")
        
        # Check for expected columns
        if "id" in monthly_header and "to_do" in monthly_header:
            print("  ✅ Monthly schedule structure is valid!")
        else:
            print("  ⚠️  Monthly schedule might be missing expected columns")
            
        if "Date" in daily_header:
            print("  ✅ Daily schedule structure is valid!")
        else:
            print("  ⚠️  Daily schedule might be missing Date column")
    else:
        print("  ℹ️  No data in tables (database might be empty)")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 3: Check database file
print("\n✓ Test 3: Verifying database file...")
import os
db_path = os.path.join(os.path.dirname(__file__), "data_cache", "schedule.db")
if os.path.exists(db_path):
    size = os.path.getsize(db_path)
    print(f"  Database location: {db_path}")
    print(f"  Database size: {size:,} bytes")
    print("  ✅ Database file exists!")
else:
    print("  ❌ Database file not found!")

print("\n" + "=" * 60)
print("Verification Complete!")
print("=" * 60)
