"""PM 어시스턴트(챗봇) 페이지 — 현재는 규칙 기반 응답, 다음 단계에서 생성형 AI 연결."""

from __future__ import annotations

import streamlit as st

from gamepulse.ai.base import ChatMessage
from gamepulse.ai.factory import get_chatbot
from gamepulse.content.games import GAME_ORDER, GAMES
from gamepulse.ui.components import hero, notice

EXAMPLES = [
    "리그 오브 레전드 KPI 알려줘",
    "FC 온라인 강화 실패 원인 가설은?",
    "배그 신규 이용자 개선 전략",
    "던파 불만 유형 정리해줘",
]


def render() -> None:
    hero("PM Assistant · Preview", "사업PM 어시스턴트", "게임별 분석 내용을 대화형으로 찾아볼 수 있습니다.")
    notice("**현재는 생성형 AI 가 연결되지 않은 미리보기**입니다. 사이트에 정리된 분석 콘텐츠에서 관련 항목을 찾아 보여 주며, 새로운 사실을 만들어 내지 않습니다.")

    options = [None] + GAME_ORDER
    game = st.selectbox("대상 게임 (선택하지 않으면 질문에서 자동 인식)", options,
                        format_func=lambda x: "자동 인식" if x is None else GAMES[x]["name"])

    if "chat" not in st.session_state:
        st.session_state.chat = []

    cols = st.columns(2)
    clicked = None
    for i, ex in enumerate(EXAMPLES):
        if cols[i % 2].button(ex, key=f"ex_{i}"):
            clicked = ex

    for m in st.session_state.chat:
        with st.chat_message(m.role):
            st.markdown(m.content.replace("~", "\\~"))  # '1~2' 가 취소선으로 바뀌는 것 방지

    prompt = st.chat_input("예: 오버워치 신규 이용자 KPI 는?") or clicked
    if prompt:
        st.session_state.chat.append(ChatMessage("user", prompt))
        answer = get_chatbot().reply(st.session_state.chat, game)
        st.session_state.chat.append(ChatMessage("assistant", answer))
        st.rerun()

    if st.session_state.chat and st.button("대화 지우기"):
        st.session_state.chat = []
        st.rerun()
