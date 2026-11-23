"""CSV 로더 · 검증 · 정규화.

사용 예:
    df_raw = read_csv_any_encoding(uploaded_file)
    report = validate_comments(df_raw)
    if report.ok:
        df = normalize_comments(df_raw)
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import pandas as pd

from gamepulse.content.games import resolve_game_id
from gamepulse.data.schema import ALL_COLUMNS, OPTIONAL_COLUMNS, REQUIRED_COLUMNS


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0


def read_csv_any_encoding(file) -> pd.DataFrame:
    """UTF-8(BOM 포함) → CP949(엑셀 한글) 순서로 시도해 CSV 를 읽습니다."""
    if hasattr(file, "read"):
        raw = file.read()
    else:
        with open(file, "rb") as f:
            raw = f.read()
    last_err: Exception | None = None
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc, dtype=str)
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            last_err = e
    raise ValueError(f"CSV 를 읽을 수 없습니다. 인코딩(UTF-8 권장)과 형식을 확인하세요. ({last_err})")


def validate_comments(df: pd.DataFrame) -> ValidationReport:
    report = ValidationReport(ok=True, row_count=len(df))
    cols = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in cols]
    if missing:
        report.errors.append(f"필수 컬럼이 없습니다: {', '.join(missing)}")

    unknown = [c for c in cols if c not in ALL_COLUMNS]
    if unknown:
        report.warnings.append(f"스키마에 없는 컬럼은 그대로 보존됩니다: {', '.join(unknown)}")

    if len(df) == 0:
        report.errors.append("데이터 행이 없습니다.")

    if not missing and len(df) > 0:
        d = df.copy()
        d.columns = cols
        if d["comment_id"].duplicated().any():
            report.warnings.append(f"중복된 comment_id {int(d['comment_id'].duplicated().sum())}건이 있습니다. 첫 행만 사용합니다.")
        empty_text = d["text"].isna() | (d["text"].astype(str).str.strip() == "")
        if empty_text.any():
            report.warnings.append(f"본문(text)이 비어 있는 행 {int(empty_text.sum())}건은 제외됩니다.")
        unknown_games = d["game_id"].map(resolve_game_id).isna()
        if unknown_games.any():
            samples = ", ".join(d.loc[unknown_games, "game_id"].astype(str).unique()[:5])
            report.warnings.append(f"인식할 수 없는 game_id {int(unknown_games.sum())}건은 제외됩니다. (예: {samples})")
        bad_dates = pd.to_datetime(d["posted_at"], errors="coerce").isna()
        if bad_dates.any():
            report.warnings.append(f"날짜(posted_at)를 해석할 수 없는 행 {int(bad_dates.sum())}건이 있습니다. 추이 그래프에서 제외됩니다.")

    report.ok = not report.errors
    return report


def normalize_comments(df: pd.DataFrame) -> pd.DataFrame:
    """검증을 통과한 DataFrame 을 분석용 표준 형태로 변환합니다."""
    d = df.copy()
    d.columns = [c.strip() for c in d.columns]
    for c in OPTIONAL_COLUMNS:
        if c not in d.columns:
            d[c] = pd.NA

    d["game_id"] = d["game_id"].map(resolve_game_id)
    d["text"] = d["text"].fillna("").astype(str).str.strip()
    d = d[d["game_id"].notna() & (d["text"] != "") & (d["text"].str.lower() != "nan")]
    d = d.drop_duplicates(subset="comment_id", keep="first")
    d["posted_at"] = pd.to_datetime(d["posted_at"], errors="coerce")
    d["rating"] = pd.to_numeric(d["rating"], errors="coerce")
    return d.reset_index(drop=True)


def row_issues(df: pd.DataFrame) -> pd.DataFrame:
    """행 단위 문제 목록: 원본 행 번호 · 사유 (누락 · 빈 본문 · 인식 못 한 게임 · 날짜 오류 · 중복 ID · 중복 본문).
    분석에서 제외되는 행과 '분석은 되지만 확인이 필요한' 행을 구분한다. 필수 컬럼이 없으면 빈 표."""
    d = df.copy()
    d.columns = [c.strip() for c in d.columns]
    if any(c not in d.columns for c in REQUIRED_COLUMNS):
        return pd.DataFrame(columns=["행", "comment_id", "사유", "처리"])
    rows = []
    text = d["text"].astype(str).str.strip()
    dup_id = d["comment_id"].duplicated(keep="first")
    dup_text = text.duplicated(keep="first") & (text != "") & (text.str.lower() != "nan")
    for i, r in d.iterrows():
        n = i + 2   # 엑셀 기준 행 번호 (1행 = 헤더)
        miss = [c for c in REQUIRED_COLUMNS if pd.isna(r[c]) or str(r[c]).strip() == ""]
        if miss:
            rows.append([n, r["comment_id"], f"필수값 누락: {', '.join(miss)}", "제외" if "text" in miss or "game_id" in miss else "확인"])
        if resolve_game_id(r["game_id"]) is None and "game_id" not in miss:
            rows.append([n, r["comment_id"], f"인식할 수 없는 game_id: {r['game_id']}", "제외"])
        if pd.isna(pd.to_datetime(r["posted_at"], errors="coerce")) and "posted_at" not in miss:
            rows.append([n, r["comment_id"], f"날짜 형식 오류: {r['posted_at']}", "추이 그래프에서만 제외"])
        if dup_id.loc[i]:
            rows.append([n, r["comment_id"], "중복 comment_id", "제외 (첫 행만 사용)"])
        elif dup_text.loc[i]:
            rows.append([n, r["comment_id"], "다른 행과 본문이 같음", "확인 (분석에는 포함)"])
    return pd.DataFrame(rows, columns=["행", "comment_id", "사유", "처리"])
