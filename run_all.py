"""Run full pipeline: Phase 1 + Phase 2 + combined insight."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from run_phase1 import run_timing_analysis
from run_phase2 import run_aev_analysis
from src.models.timing import prepare_features, fit_xgboost, predict_p_front_page_by_hour, compute_competition_load
from src.models.aev import advertising_equivalent_value
from config import DATA_DIR


def combined_insight() -> None:
    """Expected AEV per submission by hour-of-week and story type."""
    df = pd.read_parquet(DATA_DIR / "algolia_stories.parquet")
    X, Y1, _, df_out = prepare_features(df)
    df_out["competition_load"] = compute_competition_load(df_out)
    xgb = fit_xgboost(X, Y1)

    X_template = X.head(1).copy()
    X_template["competition_load"] = 50
    proba_df = predict_p_front_page_by_hour(xgb, X_template, None, use_xgb=True)

    # Expected AEV = P(front page) × E[AEV | front page]
    # Use typical AEV for front page (~$2k for general_tech, ~$20k for dev_tools)
    typical_aev = {"dev_tools": 20000, "general_tech": 2000, "adjacent": 500}
    print("\n--- Expected AEV per submission (P(front) × typical AEV) ---")
    for cat, aev in typical_aev.items():
        proba_df[f"expected_aev_{cat}"] = proba_df["p_front_page"] * aev
    best_dev = proba_df.loc[proba_df["expected_aev_dev_tools"].idxmax()]
    best_gen = proba_df.loc[proba_df["expected_aev_general_tech"].idxmax()]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    print(f"Dev tools: post {days[int(best_dev['hour_of_week']//24)]} {int(best_dev['hour_of_week']%24)}:00 UTC → ~${best_dev['expected_aev_dev_tools']:.0f} expected")
    print(f"General tech: post {days[int(best_gen['hour_of_week']//24)]} {int(best_gen['hour_of_week']%24)}:00 UTC → ~${best_gen['expected_aev_general_tech']:.0f} expected")


if __name__ == "__main__":
    run_timing_analysis(use_cached=True)
    run_aev_analysis()
    combined_insight()
