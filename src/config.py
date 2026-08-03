import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root directory
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/reddit_news.db")
DB_PATH = SQLITE_DB_PATH

# Apify API settings - default to top-rated harshmaur/reddit-scraper
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "harshmaur/reddit-scraper")

