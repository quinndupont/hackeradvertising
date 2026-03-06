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


def fit_cox_time_to_graduation(df: pd.DataFrame) -> "CoxPHFitter | None":
    """Cox PH model for time-to-graduation (stories that never graduate = censored)."""
    if not HAS_LIFELINES:
        return None
    # Requires graduation data with time-to-event and event indicator
    if "time_to_graduation" not in df.columns or "graduated" not in df.columns:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cph = CoxPHFitter()
        df_cox = df[["time_to_graduation", "graduated", "hour_of_week", "day_of_week", "hour_of_day"]].copy()
        df_cox = df_cox.rename(columns={"time_to_graduation": "duration", "graduated": "event"})
        cph.fit(df_cox, duration_col="duration", event_col="event")
    return cph
