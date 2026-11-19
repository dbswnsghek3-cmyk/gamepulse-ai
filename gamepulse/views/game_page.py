"""게임별 분석 페이지: 문제 정의 → 불만 유형 → 원인 가설 → 개선 전략 → KPI → 심층 분석."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gamepulse.ai.factory import get_classifier
from gamepulse.analysis import category_summary, classify_comments, sentiment_summary, weekly_trend
from gamepulse.content.games import GAMES
from gamepulse.data.sample import generate_sample_comments
from gamepulse.ui import charts
from gamepulse.ui.components import (badge, card, grid, hero, hypo_badge, hypothesis_notice, notice, sample_badge,
                                     sample_notice, section, tier_badge)
from gamepulse.views.deep_dives import DEEP_DIVES

DIRECTION = {"up": "↑ 높을수록 좋음", "down": "↓ 낮을수록 좋음", "keep": "→ 유지 감시"}


@st.cache_data(show_spinner=False)
def _sample_analysis(game_id: str) -> pd.DataFrame:
    df = generate_sample_comments(game_id)
    return classify_comments(df, get_classifier())


def render(game_id: str) -> None:
    g = GAMES[game_id]
    hero(f"{g['short']} · {g['genre']}", g["name"], g["theme"], g["one_liner"])
    sample_notice()

    tabs = st.tabs(["① 문제 정의", "② 불만 유형", "③ 원인 가설", "④ 개선 전략", "⑤ KPI", "⑥ 심층 분석"])
    with tabs[0]:
        _problem(g)
    with tabs[1]:
        _complaints(g)
    with tabs[2]:
        _hypotheses(g)
    with tabs[3]:
        _strategies(g)
    with tabs[4]:
        _kpis(g)
    with tabs[5]:
        DEEP_DIVES[game_id]()


def _problem(g: dict) -> None:
    p = g["problem"]
    section("핵심 문제 정의", "사업PM 관점에서 이번 분석이 답하려는 질문")
    st.markdown(f'<div class="gp-statement">{p["statement"]}</div>', unsafe_allow_html=True)
    grid([
        card("배경", p["background"], variant="accent"),
        card("분석 범위", items=p["scope"], variant="accent"),
        card("핵심 질문", items=p["questions"], variant="accent"),
    ])
    notice(f"**사실 확인 메모** · {p['fact_note']}")


def _complaints(g: dict) -> None:
    section("이용자 불만 유형", "댓글·리뷰에서 반복될 것으로 예상되는 불만 범주 (분류 기준)")
    grid([
        card(c["category"], c["description"], items=[f"가상 예시: “{c['samples'][0]}”"],
             meta=f"분류 키워드: {', '.join(c['keywords'])}", variant="accent")
        for c in g["complaints"]
    ])

    df = _sample_analysis(g["id"])
    section("예시 댓글 분류 결과", f"가상 댓글 {len(df)}건을 규칙 기반 분류기로 분류한 결과입니다. 실제 CSV 는 '데이터 랩'에서 분석할 수 있습니다.", sample_badge())
    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(charts.complaint_bar(category_summary(df), "불만 유형 분포 (예시 데이터)"), config=charts.PLOTLY_CONFIG)
    with c2:
        st.plotly_chart(charts.sentiment_donut(sentiment_summary(df), "감성 분포 (예시 데이터)"), config=charts.PLOTLY_CONFIG)

    cats = ["전체"] + [c["category"] for c in g["complaints"]]
    pick = st.selectbox("추이를 볼 불만 유형", cats, key=f"trend_{g['id']}")
    trend = weekly_trend(df)
    if pick != "전체":
        trend = trend[trend["category"] == pick]
    st.plotly_chart(charts.trend_line(trend, "주차별 불만 언급 추이 (예시 데이터)"), config=charts.PLOTLY_CONFIG)

    with st.expander("예시 댓글 원본 보기 (가상 문장)"):
        st.dataframe(
            df[["posted_at", "source", "user_segment", "text", "pred_category", "pred_sentiment", "pred_confidence"]]
            .rename(columns={"posted_at": "작성일", "source": "출처", "user_segment": "이용자 구분", "text": "댓글(가상)",
                             "pred_category": "분류 결과", "pred_sentiment": "감성", "pred_confidence": "신뢰도"}),
            hide_index=True,
        )


def _hypotheses(g: dict) -> None:
    section("원인 가설", "불만 → 원인의 연결은 검증 전까지 가설입니다. 각 가설마다 검증 방법을 함께 설계했습니다.", hypo_badge())
    hypothesis_notice()
    grid([
        card(
            f"{h['id']}. {h['statement']}",
            f"**근거(추론)** {h['rationale']}",
            items=[f"**검증 방법** {h['validation']}", f"**필요 데이터** {h['data_needed']}"],
            meta=f"관련 불만 유형: {', '.join(h['related'])}",
            top=hypo_badge(),
        )
        for h in g["hypotheses"]
    ])


def _strategies(g: dict) -> None:
    section("사업PM 개선 전략", "각 전략은 검증할 가설과 연결되어 있으며, 효과·난이도는 PM의 가정 평가입니다.")
    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(charts.priority_matrix(g["strategies"], "전략 우선순위 매트릭스 (가정 평가)"), config=charts.PLOTLY_CONFIG)
    with c2:
        order = {"단기": 0, "중기": 1, "장기": 2}
        roadmap = sorted(g["strategies"], key=lambda s: (order.get(s["phase"], 9), -s["impact"]))
        st.markdown("**실행 로드맵 (제안)**")
        for s in roadmap:
            st.markdown(f"- `{s['phase']}` **{s['title']}** · 대상 {', '.join(s['targets'])}")
        st.caption("단기: 1분기 내 실험 가능 / 중기: 2~3분기 / 장기: 시스템 개편 필요")
    grid([
        card(s["title"], items=s["actions"],
             meta=f"검증 가설 {', '.join(s['targets'])} · 예상 효과 {s['impact']}/5 · 난이도 {s['effort']}/5 (가정)",
             top=badge(s["phase"], "tier-core"), variant="accent")
        for s in g["strategies"]
    ])


def _kpis(g: dict) -> None:
    section("KPI 체계", "North Star 1개 · 핵심 지표 · 가드레일(부작용 감시) 지표로 구성", sample_badge())
    kpis = g["kpis"]
    ns = [k for k in kpis if k["tier"] == "North Star"]
    rest = [k for k in kpis if k["tier"] != "North Star"]

    def kpi_card(k, variant=""):
        arrow = "→" if k["direction"] != "keep" else "="
        value = (f'<div class="gp-kpi-value">{k["baseline"]}<small>{k["unit"]}</small> '
                 f'<span class="gp-kpi-arrow">{arrow}</span> {k["target"]}<small>{k["unit"]}</small></div>')
        return card(k["name"], k["definition"], meta=f"{DIRECTION[k['direction']]} · 현재 → 목표 (예시 수치)",
                    top=tier_badge(k["tier"]) + sample_badge() + value, variant=f"gp-kpi {variant}")

    grid([kpi_card(k, "accent") for k in ns])
    grid([kpi_card(k) for k in rest])

    st.plotly_chart(charts.kpi_compare(kpis, "비율형 KPI 현재 vs 목표 (예시 데이터)"), config=charts.PLOTLY_CONFIG)

    with st.expander("KPI 정의서 (산식 · 방향)", expanded=False):
        st.dataframe(
            pd.DataFrame([{"구분": k["tier"], "KPI": k["name"], "정의": k["definition"], "산식": k["formula"],
                           "방향": DIRECTION[k["direction"]], "현재(예시)": f"{k['baseline']}{k['unit']}",
                           "목표(예시)": f"{k['target']}{k['unit']}"} for k in kpis]),
            hide_index=True,
        )
    st.caption("현재 값이 0인 지표는 '신규 도입 기능'의 지표로, 도입 후 측정을 시작한다는 의미입니다.")
