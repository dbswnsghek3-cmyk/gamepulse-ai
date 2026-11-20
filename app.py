"""GamePulse AI — 게임 사업PM 분석 대시보드 (Streamlit 진입점).

실행:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="GamePulse AI", page_icon="📊", layout="wide", initial_sidebar_state="auto")

# 브라우저 자동 번역 방지
# Streamlit 기본 HTML 이 lang="en" 이면 Chrome 이 한국어 화면을 번역하며 React DOM 과 충돌('removeChild' 오류)할 수 있다.
# 이전에는 실행 후 스크립트로 <html> 속성을 바꿨지만, DOM 직접 조작을 피하기 위해 제거하고
# scripts/patch_streamlit_html.py 로 처음 전송되는 HTML 자체를 lang="ko" translate="no" 로 고정한다.
def _translate_guard_applied() -> bool:
    try:
        from pathlib import Path

        idx = Path(st.__file__).parent / "static" / "index.html"
        return 'translate="no"' in idx.read_text(encoding="utf-8")
    except Exception:
        return True  # 확인할 수 없으면 경고하지 않음

from gamepulse.config import APP_VERSION  # noqa: E402
from gamepulse.content.games import GAME_ORDER, GAMES  # noqa: E402
from gamepulse.ui.components import footer, html  # noqa: E402
from gamepulse.ui.styles import inject_css  # noqa: E402
from gamepulse.views import assistant, data_lab, game_page, home, overwatch  # noqa: E402

inject_css()

PAGES = {"home": "홈 · 개요"}
PAGES.update({gid: f"{GAMES[gid]['name']}" for gid in GAME_ORDER})
PAGES.update({"data_lab": "데이터 랩 (CSV 분석)", "assistant": "PM 어시스턴트 (미리보기)"})

if st.session_state.get("page") not in PAGES:
    # 첫 접속 시 주소의 ?page= 로 바로 들어갈 수 있게 (예: ?page=overwatch&tab=04)
    qp = st.query_params.get("page")
    st.session_state["page"] = qp if qp in PAGES else "home"


def _sync_page_param() -> None:
    st.query_params["page"] = st.session_state["page"]
    if st.session_state["page"] != "overwatch":
        st.query_params.pop("tab", None)

with st.sidebar:
    html('<div class="gp-brand">Game<span>Pulse</span> AI</div>'
         f'<div class="gp-brand-sub">게임 사업PM 분석 대시보드 · {APP_VERSION}</div>')
    st.radio("메뉴", list(PAGES), format_func=PAGES.get, key="page", label_visibility="collapsed", on_change=_sync_page_param)
    st.markdown("---")
    st.caption("모든 수치·그래프는 예시 데이터입니다. 원인 분석은 검증 전 가설입니다.")
    if not _translate_guard_applied():
        st.warning("자동 번역 방지 패치가 적용되지 않았습니다. 터미널에서 `python scripts/patch_streamlit_html.py` 실행 후 서버를 다시 시작하세요.")

page = st.session_state["page"]
if page == "home":
    home.render()
elif page == "data_lab":
    data_lab.render()
elif page == "assistant":
    assistant.render()
elif page == "overwatch":
    overwatch.render()  # PROJECT RE:START 전용 페이지 (v0.1 분석은 페이지 내 부록 탭으로 유지)
else:
    game_page.render(page)

footer()
