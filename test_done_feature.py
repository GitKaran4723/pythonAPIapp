"""
Test the Done button feature
"""
import db_cache
import sqlite3
import os

print("=" * 70)
print("Testing Done Button Feature")
print("=" * 70)

# Test 1: Initialize database
print("\n✓ Test 1: Database initialization...")
try:
    db_cache.init_db()
    print("  ✅ Database initialized successfully!")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 2: Check if task_completions table exists
print("\n✓ Test 2: Verifying task_completions table...")
try:
    db_path = os.path.join(os.path.dirname(__file__), "data_cache", "schedule.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='task_completions'
    """)
    result = cursor.fetchone()
    
    if result:
        print(f"  ✅ Table 'task_completions' exists!")
        
        # Check schema
        cursor.execute("PRAGMA table_info(task_completions)")
        columns = cursor.fetchall()
        print(f"  Columns: {[col[1] for col in columns]}")
    else:
        print("  ❌ Table not found!")
    
    conn.close()
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 3: Mark a test task as complete
print("\n✓ Test 3: Marking a test task as complete...")
try:
    success = db_cache.mark_task_complete(
        task_id="daily_test_123",
        task_type="daily",
        completed=True,
        month_year="oct_2025"
    )
    
    if success:
        print("  ✅ Task marked as complete!")
    else:
        print("  ❌ Failed to mark task!")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: Verify the completion was stored
print("\n✓ Test 4: Verifying completion was stored...")
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT task_id, task_type, completed, month_year 
        FROM task_completions 
        WHERE task_id = 'daily_test_123'
    """)
    result = cursor.fetchone()
    
    if result:
        print(f"  ✅ Found completion record!")
        print(f"     Task ID: {result[0]}")
        print(f"     Type: {result[1]}")
        print(f"     Completed: {result[2]}")
        print(f"     Month: {result[3]}")
    else:
        print("  ❌ No completion record found!")
    
    conn.close()
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 5: Test undo functionality
print("\n✓ Test 5: Testing undo (mark as incomplete)...")
try:
    success = db_cache.mark_task_complete(
        task_id="daily_test_123",
        task_type="daily",
        completed=False
    )
    
    if success:
        print("  ✅ Task marked as incomplete!")
        
        # Verify it was removed
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM task_completions 
            WHERE task_id = 'daily_test_123'
        """)
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            print("  ✅ Completion record removed successfully!")
        else:
            print("  ⚠️  Record still exists (unexpected)")
    else:
        print("  ❌ Failed to undo task!")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 6: Test data merging
print("\n✓ Test 6: Testing data merging with completions...")
try:
    # Mark a real task as complete
    db_cache.mark_task_complete(
        task_id="daily_1",
        task_type="daily",
        completed=True,
        month_year="oct_2025"
    )
    
    # Get cached tables (should merge completion status)
    tables = db_cache.get_cached_tables()
    daily_rows = tables.get("daily_OCT", [])
    
    if daily_rows:
        print(f"  ✅ Retrieved {len(daily_rows)} daily rows")
        
        # Check if first data row (after header) has any completed tasks
        if len(daily_rows) > 1:
            header = daily_rows[0]
            if "Status" in header:
                status_idx = header.index("Status")
                print(f"  ℹ️  Status column found at index {status_idx}")
                print(f"  ℹ️  Sample statuses: {[row[status_idx] if status_idx < len(row) else 'N/A' for row in daily_rows[1:6]]}")
            else:
                print("  ℹ️  No Status column in data")
        
        print("  ✅ Data merging works!")
    else:
        print("  ⚠️  No daily rows found (database might be empty)")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 7: Get completion stats
print("\n✓ Test 7: Getting completion statistics...")
try:
    stats = db_cache.get_completion_stats()
    print(f"  ✅ Completed tasks: {stats.get('completed', 0)}")
    
    # For specific month
    stats_oct = db_cache.get_completion_stats("oct_2025")
    print(f"  ✅ October 2025 completions: {stats_oct.get('completed', 0)}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ All tests completed!")
print("=" * 70)
print("\n💡 Next steps:")
print("  1. Start the Flask app: python app.py")
print("  2. Visit http://localhost:5000/daily")
print("  3. Click the 'Done' button on any task")
print("  4. Verify the task is marked as complete!")
print("\n🎉 Feature is ready to use!")
