"""댓글 데이터 분석 파이프라인 (예시 데이터 · 실제 CSV 공용)."""

from __future__ import annotations

import pandas as pd

from gamepulse.ai.base import CommentClassifier


def classify_comments(df: pd.DataFrame, classifier: CommentClassifier) -> pd.DataFrame:
    """game_id 별로 분류기를 돌려 pred_* 컬럼을 추가합니다."""
    out = df.copy()
    out["pred_category"] = ""
    out["pred_sentiment"] = ""
    out["pred_confidence"] = 0.0
    out["pred_method"] = classifier.name
    for gid, idx in out.groupby("game_id").groups.items():
        results = classifier.classify_many(out.loc[idx, "text"].tolist(), gid)
        out.loc[idx, "pred_category"] = [r.category for r in results]
        out.loc[idx, "pred_sentiment"] = [r.sentiment for r in results]
        out.loc[idx, "pred_confidence"] = [r.confidence for r in results]
    return out


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    s = df["pred_category"].value_counts().rename_axis("category").reset_index(name="count")
    s["share"] = (s["count"] / s["count"].sum() * 100).round(1)
    return s


def weekly_trend(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["posted_at"]).copy()
    if d.empty:
        return pd.DataFrame(columns=["week", "category", "count"])
    d["week"] = d["posted_at"].dt.to_period("W").dt.start_time
    return d.groupby(["week", "pred_category"]).size().reset_index(name="count").rename(columns={"pred_category": "category"})


def sentiment_summary(df: pd.DataFrame) -> pd.DataFrame:
    return df["pred_sentiment"].value_counts().rename_axis("sentiment").reset_index(name="count")
