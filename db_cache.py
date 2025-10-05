# db_cache.py
import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from contextlib import contextmanager

import pytz
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ------------ Configuration ------------
# Directory to store database
DATA_DIR = os.path.join(os.path.dirname(__file__), "data_cache")
DB_PATH = os.path.join(DATA_DIR, "schedule.db")

# Env var name for your Apps Script web app URL
ENV_VAR_URL = "web_app"

# Requests config
TIMEOUT_SECS = 20
RETRY_TOTAL = 3
RETRY_BACKOFF = 0.5  # seconds

# Timezone for stamps and normalization
IST = pytz.timezone("Asia/Kolkata")

os.makedirs(DATA_DIR, exist_ok=True)


# ------------ Database Setup ------------
def init_db():
    """Initialize the database with required tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Create monthly schedule table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                row_data TEXT NOT NULL
            )
        """)
        
        # Create daily schedule table with indexed Date column for faster queries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                row_data TEXT NOT NULL,
                date TEXT
            )
        """)
        
        # Create index on date for faster filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_date 
            ON daily_schedule(date)
        """)
        
        # Create task completions table to track user-marked completions
        # This persists across Google Sheets refreshes
        # For daily tasks: tracks first_read, notes, revision (3 stages)
        # For monthly tasks: uses completed field (single stage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_completions (
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
        
        # Create index on month_year for faster monthly queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_completion_month 
            ON task_completions(month_year)
        """)
        
        conn.commit()


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        yield conn
    finally:
        if conn:
            conn.close()


# ------------ HTTP Utilities ------------
def _session_with_retries() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


# ------------ Normalization helpers ------------
def _to_ist_date_str(value: str) -> str:
    """
    Convert an incoming date string to IST date (YYYY-MM-DD).
    Handles:
      - 'YYYY-MM-DD' (returns as-is)
      - ISO datetimes like 'YYYY-MM-DDTHH:MM:SSZ' or with offsets
      - Naive datetimes (assumed UTC)
    """
    if not value:
        return ""

    s = value.strip()

    # Already a plain date?
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s

    # Normalize Z to +00:00 for fromisoformat
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).date().isoformat()
    except Exception:
        if len(value) >= 10 and value[4] == "-" and value[7] == "-":
            return value[:10]
        return value


def _normalize_daily_dates(daily_rows: List[List[Any]]) -> List[List[Any]]:
    """
    Given daily rows (header + data), return a new list where 'Date'
    is normalized to IST (YYYY-MM-DD). If header missing, return unchanged.
    """
    if not daily_rows:
        return daily_rows

    header = daily_rows[0]
    try:
        date_idx = header.index("Date")
    except ValueError:
        return daily_rows

    out = [header]
    for row in daily_rows[1:]:
        new_row = list(row)
        if date_idx < len(new_row):
            new_row[date_idx] = _to_ist_date_str(new_row[date_idx])
        out.append(new_row)
    return out


# ------------ Core Logic ------------
def fetch_json(url: Optional[str] = None) -> Dict[str, Any]:
    """Fetch JSON from Apps Script Web App."""
    url = url or os.getenv(ENV_VAR_URL)
    if not url:
        raise RuntimeError(f"Missing environment variable {ENV_VAR_URL}")

    s = _session_with_retries()
    r = s.get(url, timeout=TIMEOUT_SECS)
    r.raise_for_status()
    return r.json()


def validate_payload(payload: Dict[str, Any]) -> Tuple[List[List[Any]], List[List[Any]]]:
    """
    Expecting: {"Monthly": [...2D...], "daily_OCT": [...2D...] }
    Returns (monthly, daily)
    """
    if not isinstance(payload, dict):
        raise ValueError("Payload is not a JSON object")

    monthly = payload.get("Monthly", [])
    daily   = payload.get("daily_OCT", [])

    if not isinstance(monthly, list) or not all(isinstance(row, list) for row in monthly):
        raise ValueError("Monthly must be a 2-D list")
    if not isinstance(daily, list) or not all(isinstance(row, list) for row in daily):
        raise ValueError("daily_OCT must be a 2-D list")

    return monthly, daily


def refresh_cache(url: Optional[str] = None) -> str:
    """
    Fetch from Apps Script, validate, normalize, and write to SQLite database atomically.
    Returns an ISO timestamp (IST) of when the cache was updated.
    """
    # Initialize database if it doesn't exist
    init_db()
    
    payload = fetch_json(url)
    monthly, daily = validate_payload(payload)

    # Normalize daily 'Date' to IST yyyy-mm-dd
    daily = _normalize_daily_dates(daily)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM monthly_schedule")
        cursor.execute("DELETE FROM daily_schedule")
        
        # Insert monthly data
        for row in monthly:
            cursor.execute(
                "INSERT INTO monthly_schedule (row_data) VALUES (?)",
                (json.dumps(row),)
            )
        
        # Insert daily data with extracted date for indexing
        if daily:
            header = daily[0]
            try:
                date_idx = header.index("Date")
            except ValueError:
                date_idx = None
            
            for row in daily:
                date_val = None
                if date_idx is not None and date_idx < len(row):
                    date_val = row[date_idx][:10] if row[date_idx] else None
                
                cursor.execute(
                    "INSERT INTO daily_schedule (row_data, date) VALUES (?, ?)",
                    (json.dumps(row), date_val)
                )
        
        # Update metadata
        stamp = datetime.now(IST).isoformat()
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("updated_at_ist", stamp)
        )
        
        conn.commit()
    
    return stamp


def get_cached_tables() -> Dict[str, List[List[str]]]:
    """
    Read cached data from SQLite and return both tables.
    Merges local completion status with sheet data.
    If database is empty or doesn't exist, returns empty lists.
    """
    # Initialize database if it doesn't exist
    init_db()
    
    monthly_rows = []
    daily_rows = []
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch completion status (includes three stages for daily tasks)
            cursor.execute("""
                SELECT task_id, completed, first_read, notes, revision 
                FROM task_completions
            """)
            completions = {
                row[0]: {
                    'completed': row[1],
                    'first_read': row[2],
                    'notes': row[3],
                    'revision': row[4]
                } for row in cursor.fetchall()
            }
            
            # Fetch monthly data
            cursor.execute("SELECT row_data FROM monthly_schedule ORDER BY id")
            monthly_rows = [json.loads(row[0]) for row in cursor.fetchall()]
            
            # Merge completion status for monthly tasks
            monthly_rows = _merge_completion_status(monthly_rows, completions, "monthly")
            
            # Fetch daily data
            cursor.execute("SELECT row_data FROM daily_schedule ORDER BY id")
            daily_rows = [json.loads(row[0]) for row in cursor.fetchall()]
            
            # Merge completion status for daily tasks
            daily_rows = _merge_completion_status(daily_rows, completions, "daily")
            
    except Exception as e:
        # If there's any error, return empty lists
        print(f"Error reading from database: {e}")
    
    return {
        "Monthly": monthly_rows,
        "daily_OCT": daily_rows,
    }


def _merge_completion_status(rows: List[List[Any]], completions: Dict[str, Dict], task_type: str) -> List[List[Any]]:
    """
    Merge local completion status with sheet data.
    For daily tasks: Adds first_read, notes, revision columns
    For monthly tasks: Updates Status column based on completed field
    """
    if not rows:
        return rows
    
    # Check if we have a header row
    header = rows[0]
    try:
        id_idx = header.index("id")
        status_idx = header.index("Status") if "Status" in header else None
    except (ValueError, AttributeError):
        return rows
    
    # For daily tasks, add three-stage columns to header
    if task_type == "daily":
        new_header = list(header)
        if "first_read" not in new_header:
            new_header.extend(["first_read", "notes", "revision"])
        result = [new_header]
    else:
        result = [header]
    
    for row in rows[1:]:
        new_row = list(row)
        if id_idx < len(new_row):
            task_id = f"{task_type}_{new_row[id_idx]}"
            
            if task_type == "daily":
                # For daily tasks: add three-stage completion data
                completion_data = completions.get(task_id, {
                    'first_read': 0,
                    'notes': 0,
                    'revision': 0
                })
                
                # Extend row with three-stage data
                if len(new_row) == len(header):
                    new_row.extend([
                        completion_data.get('first_read', 0),
                        completion_data.get('notes', 0),
                        completion_data.get('revision', 0)
                    ])
                
                # Update Status based on completion (all three stages done = done)
                if status_idx is not None and status_idx < len(new_row):
                    if (completion_data.get('first_read', 0) == 1 and 
                        completion_data.get('notes', 0) == 1 and 
                        completion_data.get('revision', 0) == 1):
                        new_row[status_idx] = "done"
                    else:
                        new_row[status_idx] = "Pending"
            else:
                # For monthly tasks: use single completed field
                if task_id in completions and completions[task_id].get('completed') == 1:
                    # Task is completed locally - mark as done
                    if status_idx is not None and status_idx < len(new_row):
                        new_row[status_idx] = "done"
                    elif status_idx is None:
                        # If Status column doesn't exist, add it
                        if len(header) == len(new_row):
                            new_row.append("done")
                else:
                    # Task is NOT in completions or is marked as incomplete
                    if status_idx is not None and status_idx < len(new_row):
                        if task_id not in completions:
                            original_status = str(new_row[status_idx]).lower().strip()
                            if original_status in ["done", "completed", "finished", "1", "true"]:
                                new_row[status_idx] = "Pending"
            
        result.append(new_row)
    
    return result


def mark_task_complete(task_id: str, task_type: str, completed: bool = True, month_year: str = None) -> bool:
    """
    Mark a task as complete or incomplete (for monthly tasks).
    Returns True if successful, False otherwise.
    """
    init_db()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            completed_at = datetime.now(IST).isoformat()
            
            if completed:
                cursor.execute("""
                    INSERT OR REPLACE INTO task_completions 
                    (task_id, task_type, completed, first_read, notes, revision, completed_at, month_year)
                    VALUES (?, ?, ?, 0, 0, 0, ?, ?)
                """, (task_id, task_type, 1, completed_at, month_year))
            else:
                # If uncompleting, remove from completions
                cursor.execute("""
                    DELETE FROM task_completions WHERE task_id = ?
                """, (task_id,))
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error marking task complete: {e}")
        return False


def mark_task_stage(task_id: str, task_type: str, stage: str, completed: bool = True, month_year: str = None) -> bool:
    """
    Mark a specific stage of a task (first_read, notes, or revision) as complete or incomplete.
    For daily tasks only.
    Returns True if successful, False otherwise.
    """
    init_db()
    
    if stage not in ['first_read', 'notes', 'revision']:
        print(f"Invalid stage: {stage}")
        return False
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            completed_at = datetime.now(IST).isoformat()
            
            # Check if task exists
            cursor.execute("SELECT * FROM task_completions WHERE task_id = ?", (task_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute(f"""
                    UPDATE task_completions 
                    SET {stage} = ?, completed_at = ?
                    WHERE task_id = ?
                """, (1 if completed else 0, completed_at, task_id))
            else:
                # Create new record
                stages = {
                    'first_read': 0,
                    'notes': 0,
                    'revision': 0
                }
                stages[stage] = 1 if completed else 0
                
                cursor.execute("""
                    INSERT INTO task_completions 
                    (task_id, task_type, completed, first_read, notes, revision, completed_at, month_year)
                    VALUES (?, ?, 0, ?, ?, ?, ?, ?)
                """, (task_id, task_type, stages['first_read'], stages['notes'], 
                      stages['revision'], completed_at, month_year))
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error marking task stage: {e}")
        return False


def get_completion_stats(month_year: str = None) -> Dict[str, int]:
    """
    Get completion statistics, optionally filtered by month.
    Returns dict with total, completed, pending counts.
    """
    init_db()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if month_year:
                cursor.execute("""
                    SELECT COUNT(*) FROM task_completions 
                    WHERE month_year = ? AND completed = 1
                """, (month_year,))
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM task_completions 
                    WHERE completed = 1
                """)
            
            completed_count = cursor.fetchone()[0]
            
            return {
                "completed": completed_count
            }
    except Exception as e:
        print(f"Error getting completion stats: {e}")
        return {"completed": 0}


def get_task_progress(date: str = None) -> Dict[str, Any]:
    """
    Get progress statistics for daily tasks.
    Calculates percentage based on: (completed_stages / total_stages) * 100
    Where total_stages = num_tasks * 3 (first_read, notes, revision)
    
    Args:
        date: Optional date filter (yyyy-mm-dd format)
    
    Returns:
        Dict with total_tasks, total_stages, completed_stages, percentage
    """
    init_db()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get total tasks for the date
            if date:
                cursor.execute("""
                    SELECT COUNT(*) FROM daily_schedule 
                    WHERE date = ?
                """, (date,))
            else:
                cursor.execute("SELECT COUNT(*) FROM daily_schedule")
            
            total_tasks = cursor.fetchone()[0]
            
            # Header row counts as one, so subtract it
            if total_tasks > 0:
                total_tasks -= 1
            
            total_stages = total_tasks * 3  # Each task has 3 stages
            
            # Get completed stages
            if date:
                cursor.execute("""
                    SELECT SUM(first_read) + SUM(notes) + SUM(revision) 
                    FROM task_completions tc
                    WHERE tc.task_type = 'daily'
                    AND tc.task_id IN (
                        SELECT 'daily_' || json_extract(row_data, '$[0]')
                        FROM daily_schedule
                        WHERE date = ?
                    )
                """, (date,))
            else:
                cursor.execute("""
                    SELECT SUM(first_read) + SUM(notes) + SUM(revision) 
                    FROM task_completions 
                    WHERE task_type = 'daily'
                """)
            
            completed_stages = cursor.fetchone()[0] or 0
            
            # Calculate percentage
            percentage = (completed_stages / total_stages * 100) if total_stages > 0 else 0
            
            return {
                "total_tasks": total_tasks,
                "total_stages": total_stages,
                "completed_stages": completed_stages,
                "percentage": round(percentage, 2)
            }
    except Exception as e:
        print(f"Error getting task progress: {e}")
        return {
            "total_tasks": 0,
            "total_stages": 0,
            "completed_stages": 0,
            "percentage": 0
        }


# ------------ CLI Support (optional) ------------
if __name__ == "__main__":
    try:
        ts = refresh_cache()
        print(f"Cache updated at {ts}")
    except Exception as e:
        print(f"ERROR: {e}")
        raise
