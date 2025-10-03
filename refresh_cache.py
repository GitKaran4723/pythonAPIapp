# refresh_cache.py
import os
from dotenv import load_dotenv
import sheet_cache

def main():
    load_dotenv()
    url = os.getenv("web_app")
    if not url:
        raise RuntimeError("Missing env var: web_app")
    sheet_cache.refresh_cache(url)
    print("Cache refreshed OK")

if __name__ == "__main__":
    main()
