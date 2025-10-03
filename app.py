from flask import Flask, jsonify, request, render_template, send_from_directory, make_response, url_for
from flask_cors import CORS
from dotenv import load_dotenv
import os
import pytz
from datetime import date, timedelta, datetime

# external deps you already use
import requests
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

# your module
import sheet_cache

# IMPORTANT: do NOT import/start APScheduler at module import time
# (PythonAnywhere uWSGI has threads disabled)

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app, origins=["https://karanjadhav.tech"])

Schedule_data_script_url = os.getenv('web_app')

# ---------- INITIAL (SYNC) WARMUP, OPTIONAL ----------
# This is safe because it's synchronous and wrapped in try/except.
try:
    cache = sheet_cache.get_cached_tables()
    if not cache.get("Monthly") and not cache.get("daily_OCT"):
        sheet_cache.refresh_cache(Schedule_data_script_url)
except Exception as e:
    app.logger.warning(f"Initial cache refresh failed: {e}")

# ---------- ROUTES ----------
@app.route("/schedule")
def home():
    """
    Prefer cached CSVs. If empty (first boot), try one sync refresh.
    """
    data = sheet_cache.get_cached_tables()

    if not data.get("Monthly") and not data.get("daily_OCT"):
        try:
            sheet_cache.refresh_cache(Schedule_data_script_url)
            data = sheet_cache.get_cached_tables()
        except Exception as e:
            app.logger.error(f"Live refresh failed: {e}")

    return render_template(
        "monthly_schedule.html",
        items=data.get("Monthly", []),
    )

@app.route("/daily")
def daily():
    ist = pytz.timezone("Asia/Kolkata")
    today_ist = datetime.now(ist).date()

    d = request.args.get("d")
    try:
        view_date = (datetime.strptime(d, "%Y-%m-%d").date() if d else today_ist).isoformat()
    except Exception:
        view_date = today_ist.isoformat()

    tables = sheet_cache.get_cached_tables()
    daily_rows = tables.get("daily_OCT", [])

    vd = date.fromisoformat(view_date)
    prev_url = url_for("daily", d=(vd - timedelta(days=1)).isoformat())
    next_url = url_for("daily", d=(vd + timedelta(days=1)).isoformat())
    today_url = url_for("daily", d=today_ist.isoformat())

    return render_template(
        "daily_schedule.html",
        items=daily_rows,
        view_date=view_date,
        prev_url=prev_url,
        next_url=next_url,
        today_url=today_url,
        back_to_month_url=url_for("home")
    )

# Optional raw JSON for debugging
@app.route("/schedule.json")
def schedule_json():
    return sheet_cache.get_cached_tables()

@app.route("/")
def index():
    return render_template("index.html")

# Serve the manifest with correct MIME
@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(
        "static",
        "manifest.webmanifest",
        mimetype="application/manifest+json",
    )

# Service worker from root
@app.route("/sw.js")
def sw():
    response = make_response(send_from_directory("static", "sw.js"))
    response.headers["Cache-Control"] = "no-cache"
    return response

@app.context_processor
def inject_access_code():
    return {"access_code": os.getenv("APP_ACCESS_CODE", "1234")}

# --------- GENAI ENDPOINTS ----------
genai.configure(api_key=os.getenv("GEMINI_API"))
model = genai.GenerativeModel("gemini-2.0-flash")

@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.json or {}
    mode = data.get("mode")
    prompt = data.get("prompt")

    try:
        if mode == "video":
            video_id = (prompt or "").strip().split("v=")[-1].split("&")[0]
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = " ".join([t["text"] for t in transcript_list])
            query = f"Make detailed notes from this YouTube video transcript: {transcript}"
        elif mode == "notes":
            query = f"Answer this using study notes: {prompt}"
        elif mode == "general":
            query = prompt
        else:
            return jsonify({"error": "Invalid mode"}), 400

        response = model.generate_content(query)
        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Optional: manual refresh endpoint (guarded by token)
@app.route("/admin/refresh")
def admin_refresh():
    token = request.args.get("t")
    if token != os.getenv("ADMIN_TOKEN", "dev"):
        return "Forbidden", 403
    try:
        sheet_cache.refresh_cache(Schedule_data_script_url)
        return "OK"
    except Exception as e:
        app.logger.exception("Manual refresh failed")
        return f"Error: {e}", 500


# ---------- DEV-ONLY BACKGROUND SCHEDULER ----------
# This runs ONLY when launched as `python app.py` (local dev),
# not under PythonAnywhere's uWSGI import.
if __name__ == '__main__':
    # Optional dev scheduler (safe locally; NOT used on PythonAnywhere)
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        import atexit

        scheduler = BackgroundScheduler(timezone="Asia/Kolkata", daemon=True)
        scheduler.add_job(lambda: sheet_cache.refresh_cache(Schedule_data_script_url),
                          trigger="cron", minute=0)
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown(wait=False))
    except Exception as e:
        print(f"[DEV] Scheduler not started: {e}")

    app.run(debug=True)
