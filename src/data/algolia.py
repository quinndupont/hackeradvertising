"""Algolia HN Search API data acquisition."""
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

from config import ALGOLIA_URL, DATA_DIR


def fetch_algolia_page(tags: str = "story", created_after: int = 0, created_before: int = 0, page: int = 0) -> dict:
    """Fetch one page of Algolia results."""
    filters = []
    if created_after:
        filters.append(f"created_at_i>{created_after}")
    if created_before:
        filters.append(f"created_at_i<{created_before}")
    params = {
        "tags": tags,
        "hitsPerPage": 1000,
        "page": page,
    }
    if filters:
        params["numericFilters"] = ",".join(filters)
    r = requests.get(ALGOLIA_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def pull_algolia_stories(months: int = 12, output_path: Path | None = None) -> pd.DataFrame:
    """Pull story data from Algolia for the specified number of months."""
    end = datetime.utcnow()
    start = end - timedelta(days=months * 30)
    all_hits = []

    # Chunk by week to avoid overwhelming the API
    current = start
    while current < end:
        week_end = min(current + timedelta(days=7), end)
        start_ts = int(current.timestamp())
        end_ts = int(week_end.timestamp())
        page = 0
        while True:
            data = fetch_algolia_page(created_after=start_ts, created_before=end_ts, page=page)
            hits = data.get("hits", [])
            if not hits:
                break
            all_hits.extend(hits)
            if page >= data.get("nbPages", 1) - 1:
                break
            page += 1
            time.sleep(0.4)
        current = week_end
        print(f"Fetched through {week_end.date()}")

    df = pd.DataFrame(all_hits)
    if df.empty:
        return df

    df["created_at"] = pd.to_datetime(df["created_at_i"], unit="s", utc=True)
    df["day_of_week"] = df["created_at"].dt.dayofweek  # 0=Monday
    df["hour_of_day"] = df["created_at"].dt.hour
    df["hour_of_week"] = df["day_of_week"] * 24 + df["hour_of_day"]
    df["has_url"] = df["url"].notna() & (df["url"] != "")
    df["is_show_hn"] = df["title"].str.startswith("Show HN:", na=False)
    df["is_ask_hn"] = df["title"].str.startswith("Ask HN:", na=False)
    df["title_word_count"] = df["title"].str.split().str.len().fillna(0).astype(int)
    df["front_page"] = df["points"] >= 50
    df["strong_front_page"] = df["points"] >= 100

    out = output_path or DATA_DIR / "algolia_stories.parquet"
    df.to_parquet(out, index=False)
    return df


if __name__ == "__main__":
    pull_algolia_stories(months=12)
