# sheet_cache.py
import os
import csv
import json
import tempfile
from datetime import datetime, timezone
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

# Timezone for stamps and normalization
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
    Atomically write CSV so readers never see partial files.
    Create temp in the SAME directory to avoid cross-device link errors.
    """
    dest_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(dest_dir, exist_ok=True)

    tmp_name = None
    try:
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

        os.replace(tmp_name, path)
        tmp_name = None
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
    Fetch from Apps Script, validate, normalize, and write CSVs atomically.
    Returns an ISO timestamp (IST) of when the cache was updated.
    """
    payload = fetch_json(url)
    monthly, daily = validate_payload(payload)

    # Normalize daily 'Date' to IST yyyy-mm-dd
    daily = _normalize_daily_dates(daily)

    _atomic_write_csv(MONTHLY_CSV, monthly)
    _atomic_write_csv(DAILY_CSV, daily)

    stamp = datetime.now(IST).isoformat()
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
    try:
        ts = refresh_cache()
        print(f"Cache updated at {ts}")
    except Exception as e:
        print(f"ERROR: {e}")
        raise
