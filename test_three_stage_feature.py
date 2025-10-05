"""
Test script for three-stage completion feature.
Tests database schema, API functions, and percentage calculations.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import db_cache

def test_database_schema():
    """Test that the database has the correct schema."""
    print("\n" + "="*60)
    print("TEST 1: Database Schema")
    print("="*60)
    
    db_cache.init_db()
    
    with db_cache.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check task_completions table structure
        cursor.execute("PRAGMA table_info(task_completions)")
        columns = cursor.fetchall()
        
        column_names = [col[1] for col in columns]
        print(f"✓ task_completions columns: {column_names}")
        
        required_columns = ['task_id', 'task_type', 'completed', 'first_read', 'notes', 'revision', 'completed_at', 'month_year']
        for col in required_columns:
            if col in column_names:
                print(f"  ✓ Column '{col}' exists")
            else:
                print(f"  ✗ Column '{col}' MISSING!")
                return False
    
    print("\n✅ Database schema test PASSED!")
    return True


def test_mark_task_stage():
    """Test marking individual stages."""
    print("\n" + "="*60)
    print("TEST 2: Mark Task Stages")
    print("="*60)
    
    test_task_id = "daily_test_task_123"
    
    # Mark first_read as complete
    print("\n1. Marking 'first_read' as complete...")
    success = db_cache.mark_task_stage(test_task_id, "daily", "first_read", True, "oct_2025")
    if success:
        print("  ✓ first_read marked")
    else:
        print("  ✗ Failed to mark first_read")
        return False
    
    # Mark notes as complete
    print("\n2. Marking 'notes' as complete...")
    success = db_cache.mark_task_stage(test_task_id, "daily", "notes", True, "oct_2025")
    if success:
        print("  ✓ notes marked")
    else:
        print("  ✗ Failed to mark notes")
        return False
    
    # Verify data in database
    print("\n3. Verifying data in database...")
    with db_cache.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT first_read, notes, revision 
            FROM task_completions 
            WHERE task_id = ?
        """, (test_task_id,))
        row = cursor.fetchone()
        
        if row:
            first_read, notes, revision = row
            print(f"  first_read: {first_read} (expected: 1)")
            print(f"  notes: {notes} (expected: 1)")
            print(f"  revision: {revision} (expected: 0)")
            
            if first_read == 1 and notes == 1 and revision == 0:
                print("  ✓ Data verified correctly!")
            else:
                print("  ✗ Data mismatch!")
                return False
        else:
            print("  ✗ No data found!")
            return False
    
    # Mark revision as complete
    print("\n4. Marking 'revision' as complete...")
    success = db_cache.mark_task_stage(test_task_id, "daily", "revision", True, "oct_2025")
    if success:
        print("  ✓ revision marked")
    else:
        print("  ✗ Failed to mark revision")
        return False
    
    # Verify all three stages are complete
    print("\n5. Verifying all three stages complete...")
    with db_cache.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT first_read, notes, revision 
            FROM task_completions 
            WHERE task_id = ?
        """, (test_task_id,))
        row = cursor.fetchone()
        
        if row:
            first_read, notes, revision = row
            print(f"  first_read: {first_read}")
            print(f"  notes: {notes}")
            print(f"  revision: {revision}")
            
            if first_read == 1 and notes == 1 and revision == 1:
                print("  ✓ All stages complete!")
            else:
                print("  ✗ Not all stages complete!")
                return False
        else:
            print("  ✗ No data found!")
            return False
    
    # Test unmarking a stage
    print("\n6. Unmarking 'notes' stage...")
    success = db_cache.mark_task_stage(test_task_id, "daily", "notes", False, "oct_2025")
    if success:
        print("  ✓ notes unmarked")
    else:
        print("  ✗ Failed to unmark notes")
        return False
    
    # Verify notes is now 0
    with db_cache.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT notes FROM task_completions WHERE task_id = ?
        """, (test_task_id,))
        row = cursor.fetchone()
        
        if row and row[0] == 0:
            print("  ✓ notes correctly unmarked (0)")
        else:
            print(f"  ✗ notes value incorrect: {row[0] if row else 'None'}")
            return False
    
    # Cleanup
    print("\n7. Cleaning up test data...")
    with db_cache.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM task_completions WHERE task_id = ?", (test_task_id,))
        conn.commit()
        print("  ✓ Test data cleaned up")
    
    print("\n✅ Mark task stages test PASSED!")
    return True


def test_progress_calculation():
    """Test progress percentage calculation."""
    print("\n" + "="*60)
    print("TEST 3: Progress Calculation")
    print("="*60)
    
    # Create test tasks
    test_tasks = [
        ("daily_progress_1", "daily"),
        ("daily_progress_2", "daily"),
        ("daily_progress_3", "daily"),
    ]
    
    print("\n1. Creating 3 test tasks...")
    for task_id, task_type in test_tasks:
        # Mark different stages for each task
        if task_id == "daily_progress_1":
            # Task 1: All 3 stages complete (3/3)
            db_cache.mark_task_stage(task_id, task_type, "first_read", True, "oct_2025")
            db_cache.mark_task_stage(task_id, task_type, "notes", True, "oct_2025")
            db_cache.mark_task_stage(task_id, task_type, "revision", True, "oct_2025")
            print("  ✓ Task 1: 3/3 stages complete")
        elif task_id == "daily_progress_2":
            # Task 2: 2/3 stages complete
            db_cache.mark_task_stage(task_id, task_type, "first_read", True, "oct_2025")
            db_cache.mark_task_stage(task_id, task_type, "notes", True, "oct_2025")
            print("  ✓ Task 2: 2/3 stages complete")
        else:
            # Task 3: 1/3 stages complete
            db_cache.mark_task_stage(task_id, task_type, "first_read", True, "oct_2025")
            print("  ✓ Task 3: 1/3 stages complete")
    
    print("\n2. Calculating expected percentage...")
    # Total: 3 tasks × 3 stages = 9 total stages
    # Completed: 3 + 2 + 1 = 6 completed stages
    # Percentage: (6 / 9) × 100 = 66.67%
    expected_completed = 6
    print(f"  Expected completed stages: {expected_completed}")
    print(f"  Expected percentage: 66.67%")
    
    print("\n3. Verifying data in database...")
    with db_cache.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Count completed stages
        cursor.execute("""
            SELECT 
                SUM(first_read) + SUM(notes) + SUM(revision) as total_completed
            FROM task_completions 
            WHERE task_id IN (?, ?, ?)
        """, tuple(task_id for task_id, _ in test_tasks))
        
        result = cursor.fetchone()
        actual_completed = result[0] if result else 0
        
        print(f"  Actual completed stages: {actual_completed}")
        
        if actual_completed == expected_completed:
            print("  ✓ Completed stages match!")
        else:
            print(f"  ✗ Mismatch! Expected {expected_completed}, got {actual_completed}")
            return False
    
    # Calculate percentage
    total_stages = 9  # 3 tasks × 3 stages
    percentage = (actual_completed / total_stages) * 100
    print(f"\n4. Calculated percentage: {percentage:.2f}%")
    
    if abs(percentage - 66.67) < 0.1:
        print("  ✓ Percentage calculation correct!")
    else:
        print(f"  ✗ Percentage incorrect! Expected ~66.67%, got {percentage:.2f}%")
        return False
    
    # Cleanup
    print("\n5. Cleaning up test data...")
    with db_cache.get_db_connection() as conn:
        cursor = conn.cursor()
        for task_id, _ in test_tasks:
            cursor.execute("DELETE FROM task_completions WHERE task_id = ?", (task_id,))
        conn.commit()
        print("  ✓ Test data cleaned up")
    
    print("\n✅ Progress calculation test PASSED!")
    return True


def test_merge_completion_status():
    """Test that completion status is properly merged with sheet data."""
    print("\n" + "="*60)
    print("TEST 4: Merge Completion Status")
    print("="*60)
    
    # Create mock data
    test_rows = [
        ["id", "monthly_task_id", "week_no", "Date", "Task", "Status"],
        ["merge_test_1", "M1", "1", "2025-10-01", "Test Task 1", "Pending"],
        ["merge_test_2", "M2", "1", "2025-10-01", "Test Task 2", "Pending"]
    ]
    
    # Mark stages for first task
    print("\n1. Marking stages for first task...")
    db_cache.mark_task_stage("daily_merge_test_1", "daily", "first_read", True, "oct_2025")
    db_cache.mark_task_stage("daily_merge_test_1", "daily", "notes", True, "oct_2025")
    print("  ✓ First task: 2/3 stages complete")
    
    # Create mock completions dict
    print("\n2. Creating mock completions data...")
    with db_cache.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT task_id, completed, first_read, notes, revision 
            FROM task_completions
            WHERE task_id LIKE 'daily_merge_test_%'
        """)
        
        completions = {
            row[0]: {
                'completed': row[1],
                'first_read': row[2],
                'notes': row[3],
                'revision': row[4]
            } for row in cursor.fetchall()
        }
    
    print(f"  Completions data: {completions}")
    
    # Merge completion status
    print("\n3. Merging completion status...")
    merged = db_cache._merge_completion_status(test_rows, completions, "daily")
    
    print(f"\n4. Verifying merged data...")
    print(f"  Merged header: {merged[0]}")
    
    # Check that new columns exist
    if "first_read" in merged[0] and "notes" in merged[0] and "revision" in merged[0]:
        print("  ✓ Three-stage columns added to header")
    else:
        print("  ✗ Three-stage columns NOT found in header!")
        return False
    
    # Check first task data
    first_read_idx = merged[0].index("first_read")
    notes_idx = merged[0].index("notes")
    revision_idx = merged[0].index("revision")
    
    task1_row = merged[1]
    print(f"\n  Task 1 data:")
    print(f"    first_read: {task1_row[first_read_idx]} (expected: 1)")
    print(f"    notes: {task1_row[notes_idx]} (expected: 1)")
    print(f"    revision: {task1_row[revision_idx]} (expected: 0)")
    
    if (task1_row[first_read_idx] == 1 and 
        task1_row[notes_idx] == 1 and 
        task1_row[revision_idx] == 0):
        print("  ✓ Task 1 stages merged correctly!")
    else:
        print("  ✗ Task 1 stages incorrect!")
        return False
    
    # Check second task (no completions)
    task2_row = merged[2]
    print(f"\n  Task 2 data:")
    print(f"    first_read: {task2_row[first_read_idx]} (expected: 0)")
    print(f"    notes: {task2_row[notes_idx]} (expected: 0)")
    print(f"    revision: {task2_row[revision_idx]} (expected: 0)")
    
    if (task2_row[first_read_idx] == 0 and 
        task2_row[notes_idx] == 0 and 
        task2_row[revision_idx] == 0):
        print("  ✓ Task 2 stages merged correctly (all 0)!")
    else:
        print("  ✗ Task 2 stages incorrect!")
        return False
    
    # Cleanup
    print("\n5. Cleaning up test data...")
    with db_cache.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM task_completions WHERE task_id LIKE 'daily_merge_test_%'")
        conn.commit()
        print("  ✓ Test data cleaned up")
    
    print("\n✅ Merge completion status test PASSED!")
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("THREE-STAGE COMPLETION FEATURE - TEST SUITE")
    print("="*60)
    
    tests = [
        ("Database Schema", test_database_schema),
        ("Mark Task Stages", test_mark_task_stage),
        ("Progress Calculation", test_progress_calculation),
        ("Merge Completion Status", test_merge_completion_status),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ TEST FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ✗")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\nYour three-stage completion feature is working correctly!")
        print("\nFeatures tested:")
        print("  ✓ Database schema with three-stage columns")
        print("  ✓ Marking individual stages (first_read, notes, revision)")
        print("  ✓ Progress calculation (completed_stages / total_stages × 100)")
        print("  ✓ Merging completion status with sheet data")
        return True
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("Please review the errors above and fix the issues.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
