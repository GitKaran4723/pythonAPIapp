from flask import Flask, jsonify, request
from flask_cors import CORS  # 👈 Import CORS
from dotenv import load_dotenv
import requests
import os

load_dotenv()

app = Flask(__name__)
CORS(app)  # 👈 Enable CORS for all routes

# API's for various applications

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"

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

        for item in data["items"]:
            snippet = item["snippet"]
            video = {
                "title": snippet["title"],
                "description": snippet["description"],
                "videoId": snippet["resourceId"]["videoId"],
                "thumbnail": snippet["thumbnails"]["medium"]["url"],
                "publishedAt": snippet["publishedAt"],
                "channelTitle": snippet["channelTitle"]
            }
            videos.append(video)

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return videos


@app.route("/")
def home():
    return "Hello world"

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
