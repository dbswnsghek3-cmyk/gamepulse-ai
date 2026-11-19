"""오버워치 페이지용 실제 자료 로더.

자료는 data/overwatch/ 의 CSV·JSON 으로 관리합니다. 파일만 교체하면 화면이 갱신됩니다.
필수 컬럼이 없으면 OverwatchDataError 를 발생시켜 화면에 오류를 표시합니다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "overwatch"
COLLECTED_AT = "2026-11-19"

REQUIRED = {
    "steam_monthly.csv": ["month", "avg_players", "gain", "pct_gain", "peak_players"],
    "pcbang_share.csv": ["id", "tracker", "period_start", "period_end", "granularity", "rank", "share_pct",
                         "metric", "source_title", "source_publisher", "source_published", "source_url", "status", "note"],
    "timeline.csv": ["date", "date_precision", "type", "title", "detail", "learning_note", "source_name", "source_url", "status"],
    # 요청 필드: opinion_id, platform, source_url, published_date, collected_date, user_type, sentiment,
    #           issue_category, summary_ko, verification_status, evidence_type (+ 보조 필드)
    "opinions.csv": ["opinion_id", "platform", "language", "content_type", "source_url", "thread_title", "post_ref",
                     "author_ref", "published_date", "collected_date", "user_type", "user_type_detail", "sentiment",
                     "issue_category", "issue_tags", "summary_ko", "quote_original", "evidence_type", "core_evidence",
                     "verification_status", "note"],
}

# 출발 분류에서 실제 의견을 읽은 뒤 수정: '팀원 비매너·팀 플레이 부담' 추가, 복귀·변경점 항목 통합
OPINION_CATEGORIES = ["영웅·스킬 학습 부담", "상대 영웅 대응 이해 부족", "복귀 적응·변경점 파악", "매칭·실력 차이",
                      "팀원 비매너·팀 플레이 부담", "전투 중 정보 과부하", "긍정적인 학습 경험", "기타"]
USER_TYPES = ["신규", "복귀", "기존", "미상"]
SENTIMENTS = ["부정", "중립", "긍정"]
VERIFIED = "검증 완료"

STEAM_SOURCE = {"name": "SteamCharts – Overwatch (App 2357570)", "url": "https://steamcharts.com/app/2357570"}


class OverwatchDataError(RuntimeError):
    pass


def _read_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise OverwatchDataError(f"자료 파일이 없습니다: data/overwatch/{name}")
    df = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)
    missing = [c for c in REQUIRED[name] if c not in df.columns]
    if missing:
        raise OverwatchDataError(f"{name} 에 필수 컬럼이 없습니다: {', '.join(missing)}")
    return df


def _mtime(name: str) -> float:
    path = DATA_DIR / name
    return path.stat().st_mtime if path.exists() else 0.0


def load_steam() -> pd.DataFrame:
    return _load_steam(_mtime("steam_monthly.csv"))


def load_pcbang() -> pd.DataFrame:
    return _load_pcbang(_mtime("pcbang_share.csv"))


def load_timeline() -> pd.DataFrame:
    return _load_timeline(_mtime("timeline.csv"))


def load_opinions() -> pd.DataFrame:
    return _load_opinions(_mtime("opinions.csv"))


def load_json(name: str) -> dict:
    return _load_json(name, _mtime(name))


# 파일 수정 시각(mtime)을 캐시 키에 포함해, CSV·JSON 을 교체하면 자동으로 다시 읽습니다.
@st.cache_data(show_spinner=False)
def _load_steam(mtime: float) -> pd.DataFrame:
    df = _read_csv("steam_monthly.csv")
    df["month"] = pd.to_datetime(df["month"] + "-01", errors="coerce")
    for c in ["avg_players", "gain", "pct_gain", "peak_players"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if df["month"].isna().any():
        raise OverwatchDataError("steam_monthly.csv 의 month 는 YYYY-MM 형식이어야 합니다.")
    return df.sort_values("month").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def _load_pcbang(mtime: float) -> pd.DataFrame:
    df = _read_csv("pcbang_share.csv")
    df["period_start"] = pd.to_datetime(df["period_start"], errors="coerce")
    df["period_end"] = pd.to_datetime(df["period_end"], errors="coerce")
    df["share_pct"] = pd.to_numeric(df["share_pct"], errors="coerce")
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df["plottable"] = df["period_start"].notna() & df["share_pct"].notna() & df["status"].str.contains("확인")
    return df


@st.cache_data(show_spinner=False)
def _load_timeline(mtime: float) -> pd.DataFrame:
    df = _read_csv("timeline.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def _load_opinions(mtime: float) -> pd.DataFrame:
    df = _read_csv("opinions.csv")
    if df["opinion_id"].duplicated().any():
        raise OverwatchDataError("opinions.csv 에 중복된 opinion_id 가 있습니다.")
    df["verified"] = df["verification_status"] == VERIFIED  # 원문을 확인한 행만 집계
    v = df[df["verified"]]
    checks = [("issue_category", OPINION_CATEGORIES), ("user_type", USER_TYPES), ("sentiment", SENTIMENTS)]
    for col, allowed in checks:
        bad = v.loc[~v[col].isin(allowed), "opinion_id"].tolist()
        if bad:
            raise OverwatchDataError(f"opinions.csv {col} 값 오류 (허용: {', '.join(allowed)}): {', '.join(bad)}")
    for oid, tags in zip(v["opinion_id"], v["issue_tags"]):
        bad_tags = [t for t in tags.split("|") if t and t not in OPINION_CATEGORIES]
        if bad_tags:
            raise OverwatchDataError(f"opinions.csv issue_tags 값 오류 ({oid}): {', '.join(bad_tags)}")
    if (v["source_url"].str.strip() == "").any():
        raise OverwatchDataError("검증 완료 의견에 원문 URL 이 비어 있는 행이 있습니다.")
    dup = v[v.duplicated(["source_url", "post_ref"], keep=False)]
    if len(dup):
        raise OverwatchDataError(f"opinions.csv 동일 게시글·답글 중복: {', '.join(dup['opinion_id'])}")
    dup_author = v[v["author_ref"].ne("") & v.duplicated("author_ref", keep=False)]
    if len(dup_author):
        raise OverwatchDataError(f"opinions.csv 동일 작성자 중복 집계: {', '.join(dup_author['opinion_id'])}")
    return df


def opinion_codes(row) -> list[str]:
    """주 분류 + 보조 분류 (복수 코딩)."""
    return [row["issue_category"]] + [t for t in str(row.get("issue_tags", "")).split("|") if t]


@st.cache_data(show_spinner=False)
def _load_json(name: str, m: float) -> dict:
    path = DATA_DIR / name
    if not path.exists():
        raise OverwatchDataError(f"자료 파일이 없습니다: data/overwatch/{name}")
    return json.loads(path.read_text(encoding="utf-8"))
