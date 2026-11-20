"""PUBG: NEW START — 신규 유저 정착(TRACK A) · 성장형 스킨 BM(TRACK B) 사업PM 포트폴리오.

구성 (오버워치 RE:START 와 같은 01~06 탭 · 같은 배지·차트 카드·색 규칙)
- 01 문제·결론 · 02 실제 근거 · 03 원인 가설 · 04 해결책 데모 · 05 KPI·A/B 테스트 · 06 실행·사업 제안
- 공식 사실·가정값·시연 데이터는 data/pubg/newstart.json, 실제 유저 의견은 data/pubg/opinions.csv(Steam 리뷰 직접 분류),
  공개 지표는 data/pubg/steam_monthly.csv. 계산은 gamepulse/sim/newstart_sim.py 한 곳에서 한다.
- TRACK A = 블루, TRACK B = 코랄. 두 트랙을 같은 이탈 원인으로 묶지 않는다.
- PUBG 실제 게임 화면은 아직 확보하지 못해 '캡처 필요' 자리만 표시한다 (임의 이미지 생성 금지).
"""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gamepulse.sim import newstart_sim as S
from gamepulse.ui.components import html
from gamepulse.views.overwatch import (C_CTRL, C_MUTED, C_TREAT, KIND, b_hypo, b_interp, b_mock, b_real, b_sample, b_sim,
                                       badge_legend, bullets, chart_card, head, hpair, link, note, pp, sub, table, tiles)

DATA = Path(__file__).resolve().parents[2] / "data" / "pubg"
C_CORAL, C_CORAL_L = "#E97870", "#F6C7C1"

SECTIONS = [("01", "문제·결론"), ("02", "실제 근거"), ("03", "원인 가설"), ("04", "해결책 데모"),
            ("05", "KPI·A/B 테스트"), ("06", "실행·사업 제안")]
TAB_LABELS = [f"{n} {t}" for n, t in SECTIONS]
TAB_KEY = "pg_tab"


# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load() -> tuple[dict, pd.DataFrame, pd.DataFrame, dict]:
    ns = json.loads((DATA / "newstart.json").read_text(encoding="utf-8"))
    ops = pd.read_csv(DATA / "opinions.csv", dtype=str).fillna("")
    steam = pd.read_csv(DATA / "steam_monthly.csv")
    pool = json.loads((DATA / "review_pool.json").read_text(encoding="utf-8"))
    return ns, ops, steam, pool


def tr(t: str) -> str:
    return {"A": '<span class="pg-tr a">TRACK A</span>', "B": '<span class="pg-tr b">TRACK B</span>'}.get(
        t, '<span class="pg-tr c">공통</span>')


def _tab_from_query() -> str:
    q = str(st.query_params.get("tab", ""))
    return next((lab for lab in TAB_LABELS if lab.startswith(q.zfill(2)[:2])), TAB_LABELS[0]) if q else TAB_LABELS[0]


def _sync_tab_param() -> None:
    st.query_params["page"] = "pubg"
    st.query_params["tab"] = str(st.session_state.get(TAB_KEY, TAB_LABELS[0]))[:2]


def tab_nav() -> int:
    if st.session_state.get(TAB_KEY) not in TAB_LABELS:
        st.session_state[TAB_KEY] = _tab_from_query()
    sel = st.radio("섹션 선택", TAB_LABELS, key=TAB_KEY, horizontal=True, label_visibility="collapsed", on_change=_sync_tab_param)
    return TAB_LABELS.index(sel)


def slot(title: str, need: str) -> None:
    html(f'<div class="pg-slot"><b>실제 게임 화면 캡처 필요</b><span>{escape(title)}</span><small>{escape(need)}</small></div>')


def gantt(sc: dict) -> str:
    W = sc["decision"]
    rows = [("TRACK A · A1 (신규)", {**{w: ("assign", "배정") for w in range(sc["a_assign"][0], sc["a_assign"][1] + 1)},
                                    sc["a_d7"]: ("d7", "D7 판정"), sc["a_d30"]: ("d30", "D30")}),
            ("TRACK B · B1 (상점)", {**{w: ("assign", "배정") for w in range(sc["b_assign"][0], sc["b_assign"][1] + 1)},
                                    sc["b_conv"]: ("d7", "전환 판정"), sc["b_repurchase"]: ("d30", "재구매")}),
            ("의사결정", {sc["a_d7"]: ("dec", "A1 1차"), sc["b_conv"]: ("dec", "B1 1차"), W: ("dec", "최종")})]
    head_ = "".join(f"<th>{w}주</th>" for w in range(1, W + 1))
    body = "".join(f"<tr><th>{escape(n)}</th>" + "".join(
        f'<td class="{c[w][0]}">{escape(c[w][1])}</td>' if w in c else "<td></td>" for w in range(1, W + 1)) + "</tr>" for n, c in rows)
    return f'<div class="gp-table-wrap"><table class="ow-gantt"><tr><th>준비 2주 이후</th>{head_}</tr>{body}</table></div>'


# ======================================================================
def render() -> None:
    ns, ops, steam, pool = load()
    plan = S.plan(ns["experiment"])
    html('<div class="gp-ow-page"></div>')          # 오버워치와 같은 반응형·배경 스타일 범위
    cv = ns["cover"]
    html(f'<div class="ow-cover"><div class="ow-cover-t">{escape(cv["title"])}</div>'
         f'<div class="ow-cover-c">{escape(cv["copy"])}</div></div>')
    html('<div class="ow-hero3 pg-hero">'
         f'<div><span>TRACK A · 신규 유저 정착</span><b>{escape(cv["problem"])}</b><small>{escape(cv["problem_sub"])}</small></div>'
         f'<div><span>TRACK B · 성장형 스킨 BM</span><b>{escape(cv["bm_problem"])}</b><small>{escape(cv["bm_problem_sub"])}</small></div>'
         f'<div><span>우선 검증할 MVP</span><b>{escape(cv["solution"])}</b><small>{escape(cv["solution_sub"])}</small></div></div>')
    i = tab_nav()
    badge_legend()
    html(f'<div class="ow-pane-mark" data-tab="{SECTIONS[i][0]}"></div>')   # 정적 보고서 탭 경계 표식
    [lambda: s1(ns, ops, plan, pool), lambda: s2(ns, ops, steam, pool), lambda: s3(ns, ops, pool),
     lambda: s4(ns), lambda: s5(ns, plan), lambda: s6(ns, plan)][i]()
    st.caption(f"{ns['disclaimer']} · 자료 확인일 2026-11-20 · 실제 게임 화면은 캡처 확보 전")


# ======================================================================
# 01 문제·결론
def s1(ns: dict, ops: pd.DataFrame, plan: dict, pool: dict) -> None:
    pr = {p["key"]: p for p in ns["proposals"]}
    sub("두 가지 문제 → 우선 검증할 MVP 2개", b_mock())
    html('<div class="ow-map">' + "".join(
        f'<div class="ow-map-i pg-{t.lower()}"><div class="ow-map-p"><span>TRACK {t} 문제</span>{escape(pr[k]["problem"])}</div>'
        f'<div class="ow-map-a">→</div><div class="ow-map-s"><span>{k} · MVP</span><b>{escape(pr[k]["name"])}</b>'
        f'<small>{escape(pr[k]["tagline"])} · {escape(pr[k]["diff"])}</small></div></div>' for t, k in [("A", "A1"), ("B", "B1")]) + "</div>")

    a = ops[ops["track"] == "A"]
    gap = a["category"].isin(["실력 격차·매칭", "봇→실전 전환", "초반 교전·첫 사망"]).sum()
    a_ = plan["A"]
    sub("PM 의사결정 요약")
    cards = [("a", "왜 먼저인가", b_real(), f"훈련(17챕터·14일 미션)은 이미 있다. 리뷰 {len(a)}건 중 {gap}건이 '실전 전환 뒤' 격차를 말한다."),
             ("b", "BM은 왜 정보부터", b_real(), "이중 가챠는 42.1에서 제거됐다. 남은 불만은 결과·총비용 예측이라 확률보다 안내가 먼저다."),
             ("a", "무엇으로 판단", b_mock(), f"A1: 신규 D7 +{a_['mde']:.1f}%p(MDE) · B1: 구매 전환율 −{ns['experiment']['B']['ni_margin']:.1f}%p 이내 유지"),
             ("a", "비용 대비 효과", b_sim(), f"A1 {plan['a1_cost'] / 1e4:,.0f}만 원 ÷ 분기 추가 D7 {plan['quarter_added_d7']:,.0f}명 ≈ 1명당 {plan['a1_cost_per_added']:,.0f}원")]
    html('<div class="ow-dec">' + "".join(
        f'<div class="ow-dec-i"><div class="ow-dec-q">{escape(q)} <span class="ow-dec-b">{b}</span></div><div class="ow-dec-a">{escape(t)}</div></div>'
        for _, q, b, t in cards) + "</div>")

    sub("사업적으로 왜 중요한가", b_interp())
    html('<div class="pg-cards">'
         '<div class="pg-card a"><div class="k">TRACK A</div><h4>유입은 꾸준, 정착은 측정 대상</h4>'
         '<ul><li>Steam 월평균 30만 명 안팎 · 시즌 이벤트 때 급증</li><li>이 수치는 잔존율이 아니다 → D7로 검증</li></ul></div>'
         '<div class="pg-card b"><div class="k">TRACK B</div><h4>BM은 매출의 핵심</h4>'
         '<ul><li>확률·보장 변경은 매출 위험이 크다</li><li>가격·확률은 그대로 두고 정보만 더해 신뢰를 시험</li></ul></div>'
         '<div class="pg-card"><div class="k">공통</div><h4>기존 유저도 보호</h4>'
         '<ul><li>매칭·밸런스·확률 변경 없음</li><li>핵 문제는 별도 운영 과제로 분리</li></ul></div></div>')
    with st.expander("자세히 보기 · 제외한 아이디어 (기존 기능과 중복)"):
        st.markdown("- 무기 숙련도(무기별 레벨·메달)가 이미 있어 **마이건 성장 · 킬 수 칭호 · 사용량 레벨업**은 제외\n"
                    "- 기본 훈련·초심자 훈련소·데스캠·리플레이는 **기존 기능**으로만 다룸\n"
                    "- 이중 가챠는 2026-06(42.1)에 제거된 **과거 문제** → 개선 대상에서 제외")


# ======================================================================
# 02 실제 근거
def s2(ns: dict, ops: pd.DataFrame, steam: pd.DataFrame, pool: dict) -> None:
    head("근거: 리뷰 · 공개 지표 · 공식 BM 구조")
    _review_chart(ops, pool)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        _steam_chart(steam)
    with c2:
        _milestone_chart()
    html('<div class="ow-limits"><b>읽는 법</b>'
         f'<span>리뷰 {len(ops)}건 = 최신 리뷰 {sum(pool["pool"].values()):,}건에서 직접 고른 사례 · 비율 아님</span>'
         '<span>Steam 접속자 = 시장 규모 참고 · 신규 잔존·이탈률 아님</span>'
         f'<span>핵 키워드 리뷰 {pool["cheat_keyword_reviews"]}건은 별도 운영 리스크</span></div>')
    t = st.tabs([f"유저 의견 {len(ops)}건", f"공식 시스템 {len(ns['official'])}건", "기존 기능 vs 제안", "자료 한계"])
    with t[0]:
        _opinions(ops)
    with t[1]:
        table(["날짜 · 트랙", "자료", "확인한 사실", "출처"],
              [[f"{escape(o['date'])}<br>{tr(o['track'])}", f"<b>{escape(o['title'])}</b>", escape(o["fact"]), link(o["url"], o["status"])]
               for o in ns["official"]], badge_html=b_real())
        st.caption("'매체 보도'는 공식 원문을 찾지 못해 언론 보도로 확인한 항목입니다.")
    with t[2]:
        table(["영역", "기존 기능 (실제)", "남은 빈틈", "이번 제안"],
              [[escape(x["area"]), escape(x["existing"]), escape(x["gap"]), f"<b>{escape(x['new'])}</b>"] for x in ns["existing_vs_new"]],
              badge_html=b_interp())
    with t[3]:
        st.markdown(f"- 리뷰 표본: {pool['source']} · 한국어 {pool['pool']['한국어']}건({pool['period']['한국어']}) · "
                    f"영어 필터 {pool['pool']['영어 필터']}건({pool['period']['영어 필터']}) · 추천 비율 {pool['recommend_rate']['한국어']}% / {pool['recommend_rate']['영어 필터']}%\n"
                    f"- 그중 신규 정착·BM 관련 리뷰 {len(ops)}건을 기획자가 직접 읽고 분류 (AI 자동 분류 아님) · 원문 발췌는 원본과 글자 그대로 대조\n"
                    "- Steam 리뷰는 Steam 이용자만, 리뷰를 쓴 사람만 포함 → 전체 이용자 의견 비율이 아니다\n"
                    "- Reddit은 수집 환경에서 접근 차단(403), 국내 커뮤니티는 이번 범위에서 수집하지 않음\n"
                    "- 욕설·혐오 표현이 섞인 리뷰는 해당 부분을 빼고 발췌 · 작성자 이름은 저장하지 않음\n"
                    "- 밀수품 상자 확률은 게임 안 페이지에서만 공개되어 이 보고서에서는 '예시' 값으로만 계산")
        st.caption("Steam Charts(steamcharts.com/app/578080) 월평균 동시접속자 · 확인일 2026-11-20")


def _review_chart(ops: pd.DataFrame, pool: dict) -> None:
    cnt = ops.groupby(["track", "category"]).size().reset_index(name="n").sort_values(["track", "n"], ascending=[True, False])
    labels = [f"{c}" for c in cnt["category"]]
    colors = [C_TREAT if t == "A" else C_CORAL for t in cnt["track"]]
    fig = go.Figure(go.Bar(y=labels, x=cnt["n"], orientation="h", marker_color=colors, text=[f"{n}건" for n in cnt["n"]],
                           textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x}건<extra></extra>"))
    fig.update_yaxes(autorange="reversed", automargin=True, title="")
    fig.update_xaxes(title="리뷰 수 (건)", range=[0, cnt["n"].max() * 1.35], dtick=1, rangemode="tozero")
    a, b = (ops["track"] == "A").sum(), (ops["track"] == "B").sum()
    pos = (ops["sentiment"] == "긍정").sum()
    chart_card(fig, key="pg_rev", kind="real", title=f"리뷰 분류 (직접 분류 {len(ops)}건)",
               unit="건 · 파랑 = TRACK A, 코랄 = TRACK B",
               kpis=[("TRACK A · 신규 정착", f"{a}건"), ("TRACK B · BM", f"{b}건"), ("긍정 의견 (반대 사례)", f"{pos}건")],
               analysis=f"A는 '학습 곡선·실력 격차·봇→실전 전환', B는 '확률 결과·총비용'이 많다",
               decision="A1은 전환 구간, B1은 총비용 정보에 집중",
               basis=f"최신 리뷰 {sum(pool['pool'].values()):,}건 중 관련 리뷰 직접 분류 · 비율 아님",
               height=430, legend=False, cols=("분류", "리뷰 수 (건)"))


def _steam_chart(steam: pd.DataFrame) -> None:
    d = steam.copy()
    d["m"] = pd.to_datetime(d["month"])
    pk = d.loc[d["avg_players"].idxmax()]
    last = d.iloc[-1]
    fig = go.Figure(go.Bar(x=d["m"], y=d["avg_players"], marker_color=[C_TREAT if m == pk["m"] else C_MUTED for m in d["m"]],
                           hovertemplate="%{x|%Y-%m} · %{y:,.0f}명<extra></extra>"))
    fig.update_yaxes(title="월평균 동시접속자 (명)", tickformat=",", rangemode="tozero", range=[0, d["avg_players"].max() * 1.15])
    fig.update_xaxes(title="월", tickformat="%y.%m", dtick="M3")
    chart_card(fig, key="pg_steam", kind="real", title="Steam 월평균 동시접속자 (24개월)",
               unit="명 · 파랑 = 최고치",
               kpis=[(f"최고 {pk['m']:%y.%m}", f"{pk['avg_players']:,.0f}명"), (f"최근 {last['m']:%y.%m}", f"{last['avg_players']:,.0f}명")],
               analysis="시즌·이벤트 달에 급증 후 30만 명 안팎으로 회귀 · 원인은 이 자료로 알 수 없음",
               decision="규모 참고용 · 신규 잔존은 D7로 따로 측정",
               basis="Steam만 포함 (카카오·콘솔 제외) · Steam Charts",
               height=300, legend=False, cols=("월", "월평균 동시접속자 (명)"))


def _milestone_chart() -> None:
    ms = [(15, "Cargo 티켓 1"), (30, "토큰 150"), (55, "폴리머 900"), (85, "토큰 300"), (115, "설계도 1"), (145, "토큰 450"), (180, "연막탄 스킨")]
    x = [m for m, _ in ms]
    y = [m * 250 for m in x]
    fig = go.Figure(go.Scatter(x=x, y=y, mode="lines+markers+text", line=dict(color=C_CORAL, width=3), marker=dict(size=9, color=C_CORAL),
                               text=[t for _, t in ms], textposition="top left", textfont=dict(size=11),
                               hovertemplate="누적 %{x}회 · %{y:,} G-Coin<extra></extra>"))
    fig.update_yaxes(title="누적 비용 (G-Coin)", tickformat=",", rangemode="tozero", range=[0, 52000])
    fig.update_xaxes(title="누적 개봉 수 (회)", range=[0, 195])
    chart_card(fig, key="pg_ms", kind="real", title="블랙마켓 2026 누적 개봉 보상",
               unit="G-Coin · 1회 250 기준",
               kpis=[("1회 가격", "250 G-Coin"), ("마지막 보상까지", "180회 · 45,000")],
               analysis="누적 보상은 고정 · 랜덤 보상 확률은 별도 페이지",
               decision="누적 구조는 이미 있음 → 총비용 '안내'를 검증",
               basis="공식 공지 2026-06-17 · 10회 묶음(2,500)도 같은 단가",
               height=300, legend=False, cols=("누적 개봉 수 (회)", "누적 비용 (G-Coin)"))


def _opinions(ops: pd.DataFrame) -> None:
    c1, c2 = st.columns(2)
    trk = c1.selectbox("트랙", ["TRACK A · 신규 정착", "TRACK B · BM"], key="pg_op_tr")
    t = "A" if "A" in trk else "B"
    q = ops[ops["track"] == t]
    cat = c2.selectbox("분류", ["전체"] + sorted(q["category"].unique().tolist()), key="pg_op_cat")
    if cat != "전체":
        q = q[q["category"] == cat]
    rows = q.head(6)
    html('<div class="ow-grid2">' + "".join(
        f'<div class="ow-quote {"neg" if r.sentiment == "부정" else "pos" if r.sentiment == "긍정" else "neu"}">'
        f'<div class="ow-quote-tag">{escape(r.sentiment)} · {escape(r.category)} · 플레이 {escape(r.hours_on_record)}시간</div>'
        f'<div class="ow-quote-t">{escape(r.summary_ko)}</div><div class="ow-quote-o">“{escape(r.quote_original)}”</div>'
        f'<div class="ow-quote-m">Steam 리뷰 · {escape(r.published_date)} · {escape(r.language)} · {link(r.source_url, "원문 보기")}</div></div>'
        for r in rows.itertuples()) + "</div>")
    with st.expander(f"전체 의견 표 {len(ops)}건"):
        st.dataframe(ops[["opinion_id", "track", "category", "tags", "sentiment", "language", "published_date", "recommended",
                          "hours_on_record", "summary_ko", "quote_original", "source_url"]]
                     .rename(columns={"opinion_id": "의견 번호", "track": "트랙", "category": "주 분류", "tags": "보조 분류", "sentiment": "방향",
                                      "language": "언어", "published_date": "작성일", "recommended": "추천 여부", "hours_on_record": "플레이 시간",
                                      "summary_ko": "요약", "quote_original": "원문 발췌", "source_url": "원문"}),
                     hide_index=True, column_config={"원문": st.column_config.LinkColumn("원문", display_text="열기")})


# ======================================================================
# 03 원인 가설
def _flow(steps: list[tuple]) -> None:
    out = []
    for i, (kind, title, desc, basis, check) in enumerate(steps):
        out.append(f'<div class="ow-step {kind}"><div class="ow-step-n">{i + 1} {KIND[kind]()}</div><div class="ow-step-t">{escape(title)}</div>'
                   f'<div class="ow-step-d">{escape(desc)}</div><div class="ow-step-b">근거 · {escape(basis)}</div>'
                   f'<div class="ow-step-c">검증 · {escape(check)}</div></div>')
        if i < len(steps) - 1:
            out.append('<div class="ow-step-a">→</div>')
    html(f'<div class="ow-flow">{"".join(out)}</div>')


def s3(ns: dict, ops: pd.DataFrame, pool: dict) -> None:
    n = ops.groupby("category").size()
    head("두 트랙은 별개의 가설", "같은 이탈 원인으로 묶지 않는다. 관찰 → 해석 → 가설 순으로 근거가 약해진다.", b_hypo())
    sub("TRACK A · 신규 유저가 성장 경험을 못 얻는 지점")
    _flow([("real", "훈련 완료", "기본 훈련 17챕터 · 훈련소 14일 미션", "공식 패치노트 42.2", "훈련 완료율 · 첫 일반전 진입률"),
           ("interp", "봇 위주 초반 경기", "도전감 없이 이겨 실전 감각을 못 얻음", f"리뷰 '봇→실전 전환' {int(n.get('봇→실전 전환', 0))}건", "경기당 봇 비율 · 첫 10경기 순위"),
           ("interp", "숙련자 로비 전환", "갑자기 수백 레벨 상대와 만나 반복 사망", f"리뷰 '실력 격차' {int(n.get('실력 격차·매칭', 0))}건 · '첫 사망' {int(n.get('초반 교전·첫 사망', 0))}건", "첫 교전 생존율 · 기절 거리"),
           ("hypo", "이유 모를 패배 → 이탈", "무엇을 고칠지 몰라 재접속 의향 감소", "가설 · 로그 검증 필요", "첫 3경기 후 재접속 · D7 (A/B)")])
    sub("TRACK B · 구매 만족도가 떨어지는 지점")
    _flow([("real", "확률형 구매", "밀수품 상자 1,800 G-Coin · 확률은 게임 안 페이지", "공식 상점 공지 2026-11", "상점 방문 → 구매 전환"),
           ("interp", "원하는 결과 미획득", "최고 등급 대신 크로마 반복", f"리뷰 '확률·결과' {int(n.get('확률·결과 불만', 0))}건", "구매 후 문의율"),
           ("interp", "총비용 예측 어려움", "목표 스킨·업그레이드까지 얼마인지 모름", f"리뷰 '총비용' {int(n.get('총비용 부담', 0))}건 + 업그레이드 비용 지적 1건", "구매 과정 이탈률"),
           ("hypo", "신뢰·재구매 하락", "만족도·신뢰가 낮아져 재구매가 줄 수 있음", "가설 · 매출 로그 검증 필요", "30일 재구매율 (A/B)")])
    sub("다른 원인도 함께 확인")
    alts = [("A", "핵·부정 플레이", f"핵 키워드 리뷰 {pool['cheat_keyword_reviews']}건 (최다)", "운영 과제 · 실험 기간 신고율 모니터링"),
            ("A", "봇 비율·매칭 대기", f"'봇→실전 전환' {int(n.get('봇→실전 전환', 0))}건", "봇 비율별 D7 비교"),
            ("A", "서버·최적화", "튕김·패킷 손실 불만 (분류 제외)", "크래시율과 이탈 비교"),
            ("B", "스킨 디자인·콘텐츠 우선순위", f"'콘텐츠 대비 스킨' {int(n.get('콘텐츠 대비 스킨 출시', 0))}건", "상품별 판매·평가"),
            ("B", "계정 보안·신뢰", f"'신뢰·계정 보안' {int(n.get('신뢰·계정 보안', 0))}건", "도용 문의와 결제 중단 관계"),
            ("B", "유료 모드 접근", f"'유료 모드' {int(n.get('유료 모드 접근', 0))}건", "BATTLEGROUNDS Plus 전환과 분리")]
    html('<div class="ow-grid3">' + "".join(
        f'<div class="ow-alt"><div class="ow-alt-t">{tr(t)} {escape(c)}</div><div class="ow-alt-n">{escape(e)}</div>'
        f'<div class="ow-alt-c">확인: {escape(k)}</div></div>' for t, c, e, k in alts) + "</div>")
    note("A/B 테스트는 무작위 배정이라 위 원인들이 두 그룹에 고르게 섞인다 → 기능 효과만 분리된다.")


# ======================================================================
# 04 해결책 데모
def s4(ns: dict) -> None:
    head("6개 안을 비교해 MVP 2개만 시연", "매칭·밸런스·확률은 바꾸지 않는다.", b_mock())
    lab = ns["score_labels"]
    html('<div class="pg-cards">' + "".join(
        f'<div class="pg-card {p["track"].lower()}{" mvp" if p["decision"] == "MVP" else ""}"><div class="k">{tr(p["track"])} {p["key"]} · {escape(p["decision"])}</div>'
        f'<h4>{escape(p["name"])}</h4>'
        f'<div class="row"><span>문제</span><div>{escape(p["problem"])}</div></div>'
        f'<div class="row"><span>기존 기능</span><div>{escape(p["existing"])}</div></div>'
        f'<div class="row"><span>차이</span><div>{escape(p["diff"])}</div></div></div>' for p in ns["proposals"]) + "</div>")
    with st.expander("자세히 보기 · 평가 점수 (1~5, 높을수록 유리) · 데이터·위험"):
        table(["안", *lab.values(), "합계", "필요 데이터", "위험"],
              [[f"<b>{p['key']}</b> {escape(p['name'])}", *[str(p["scores"][k]) for k in lab], f"<b>{sum(p['scores'].values())}</b>",
                escape(p["data"]), escape(p["risk"])] for p in ns["proposals"]], badge_html=b_interp())

    sub("직접 눌러 보기")
    t = st.tabs(["시연 A · 첫 10경기 성장 기록", "시연 B · 첫 실전 피드백 (A1)", "시연 C · 총비용 시뮬레이터 (B1)", "강화 비용 안내 (B2 · 추정)"])
    with t[0]:
        demo_a(ns)
    with t[1]:
        demo_b(ns)
    with t[2]:
        demo_c(ns)
    with t[3]:
        demo_b2(ns)


def demo_a(ns: dict) -> None:
    dm = ns["demo_matches"]
    df = pd.DataFrame(dm["rows"], columns=dm["cols"])
    html(f'<div class="ow-vs"><div><b>기존 기능</b> 경기 결과 화면(순위·킬) · 초심자 훈련소 일일 미션</div>'
         f'<div><b>제안</b> 실전 기록을 1경기와 비교해 성장 지표 + 다음 목표 1개 (보상 없음)</div></div>')
    k = st.select_slider("경기 번호 (예시 계정)", options=list(range(1, 11)), value=5, key="pg_a_match")
    r, r0 = df.iloc[k - 1], df.iloc[0]

    def delta(v, v0, unit, better_up=True):
        if v is None or (isinstance(v, float) and math.isnan(v)) or v0 is None or (isinstance(v0, float) and math.isnan(v0)) or k == 1:
            return ""
        d = v - v0
        return f"<em>{'+' if d > 0 else ''}{d:,.1f}{unit} vs 1경기</em>"
    eng = "참여" if r["engaged"] else "없음"
    dist = "—" if pd.isna(r["engage_dist_m"]) else f"{r['engage_dist_m']:.0f}m"
    html(f'<div class="pg-demo"><h4>{k}경기째 기록 {b_sample()}</h4><div class="pg-metric">'
         f'<div><small>생존 시간</small><b>{r["survive_min"]:.1f}분</b>{delta(r["survive_min"], r0["survive_min"], "분")}</div>'
         f'<div><small>첫 교전</small><b>{eng}</b><small>거리 {dist}</small></div>'
         f'<div><small>팀원과 평균 거리</small><b>{r["team_dist_m"]:.0f}m</b>{delta(r["team_dist_m"], r0["team_dist_m"], "m")}</div>'
         f'<div><small>부활</small><b>{int(r["revives"])}회</b></div><div><small>순위</small><b>{int(r["place"])}위</b></div></div>'
         f'<div class="act">다음 목표 · {escape(r["goal"])}</div>'
         f'<div class="src">{escape(dm["note"])} · 지표는 기존 텔레메트리(위치·기절·부활)로 계산 가능</div></div>')
    shown = df[df["match"] <= k]
    fig = go.Figure(go.Scatter(x=shown["match"], y=shown["survive_min"], mode="lines+markers+text", line=dict(color=C_TREAT, width=3),
                               text=[f"{v:.1f}" for v in shown["survive_min"]], textposition="top center"))
    fig.update_xaxes(title="경기 번호", range=[0.5, 10.5], dtick=1)
    fig.update_yaxes(title="생존 시간 (분)", rangemode="tozero", range=[0, df["survive_min"].max() * 1.25])
    chart_card(fig, key="pg_demo_a", kind="sample", title="생존 시간 추이 (예시 계정)", unit="분",
               kpis=[], analysis=f"{k}경기까지 생존 {r0['survive_min']:.1f} → {r['survive_min']:.1f}분",
               decision="첫 10경기는 기획 구간 · 최적 경기 수는 데이터로 결정",
               basis="예시 데이터 · 실제 계정 기록 아님", height=260, legend=False, cols=("경기 번호", "생존 시간 (분)"))


def demo_b(ns: dict) -> None:
    fb = {f["label"]: f for f in ns["demo_feedback"]}
    left, right = st.columns([1, 1], gap="medium")
    with left:
        html('<div class="ow-colh real">현재 · 데스캠·리플레이 (장면 재생)</div>')
        slot("처치당한 직후 데스캠 화면", "직접 캡처 후 assets/pubg/ 에 추가 예정")
    with right:
        html('<div class="ow-colh mock">제안 · 경기 후 고칠 점 1개</div>')
        lab = st.radio("상황 선택", list(fb), horizontal=True, key="pg_b_sit")
        f = fb[lab]
        html(f'<div class="pg-demo"><h4>첫 실전 피드백 {b_mock()}</h4>'
             f'<div class="src">상황 (예시) · {escape(f["scene"])}</div>'
             f'<div><b>원인</b> {escape(f["problem"])}</div>'
             f'<div class="act">{escape(f["action"])}</div>'
             f'<div class="src">판정 데이터 · {escape(f["data"])}<br>적용 단계 · <b>{escape(f["mvp"])}</b></div></div>')
        st.toggle("피드백 끄기", key="pg_b_off", help="설정에서 언제든 끄고 켤 수 있다 (기획 시안)")
        if st.session_state.get("pg_b_off"):
            st.info("피드백을 껐습니다. 결과 화면은 기존과 같습니다. (기획 시안)")
    note("MVP는 기존 로그로 판정되는 '차량·팀플레이'부터. 엄폐는 신규 로그, 자기장은 필드 확인 후.")


def demo_c(ns: dict) -> None:
    bm = ns["bm_sim"]
    html('<div class="ow-vs"><div><b>기존 기능</b> 확률 보기 페이지 · 누적 개봉 보상 · 스크랩 교환이 각각 다른 화면</div>'
         '<div><b>제안</b> 목표 스킨 기준으로 기대 비용·50%/90% 비용·교환 시점을 한 화면에 (확률·가격은 그대로)</div></div>')
    c1, c2, c3 = st.columns(3)
    price = c1.number_input("1회 가격 (G-Coin)", 100, 10000, int(bm["price"]), step=100, key="pg_c_price")
    prob = c2.slider("목표 스킨 확률 (%)", 0.1, 10.0, float(bm["prob"]), 0.1, key="pg_c_prob")
    n = c3.slider("구매 횟수", 1, 400, 100, key="pg_c_n")
    c1, c2, c3 = st.columns(3)
    per = c1.number_input("1회당 스크랩", 0, 100, int(bm["scrap_per_open"]), key="pg_c_spo")
    ex = c2.number_input("교환 필요 스크랩", 0, 20000, int(bm["exchange_scrap"]), step=100, key="pg_c_ex")
    own = c3.number_input("보유 스크랩", 0, 20000, 0, step=100, key="pg_c_own")
    s = S.crate_summary(price, prob, per, ex, own, n)
    cap = s["cap"]
    cap_v = "없음" if cap is None else f"{s['cap_cost']:,.0f}"
    cap_n = "" if cap is None else f"{cap}회"
    html(f'<div class="pg-demo b"><h4>목표 스킨까지 예상 비용 {b_sim()}</h4><div class="pg-metric">'
         f'<div><small>{n}회 안에 얻을 확률</small><b class="big">{s["within_n"] * 100:.1f}%</b></div>'
         f'<div><small>기대 비용 (교환 포함)</small><b>{s["exp_cost"]:,.0f}</b><small>G-Coin · {s["exp_opens"]:.0f}회</small></div>'
         f'<div><small>50% 도달</small><b>{(s["c50"] or 0):,.0f}</b><small>{s["o50"]}회</small></div>'
         f'<div><small>90% 도달</small><b>{(s["c90"] or 0):,.0f}</b><small>{s["o90"]}회</small></div>'
         f'<div><small>교환 확정 (천장)</small><b>{cap_v}</b><small>{cap_n}</small></div></div>'
         f'<div class="src">가격 1,800: {escape(bm["notes"]["price"])} · 확률: {escape(bm["notes"]["prob"])} · 스크랩 10/회: {escape(bm["notes"]["scrap_per_open"])} · '
         f'교환가: {escape(bm["notes"]["exchange_scrap"])}</div></div>')
    mx = max(n, (cap or 0), s["o90"] or 0) + 20
    curve = S.crate_curve(prob, cap, mx)
    fig = go.Figure()
    fig.add_scatter(x=[c[0] for c in curve], y=[c[1] for c in curve], name="교환 없이", line=dict(color=C_CTRL, width=2, dash="dot"))
    fig.add_scatter(x=[c[0] for c in curve], y=[c[2] for c in curve], name="스크랩 교환 포함", line=dict(color=C_CORAL, width=3))
    fig.add_vline(x=n, line_dash="dash", line_color="#1E293B")
    fig.add_annotation(x=n, y=8, text=f"{n}회", showarrow=False, xanchor="left", xshift=4)
    fig.update_xaxes(title="구매 횟수 (회)", range=[0, mx])
    fig.update_yaxes(title="1번 이상 얻을 확률 (%)", range=[0, 105], ticksuffix="%")
    chart_card(fig, key="pg_demo_c", kind="sim", title="구매 횟수별 획득 확률", unit="% · 독립 시행 · 코랄 = 교환 포함",
               kpis=[], analysis=f"교환 없이 기대 {s['exp_cost_nocap']:,.0f} → 교환 포함 {s['exp_cost']:,.0f} G-Coin",
               decision="구매 전 이 정보를 보여도 전환율이 유지되는지 검증",
               basis="P(n회 내) = 1 − (1 − p)^n · 천장 = 교환 스크랩 ÷ 1회당 스크랩", height=320,
               cols=("구매 횟수 (회)", "획득 확률 (%)"), series="계산")
    with st.expander("자세히 보기 · 계산식과 가정"):
        st.markdown("- n회 안에 1번 이상 얻을 확률 = 1 − (1 − p)^n (매 구매가 독립이라고 가정)\n"
                    "- 천장 K = ⌈(교환 필요 스크랩 − 보유 스크랩) ÷ 1회당 스크랩⌉ → K회째에는 교환으로 확보\n"
                    "- 기대 구매 횟수 = (1 − (1 − p)^K) ÷ p (교환 없으면 1 ÷ p) · 기대 비용 = 기대 횟수 × 1회 가격\n"
                    "- 10회 묶음 첫 구매 할인, 중복 보상의 분해·토큰 환급은 반영하지 않음 → 실제 비용은 이보다 낮을 수 있다\n"
                    "- 공식 확률·상품별 교환가를 확인하기 전까지 결과는 '예시'로만 해석")


def demo_b2(ns: dict) -> None:
    html('<div class="ow-defer"><b>검토 대기</b> 업그레이드 화면이 단계별 필요 재료를 이미 보여 주는지 확인 후 결정 · '
         '레벨별 필요량은 공식 미공개라 분해 환급표로 추정</div>')
    c1, c2 = st.columns(2)
    cur = c1.slider("현재 레벨", 1, 10, 3, key="pg_u_cur")
    tgt = c2.slider("목표 레벨", 1, 10, 10, key="pg_u_tgt")
    c1, c2 = st.columns(2)
    pol = c1.number_input("보유 폴리머", 0, 100000, 5000, step=500, key="pg_u_pol")
    sch = c2.number_input("보유 설계도", 0, 200, 10, key="pg_u_sch")
    u = S.upgrade_need(ns["salvage"], cur, tgt, pol, sch)
    tiles([("필요 폴리머 (추정)", f"{u['polymer']:,}", f"부족 <b>{u['short_polymer']:,}</b>"),
           ("필요 설계도 (추정)", f"{u['schematic']:,}", f"부족 <b>{u['short_schematic']:,}</b>"),
           ("획득 경로 (공식)", "분해 · 패키지", "성장형 스킨 분해 · 이벤트 패키지 · 누적 개봉 보상")])
    if u["steps"]:
        with st.expander("단계별 추정 필요량"):
            table(["레벨", "폴리머", "설계도"], [[f"{lv - 1}→{lv}", f"{p:,}", str(s)] for lv, p, s in u["steps"]], badge_html=b_sim())
    st.caption("추정 근거: 공식 분해 환급표(2025-03, 34.2)를 '그 레벨까지 누적 투입량'으로 가정. 실제 필요량과 다를 수 있음.")


# ======================================================================
# 05 KPI·A/B 테스트
def s5(ns: dict, plan: dict) -> None:
    ex = ns["experiment"]
    A, B = ex["A"], ex["B"]
    pa, pb, sc = plan["A"], plan["B"], plan["sched"]
    head("실험 2개 · 트랙마다 주요 지표 1개", "기준값은 모두 가정 · 내부 데이터로 교체 필요", b_mock())
    tiles([("A1 · 신규 D7 (주요)", f"+{pa['mde']:.1f}%p", f"기준 {A['base_d7']:.0f}% 가정 · 우월성"),
           ("A1 · 표본", f"{pa['n']:,}명 × 2", f"주당 신규 {A['weekly']:,}명 가정 → {pa['assign_weeks']}주"),
           ("B1 · 구매 전환율 (주요)", f"−{B['ni_margin']:.1f}%p 이내", f"기준 {B['base_conv']:.0f}% 가정 · 비열등성"),
           ("B1 · 표본", f"{pb['n']:,}명 × 2", f"주당 방문 {B['weekly']:,}명 가정 → {pb['assign_weeks']}주")])
    table(["실험", "대조군 → 실험군", "배정 · 대상", "주요 지표 · 기준", "MDE · 표본", "기간", "성공 · 중단"],
          [[f"{tr('A')}<b>A1 첫 실전 피드백</b>", f"{escape(A['control'])} → {escape(A['treatment'])}", f"{escape(A['unit'])}<br>{escape(A['segment'])}",
            f"신규 D7 (ITT)<br><small>기준 {A['base_d7']:.0f}% 가정</small>",
            f"+{pa['mde']:.1f}%p (열람 {A['participation']}% × {A['uplift_viewer']:.0f}%p)<br>{pa['n']:,}명 × 2",
            f"배정 {sc['a_assign'][0]}~{sc['a_assign'][1]}주 · D7 {sc['a_d7']}주 · D30 {sc['a_d30']}주",
            "성공: 95% CI 하한 > 0, 점추정 ≥ MDE<br>중단: 대기시간·신고율 악화"],
           [f"{tr('B')}<b>B1 구매 전 총비용 안내</b>", f"{escape(B['control'])} → {escape(B['treatment'])}", f"{escape(B['unit'])}<br>{escape(B['segment'])}",
            f"30일 구매 전환율<br><small>기준 {B['base_conv']:.0f}% 가정</small>",
            f"비열등 한계 −{B['ni_margin']:.1f}%p<br>{pb['n']:,}명 × 2",
            f"배정 {sc['b_assign'][0]}주 · 전환 {sc['b_conv']}주 · 재구매 {sc['b_repurchase']}주",
            "성공: 비열등 + 재구매·문의 개선<br>중단: 총매출 −5%"]], badge_html=b_mock())
    with st.expander("자세히 보기 · 보조 KPI · 가드레일 · 계산식"):
        table(["트랙", "보조 KPI", "가드레일"],
              [[tr("A"), "D1·D30 · 첫 3경기 후 재접속 · 첫 10경기 완료율 · 피드백 열람률 · 스쿼드 재참여율", escape(" · ".join(A["guardrails"]))],
               [tr("B"), "ARPPU · 총매출 · 30일 재구매율 · 구매 과정 이탈률 · 문의·불만", escape(" · ".join(B["guardrails"]))]])
        st.markdown(f"- A1 MDE(배정 기준) = 피드백 열람률 {A['participation']}% × 열람자 개선 {A['uplift_viewer']}%p = +{pa['mde']:.1f}%p\n"
                    f"- 우월성 표본: 두 비율 차이 양측 검정 α {ex['alpha']} · 검정력 {ex['power']:.0%}\n"
                    f"- 비열등성 표본: 한쪽 검정 α {ex['alpha']} · 검정력 {ex['power']:.0%} · n = (z₁₋α + z₁₋β)² × 2p(1−p) ÷ 한계²\n"
                    f"- 배정 주수 = ⌈두 그룹 표본 합 ÷ 주당 대상⌉ · D7 판정 = 마지막 배정일 + 7일 · 전환 판정 = 배정 + {B['window_days']}일")

    sub("가정 시뮬레이션", b_sim())
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        d30_base, d30_up = A["base_d7"] / 2, pa["mde"] / 2
        cats = ["신규 D7", "신규 D30", "첫 10경기 완료율"]
        before = [A["base_d7"], d30_base, A["base_m10"]]
        after = [A["base_d7"] + pa["mde"], d30_base + d30_up, A["base_m10"] + pa["m10_mde"]]
        fig = hpair(cats, before, after, xtitle="비율 (%)", names=("대조군 (가정)", "실험군 (가정)"), xmax=max(after) * 1.3)
        chart_card(fig, key="pg_sim_a", kind="sim", title="A1 · 대조군 vs 실험군", unit="% · 회색 = 대조군, 파랑 = 실험군",
                   kpis=[("신규 D7", f"{before[0]:.0f}% → <b>{after[0]:.0f}%</b> <em>{pp(pa['mde'])}</em>")],
                   analysis="D30은 D7 효과의 절반 유지 가정 · 10경기 완료율은 열람 50% × 8%p",
                   decision="D7이 MDE 이상 유의할 때만 확대", basis="같은 신규 코호트 · 배정 기준(ITT)",
                   height=330, cols=("지표", "비율 (%)"), series="그룹")
    with c2:
        sv = S.scenarios(ns["scenarios"])
        fig = go.Figure()
        for s in sv:
            col = C_CTRL if s["key"] == "A" else (C_CORAL if s["key"] == "C" else C_TREAT)
            mid = (s["low"]["total"] + s["high"]["total"]) / 2 / 1e6
            fig.add_bar(x=[f"{s['key']} {s['name']}"], y=[mid], marker_color=col, showlegend=False,
                        error_y=dict(type="data", symmetric=False, array=[s["high"]["total"] / 1e6 - mid], arrayminus=[mid - s["low"]["total"] / 1e6],
                                     color="#1E293B", thickness=1.5, width=8),
                        hovertemplate=f"{s['name']}: {s['low']['total'] / 1e6:,.1f}~{s['high']['total'] / 1e6:,.1f}백만 G-Coin<extra></extra>")
        fig.update_yaxes(title="60일 매출 (백만 G-Coin)", rangemode="tozero")
        fig.update_xaxes(title="")
        b_, c_ = sv[1], sv[2]
        chart_card(fig, key="pg_sim_b", kind="sim", title="BM 시나리오 · 60일 매출 범위", unit="방문 10만 명당 · 막대 = 비관~낙관",
                   kpis=[("B 안내 강화", f"{b_['low_pct']:+.0f}%~{b_['high_pct']:+.0f}%"), ("C 누적 보장", f"{c_['low_pct']:+.0f}%~{c_['high_pct']:+.0f}%")],
                   analysis="C는 하방이 가장 크다 (고액 결제 감소 가정)",
                   decision="B부터 실험, C는 B 결과 후 재검토", basis="전환율·ARPPU·재구매 모두 가정 · 현행 대비",
                   height=330, legend=False, cols=("시나리오", "60일 매출 (백만 G-Coin)"))
    with st.expander("자세히 보기 · BM 시나리오 가정값"):
        table(["시나리오", "전환율 (%)", "ARPPU (G-Coin)", "재구매율 (%)", "60일 매출 (백만)", "현행 대비"],
              [[f"<b>{s['key']}</b> {escape(s['name'])}", f"{s['conv'][0]}~{s['conv'][1]}", f"{s['arppu'][0]:,}~{s['arppu'][1]:,}",
                f"{s['repurchase'][0]}~{s['repurchase'][1]}", f"{s['low']['total'] / 1e6:,.1f}~{s['high']['total'] / 1e6:,.1f}",
                f"{s['low_pct']:+.1f}%~{s['high_pct']:+.1f}%"] for s in sv], badge_html=b_sim())
        st.caption(f"60일 매출 = 방문자 × 전환율 × ARPPU + 구매자 × 재구매율 × ARPPU × {ns['scenarios']['repurchase_arppu_ratio']}")

    sub("성공·중단 기준", b_mock())
    table(["결과", "A1 첫 실전 피드백", "B1 총비용 안내"],
          [["<b>확대</b>", "D7 95% CI 하한 > 0 · 점추정 ≥ MDE · 대기시간·신고율 악화 없음", "전환율 비열등 + 재구매·문의 중 1개 이상 개선"],
           ["<b>수정 후 재실험</b>", "유의하지 않지만 열람률 50% 미만 → 노출 위치 수정", "비열등이지만 개선 없음 → 문구·위치 수정"],
           ["<b>중단</b>", "재실험에도 효과 없음 · 피드백 끄기 10% 초과", "전환율 비열등 실패 또는 총매출 −5%"]])
    with st.expander(f"자세히 보기 · 주차별 일정 (준비 2주 + 운영 {sc['decision']}주)"):
        html(gantt(sc))


# ======================================================================
# 06 실행·사업 제안
def s6(ns: dict, plan: dict) -> None:
    sc = plan["sched"]
    head(f"MVP 2개 · {sc['decision'] + 2}주 파일럿 (준비 2주 + 운영 {sc['decision']}주)", "", b_mock())
    sub("우선순위와 이유")
    order = sorted(ns["proposals"], key=lambda p: (p["decision"] != "MVP", -sum(p["scores"].values())))
    table(["순서", "안", "판단", "점수 합", "이유"],
          [[str(i + 1), f"{tr(p['track'])} <b>{p['key']}</b> {escape(p['name'])}", f"<b>{escape(p['decision'])}</b>",
            str(sum(p["scores"].values())), escape(ns["mvp_reason"].get(p["key"], p["risk"]))] for i, p in enumerate(order)], badge_html=b_interp())

    sub("비용·인력 가정", b_sim())
    c = ns["experiment"]["cost"]
    tiles([("A1 개발·운영", f"{c['A1_effort']}인월", f"≈ {plan['a1_cost'] / 1e4:,.0f}만 원 · 클라이언트 UI·데이터·QA"),
           ("B1 개발·운영", f"{c['B1_effort']}인월", f"≈ {plan['b1_cost'] / 1e4:,.0f}만 원 · 상점 UI·법무 검토"),
           ("A1 추가 D7 1명당", f"{plan['a1_cost_per_added']:,.0f}원", f"분기 신규 {ns['experiment']['quarter_new']:,}명 × MDE")])
    sub("실행 일정", b_mock())
    weeks = [("준비 (−2~0주)", "텔레메트리 판정 규칙 · 피드백 문구 검수 · 상점 패널 · 법무 · 실험 배정 점검"),
             (f"{sc['a_assign'][0]}~{sc['a_assign'][1]}주", "A1 배정 (신규 50:50) · B1 배정 (상점 방문 50:50)"),
             (f"{sc['a_d7']}~{sc['a_d30']}주", f"{sc['a_d7']}주 A1 D7 판정 · {sc['b_conv']}주 B1 전환 판정"),
             (f"{sc['a_d30'] + 1}~{sc['decision']}주", f"{sc['b_repurchase']}주 B1 재구매 확인 · {sc['decision']}주 확대·수정·중단 결정")]
    html('<div class="ow-timeline">' + "".join(
        f'<div class="ow-tl"><div class="ow-tl-d">{escape(p)}</div><div class="ow-tl-b">{escape(w)}</div></div>' for p, w in weeks) + "</div>")
    sub("위험 관리", b_interp())
    table(["위험", "대응"], [[escape(r["risk"]), escape(r["response"])] for r in ns["risks"]])

    pa = plan["A"]
    html(f'<div class="ow-conclusion"><div class="ow-conclusion-k">최종 사업PM 제안 {b_mock()}</div>'
         f'<b>매칭·확률은 그대로, 정보만 더해 두 가지를 동시에 검증한다.</b><br>'
         f'A1은 신규 D7 +{pa["mde"]:.1f}%p, B1은 구매 전환율을 지키면서 재구매·문의 개선을 확인한다. '
         'A2·B2는 결과를 본 뒤, A3·누적 보장 강화는 위험이 커 보류한다.</div>')
    with st.expander("자세히 보기 · PPT 10장 구성"):
        html("<ol>" + "".join(f"<li>{escape(x)}</li>" for x in ns["ppt"]) + "</ol>")
    note("한계: 리뷰는 표본 사례일 뿐이고, D7·전환율 기준값은 가정이다. 인과는 A/B 테스트로만 판단한다.")
