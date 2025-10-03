# sheet_cache.py
import os
import csv
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

import pytz
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ------------ Configuration ------------
# Directory to store cached CSVs
DATA_DIR = os.path.join(os.path.dirname(__file__), "data_cache")
MONTHLY_CSV = os.path.join(DATA_DIR, "monthly.csv")
DAILY_CSV   = os.path.join(DATA_DIR, "daily_OCT.csv")

# Env var name for your Apps Script web app URL
ENV_VAR_URL = "web_app"

# Requests config
TIMEOUT_SECS = 20
RETRY_TOTAL = 3
RETRY_BACKOFF = 0.5  # seconds

# Timezone for stamps
IST = pytz.timezone("Asia/Kolkata")

os.makedirs(DATA_DIR, exist_ok=True)


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


# ------------ File I/O ------------
def _atomic_write_csv(path: str, rows_2d: List[List[Any]]) -> None:
    """
    Write a CSV atomically so readers never see partial files.

    IMPORTANT: Create the temp file in the SAME directory as the destination
    to avoid cross-device link errors on platforms like PythonAnywhere.
    """
    dest_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(dest_dir, exist_ok=True)

    tmp_name = None
    try:
        # Create temp file in destination directory (same filesystem)
        with tempfile.NamedTemporaryFile(
            delete=False,
            mode="w",
            newline="",
            encoding="utf-8",
            dir=dest_dir,
            prefix=".tmp_",
        ) as tmp:
            writer = csv.writer(tmp)
            for row in rows_2d:
                writer.writerow(row)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_name = tmp.name

        # Atomic replace within same FS
        os.replace(tmp_name, path)
        tmp_name = None  # prevent cleanup below
    finally:
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except Exception:
                pass


def read_csv(path: str) -> List[List[str]]:
    """Read CSV into a list of rows (each row is a list of strings)."""
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


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
    Fetch from Apps Script, validate, and write CSVs atomically.
    Returns an ISO timestamp (IST) of when the cache was updated.
    """
    payload = fetch_json(url)
    monthly, daily = validate_payload(payload)
    _atomic_write_csv(MONTHLY_CSV, monthly)
    _atomic_write_csv(DAILY_CSV, daily)
    stamp = datetime.now(IST).isoformat()
    # Also write a small metadata file for debugging/monitoring
    with open(os.path.join(DATA_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"updated_at_ist": stamp}, f, ensure_ascii=False)
    return stamp


def get_cached_tables() -> Dict[str, List[List[str]]]:
    """
    Read cached CSVs and return both tables.
    If files are missing, returns empty lists for them.
    """
    return {
        "Monthly": read_csv(MONTHLY_CSV),
        "daily_OCT": read_csv(DAILY_CSV),
    }


# ------------ CLI Support (optional) ------------
if __name__ == "__main__":
    # Allows: python sheet_cache.py  -> refresh now (useful for cron)
    try:
        ts = refresh_cache()
        print(f"Cache updated at {ts}")
    except Exception as e:
        print(f"ERROR: {e}")
        raise
