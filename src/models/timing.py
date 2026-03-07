"""Phase 1: Timing analysis models."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import warnings

try:
    from lifelines import CoxPHFitter
    HAS_LIFELINES = True
except ImportError:
    HAS_LIFELINES = False


def compute_competition_load(df: pd.DataFrame) -> pd.Series:
    """Stories submitted in same hour (UTC)."""
    return df.groupby(["day_of_week", "hour_of_day"]).transform("size")


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """Prepare X, Y1, Y2 for modeling."""
    df = df.copy()
    df["competition_load"] = compute_competition_load(df)

    feature_cols = [
        "hour_of_week", "day_of_week", "hour_of_day",
        "competition_load", "has_url", "is_show_hn", "is_ask_hn",
        "title_word_count",
    ]
    X = df[feature_cols].fillna(0).astype(float)
    X["has_url"] = X["has_url"].astype(int)
    X["is_show_hn"] = X["is_show_hn"].astype(int)
    X["is_ask_hn"] = X["is_ask_hn"].astype(int)

    Y1 = (df["points"] >= 50).astype(int)
    Y2 = df["points"].clip(upper=500)
    return X, Y1, Y2, df


def fit_logistic(X: pd.DataFrame, y: pd.Series) -> tuple[LogisticRegression, StandardScaler]:
    """Logistic regression baseline for Y1."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_scaled, y)
    return clf, scaler


def fit_xgboost(X: pd.DataFrame, y: pd.Series) -> XGBClassifier:
    """Gradient boosted classifier for Y1."""
    clf = XGBClassifier(n_estimators=100, max_depth=4, random_state=42, eval_metric="logloss")
    clf.fit(X, y)
    return clf


def feature_importance_xgb(model: XGBClassifier, feature_names: list) -> pd.DataFrame:
    """Extract feature importance from XGBoost."""
    imp = model.feature_importances_
    return pd.DataFrame({"feature": feature_names, "importance": imp}).sort_values("importance", ascending=False)


def predict_p_front_page_by_hour(model, X_template: pd.DataFrame, scaler: StandardScaler | None, use_xgb: bool) -> pd.DataFrame:
    """Generate P(front page) for each hour-of-week."""
    hours = np.arange(168)
    rows = []
    for h in hours:
        row = X_template.iloc[0].copy()
        row["hour_of_week"] = h
        row["day_of_week"] = h // 24
        row["hour_of_day"] = h % 24
        row["competition_load"] = 50  # placeholder
        rows.append(row)
    X_pred = pd.DataFrame(rows)
    if use_xgb:
        proba = model.predict_proba(X_pred)[:, 1]
    else:
        X_scaled = scaler.transform(X_pred)
        proba = model.predict_proba(X_scaled)[:, 1]
    return pd.DataFrame({"hour_of_week": hours, "p_front_page": proba})


def prepare_graduation_features(
    firebase_df: pd.DataFrame, algolia_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """
    Merge Firebase graduation data with Algolia-derived features (has_url, is_show_hn, etc.).
    Algolia uses objectID = HN item id.
    """
    df = firebase_df.copy()
    df["id"] = df["id"].astype(int)
    if algolia_df is not None and "objectID" in algolia_df.columns:
        algolia_df = algolia_df.rename(columns={"objectID": "id"})
        algolia_df["id"] = algolia_df["id"].astype(int)
        feature_cols = ["id", "has_url", "is_show_hn", "is_ask_hn", "title_word_count"]
        available = [c for c in feature_cols if c in algolia_df.columns and c != "id"]
        if available:
            merge_cols = ["id"] + available
            algolia_sub = algolia_df[merge_cols].drop_duplicates(subset=["id"])
            df = df.merge(algolia_sub, on="id", how="left")
            for c in available:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(float)
    return df


def fit_cox_time_to_graduation(df: pd.DataFrame) -> "CoxPHFitter | None":
    """
    Cox PH model for time-to-graduation (stories that never graduate = censored).
    Includes velocity covariates (early_velocity_30, velocity_votes_per_min) if present.
    """
    if not HAS_LIFELINES:
        return None
    if "time_to_graduation" not in df.columns or "graduated" not in df.columns:
        return None
    covar_cols = [c for c in ["hour_of_week", "early_velocity_30", "velocity_votes_per_min"] if c in df.columns]
    for attempt in [covar_cols, ["early_velocity_30", "velocity_votes_per_min"], ["hour_of_week"], []]:
        cols = [c for c in attempt if c in df.columns]
        df_cox = df[["time_to_graduation", "graduated", *cols]].copy().dropna()
        if len(df_cox) < 10 or df_cox["graduated"].sum() < 3:
            continue
        df_cox = df_cox.rename(columns={"time_to_graduation": "duration", "graduated": "event"})
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cph = CoxPHFitter()
            try:
                cph.fit(df_cox, duration_col="duration", event_col="event")
                return cph
            except Exception:
                continue
    return None
