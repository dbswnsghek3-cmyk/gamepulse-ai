"""FC 온라인 — 축구 게임인가, 주식 게임인가? (사업PM 포트폴리오 · 01~06 탭)

- A 구단 가치 하락과 성장 박탈감 40% · B 강화 실패와 이탈 25% · C 키보드 vs 패드 경쟁 공정성 35% (기획 비중)
- 사실·가정·시안 데이터: data/fconline/fc.json · 계산: gamepulse/sim/fc_sim.py (정적 페이지 JS 와 같은 식)
- 게임 화면: assets/fconline/*.jpg (작성자 캡처 · 창 테두리·작업표시줄 제거 · 상대 닉네임 가림). 원본은 _originals/ (git 제외)
- 유저 의견: 인벤 게시글 제목(실제 · 링크) + 작성자 캡처 화면 관측값. 확인하지 못한 댓글·수치는 만들지 않는다.
- 데모 3개(A1·B1·C5)는 왼쪽 입력 칸 첫머리에 fc-anchor 표식을 둔다 → 정적 페이지에서 JS 조작판으로 교체.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from gamepulse.data.overwatch_images import web_jpeg_b64
from gamepulse.sim import fc_sim as F
from gamepulse.ui.components import html
from gamepulse.views.overwatch import (C_CTRL, C_TREAT, b_hypo, b_interp, b_mock, b_real, b_sample, b_sim, badge_legend,
                                       chart_card, head, link, note, sub, table)

ROOT = Path(__file__).resolve().parents[2]
DATA, ASSETS = ROOT / "data" / "fconline", ROOT / "assets" / "fconline"
SECTIONS = [("01", "문제·결론"), ("02", "유저 근거"), ("03", "A 구단 가치"), ("04", "B 강화 리스크"),
            ("05", "C 키보드 vs 패드"), ("06", "KPI·실행")]
TAB_LABELS = [f"{n} {t}" for n, t in SECTIONS]
TAB_KEY = "fc_tab"
C_GREEN, C_PURPLE, C_KB, C_PAD = "#15803D", "#6D28D9", "#0F766E", "#7C3AED"


@st.cache_data(show_spinner=False)
def load() -> dict:
    return json.loads((DATA / "fc.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _img(name: str, mtime: float, max_w: int = 1400) -> str:
    return web_jpeg_b64(str(ASSETS / name), max_w=max_w)


def shot(name: str, title: str, caption: str = "", cls: str = "") -> str:
    p = ASSETS / name
    if not p.is_file():
        return ""
    cap = f"<figcaption><b>{escape(caption)}</b><span>실제 게임 화면 · 작성자 직접 캡처 (2026-11-23) · © NEXON · EA SPORTS</span></figcaption>" if caption else ""
    return (f'<figure class="fc-shot {cls}"><div class="bar"><span>실제 게임 화면</span>{escape(title)}</div>'
            f'<img src="data:image/jpeg;base64,{_img(name, p.stat().st_mtime)}" alt="실제 게임 화면: {escape(title)}" loading="lazy">{cap}</figure>')


def bp(x: float) -> str:
    """BP 금액 → '1억 300만 BP' (화폐 단위 조정 이후 BP)."""
    x = round(x)
    sign = "−" if x < 0 else ""
    x = abs(x)
    jo, eok, man = x // 10**12, (x % 10**12) // 10**8, (x % 10**8) // 10**4
    parts = [f"{jo:,}조" if jo else "", f"{eok:,}억" if eok else "", f"{man:,}만" if man else ""]
    s = " ".join(p for p in parts if p) or f"{x:,}"
    return f"{sign}{s} BP"


def tr(t: str) -> str:
    return f'<span class="fc-tr {t.lower()}">{t}</span>'


def _tab_from_query() -> str:
    q = str(st.query_params.get("tab", ""))
    return next((lab for lab in TAB_LABELS if lab.startswith(q.zfill(2)[:2])), TAB_LABELS[0]) if q else TAB_LABELS[0]


def _sync_tab_param() -> None:
    st.query_params["page"] = "fconline"
    st.query_params["tab"] = str(st.session_state.get(TAB_KEY, TAB_LABELS[0]))[:2]


def tab_nav() -> int:
    if st.session_state.get(TAB_KEY) not in TAB_LABELS:
        st.session_state[TAB_KEY] = _tab_from_query()
    sel = st.radio("섹션 선택", TAB_LABELS, key=TAB_KEY, horizontal=True, label_visibility="collapsed", on_change=_sync_tab_param)
    return TAB_LABELS.index(sel)


def anchor(k: str) -> None:
    """정적 페이지에서 이 입력 칸이 들어 있는 행 전체를 JS 조작판으로 바꾼다."""
    html(f'<div class="fc-anchor" data-k="{k}"></div>')


# ----------------------------------------------------------------------
def _cover(d: dict) -> None:
    cv = d["cover"]
    p = ASSETS / "market_trend.jpg"
    img = (f'<figure class="fc-hero-img"><img src="data:image/jpeg;base64,{_img("market_trend.jpg", p.stat().st_mtime)}" '
           'alt="실제 게임 화면: 이적시장 인기 선수 · 시세 급상승 · 최고 거래가"><figcaption>실제 게임 화면 · 이적시장 (시세 급상승 · 최고 거래가) · 작성자 캡처</figcaption></figure>') if p.is_file() else ""
    html(f'<div class="fc-hero"><div class="fc-hero-t"><div class="k">{escape(cv["kicker"])}</div>'
         f'<div class="q" role="heading" aria-level="1">{escape(cv["title"])}</div><div class="s">{escape(cv["subtitle"])}</div>'
         '<div class="tick"><span>시세 급상승 <b>▲40.00%</b></span><span>최고 거래가 <b>1,800억 BP</b></span><span>8강 카드 한 달 <b class="dn">▼70%</b></span></div>'
         f'</div>{img}</div>')
    html('<div class="fc-tracks">' + "".join(
        f'<div class="{t["key"].lower()}"><div class="h">{tr(t["key"])}<b>{t["weight"]}%</b><span>{escape(t["name"])}</span></div>'
        f'<strong>{escape(t["line"])}</strong><small>{escape(t["sol"])}</small></div>' for t in d["tracks"])
        + f'</div><div class="fc-cav">{escape(d["weight_note"])} · 시세 수치는 2026-08-20 화폐 단위 조정 이후 BP</div>')


def render() -> None:
    d = load()
    html('<div class="gp-ow-page"></div>')
    _cover(d)
    i = tab_nav()
    badge_legend()
    html(f'<div class="ow-pane-mark" data-tab="{SECTIONS[i][0]}"></div>')
    [s1, s2, s3, s4, s5, s6][i](d)
    st.caption(f"{d['disclaimer']} · 자료 확인일 {d['checked_at']}")


# ======================================================================
# 01 문제·결론
def s1(d: dict) -> None:
    head("결론: 자산 가격과 경기의 재미를 분리해 보여 주고, 입력 장치 갈등은 선택형 매칭으로 실험한다", "1차 C 매칭 실험 → 2차 A 구단 가치 → 3차 B 강화", b_mock())
    html('<div class="fc-why">'
         f'<div><span>A · 주식처럼 움직이는 구단</span><b>8강 카드 2장 · 한 달 그래프 안에서 <em>6,260만 → 약 1,900만 BP</em> (약 3분의 1)</b><small>{b_real()} 작성자 캡처 · 루이스 디아스 · 오야르사발</small></div>'
         f'<div><span>B · 한 번에 걸린 구단</span><b>7→8강 성공 확률 <em>7%</em> · 8강 판매가는 7강의 약 <em>16배</em></b><small>{b_real()} 공식 확률 · 캡처 시세</small></div>'
         f'<div><span>C · 같은 경기, 다른 조작</span><b>인벤 최근 글: <em>"패드보다 키보드가 불리하니까"</em> · <em>"분리매칭주장하는 키보드유저들은"</em></b><small>{b_real()} 게시글 제목 · 양쪽 의견</small></div></div>')
    html('<div class="fc-pair">' + shot("squad.jpg", "스쿼드 관리 · 클럽 선수 가치 4억 8,620만", "구단 = 선수 가치의 합으로 보인다")
         + shot("manager_mode.jpg", "공식경기 감독모드", "직접 조작 대신 전술로 경기 · 상대 닉네임 가림") + "</div>")
    with st.expander("자세히 보기 · 판단 근거 · 하지 않는 것"):
        html("<ul class='pg-ul'>"
             f"<li><b>왜 C가 먼저인가</b> {b_interp()} 키보드·패드 논쟁이 같은 달 게시판에 양쪽 입장으로 반복된다. 매칭 로그로 바로 검증할 수 있고 재화를 건드리지 않는다.</li>"
             f"<li><b>A의 핵심</b> {b_interp()} 시세는 시장이 정한다. 게임사가 시세를 보장할 수는 없지만, '가치가 떨어져도 경기력은 그대로'라는 사실과 재건 경로는 보여 줄 수 있다.</li>"
             f"<li><b>B의 핵심</b> {b_hypo()} 강화의 재미는 유지한다. 실패 직후 '재도전'만 보이는 순간을 바꿔 극단적 손실 후 이탈을 줄인다 (검증 전 가설).</li>"
             "<li><b>하지 않는 것</b> 무제한 재화 지급 · 시세 보장 · 강화 확률 변경 · 기존 BP 강화 등급 보호·부스트·확정 성공권과 겹치는 신규 재화</li>"
             "<li><b>화폐 단위</b> 2026-08-20 정기 점검으로 1억 BP → 1 BP 조정 · 이 페이지의 시세는 모두 조정 이후 값</li></ul>")


# ======================================================================
# 02 유저 근거
def s2(d: dict) -> None:
    head("근거: 키보드·패드 논쟁은 양쪽 목소리가 뚜렷하고, 구단 가치·강화는 화면 관측이 먼저다", "실제 확인한 것만 · 비율이 아닌 사례 수 · 찬반 모두 포함", b_real())
    sub("유저 발언 → 핵심 불만 → 이탈 위험 → 사업적 시사점")
    html('<div class="fc-voice">' + "".join(
        f'<div><span class="v">{escape(v)}</span><i>→</i><b>{escape(c)}</b><i>→</i><span class="r">{escape(r)}</span><i>→</i><strong>{escape(s)}</strong></div>'
        for v, c, r, s in d["voices"]) + "</div>")
    html(f'<div class="fc-cav">{b_real()} 발언 = 인벤 게시글 제목·작성자 캡처 화면 · {b_hypo()} 이탈 위험은 검증 전 가설 · {b_interp()} 시사점은 분석자 해석</div>')
    sub("조사 범주 8개 · 확인한 근거")
    table(["범주", "확인", "근거", "상태"], [[f"<b>{escape(a)}</b>", escape(b), escape(c), f"<em>{escape(e)}</em>" if e else "—"] for a, b, c, e in d["categories"]],
          badge_html=b_real())
    sub("인벤 FC 온라인 게시판 · 실제 게시글 제목")
    side_cls = {"키보드": "kb", "패드": "pad", "질문": "q", "중립": "q", "강화": "en"}
    html('<div class="fc-posts">' + "".join(
        f'<a class="{side_cls[o["side"]]}" href="{escape(o["url"], quote=True)}" target="_blank" rel="noopener"><span>{escape(o["side"])} · {escape(o["cat"])}</span>'
        f'<b>“{escape(o["title"])}”</b><small>인벤 자유게시판 · {escape(o["date"])} · 원문 보기</small></a>' for o in d["opinions"]) + "</div>")
    note(d["opinion_note"] + " · 게시글 몇 개가 전체 이용자를 대표하지 않는다")
    with st.expander("자세히 보기 · 공식 자료 · 화면 관측 · 자료 한계"):
        table(["날짜", "자료", "구분", "확인한 사실", "출처"],
              [[escape(o["date"]), f"<b>{escape(o['title'])}</b>", escape(o["kind"]), escape(o["fact"]), link(o["url"], "열기")] for o in d["official"]],
              badge_html=b_real())
        table(["관측", "값", "내용"], [[escape(a), f"<b>{escape(b)}</b>", escape(c)] for a, b, c in d["market_obs"]], badge_html=b_real())
        html(shot("market_trend.jpg", "이적시장 · 인기 선수", "시세 급상승 · 최다 조회 · 최고 거래가"))
        st.markdown("- **YouTube 댓글 캡처**: 요청서에 적힌 캡처 4장은 이번에 전달되지 않아 사용하지 않았다 → 받으면 별도 표본으로 추가\n"
                    "- 인벤 게시글은 목록의 **제목만** 확인했다 (본문은 수집 환경에서 열리지 않음) · 제목으로 입장을 나눈 것은 분석자 판단\n"
                    "- '구단 가치' 검색 결과는 가치 하락이 아닌 일반 잡담이었고, '강화 실패' 검색은 0건 (2026-11-23) → A·B 유저 발언은 표본 부족\n"
                    "- 상위 랭커의 패드 사용 비율 같은 수치는 검증 가능한 자료가 없어 쓰지 않는다\n"
                    "- 작성자 이름은 저장하지 않는다")


# ======================================================================
# 03 A 구단 가치
def s3(d: dict) -> None:
    bg = d["baggio"]
    head("A · 내가 키운 구단은 왜 시간이 지날수록 가치가 떨어지는가?", "목표: 자산 가격이 떨어져도 성장 경험까지 사라지지 않게 한다", b_mock())
    c1, c2 = st.columns([1.25, 1], gap="medium")
    with c1:
        html(shot("market_baggio.jpg", "이적시장 · 로베르토 바조 시세 그래프", "한 카드의 실제 관측값 · 시세를 대표하지 않음"))
    with c2:
        drop = 1 - bg["graph"]["now"] / bg["graph"]["peak"]
        html(f'<div class="fc-big"><span>{b_real()} 화면 관측 · {escape(bg["card"])}</span>'
             f'<b>{bp(bg["graph"]["peak"])}</b><small>{escape(bg["graph"]["peak_date"])} 그래프 최고점</small>'
             f'<b class="dn">{bp(bg["graph"]["now"])}</b><small>{escape(bg["graph"]["now_label"])} · 약 <em>{drop * 100:.0f}%</em> 하락</small></div>'
             f'<div class="fc-scn">{b_sample()} <b>설명용 가상 시나리오</b><div><span>10억</span><i>→</i><span>5억</span><i>→</i><span class="dn">3억 BP</span></div>'
             '<small>실제 시세 데이터가 아님 · 조정 이후 BP 단위로만 표기</small></div>')
    sub("실제 시세 급락 사례 · 작성자 캡처", b_real())
    html('<div class="fc-drops">' + "".join(
        f'<div><span>{escape(x["card"])}</span><b>{bp(x["peak"]).replace(" BP", "")} <i>→</i> <em>{bp(x["now"]).replace(" BP", "")}</em></b>'
        f'<strong>▼{(1 - x["now"] / x["peak"]) * 100:.0f}%</strong><small>그래프 최고 → 최근 · 선수가치 {bp(x["value"])} · {escape(x["when"])}</small></div>'
        for x in d["drops"]) + "</div>")
    imgs = [shot(x["file"], f"이적시장 · {x['card']}", "") for x in d["drops"][:2]]
    if all(imgs):
        html('<div class="fc-pair">' + "".join(imgs) + "</div>")
    note(d["drops_note"])
    sub("A1 · 구단 가치 변동 분석기", b_mock())
    c1, c2 = st.columns([1, 1.2], gap="medium")
    with c1:
        anchor("a1")
        v0 = st.number_input("초기 구단 가치 (억 BP · 가상)", 1.0, 100000.0, 10.0, step=1.0, key="fc_a1_v0")
        my = st.slider("내 구단 가치 하락률 (%)", 0, 90, 50, key="fc_a1_my")
        mk = st.slider("시장 전체 하락률 (%)", 0, 90, 20, key="fc_a1_mk")
    r = F.value_change(v0 * 1e8, my / 100, mk / 100)
    with c2:
        html(f'<div class="fc-demo"><h4>구단 가치 진단 {b_sim()}</h4><div class="fc-m">'
             f'<div><small>현재 구단 가치</small><b>{bp(r["now"])}</b><em class="dn">−{bp(r["loss"]).replace("BP", "")}</em></div>'
             f'<div><small>원래 가치로 돌아가려면</small><b class="up">+{r["recover_pct"]:.0f}%</b><em>상승 필요</em></div>'
             f'<div><small>시장 대비</small><b>{r["vs_market_pct"]:+.0f}%</b><em>{"시장보다 더 하락" if r["vs_market_pct"] < 0 else "시장과 같거나 덜 하락"}</em></div></div>'
             '<div class="fc-act"><b>가치가 떨어져도 선수 능력치·팀컬러는 그대로다</b> → 경기력 목표로 다시 성장 (A2)</div>'
             '<div class="src">자산 가치(시세)와 경기 성능(능력치)은 다른 숫자 · 시세 보장 없음</div></div>')
    cv = F.recovery_curve()
    fig = go.Figure(go.Scatter(x=[a for a, _ in cv], y=[b for _, b in cv], mode="lines+markers", line=dict(color=C_PURPLE, width=3)))
    fig.add_scatter(x=[my], y=[r["recover_pct"]], mode="markers", marker=dict(size=14, color="#DC2626"), name="현재 입력")
    fig.update_xaxes(title="구단 가치 하락률 (%)", ticksuffix="%")
    fig.update_yaxes(title="회복에 필요한 상승률 (%)", ticksuffix="%", rangemode="tozero")
    chart_card(fig, key="fc_rec", kind="sim", title="하락률별 회복에 필요한 상승률", unit="% · 빨간 점 = 현재 입력",
               kpis=[("50% 하락 후", "+100% 필요")], analysis="하락이 클수록 회복에 필요한 상승은 더 가파르게 커진다",
               decision="'다시 오르면 된다'가 아니라 경기력 목표를 따로 제시", basis="필요 상승률 = 하락률 ÷ (1 − 하락률) · 계산식", height=260,
               legend=False, cols=("하락률 (%)", "필요 상승률 (%)"))
    sub("A2 · 구단 재건 로드맵", b_mock())
    table(["단계", "내용", "구분"], [[f"<b>{escape(a)}</b>", escape(b), escape(c)] for a, b, c in d["a2_steps"]])
    html(f'<div class="fc-cav"><b>{escape(d["a2_not"])}</b></div>')


# ======================================================================
# 04 B 강화 리스크
def s4(d: dict) -> None:
    bg, pt = d["baggio"], d["enhance_prob"]
    head("B · 마지막 강화 한 번이 마지막 접속이 되는 이유는?", "목표: 강화의 재미는 유지하면서 극단적 손실 후 이탈 위험을 줄인다 · 이탈 흐름은 검증 전 가설", b_mock())
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        fig = go.Figure(go.Bar(x=[f"{a}→{b}" for a, b, _ in pt], y=[p for *_, p in pt], marker_color=[C_TREAT if p >= 50 else "#93C5FD" if p >= 10 else "#DC2626" for *_, p in pt],
                               text=[f"{p}%" for *_, p in pt], textposition="outside", cliponaxis=False))
        fig.update_yaxes(title="성공 확률 (%)", range=[0, 115], ticksuffix="%")
        fig.update_xaxes(title="강화 단계")
        chart_card(fig, key="fc_prob", kind="real", title="공식 강화 성공 확률 (부스트 게이지 100%)", unit="% · 26.4 기준 공지",
                   kpis=[("7→8강", "7%"), ("12→13강", "1%")], analysis="7강부터 한 자릿수 확률", decision="고위험 구간(7강+) 실패 직후를 B2의 대상으로",
                   basis="FC 온라인 공지 '선수 강화 성공 확률 안내' · 실제 확률 = 표 × 부스트 게이지 비율", height=280, legend=False, cols=("강화 단계", "성공 확률 (%)"))
    with c2:
        lv = bg["levels"]
        fig = go.Figure(go.Bar(x=[f"{a}강" for a, _ in lv], y=[v for _, v in lv], marker_color=[C_PURPLE if a >= 8 else "#C4B5FD" for a, _ in lv],
                               text=[bp(v).replace(" BP", "") for _, v in lv], textposition="outside", cliponaxis=False))
        fig.update_yaxes(title="판매 최저가 (BP · 로그)", type="log")
        fig.update_xaxes(title="강화 단계")
        chart_card(fig, key="fc_lv", kind="real", title="한 카드의 강화 단계별 판매 최저가", unit="BP · 로그 축 · 화면 관측",
                   kpis=[("7강", bp(6840000)), ("8강", bp(110000000))], analysis="한 단계 차이로 가치가 몇 배씩 뛴다",
                   decision="구단 자산이 한 번의 강화에 걸리는 구조 → 실패 직후 경험을 설계", basis=bg["levels_note"], height=280, legend=False,
                   cols=("강화 단계", "판매 최저가 (BP)"))
    sub("B1 · 강화 리스크 시뮬레이터", b_mock())
    c1, c2 = st.columns([1, 1.2], gap="medium")
    steps = [f"{a}→{b}강 ({p}%)" for a, b, p in pt]
    with c1:
        anchor("b1")
        st_i = st.selectbox("강화 단계 (공식 확률)", steps, index=6, key="fc_b1_step")
        gauge = st.slider("부스트 게이지 (%)", 0, 100, 100, key="fc_b1_g")
        val = st.number_input("현재 선수 가치 (만 BP)", 0.0, 1e9, 684.0, step=10.0, key="fc_b1_v")
        cost = st.number_input("강화 비용 · 재료 가치 (만 BP · 가정)", 0.0, 1e9, 500.0, step=10.0, key="fc_b1_c")
        vs = st.number_input("성공 시 예상 가치 (만 BP)", 0.0, 1e10, 11000.0, step=100.0, key="fc_b1_s")
        vf = st.number_input("실패 시 잔존 가치 (만 BP · 가정)", 0.0, 1e9, 382.0, step=10.0, key="fc_b1_f")
        prot = st.toggle("보호 수단 사용 (실패해도 등급 유지 · 대상 제한)", key="fc_b1_p")
    p_tab = pt[steps.index(st_i)][2]
    e = F.enhance(val * 1e4, cost * 1e4, p_tab, gauge, vs * 1e4, vf * 1e4, prot)
    with c2:
        html(f'<div class="fc-demo b"><h4>이번 강화의 손익 {b_sim()}</h4><div class="fc-m">'
             f'<div><small>실제 성공 확률</small><b>{e["p"]:.1f}%</b><em>공식 {p_tab}% × 게이지 {gauge}%</em></div>'
             f'<div><small>성공하면</small><b class="up">{bp(e["win"])}</b><em>시도 전 대비</em></div>'
             f'<div><small>실패하면</small><b class="dn">{bp(e["lose"])}</b><em>{100 - e["p"]:.0f}% 확률</em></div></div>'
             f'<div class="fc-m"><div><small>확률 가중 기대값</small><b>{bp(e["ev"])}</b></div>'
             f'<div><small>최대 손실</small><b class="dn">{bp(e["max_loss"])}</b></div>'
             f'<div><small>손익분기 확률</small><b>{e["breakeven_p"]:.1f}%</b></div></div>'
             '<div class="fc-act"><b>기대값이 0 근처여도, 대부분은 실패 쪽 결과를 겪는다</b> → 실패 직후 선택지(B2)가 필요</div>'
             '<div class="src">기본값 = 바조 카드 7강 → 8강 · 7강 684만·8강 1억 1,000만은 캡처 판매 최저가 · 실패 시 6강(382만)으로 복구된다고 가정 '
             '(공식 복구 확률표는 이미지라 미확인) · 재료 비용은 가정</div></div>')
    sub("B2 · 강화 실패 이후 재건 선택지", b_mock())
    html('<div class="fc-opts">' + "".join(f'<div><b>{escape(a)}</b><span>{escape(b)}</span><small>{escape(c)}</small></div>' for a, b, c in d["b2_options"]) + "</div>")
    with st.expander("자세히 보기 · 기존 강화 관련 제도 (중복 회피)"):
        table(["제도", "내용", "확인"], [[f"<b>{escape(a)}</b>", escape(b), escape(c)] for a, b, c in d["existing"]], badge_html=b_real())
        st.caption("B2는 새 재화나 확률 변경이 아니라, 실패 직후 화면에서 기존 제도와 다른 경로를 함께 보여 주는 안내다.")


# ======================================================================
# 05 C 키보드 vs 패드
def s5(d: dict) -> None:
    cs, ops = d["c_sides"], {o["id"]: o for o in d["opinions"]}
    head("C · 같은 축구 게임, 다른 조작 환경. 공정한 경쟁은 가능한가?", "키보드 유저와 패드 유저의 대립, 게임사는 누구의 손을 들어야 할까?", b_mock())
    q = lambda k: f'<a href="{escape(ops[k]["url"], quote=True)}" target="_blank" rel="noopener">“{escape(ops[k]["title"])}”</a>'
    html('<div class="fc-vs"><div class="kb"><div class="h">⌨️ 키보드 유저 측</div><ul>' + "".join(f"<li>{escape(x)}</li>" for x in cs["keyboard"])
         + f'</ul><div class="qs">{q("K1")}{q("K2")}{q("K3")}</div></div><div class="mid"><b>VS</b><span>공통으로 원하는 것 (가설)</span>'
         + "".join(f"<em>{escape(x)}</em>" for x in cs["common"]) + '</div>'
         '<div class="pad"><div class="h">🎮 패드 유저 측</div><ul>' + "".join(f"<li>{escape(x)}</li>" for x in cs["pad"])
         + f'</ul><div class="qs">{q("P1")}{q("P2")}{q("M1")}</div></div></div>')
    html(f'<div class="fc-cav">{b_real()} 링크 = 인벤 게시글 제목 · {escape(cs["note"])} · 상위 랭커 장비 비율 등은 검증 자료가 없어 숫자로 쓰지 않음</div>')
    sub("해결책 3가지 비교", b_mock())
    html('<div class="fc-pol">' + "".join(
        f'<div class="{"rec" if p["key"] == "3" else ""}"><span>{p["key"]}안</span><b>{escape(p["name"])}</b><small>{escape(p["how"])}</small>'
        f'<p class="pro">+ {escape(p["pro"])}</p><p class="con">− {escape(p["con"])}</p></div>' for p in d["c_policies"]) + "</div>")
    sub("당신이 FC 온라인 사업PM이라면?", b_mock())
    c1, c2 = st.columns([1, 1.25], gap="medium")
    ranks = {"상위 랭크 (구간 비율 5% · 가정)": 0.05, "중위 랭크 (35% · 가정)": 0.35, "일반 랭크 (60% · 가정)": 0.60}
    with c1:
        anchor("c5")
        pol = st.radio("정책 선택", list(F.POLICIES), format_func=lambda k: f"{k}안 · {F.POLICIES[k]}", index=2, key="fc_c5_pol")
        kb = st.slider("키보드 이용자 비중 (% · 가정)", 5, 95, 50, key="fc_c5_kb")
        n = st.number_input("동시 매칭 대기 인원 (명 · 가정)", 100, 1_000_000, 10_000, step=500, key="fc_c5_n")
        rk = st.selectbox("랭크 구간", list(ranks), index=0, key="fc_c5_rk")
        allow = st.slider("허용 대기시간 (통합 대비 배수)", 1.0, 5.0, 2.0, 0.5, key="fc_c5_allow")
        pref = st.slider("동일 장치 매칭 선호 비율 (% · 가정)", 0, 100, 40, key="fc_c5_pref")
    m = F.matching(n, ranks[rk], kb / 100, pref / 100, allow)
    pp = m["policies"][pol]
    worst = max(pp["kb_wait_x"], pp["pad_wait_x"])
    risk = "주의 · 통합 확대" if pp["fallback"] else "높음" if worst > allow else "주의" if worst > allow * 0.7 else "낮음"
    with c2:
        html(f'<div class="fc-demo c"><h4>{pol}안 · {escape(F.POLICIES[pol])} {b_sim()}</h4><div class="fc-m">'
             f'<div><small>키보드 유저{"(우선 선택)" if pol == "3" else ""}의 상대 풀</small><b>{pp["kb_pool"]:,.0f}명</b><em>대기 ≈ 통합의 {pp["kb_wait_x"]:.1f}배</em></div>'
             f'<div><small>패드 유저{"(우선 선택)" if pol == "3" else ""}의 상대 풀</small><b>{pp["pad_pool"]:,.0f}명</b><em>대기 ≈ 통합의 {pp["pad_wait_x"]:.1f}배</em></div>'
             f'<div><small>대기시간 위험</small><b class="{"dn" if risk == "높음" else ""}">{risk}</b><em>허용 {allow:.1f}배 기준</em></div></div>'
             '<div class="fc-act">' + {"1": "<b>공정성 체감은 좋아질 수 있지만</b> 소수 장치·상위 랭크의 대기시간이 가장 먼저 무너진다",
                                       "2": "<b>매칭 풀은 그대로</b> · 조작 밸런스 개선만으로 불만이 줄어드는지 만족도로 검증",
                                       "3": "<b>원하는 사람만 같은 장치 우선</b> · 오래 걸리면 통합으로 넓히는 선택권 → 대기시간·포기율을 가드레일로"}[pol]
             + '</div><div class="src">' + ("3안은 허용 배수에 닿으면 통합으로 넓히므로 대기 상한 = 허용 배수 · 우선을 고르지 않은 유저는 통합 그대로 · " if pol == "3" else "") + '실제 매칭 알고리즘이 아닌 단순 모델 · 대기시간은 실제 초가 아니라 통합 매칭 대비 상대 배수 (풀 크기에 반비례 가정)</div></div>')
    html('<div class="fc-final"><div class="k">C 사업PM 결론 ' + b_mock() + '</div>'
         '<b>초기 권고: 3안 선택형 동일 입력 장치 우선 매칭을 제한적으로 실험한다.</b> 정답으로 확정하지 않는다.'
         '<div class="chk">' + "".join(f"<span>{escape(x)}</span>" for x in d["c_checks"]) + '</div>'
         '<p>결과에 따라 <b>완전 분리 · 선택형 유지 · 통합+조작 밸런스</b> 중 최종 정책을 고른다. 상위 랭크와 일반 랭크는 따로 판단한다.</p>'
         '<strong>어느 한쪽의 승리가 아니라, 양쪽이 납득할 수 있는 경쟁 환경을 만드는 것이 사업PM의 역할이다.</strong></div>')


# ======================================================================
# 06 KPI·실행
def s6(d: dict) -> None:
    head("KPI·실행: A·B·C를 따로 검증한다 · 목표 수치는 실제 성과가 아니다", "1차 C 매칭 실험 → 2차 A → 3차 B", b_mock())
    html('<div class="fc-kpi">' + "".join(
        f'<div class="{t.lower()}"><div class="h">{tr(t)} {"구단 가치" if t == "A" else "강화" if t == "B" else "입력 장치 갈등"}</div>' + "".join(
            f'<p><b>{escape(a)}</b><span>{escape(b)} · {escape(c)}</span></p>' for a, b, c in d["kpis"][t]) + "</div>" for t in ("A", "B", "C")) + "</div>")
    sub("실험 설계 (대조군 · 실험군 · 성공 · 중단)", b_mock())
    table(["트랙", "대조군", "실험군", "대상", "주요 지표", "가드레일"],
          [[tr(a), escape(b), f"<b>{escape(c)}</b>", escape(e), escape(f), escape(g)] for a, b, c, e, f, g in d["experiments"]])
    table(["결과", "기준"], [[f"<b>{escape(a)}</b>", escape(b)] for a, b in d["stop_rules"]])
    sub("개발·운영 비용 (기획 추정치 · 실제 견적 아님)", b_sim())
    mc = d["cost"]["monthly_cost_per_person"]
    rows, tot = [], 0.0
    for name, eff, why in d["cost"]["items"]:
        c = eff * mc
        tot += c
        rows.append([f"<b>{escape(name)}</b>", f"{eff}인월", f"<b>{bp(c).replace(' BP', '')}원</b>", escape(why)])
    rows.append(["<b>합계</b>", f"{sum(x[1] for x in d['cost']['items'])}인월", f"<b>{bp(tot).replace(' BP', '')}원</b>", "재화 지급 0원 원칙 · 서버·QA 포함 추정"])
    table(["개선안", "공수", "비용", "산출 근거"], rows)
    st.caption(f"비용 = 공수 × 1인 월 {mc / 1e4:,.0f}만 원 (가정 · 다른 프로젝트와 같은 기준)")
    sub("실행 우선순위", b_interp())
    html('<ol class="fc-order">' + "".join(f'<li class="{t.lower()}"><span>{n}</span>{tr(t)}<b>{escape(k)}</b><small>{escape(w)}</small></li>'
                                           for n, t, k, w in d["priority"]) + "</ol>")
    html('<div class="fc-final"><div class="k">최종 사업PM 판단 ' + b_mock() + '</div>'
         '<b>시세는 보장하지 않고, 경기의 재미와 공정한 경쟁을 지킨다.</b>'
         '<p>이 포트폴리오가 보여 주는 역량: <b>게임 경제를 이해하는 능력</b> · <b>유저 이탈 문제를 해결하는 능력</b> · '
         '<b>서로 충돌하는 유저 요구 사이에서 사업적 의사결정을 내리는 능력</b></p></div>')
    note("한계: 유저 의견은 게시글 제목과 화면 관측 중심이며 대표 표본이 아니다. 인과는 실험으로만 판단한다.")
