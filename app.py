from flask import Flask, jsonify, request, render_template, send_from_directory, make_response, url_for, request
from flask_cors import CORS  # 👈 Import CORS
from dotenv import load_dotenv
import requests
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import date, timedelta, datetime
import pytz

# NEW: import our cache helper
import sheet_cache

# OPTIONAL: scheduler for hourly refresh inside the web process
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app, origins=["https://karanjadhav.tech"])

Schedule_data_script_url = os.getenv('web_app')

# ---------- OPTIONAL: start hourly refresh job (Asia/Kolkata) ----------
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
# run at the top of every hour
scheduler.add_job(lambda: sheet_cache.refresh_cache(Schedule_data_script_url),
                  trigger="cron", minute=0)
scheduler.start()
atexit.register(lambda: scheduler.shutdown(wait=False))

# On startup, try to warm the cache once (non-fatal)
try:
    # Only refresh if files not present yet
    cache = sheet_cache.get_cached_tables()
    if not cache["Monthly"] and not cache["daily_OCT"]:
        sheet_cache.refresh_cache(Schedule_data_script_url)
except Exception as e:
    app.logger.warning(f"Initial cache refresh failed: {e}")

# ---------- ROUTES ----------
@app.route("/schedule")
def home():
    """
    Prefer cached CSVs (fast & resilient). If empty (first boot),
    we attempt a synchronous refresh once.
    """
    data = sheet_cache.get_cached_tables()

    if not data["Monthly"] and not data["daily_OCT"]:
        try:
            sheet_cache.refresh_cache(Schedule_data_script_url)
            data = sheet_cache.get_cached_tables()
        except Exception as e:
            app.logger.error(f"Live refresh failed: {e}")

    # if your template currently expects a single 'items', you can pass Monthly
    # or adjust the template to use both. Example below passes both:
    return render_template(
        "monthly_schedule.html",
        items=data["Monthly"],
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

    # read cached daily csv rows (2D, includes header)
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

# Optional raw JSON for debugging in browser
@app.route("/schedule.json")
def schedule_json():
    return sheet_cache.get_cached_tables()

@app.route("/")
def index():
    return render_template("index.html")

# Serve the manifest with the correct MIME type
@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(
        "static",
        "manifest.webmanifest",
        mimetype="application/manifest+json",
    )

# Serve the service worker from the root so it controls the whole site
@app.route("/sw.js")
def sw():
    response = make_response(send_from_directory("static", "sw.js"))
    # Avoid aggressive caching of the SW itself so updates take effect
    response.headers["Cache-Control"] = "no-cache"
    return response

@app.context_processor
def inject_access_code():
    return {"access_code": os.getenv("APP_ACCESS_CODE", "1234")}


    
genai.configure(api_key=os.getenv("GEMINI_API"))
model = genai.GenerativeModel("gemini-2.0-flash")

@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.json
    mode = data.get("mode")
    prompt = data.get("prompt")

    try:
        if mode == "video":
            video_id = prompt.strip().split("v=")[-1].split("&")[0]
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = " ".join([t["text"] for t in transcript_list])
            query = f"Make detailed notes from this YouTube video transcript:{transcript}"
        elif mode == "notes":
            # Placeholder for markdown-based RAG (simple context-based)
            # You can replace this with actual vector search in future
            query = f"Answer this using study notes: {prompt}"
        elif mode == "general":
            query = prompt
        else:
            return jsonify({"error": "Invalid mode"}), 400

        response = model.generate_content(query)
        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/playlist/aptitude/<playlist_id>', methods=['GET'])
def get_playlist_videos(playlist_id):
    print(playlist_id)
    
    if not playlist_id:
        return jsonify({"error": "Missing playlistId in URL path"}), 400

    result = fetch_playlist_videos(YOUTUBE_API_KEY, playlist_id)

    if isinstance(result, dict) and result.get("error"):
        return jsonify(result), 500

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
