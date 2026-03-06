"""Phase 1: Timing analysis pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from config import DATA_DIR
from src.data.algolia import pull_algolia_stories
from src.analysis.replicate import prior_studies_table
from src.models.timing import (
    prepare_features,
    fit_logistic,
    fit_xgboost,
    feature_importance_xgb,
    predict_p_front_page_by_hour,
    compute_competition_load,
)


def run_timing_analysis(months: int = 6, use_cached: bool = True) -> None:
    """Run full Phase 1 pipeline."""
    cache_path = DATA_DIR / "algolia_stories.parquet"
    if use_cached and cache_path.exists():
        df = pd.read_parquet(cache_path)
        print(f"Loaded {len(df)} stories from cache")
    else:
        df = pull_algolia_stories(months=months)
        print(f"Fetched {len(df)} stories")

    if df.empty or len(df) < 1000:
        print("Insufficient data. Run without use_cached=True to fetch fresh data.")
        return

    # Replication
    print("\n--- Prior Studies Replication ---")
    table = prior_studies_table(df)
    print(table.to_string())

    # Prepare features
    df["competition_load"] = compute_competition_load(df)
    X, Y1, Y2, _ = prepare_features(df)

    # Models
    print("\n--- Logistic Regression (Y1) ---")
    lr, scaler = fit_logistic(X, Y1)
    print(f"Logistic accuracy: {(lr.predict(scaler.transform(X)) == Y1).mean():.3f}")

    print("\n--- XGBoost (Y1) ---")
    xgb = fit_xgboost(X, Y1)
    imp = feature_importance_xgb(xgb, list(X.columns))
    print(imp.to_string(index=False))

    # Heatmap
    X_template = X.head(1).copy()
    X_template["competition_load"] = 50
    proba_df = predict_p_front_page_by_hour(xgb, X_template, None, use_xgb=True)
    pivot = proba_df.set_index("hour_of_week")["p_front_page"].values.reshape(7, 24)

    fig, ax = plt.subplots(figsize=(12, 4))
    sns.heatmap(
        pivot,
        xticklabels=range(24),
        yticklabels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        cmap="YlOrRd",
        ax=ax,
        cbar_kws={"label": "P(front page)"},
    )
    ax.set_xlabel("Hour (UTC)")
    ax.set_ylabel("Day of week")
    ax.set_title("P(front page) by hour-of-week (XGBoost)")
    plt.tight_layout()
    out = DATA_DIR.parent / "reports"
    out.mkdir(exist_ok=True)
    plt.savefig(out / "timing_heatmap.png", dpi=150)
    plt.close()
    print(f"\nHeatmap saved to {out / 'timing_heatmap.png'}")

    # Recommendations
    best_hour = proba_df.loc[proba_df["p_front_page"].idxmax(), "hour_of_week"]
    best_day = int(best_hour // 24)
    best_hr = int(best_hour % 24)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    print(f"\n--- Recommendation ---")
    print(f"Maximize P(front page): {days[best_day]} {best_hr}:00 UTC")
    print("Maximize reach: Post during peak traffic (typically US daytime UTC 14-22)")


if __name__ == "__main__":
    run_timing_analysis(months=6, use_cached=True)
