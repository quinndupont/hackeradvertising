"""Firebase HN API for real-time graduation tracking."""
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from config import DATA_DIR, FIREBASE_ITEM, FIREBASE_NEW, FIREBASE_TOP


def fetch_json(url: str) -> list | dict:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def get_item(item_id: int) -> dict | None:
    return fetch_json(FIREBASE_ITEM.format(id=item_id))


def poll_graduations(interval_sec: int = 90, duration_min: int = 60) -> pd.DataFrame:
    """
    Poll newstories and topstories to track graduations.
    A story graduates when it moves from newstories to topstories.
    """
    seen_new = set()
    graduations = []

    end_time = time.time() + duration_min * 60
    while time.time() < end_time:
        try:
            new_ids = set(fetch_json(FIREBASE_NEW)[:100])
            top_ids = set(fetch_json(FIREBASE_TOP)[:50])

            for sid in new_ids:
                if sid not in seen_new:
                    seen_new.add(sid)
                    item = get_item(sid)
                    if item and item.get("type") == "story":
                        graduations.append({
                            "id": sid,
                            "submitted_at": datetime.utcnow().isoformat(),
                            "in_new": True,
                        })

            for entry in graduations:
                if entry.get("in_new") and entry["id"] in top_ids:
                    item = get_item(entry["id"])
                    if item:
                        entry["in_new"] = False
                        entry["graduated"] = True
                        entry["score_at_grad"] = item.get("score", 0)
                        entry["rank"] = list(top_ids).index(entry["id"]) + 1

        except Exception as e:
            print(f"Poll error: {e}")
        time.sleep(interval_sec)

    df = pd.DataFrame([g for g in graduations if g.get("graduated")])
    if not df.empty:
        df["submitted_at"] = pd.to_datetime(df["submitted_at"], utc=True)
        df["day_of_week"] = df["submitted_at"].dt.dayofweek
        df["hour_of_day"] = df["submitted_at"].dt.hour
        out = DATA_DIR / "firebase_graduations.parquet"
        df.to_parquet(out, index=False)
    return df


def fetch_top_stories_snapshot() -> pd.DataFrame:
    """One-time fetch of current top stories for score/traffic calibration."""
    top_ids = fetch_json(FIREBASE_TOP)[:30]
    rows = []
    for i, sid in enumerate(top_ids):
        item = get_item(sid)
        if item and item.get("type") == "story":
            rows.append({
                "id": sid,
                "rank": i + 1,
                "score": item.get("score", 0),
                "title": item.get("title", ""),
                "time": item.get("time"),
            })
    return pd.DataFrame(rows)
