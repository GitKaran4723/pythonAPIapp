from flask import Flask, jsonify, request
from flask_cors import CORS  # 👈 Import CORS
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)  # 👈 Enable CORS for all routes

# API's for various applications

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

@app.route("/")
def home():
    return "Hello world"

if __name__ == '__main__':
    app.run(debug=True)
