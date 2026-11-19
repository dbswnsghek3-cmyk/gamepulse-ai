"""홈 · 개요 페이지."""

from __future__ import annotations

import streamlit as st

from gamepulse.config import APP_NAME, APP_TAGLINE
from gamepulse.content.games import GAME_ORDER, GAMES
from gamepulse.ui.components import badge, card, grid, hero, sample_notice, section


def _go(page: str) -> None:
    st.session_state["page"] = page


def render() -> None:
    hero("Game Business PM Portfolio", APP_NAME, APP_TAGLINE,
         "불만을 '가설'로 바꾸고, 가설을 '실험 가능한 전략'과 'KPI'로 바꾼다.")
    sample_notice()

    section("분석 대상 게임", "게임을 선택하면 문제 정의부터 KPI까지 한 흐름으로 볼 수 있습니다. (모바일은 좌측 상단 › 메뉴에서도 선택 가능)")
    cols = st.columns(len(GAME_ORDER))
    for i, gid in enumerate(GAME_ORDER):
        g = GAMES[gid]
        with cols[i % len(cols)]:
            st.markdown(
                card(g["name"], g["theme"], top=badge(g["genre"], "plain"), variant="accent"),
                unsafe_allow_html=True,
            )
            st.button("분석 보기 →", key=f"go_{gid}", on_click=_go, args=(gid,))

    section("분석 프레임워크", "모든 게임을 같은 5단계 구조로 분석해 비교 가능성을 확보했습니다.")
    grid([
        card("① 문제 정의", "사업 관점에서 '누가, 어디서, 왜 떠나는가'를 한 문장으로 정의"),
        card("② 불만 유형", "댓글·리뷰를 분류할 기준(카테고리·키워드)을 먼저 설계"),
        card("③ 원인 가설", "불만과 원인의 연결을 가설로 두고, 검증 방법·필요 데이터를 명시"),
        card("④ 개선 전략", "가설별 실행안을 효과·난이도로 우선순위화하고 로드맵화"),
        card("⑤ KPI", "North Star · 핵심 · 가드레일 지표를 게임별 주제에 맞게 다르게 구성"),
    ])

    section("데이터 · AI 확장 구조", "현재는 기본 웹사이트 단계이며, 아래 기능은 다음 단계에서 연결합니다.")
    grid([
        card("실제 댓글 CSV 분석", "표준 스키마(comment_id, game_id, source, posted_at, text …)를 따르는 CSV 를 '데이터 랩'에서 업로드하면 같은 파이프라인으로 분석", top=badge("지금 사용 가능", "tier-core")),
        card("AI 댓글 분류", "현재는 키워드 규칙 기반 분류기. 공통 인터페이스로 설계되어 생성형 AI 분류기로 교체 가능", top=badge("다음 단계", "tier-guard")),
        card("사업PM 챗봇", "현재는 분석 콘텐츠 검색형 응답. 이후 생성형 AI 를 연결해 질의응답 고도화", top=badge("다음 단계", "tier-guard")),
    ])
