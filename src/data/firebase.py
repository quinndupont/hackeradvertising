"""Firebase HN API for real-time graduation tracking."""
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from config import DATA_DIR, FIREBASE_ITEM, FIREBASE_NEW, FIREBASE_TOP

MAX_TRACKED = 50


def fetch_json(url: str) -> list | dict:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def get_item(item_id: int) -> dict | None:
    return fetch_json(FIREBASE_ITEM.format(id=item_id))


def poll_graduations(interval_sec: int = 90, duration_min: int = 60) -> pd.DataFrame:
    """
    Poll newstories and topstories to track graduations with velocity.
    A story graduates when it moves from newstories to topstories.
    Records time_to_graduation, early_velocity_30, velocity_votes_per_min.
    """
    seen_new = set()
    tracked: dict[int, dict] = {}
    graduations = []

    end_time = time.time() + duration_min * 60
    while time.time() < end_time:
        poll_time = datetime.now(timezone.utc)
        try:
            new_ids = set(fetch_json(FIREBASE_NEW)[:100])
            top_ids = list(fetch_json(FIREBASE_TOP)[:50])

            for sid in new_ids:
                if sid not in seen_new:
                    seen_new.add(sid)
                    item = get_item(sid)
                    if item and item.get("type") == "story":
                        submitted_ts = item.get("time", 0)
                        submitted_at = datetime.fromtimestamp(submitted_ts, tz=timezone.utc)
                        tracked[sid] = {
                            "id": sid,
                            "submitted_at": submitted_at,
                            "submitted_ts": submitted_ts,
                            "in_new": True,
                            "graduated": False,
                            "score_history": [(0, item.get("score", 1))],
                        }
                        if len(tracked) > MAX_TRACKED:
                            oldest = min(tracked.keys(), key=lambda k: tracked[k]["submitted_ts"])
                            if not tracked[oldest].get("graduated"):
                                del tracked[oldest]

            for sid, entry in list(tracked.items()):
                if entry.get("graduated"):
                    continue
                item = get_item(sid)
                if not item:
                    continue
                elapsed_min = (poll_time.timestamp() - entry["submitted_ts"]) / 60
                score = item.get("score", 0)
                entry["score_history"].append((elapsed_min, score))

                if sid in top_ids:
                    entry["in_new"] = False
                    entry["graduated"] = True
                    entry["graduated_at"] = poll_time
                    entry["score_at_grad"] = score
                    entry["rank"] = top_ids.index(sid) + 1
                    entry["time_to_graduation"] = (poll_time - entry["submitted_at"]).total_seconds() / 60
                    _compute_velocity(entry)
                    graduations.append(_to_row(entry))
                    del tracked[sid]
                elif elapsed_min >= 30:
                    entry["graduated"] = False
                    entry["time_to_graduation"] = elapsed_min
                    entry["score_at_grad"] = None
                    entry["rank"] = None
                    _compute_velocity(entry)
                    graduations.append(_to_row(entry))
                    del tracked[sid]

        except Exception as e:
            print(f"Poll error: {e}")
        time.sleep(interval_sec)

    df = pd.DataFrame(graduations)
    if not df.empty:
        df["day_of_week"] = df["submitted_at"].dt.dayofweek
        df["hour_of_day"] = df["submitted_at"].dt.hour
        df["hour_of_week"] = df["day_of_week"] * 24 + df["hour_of_day"]
    return df


def _to_row(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if k != "score_history"}


def _compute_velocity(entry: dict) -> None:
    history = entry.get("score_history", [])
    if not history:
        return
    history.sort(key=lambda x: x[0])
    score_at_0 = history[0][1] if history[0][1] > 0 else 1
    best = None
    for elapsed_min, score in history:
        if elapsed_min >= 25:
            best = (elapsed_min, score)
            break
    if best:
        elapsed, score = best
        entry["early_velocity_30"] = score
        entry["velocity_votes_per_min"] = (score - score_at_0) / max(elapsed, 1)
    else:
        elapsed, score = history[-1]
        entry["early_velocity_30"] = score
        entry["velocity_votes_per_min"] = (score - score_at_0) / max(elapsed, 1) if elapsed > 0 else 0


def append_graduations(new_df: pd.DataFrame) -> None:
    """Append new graduations to persistent store, deduplicate by id."""
    out = DATA_DIR / "firebase_graduations.parquet"
    if new_df.empty:
        return
    if out.exists():
        existing = pd.read_parquet(out)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["id"], keep="last")
    else:
        combined = new_df
    combined.to_parquet(out, index=False)


def poll_and_persist(interval_sec: int = 90, duration_min: int = 60) -> int:
    """Poll for graduations and append to persistent store. Returns count of new graduations."""
    df = poll_graduations(interval_sec=interval_sec, duration_min=duration_min)
    if df.empty:
        return 0
    append_graduations(df)
    return len(df)


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
