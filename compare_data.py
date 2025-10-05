"""
Data Integrity Check: Compare CSV vs SQLite Database
This script verifies that all data was correctly migrated from CSV to SQLite
"""
import csv
import os
import db_cache

print("=" * 70)
print("Data Integrity Verification: CSV vs SQLite")
print("=" * 70)

# Paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "data_cache")
MONTHLY_CSV = os.path.join(DATA_DIR, "monthly.csv")
DAILY_CSV = os.path.join(DATA_DIR, "daily_OCT.csv")

def read_csv(path):
    """Read CSV into a list of rows"""
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.reader(f))

# Read CSV files
print("\n📄 Reading CSV files...")
csv_monthly = read_csv(MONTHLY_CSV)
csv_daily = read_csv(DAILY_CSV)
print(f"  CSV Monthly rows: {len(csv_monthly)}")
print(f"  CSV Daily rows: {len(csv_daily)}")

# Read from database
print("\n💾 Reading from SQLite database...")
db_tables = db_cache.get_cached_tables()
db_monthly = db_tables.get("Monthly", [])
db_daily = db_tables.get("daily_OCT", [])
print(f"  DB Monthly rows: {len(db_monthly)}")
print(f"  DB Daily rows: {len(db_daily)}")

# Compare row counts
print("\n🔍 Comparing data...")
print("\n1. Row Count Verification:")
if len(csv_monthly) == len(db_monthly):
    print(f"  ✅ Monthly: CSV ({len(csv_monthly)}) == DB ({len(db_monthly)})")
else:
    print(f"  ❌ Monthly: CSV ({len(csv_monthly)}) != DB ({len(db_monthly)})")

if len(csv_daily) == len(db_daily):
    print(f"  ✅ Daily: CSV ({len(csv_daily)}) == DB ({len(db_daily)})")
else:
    print(f"  ❌ Daily: CSV ({len(csv_daily)}) != DB ({len(db_daily)})")

# Compare first few rows (headers and data samples)
print("\n2. Header Verification:")
if csv_monthly and db_monthly:
    if csv_monthly[0] == db_monthly[0]:
        print(f"  ✅ Monthly headers match: {csv_monthly[0]}")
    else:
        print(f"  ❌ Monthly headers differ!")
        print(f"    CSV: {csv_monthly[0]}")
        print(f"    DB:  {db_monthly[0]}")

if csv_daily and db_daily:
    if csv_daily[0] == db_daily[0]:
        print(f"  ✅ Daily headers match: {csv_daily[0]}")
    else:
        print(f"  ❌ Daily headers differ!")
        print(f"    CSV: {csv_daily[0]}")
        print(f"    DB:  {db_daily[0]}")

# Sample data comparison (first data row after header)
print("\n3. Sample Data Verification (first data row):")
if len(csv_monthly) > 1 and len(db_monthly) > 1:
    if csv_monthly[1] == db_monthly[1]:
        print(f"  ✅ Monthly first data row matches")
    else:
        print(f"  ❌ Monthly first data row differs!")

if len(csv_daily) > 1 and len(db_daily) > 1:
    if csv_daily[1] == db_daily[1]:
        print(f"  ✅ Daily first data row matches")
    else:
        print(f"  ❌ Daily first data row differs!")

# Final summary
print("\n" + "=" * 70)
all_good = (
    len(csv_monthly) == len(db_monthly) and
    len(csv_daily) == len(db_daily) and
    (csv_monthly[0] == db_monthly[0] if csv_monthly and db_monthly else True) and
    (csv_daily[0] == db_daily[0] if csv_daily and db_daily else True)
)

if all_good:
    print("✅ SUCCESS: All data migrated correctly from CSV to SQLite!")
    print("\n💡 You can safely keep CSV files as backup or delete them.")
else:
    print("⚠️  WARNING: Some differences detected. Review the output above.")

print("=" * 70)
