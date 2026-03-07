"""Run graduation analysis (Cox model) when Firebase data exists."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from config import DATA_DIR
from src.models.timing import prepare_graduation_features, fit_cox_time_to_graduation

MIN_ROWS = 50


def run_graduation_analysis() -> None:
    """Load Firebase graduations, merge with Algolia, fit Cox model."""
    firebase_path = DATA_DIR / "firebase_graduations.parquet"
    if not firebase_path.exists():
        print("No Firebase graduation data. Run collect_graduations.py to collect.")
        return
    firebase_df = pd.read_parquet(firebase_path)
    if len(firebase_df) < MIN_ROWS:
        print(f"Only {len(firebase_df)} rows. Need {MIN_ROWS}+ for Cox model.")
        return

    algolia_path = DATA_DIR / "algolia_stories.parquet"
    algolia_df = pd.read_parquet(algolia_path) if algolia_path.exists() else None
    if algolia_df is not None:
        algolia_df["has_url"] = algolia_df["url"].notna() & (algolia_df["url"] != "")
        algolia_df["is_show_hn"] = algolia_df["title"].str.startswith("Show HN:", na=False)
        algolia_df["is_ask_hn"] = algolia_df["title"].str.startswith("Ask HN:", na=False)
        algolia_df["title_word_count"] = algolia_df["title"].str.split().str.len().fillna(0).astype(int)

    df = prepare_graduation_features(firebase_df, algolia_df)
    cph = fit_cox_time_to_graduation(df)
    if cph is None:
        print("Could not fit Cox model (need 50+ rows with 3+ graduations; collect more data).")
        return
    print("--- Cox Proportional Hazards (time-to-graduation) ---")
    print(cph.summary.to_string())


if __name__ == "__main__":
    run_graduation_analysis()
