"""Replicate prior studies and produce comparison table."""
import pandas as pd
from config import DATA_DIR


def replicate_schaefer_2017(df: pd.DataFrame) -> dict:
    """Schaefer/Medium 2017: score>250 as top post, when submitted. Conclusion: Mon/Wed 5-6 PM UTC."""
    top = df[df["points"] >= 250]
    if top.empty:
        return {"conclusion": "Mon/Wed 5-6 PM UTC", "replicated_best": "N/A (insufficient data)", "delta": "N/A"}
    best = top.groupby(["day_of_week", "hour_of_day"]).size().idxmax()
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    replicated = f"{day_names[best[0]]} {best[1]}:00 UTC"
    return {"conclusion": "Mon/Wed 5-6 PM UTC", "replicated_best": replicated, "delta": "Compare"}


def replicate_chanind_2019(df: pd.DataFrame) -> dict:
    """chanind.github.io 2019: P(front page | hour), score>50, posts/hour normalization. Sun 6am UTC best."""
    df = df.copy()
    df["fp"] = df["points"] >= 50
    id_col = "objectID" if "objectID" in df.columns else "created_at"
    hourly = df.groupby(["day_of_week", "hour_of_day"]).agg({"fp": "mean", id_col: "count"}).reset_index()
    hourly.columns = ["day_of_week", "hour_of_day", "fp_rate", "posts"]
    hourly = hourly[hourly["posts"] >= 10]
    if hourly.empty:
        return {"conclusion": "Sun 6am UTC 2.5x better", "replicated_best": "N/A", "delta": "N/A"}
    best_row = hourly.loc[hourly["fp_rate"].idxmax()]
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    # chanind uses Sunday=0
    d = int(best_row["day_of_week"])
    h = int(best_row["hour_of_day"])
    replicated = f"{day_names[d]} {h}:00 UTC"
    return {"conclusion": "Sun 6am UTC 2.5x better", "replicated_best": replicated, "delta": "Compare"}


def replicate_myriade_2025(df: pd.DataFrame) -> dict:
    """Myriade 2025: Show HN, 12:00 UTC weekends. European midday + pre-West-Coast."""
    show = df[df["is_show_hn"]]
    if len(show) < 100:
        return {"conclusion": "12:00 UTC weekends", "replicated_best": "N/A (few Show HN)", "delta": "N/A"}
    show_fp = show[show["points"] >= 50]
    best = show_fp.groupby(["day_of_week", "hour_of_day"]).size().idxmax()
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    replicated = f"{day_names[best[0]]} {best[1]}:00 UTC"
    return {"conclusion": "12:00 UTC weekends", "replicated_best": replicated, "delta": "Compare"}


def prior_studies_table(df: pd.DataFrame) -> pd.DataFrame:
    """Produce [Study | Their Conclusion | Replicated on Current Data | Delta] table."""
    rows = [
        replicate_schaefer_2017(df),
        replicate_chanind_2019(df),
        replicate_myriade_2025(df),
    ]
    studies = ["Schaefer/Medium 2017", "chanind.github.io 2019", "Myriade 2025"]
    table = pd.DataFrame(rows, index=studies)
    table.index.name = "Study"
    return table
