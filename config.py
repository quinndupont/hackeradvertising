"""Configuration for HN research pipeline."""
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search_by_date"
FIREBASE_NEW = "https://hacker-news.firebaseio.com/v0/newstories.json"
FIREBASE_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
FIREBASE_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

FRONT_PAGE_THRESHOLD = 50
STRONG_FRONT_PAGE_THRESHOLD = 100
GRADUATION_WINDOW_HOURS = 6
