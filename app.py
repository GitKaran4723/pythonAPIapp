from flask import Flask, jsonify, request
from flask_cors import CORS  # 👈 Import CORS
from dotenv import load_dotenv
import requests
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://karanjadhav.tech"])

# API's for various applications

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"

import re

def extract_lesson_number(title):
    match = re.search(r"L(\d+)", title)
    return int(match.group(1)) if match else float('inf')  # Put unnumbered titles at the end


def fetch_playlist_videos(api_key, playlist_id):
    videos = []
    next_page_token = ""

    while True:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
            "pageToken": next_page_token,
            "key": api_key
        }

        response = requests.get(YOUTUBE_API_URL, params=params)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]["message"]}

        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            title = snippet.get("title", "").lower()

            # 🚫 Skip deleted/private videos
            if "deleted video" in title or "private video" in title:
                continue

            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("medium", {}).get("url") or
                thumbnails.get("default", {}).get("url") or
                thumbnails.get("high", {}).get("url") or
                ""
            )

            video = {
                "title": snippet.get("title", "No Title"),
                "description": snippet.get("description", ""),
                "videoId": snippet.get("resourceId", {}).get("videoId", ""),
                "thumbnail": thumbnail_url,
                "publishedAt": snippet.get("publishedAt", ""),
                "channelTitle": snippet.get("channelTitle", "")
            }

            videos.append(video)

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    videos.sort(key=lambda x: extract_lesson_number(x["title"]))

    return videos

@app.route("/")
def home():
    return "Hello world"

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
