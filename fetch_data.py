"""Fetch HN data from Algolia. Run from project root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.data.algolia import pull_algolia_stories
from config import DATA_DIR

if __name__ == "__main__":
    print("Fetching 12 months of HN stories from Algolia...")
    df = pull_algolia_stories(months=12)
    print(f"Saved {len(df)} stories to {DATA_DIR / 'algolia_stories.parquet'}")
