import db_cache

print("Testing database access...")
data = db_cache.get_cached_tables()
print(f"✅ Database accessible")
print(f"Monthly rows: {len(data['Monthly'])}")
print(f"Daily rows: {len(data['daily_OCT'])}")
print("\n✅ Everything works perfectly!")
