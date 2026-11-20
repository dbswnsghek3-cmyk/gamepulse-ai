"""GamePulse AI — 게임 사업PM 분석 대시보드 (Streamlit 진입점).

실행:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="GamePulse AI", page_icon="📊", layout="wide", initial_sidebar_state="auto")

from gamepulse.config import APP_VERSION  # noqa: E402
from gamepulse.content.games import GAME_ORDER, GAMES  # noqa: E402
from gamepulse.ui.components import footer, html  # noqa: E402
from gamepulse.ui.styles import inject_css  # noqa: E402
from gamepulse.ui.translate_guard import ensure as ensure_translate_guard  # noqa: E402
from gamepulse.views import assistant, data_lab, game_page, home, overwatch, pubg  # noqa: E402


@st.cache_resource(show_spinner=False)
def _translate_guard() -> tuple[bool, str]:
    """브라우저 자동 번역 방지 (lang="ko" translate="no"). 서버 프로세스당 1회 자동 적용.

    Streamlit Cloud 처럼 배포 때마다 패키지가 새로 설치되는 환경에서도 수동 실행 없이 적용된다.
    실패해도 앱은 그대로 실행되고, 원인은 서버 로그에만 남긴다 (방문자 화면에 개발용 경고를 띄우지 않음).
    """
    return ensure_translate_guard()


_translate_guard()
inject_css()

PAGES = {"home": "홈 · 개요"}
PAGES.update({gid: f"{GAMES[gid]['name']}" for gid in GAME_ORDER})
PAGES["pubg"] = "PUBG: NEW START"
PAGES.update({"data_lab": "데이터 랩 (CSV 분석)", "assistant": "PM 어시스턴트 (미리보기)"})

if st.session_state.get("page") not in PAGES:
    # 첫 접속 시 주소의 ?page= 로 바로 들어갈 수 있게 (예: ?page=overwatch&tab=04)
    qp = st.query_params.get("page")
    st.session_state["page"] = qp if qp in PAGES else "home"


def _sync_page_param() -> None:
    st.query_params["page"] = st.session_state["page"]
    if st.session_state["page"] not in ("overwatch", "pubg"):
        st.query_params.pop("tab", None)

with st.sidebar:
    html('<div class="gp-brand">Game<span>Pulse</span> AI</div>'
         f'<div class="gp-brand-sub">게임 사업PM 분석 대시보드 · {APP_VERSION}</div>')
    st.radio("메뉴", list(PAGES), format_func=PAGES.get, key="page", label_visibility="collapsed", on_change=_sync_page_param)
    st.markdown("---")
    st.caption("'실제 자료' 배지가 없는 수치·그래프는 예시·가정 데이터입니다. 원인 분석은 검증 전 가설입니다.")

page = st.session_state["page"]
if page == "home":
    home.render()
elif page == "data_lab":
    data_lab.render()
elif page == "assistant":
    assistant.render()
elif page == "overwatch":
    overwatch.render()  # PROJECT RE:START 전용 페이지 (v0.1 분석은 페이지 내 부록 탭으로 유지)
elif page == "pubg":
    pubg.render()       # PUBG: NEW START (v0.1 예시 분석은 game_page·games.py 에 보관, 메뉴에서는 제외)
else:
    game_page.render(page)

footer()
