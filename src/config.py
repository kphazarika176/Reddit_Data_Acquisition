import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root directory
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "reddit_news_db")

# Apify API settings - use working trudax/reddit-scraper-lite
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "trudax~reddit-scraper-lite")