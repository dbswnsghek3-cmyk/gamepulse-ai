"""댓글 데이터 스키마.

실제 댓글 CSV 를 불러올 때 아래 컬럼 구조를 따르면 바로 분석할 수 있습니다.
개인정보 보호를 위해 작성자 닉네임·계정 ID 등은 수집하지 않는 것을 권장합니다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Column:
    name: str
    required: bool
    dtype: str
    description: str
    example: str


COMMENT_SCHEMA: list[Column] = [
    Column("comment_id", True, "str", "댓글 고유 ID (중복 불가)", "c_000123"),
    Column("game_id", True, "str", "게임 ID 또는 게임 이름 (overwatch / pubg / fconline / dnf / lol, '오버워치' 등 한글명도 허용)", "lol"),
    Column("source", True, "str", "수집 출처 (커뮤니티, 앱 리뷰, SNS, 설문 등)", "커뮤니티"),
    Column("posted_at", True, "date", "작성 일시 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM)", "2026-10-01"),
    Column("text", True, "str", "댓글 본문", "연패 오니까 솔랭은 너무 스트레스라 칼바람만 해요"),
    Column("rating", False, "float", "별점 등 수치 평가 (1~5, 없으면 비움)", "2"),
    Column("user_segment", False, "str", "이용자 구분 (신규 / 기존 / 복귀 등, 알 수 있을 때만)", "기존"),
    Column("category", False, "str", "사람이 직접 붙인 불만 유형 라벨 (있으면 분류기 결과와 비교 가능)", "연패 스트레스·경쟁 피로"),
    Column("sentiment", False, "str", "사람이 직접 붙인 감성 라벨 (부정 / 중립 / 긍정)", "부정"),
    Column("url", False, "str", "원문 링크 (선택)", ""),
]

REQUIRED_COLUMNS = [c.name for c in COMMENT_SCHEMA if c.required]
OPTIONAL_COLUMNS = [c.name for c in COMMENT_SCHEMA if not c.required]
ALL_COLUMNS = [c.name for c in COMMENT_SCHEMA]

# 분류기가 결과를 채워 넣는 컬럼
PREDICTED_COLUMNS = ["pred_category", "pred_sentiment", "pred_confidence", "pred_method"]

SENTIMENTS = ["부정", "중립", "긍정"]


def schema_table() -> pd.DataFrame:
    """화면 표시용 스키마 표."""
    return pd.DataFrame(
        [
            {
                "컬럼": c.name,
                "필수": "필수" if c.required else "선택",
                "형식": c.dtype,
                "설명": c.description,
                "예시": c.example,
            }
            for c in COMMENT_SCHEMA
        ]
    )


def template_dataframe() -> pd.DataFrame:
    """빈 CSV 템플릿 (예시 1행 포함)."""
    return pd.DataFrame([{c.name: c.example for c in COMMENT_SCHEMA}])
