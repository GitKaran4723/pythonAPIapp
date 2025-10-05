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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_completions (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 1,
                completed_at TEXT NOT NULL,
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
            
            # Fetch completion status
            cursor.execute("SELECT task_id, completed FROM task_completions")
            completions = {row[0]: row[1] for row in cursor.fetchall()}
            
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


def _merge_completion_status(rows: List[List[Any]], completions: Dict[str, int], task_type: str) -> List[List[Any]]:
    """
    Merge local completion status with sheet data.
    Updates the Status column based on local completions.
    IMPORTANT: Only marks as 'done' if task_id is in completions AND completed=1
    Otherwise, preserves original status or sets to empty/pending.
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
    
    result = [header]
    
    for row in rows[1:]:
        new_row = list(row)
        if id_idx < len(new_row):
            task_id = f"{task_type}_{new_row[id_idx]}"
            
            # Check if this task has a local completion record
            if task_id in completions and completions[task_id] == 1:
                # Task is completed locally - mark as done
                if status_idx is not None and status_idx < len(new_row):
                    new_row[status_idx] = "done"
                elif status_idx is None:
                    # If Status column doesn't exist, add it
                    if len(header) == len(new_row):
                        new_row.append("done")
            else:
                # Task is NOT in completions or is marked as incomplete
                # Ensure it's not showing as done (reset to original or pending)
                if status_idx is not None and status_idx < len(new_row):
                    original_status = str(new_row[status_idx]).lower().strip()
                    # If original status says done but we don't have a completion record, reset it
                    if original_status in ["done", "completed", "finished", "1", "true"]:
                        # Check if it's from the sheet or local - if not in completions, reset to pending
                        if task_id not in completions:
                            new_row[status_idx] = "Pending"
            
        result.append(new_row)
    
    return result


def mark_task_complete(task_id: str, task_type: str, completed: bool = True, month_year: str = None) -> bool:
    """
    Mark a task as complete or incomplete.
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
                    (task_id, task_type, completed, completed_at, month_year)
                    VALUES (?, ?, ?, ?, ?)
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


# ------------ CLI Support (optional) ------------
if __name__ == "__main__":
    try:
        ts = refresh_cache()
        print(f"Cache updated at {ts}")
    except Exception as e:
        print(f"ERROR: {e}")
        raise
