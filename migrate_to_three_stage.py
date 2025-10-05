"""
Database migration script to add three-stage tracking columns.
Converts existing single 'completed' field to three-stage tracking.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from datetime import datetime
import pytz

# Import the database configuration
from db_cache import DB_PATH, IST

def migrate_database():
    """
    Migrate the database to support three-stage tracking.
    Adds first_read, notes, revision columns to task_completions table.
    """
    print("="*60)
    print("DATABASE MIGRATION: Three-Stage Tracking")
    print("="*60)
    
    if not os.path.exists(DB_PATH):
        print(f"\n✗ Database not found at: {DB_PATH}")
        print("Please run refresh_cache.py first to create the database.")
        return False
    
    print(f"\n✓ Database found: {DB_PATH}")
    
    # Backup the database first
    backup_path = DB_PATH + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n1. Creating backup: {backup_path}")
    
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"   ✓ Backup created successfully")
    except Exception as e:
        print(f"   ✗ Backup failed: {e}")
        print("   Migration aborted for safety.")
        return False
    
    # Connect to database
    print(f"\n2. Connecting to database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current schema
    print(f"\n3. Checking current schema...")
    cursor.execute("PRAGMA table_info(task_completions)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    print(f"   Current columns: {column_names}")
    
    # Check if migration needed
    if 'first_read' in column_names:
        print(f"\n   ✓ Database already migrated!")
        print(f"   No migration needed.")
        conn.close()
        return True
    
    print(f"\n4. Starting migration...")
    
    try:
        # Step 1: Rename old table
        print(f"\n   Step 1: Backing up old table structure...")
        cursor.execute("""
            ALTER TABLE task_completions 
            RENAME TO task_completions_old
        """)
        print(f"   ✓ Old table renamed to task_completions_old")
        
        # Step 2: Create new table with three-stage columns
        print(f"\n   Step 2: Creating new table with three-stage columns...")
        cursor.execute("""
            CREATE TABLE task_completions (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                first_read INTEGER NOT NULL DEFAULT 0,
                notes INTEGER NOT NULL DEFAULT 0,
                revision INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                month_year TEXT
            )
        """)
        print(f"   ✓ New table created")
        
        # Step 3: Migrate data
        print(f"\n   Step 3: Migrating existing completion data...")
        cursor.execute("SELECT COUNT(*) FROM task_completions_old")
        old_count = cursor.fetchone()[0]
        print(f"   Found {old_count} existing completions to migrate")
        
        if old_count > 0:
            # For daily tasks with completed=1, mark all three stages as complete
            # For monthly tasks, just migrate the completed field
            cursor.execute("""
                INSERT INTO task_completions 
                (task_id, task_type, completed, first_read, notes, revision, completed_at, month_year)
                SELECT 
                    task_id,
                    task_type,
                    completed,
                    CASE 
                        WHEN task_type = 'daily' AND completed = 1 THEN 1
                        ELSE 0
                    END as first_read,
                    CASE 
                        WHEN task_type = 'daily' AND completed = 1 THEN 1
                        ELSE 0
                    END as notes,
                    CASE 
                        WHEN task_type = 'daily' AND completed = 1 THEN 1
                        ELSE 0
                    END as revision,
                    completed_at,
                    month_year
                FROM task_completions_old
            """)
            
            migrated_count = cursor.rowcount
            print(f"   ✓ Migrated {migrated_count} records")
            print(f"   Note: Daily tasks marked 'done' now have all 3 stages complete")
        
        # Step 4: Recreate indexes
        print(f"\n   Step 4: Recreating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_completion_month 
            ON task_completions(month_year)
        """)
        print(f"   ✓ Indexes recreated")
        
        # Step 5: Drop old table
        print(f"\n   Step 5: Cleaning up old table...")
        cursor.execute("DROP TABLE task_completions_old")
        print(f"   ✓ Old table dropped")
        
        # Commit changes
        conn.commit()
        print(f"\n   ✓ Migration committed to database")
        
    except Exception as e:
        print(f"\n   ✗ Migration failed: {e}")
        print(f"   Rolling back changes...")
        conn.rollback()
        print(f"   Database unchanged. Backup available at: {backup_path}")
        conn.close()
        return False
    
    # Verify migration
    print(f"\n5. Verifying migration...")
    cursor.execute("PRAGMA table_info(task_completions)")
    new_columns = cursor.fetchall()
    new_column_names = [col[1] for col in new_columns]
    
    print(f"   New columns: {new_column_names}")
    
    required_columns = ['task_id', 'task_type', 'completed', 'first_read', 'notes', 'revision', 'completed_at', 'month_year']
    missing = [col for col in required_columns if col not in new_column_names]
    
    if missing:
        print(f"   ✗ Missing columns: {missing}")
        conn.close()
        return False
    
    print(f"   ✓ All required columns present")
    
    # Show migration summary
    cursor.execute("SELECT COUNT(*) FROM task_completions")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM task_completions 
        WHERE task_type = 'daily' AND first_read = 1 AND notes = 1 AND revision = 1
    """)
    daily_migrated = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM task_completions 
        WHERE task_type = 'monthly' AND completed = 1
    """)
    monthly_migrated = cursor.fetchone()[0]
    
    print(f"\n6. Migration summary:")
    print(f"   Total records: {final_count}")
    print(f"   Daily tasks (3 stages complete): {daily_migrated}")
    print(f"   Monthly tasks (completed): {monthly_migrated}")
    
    conn.close()
    
    print(f"\n✅ MIGRATION COMPLETED SUCCESSFULLY!")
    print(f"\n📋 What changed:")
    print(f"   • Added columns: first_read, notes, revision")
    print(f"   • Daily tasks previously marked 'done' now have all 3 stages complete")
    print(f"   • Monthly tasks unchanged (still use 'completed' field)")
    print(f"   • Backup saved at: {backup_path}")
    
    print(f"\n🚀 You can now use the three-stage completion feature!")
    print(f"   Run: python test_three_stage_feature.py to verify")
    
    return True


if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n" + "="*60)
        print("Next steps:")
        print("="*60)
        print("1. Run tests: python test_three_stage_feature.py")
        print("2. Start app: python app.py")
        print("3. Visit daily schedule page to see three buttons!")
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("Migration failed. Please check the errors above.")
        print("="*60)
        sys.exit(1)
