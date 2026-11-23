"""FC 온라인 — 축구 게임인가, 주식 게임인가? (사업PM 포트폴리오 · 01~06 탭)

- A 구단 가치 하락 40% · B 강화·훈련코치 진입장벽 25% · C 키보드 vs 패드 35% (기획 비중 · 불만 비율 아님)
- 01 문제 정의 · 02 실제 유저 댓글 · 03 이탈·갈등 원인 · 04 A·B·C 해결 전략 · 05 데모·KPI · 06 실행·예산·리스크
- 사실·가정·시안: data/fconline/fc.json · 계산: gamepulse/sim/fc_sim.py (정적 페이지 JS 와 같은 식)
- 게임 화면: assets/fconline/*.jpg (작성자 캡처 · 내 닉네임·레벨·클럽명·상대 닉네임 블러 · 창 테두리 제거). 원본은 _originals/ (git 제외)
- 유튜브 댓글: 캡처 원본을 받지 못해 사용자 확인 요약만 '요약'으로 표시 (직접 인용·개수·비율 없음)
- 데모 2개(A1·C)는 입력 칸 첫머리에 fc-anchor 표식 → 정적 페이지에서 JS 조작판으로 교체
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
from gamepulse.views.overwatch import (b_hypo, b_interp, b_mock, b_real, b_sim, badge_legend, chart_card, head, link,
                                       note, sub, table)

ROOT = Path(__file__).resolve().parents[2]
DATA, ASSETS = ROOT / "data" / "fconline", ROOT / "assets" / "fconline"
SECTIONS = [("01", "문제 정의"), ("02", "실제 유저 댓글"), ("03", "이탈·갈등 원인"), ("04", "A·B·C 해결 전략"),
            ("05", "데모·KPI"), ("06", "실행·예산·리스크")]
TAB_LABELS = [f"{n} {t}" for n, t in SECTIONS]
TAB_KEY = "fc_tab"
C_PURPLE = "#6D28D9"
CREDIT = "실제 게임 화면 · 작성자 캡처 (2026-11-23) · 계정 식별정보 블러 · © NEXON · EA SPORTS"


@st.cache_data(show_spinner=False)
def load() -> dict:
    return json.loads((DATA / "fc.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _img(name: str, mtime: float, max_w: int = 1400) -> str:
    return web_jpeg_b64(str(ASSETS / name), max_w=max_w)


def shot(name: str, title: str, caption: str = "") -> str:
    p = ASSETS / name
    if not p.is_file():
        return ""
    cap = f"<b>{escape(caption)}</b>" if caption else ""
    return (f'<figure class="fc-shot"><div class="bar"><span>실제 게임 화면</span>{escape(title)}</div>'
            f'<img src="data:image/jpeg;base64,{_img(name, p.stat().st_mtime)}" alt="실제 게임 화면: {escape(title)}" loading="lazy">'
            f'<figcaption>{cap}<span>{CREDIT}</span></figcaption></figure>')


def bp(x: float) -> str:
    """BP 금액 → '1억 300만 BP' (2026-08-20 화폐 단위 조정 이후 BP)."""
    x = round(x)
    sign = "−" if x < 0 else ""
    x = abs(x)
    jo, eok, man = x // 10**12, (x % 10**12) // 10**8, (x % 10**8) // 10**4
    s = " ".join(p for p in (f"{jo:,}조" if jo else "", f"{eok:,}억" if eok else "", f"{man:,}만" if man else "") if p) or f"{x:,}"
    return f"{sign}{s} BP"


def won(x: float) -> str:
    return bp(x).replace(" BP", " 원")


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
    html(f'<div class="fc-anchor" data-k="{k}"></div>')


def lead(t: str, title: str, line: str) -> None:
    html(f'<div class="fc-lead {t.lower()}">{tr(t)}<b>{escape(title)}</b><span>{escape(line)}</span></div>')


def conclude(text: str) -> None:
    html(f'<div class="fc-pm"><span>사업PM 결론</span><b>{escape(text)}</b></div>')


# ----------------------------------------------------------------------
def _cover(d: dict) -> None:
    cv = d["cover"]
    p = ASSETS / "market_trend.jpg"
    img = (f'<figure class="fc-hero-img"><img src="data:image/jpeg;base64,{_img("market_trend.jpg", p.stat().st_mtime)}" '
           'alt="실제 게임 화면: 이적시장 인기 선수 · 시세 급상승 · 최고 거래가"><figcaption>실제 게임 화면 · 이적시장 · 작성자 캡처 (계정 정보 블러)</figcaption></figure>') if p.is_file() else ""
    html(f'<div class="fc-hero"><div class="fc-hero-t"><div class="k">{escape(cv["kicker"])}</div>'
         f'<div class="q" role="heading" aria-level="1">{escape(cv["title"])}</div><div class="s">{escape(cv["subtitle"])}</div>'
         '<div class="tick"><span>시세 급상승 <b>▲40.00%</b></span><span>최고 거래가 <b>1,800억 BP</b></span><span>8강 카드 한 달 <b class="dn">▼70%</b></span></div>'
         f'</div>{img}</div>')
    html('<div class="fc-tracks">' + "".join(
        f'<div class="{t["key"].lower()}"><div class="h">{tr(t["key"])}<b>{t["weight"]}%</b><span>{escape(t["name"])}</span></div>'
        f'<strong>{escape(t["line"])}</strong><small>→ {escape(t["sol"])}</small></div>' for t in d["tracks"])
        + f'</div><div class="fc-cav">{escape(d["weight_note"])} · 시세는 2026-08-20 화폐 단위 조정 이후 BP</div>')


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
# 01 문제 정의
def s1(d: dict) -> None:
    head("결론: 시세는 보장하지 않고, 성장 경로와 공정한 조작 환경을 만든다", "1차 C 조작 환경 개선 → 2차 A 구단 재건 → 3차 B 초기 세팅 가이드", b_mock())
    html('<div class="fc-why">'
         f'<div><span>A · 구단 가치</span><b>8강 카드 2장, 한 달 그래프 안에서 <em>6,260만 → 약 1,900만 BP</em></b><small>{b_real()} 작성자 캡처</small></div>'
         f'<div><span>B · 강화·훈련코치</span><b>7→8강 성공 <em>7%</em> · 코치 DIY는 <em>장기 목표</em></b><small>{b_real()} 공식 확률 · 인벤 가이드</small></div>'
         f'<div><span>C · 키보드 vs 패드</span><b>분리 매칭 <em>찬성·반대</em>가 같은 달 게시판에 반복</b><small>{b_real()} 인벤 게시글 제목</small></div></div>')
    html('<div class="fc-pair">' + shot("squad.jpg", "스쿼드 관리 · 클럽 선수 가치", "구단 = 선수 가치의 합으로 보인다")
         + shot("manager_mode.jpg", "공식경기 감독모드", "직접 조작 대신 전술로 경기") + "</div>")


# ======================================================================
# 02 실제 유저 댓글
def s2(d: dict) -> None:
    yt = d["youtube"]
    head("근거: 조작 불만은 공통, 해법(분리 vs 개선)은 갈린다", "사례이지 비율이 아니다", b_real())
    sub("유튜브 댓글 · 유저 의견 요약")
    html('<div class="fc-yt">' + "".join(f'<a href="{escape(u, quote=True)}" target="_blank" rel="noopener"><span>YouTube · {escape(t)}</span><b>{escape(k)}</b></a>'
                                          for t, u, k in yt["videos"]) + "</div>")
    cls = {"조작 불만": "q", "분리 찬성": "kb", "분리 반대": "pad", "제3의 의견": "alt"}
    urls = {i + 1: v[1] for i, v in enumerate(yt["videos"])}
    html('<div class="fc-themes yt">' + "".join(
        f'<div class="{cls[g]}"><span>{escape(g)} · 유저 의견 요약</span><b>{escape(t)}</b>'
        f'<a href="{escape(urls[s], quote=True)}" target="_blank" rel="noopener">출처 {s} · 영상 보기</a></div>' for g, t, s in yt["cards"]) + "</div>")
    html(f'<div class="fc-cav">{escape(yt["note"])}</div>')
    html(f'<div class="fc-pm"><span>사업PM 해석</span><b>{escape(yt["pm"])}</b></div>')
    sub("인벤 FC 온라인 게시판 · 실제 게시글 제목", b_real())
    side = {"키보드": "kb", "패드": "pad", "질문": "q", "중립": "q", "강화": "en"}
    html('<div class="fc-posts">' + "".join(
        f'<a class="{side[o["side"]]}" href="{escape(o["url"], quote=True)}" target="_blank" rel="noopener"><span>{escape(o["side"])} · {escape(o["cat"])}</span>'
        f'<b>“{escape(o["title"])}”</b><small>인벤 · {escape(o["date"])} · 원문</small></a>' for o in d["opinions"]) + "</div>")
    with st.expander("자세히 보기 · 발언→불만→이탈 위험 · 조사 범주 · 공식 자료 · 자료 한계"):
        html('<div class="fc-voice">' + "".join(
            f'<div><span class="v">{escape(v)}</span><i>→</i><b>{escape(c)}</b><i>→</i><span class="r">{escape(r)}</span><i>→</i><strong>{escape(s)}</strong></div>'
            for v, c, r, s in d["voices"]) + "</div>")
        table(["범주", "확인", "근거", "상태"], [[f"<b>{escape(a)}</b>", escape(b), escape(c), f"<em>{escape(e)}</em>" if e else "—"] for a, b, c, e in d["categories"]],
              badge_html=b_real())
        table(["날짜", "자료", "구분", "확인한 사실", "출처"],
              [[escape(o["date"]), f"<b>{escape(o['title'])}</b>", escape(o["kind"]), escape(o["fact"]), link(o["url"], "열기")] for o in d["official"]], badge_html=b_real())
        st.markdown(f"- 인벤 게시글: {d['opinion_note']}\n"
                    "- 유튜브: 작성자가 두 영상의 댓글을 직접 캡처(10장)해 요약 · 원문 인용·닉네임은 싣지 않음 · A·B 근거로는 쓰지 않음\n"
                    "- '구단 가치' 검색은 일반 잡담, '강화 실패' 검색은 0건 (2026-11-23) → A·B 유저 발언은 표본 부족\n"
                    "- 상위 랭커 장비 비율 같은 수치는 검증 자료가 없어 쓰지 않는다 · 작성자 이름은 저장하지 않는다")


# ======================================================================
# 03 이탈·갈등 원인
def s3(d: dict) -> None:
    cs, ops = d["c_sides"], {o["id"]: o for o in d["opinions"]}
    head("원인: A는 자산 급락, B는 늦은 적응, C는 조작 조건 갈등", "인과는 실험으로만 판단", b_hypo())
    lead("A", "열심히 키운 구단, 왜 내 노력의 가치는 떨어질까?", "자산 급락 → 성장 박탈감 (가설)")
    html('<div class="fc-drops">' + "".join(
        f'<div><span>{escape(x["card"])}</span><b>{bp(x["peak"]).replace(" BP", "")} <i>→</i> <em>{bp(x["now"]).replace(" BP", "")}</em></b>'
        f'<strong>▼{(1 - x["now"] / x["peak"]) * 100:.0f}%</strong><small>그래프 최고 → 최근 · {escape(x["when"])}</small></div>' for x in d["drops"]) + "</div>")
    imgs = [x for x in (shot(x["file"], f"이적시장 · {x['card']}") for x in d["drops"]) if x]
    if imgs:
        html('<div class="fc-pair">' + "".join(imgs[:2]) + "</div>")
    note(d["drops_note"])
    lead("B", "신규·복귀 유저는 왜 경쟁에 적응하기 전에 지칠까?", "강화 실패 · 늦은 훈련코치 세팅 → 초기 이탈 (가설)")
    html('<div class="fc-facts">' + "".join(f'<div><span>{escape(a)}</span><b>{escape(b)}</b><small>{escape(c)}</small></div>' for a, b, c in d["b_facts"]) + "</div>")
    lead("C", "키보드 vs 패드, 같은 경기인데 공정한가?", "조작의 자유인가, 경쟁의 형평성인가?")

    def q(k: str) -> str:
        return f'<a href="{escape(ops[k]["url"], quote=True)}" target="_blank" rel="noopener">“{escape(ops[k]["title"])}”</a>'
    html('<div class="fc-vs"><div class="kb"><div class="h">⌨️ 키보드 유저</div><ul>' + "".join(f"<li>{escape(x)}</li>" for x in cs["keyboard"][:3])
         + f'</ul><div class="qs">{q("K1")}{q("K2")}</div></div><div class="mid"><b>VS</b><span>공통 요구 (가설)</span>'
         + "".join(f"<em>{escape(x)}</em>" for x in cs["common"]) + '</div>'
         '<div class="pad"><div class="h">🎮 패드 유저</div><ul>' + "".join(f"<li>{escape(x)}</li>" for x in cs["pad"][:3])
         + f'</ul><div class="qs">{q("P1")}{q("P2")}</div></div></div>')
    html(f'<div class="fc-cav">{b_interp()} 대표 주장 (직접 인용 아님) · 따옴표 링크만 실제 게시글 제목</div>')


# ======================================================================
# 04 A·B·C 해결 전략
def s4(d: dict) -> None:
    ap = d["a_plan"]
    head("해결: 시세 보장·보상 확대·매칭 분리 대신, 성장 경로·적응 시간·조작 환경을 바꾼다", "모두 기획 시안", b_mock())
    lead("A", "A1 하락 원인 분석 · A2 구단 재건 플랜", "A1 데모는 05 탭")
    html('<div class="fc-two"><div><b>A1 · 하락 원인 분석</b><ul>' + "".join(f"<li>{escape(x)}</li>" for x in ap["a1"]) + "</ul></div>"
         '<div><b>A2 · 구단 재건 플랜</b><ul>' + "".join(f"<li>{escape(x)}</li>" for x in ap["a2"]) + "</ul></div></div>")
    html(f'<div class="fc-cav">{escape(ap["dup"])}</div>')
    conclude("시세를 보장하는 대신, 유저가 다시 성장할 수 있는 경로를 제공한다.")
    lead("B", "초기 경쟁력 세팅 가이드", "있는 지원을 '다음 할 일' 순서로 묶는다")
    html('<div class="fc-steps">' + "".join(f'<div><span>{escape(a)}</span><b>{escape(b)}</b><small>{escape(c)}</small></div>' for a, b, c in d["b_guide"]) + "</div>")
    with st.expander("자세히 보기 · 기존 지원과 중복 확인"):
        table(["기존 제도 · 제안", "역할", "확인"], [[f"<b>{escape(a)}</b>", escape(b), escape(c)] for a, b, c in d["existing"]], badge_html=b_real())
    conclude("보상을 무작정 늘리기보다, 신규 유저가 경쟁에 적응하는 시간을 단축한다.")
    lead("C", "정책 3가지 비교 → 3안 권고", "매칭을 나누기보다 납득할 수 있는 조작 환경")
    html('<div class="fc-pol">' + "".join(
        f'<div class="{"rec" if p["key"] == "3" else ""}"><span>{p["key"]}안{" · 권고" if p["key"] == "3" else ""}</span><b>{escape(p["name"])}</b>'
        f'<small>{escape(p["how"])}</small><p class="pro">+ {escape(p["pro"])}</p><p class="con">− {escape(p["con"])}</p></div>' for p in d["c_policies"]) + "</div>")
    sub("왜 3안인가 · 유튜브 댓글 근거 → 결정", b_interp())
    html('<div class="fc-facts why">' + "".join(f'<div><span>{escape(a)}</span><b>{escape(b)}</b><small>{escape(c)}</small></div>' for a, b, c in d["c_why"]) + "</div>")
    html(f'<div class="fc-cav">{escape(d["c_why_note"])}</div>')
    html('<div class="fc-planc"><b>실행 계획</b><ol>' + "".join(f"<li>{escape(x)}</li>" for x in d["c_plan"]) + f'</ol><small>{escape(d["c_not"])}</small></div>')
    conclude("매칭을 나누기보다, 같은 경기에서 납득할 수 있는 조작 환경을 만든다.")
    html('<div class="fc-cav">분리·선택형은 보류 · 대기시간 증가는 <b>검증 전 위험 요인</b> · 격차가 안 줄면 선택형 재검토</div>')


# ======================================================================
# 05 데모·KPI
def s5(d: dict) -> None:
    head("데모·KPI: 직접 계산하고, 판단 기준을 정한다", "수치는 모두 가정 · 실제 성과 아님", b_mock())
    sub("A1 · 구단 가치 하락 원인 분석기", b_mock())
    c1, c2 = st.columns([1, 1.2], gap="medium")
    with c1:
        anchor("a1")
        v0 = st.number_input("초기 구단 가치 (억 BP · 가상)", 1.0, 100000.0, 10.0, step=1.0, key="fc_a1_v0")
        my = st.slider("내 구단 가치 하락률 (%)", 0, 90, 50, key="fc_a1_my")
        mk = st.slider("시장 전체 하락률 (%)", 0, 90, 20, key="fc_a1_mk")
    r = F.value_change(v0 * 1e8, my / 100, mk / 100)
    with c2:
        html(f'<div class="fc-demo"><h4>구단 가치 진단 {b_sim()}</h4><div class="fc-m">'
             f'<div><small>현재 구단 가치</small><b>{bp(r["now"])}</b><em class="dn">−{bp(r["loss"]).replace(" BP", "")}</em></div>'
             f'<div><small>원래대로 돌아가려면</small><b class="up">+{r["recover_pct"]:.0f}%</b><em>상승 필요</em></div>'
             f'<div><small>시장 대비</small><b>{r["vs_market_pct"]:+.0f}%</b><em>{"시장보다 더 하락" if r["vs_market_pct"] < 0 else "시장과 같거나 덜 하락"}</em></div></div>'
             '<div class="fc-act"><b>가치가 떨어져도 능력치·팀컬러는 그대로</b> → 재건 플랜(A2)</div>'
             '<div class="src">시세와 경기 성능은 다른 숫자 · 시세 보장 없음</div></div>')
    with st.expander("자세히 보기 · 하락률별 회복에 필요한 상승률"):
        cv = F.recovery_curve()
        fig = go.Figure(go.Scatter(x=[a for a, _ in cv], y=[b for _, b in cv], mode="lines+markers", line=dict(color=C_PURPLE, width=3)))
        fig.add_scatter(x=[my], y=[r["recover_pct"]], mode="markers", marker=dict(size=14, color="#DC2626"))
        fig.update_xaxes(title="구단 가치 하락률 (%)", ticksuffix="%")
        fig.update_yaxes(title="회복에 필요한 상승률 (%)", ticksuffix="%", rangemode="tozero")
        chart_card(fig, key="fc_rec", kind="sim", title="하락률별 회복에 필요한 상승률", unit="% · 빨간 점 = 현재 입력",
                   kpis=[("50% 하락 후", "+100% 필요")], analysis="하락이 클수록 회복에 필요한 상승은 더 가파르게 커진다",
                   decision="'다시 오르면 된다' 대신 경기력 목표를 따로 제시", basis="필요 상승률 = 하락률 ÷ (1 − 하락률)", height=240,
                   legend=False, cols=("하락률 (%)", "필요 상승률 (%)"))
    sub("C · 당신이 FC 온라인 사업PM이라면?", b_mock())
    c1, c2 = st.columns([1, 1.35], gap="medium")
    ranks = {"상위 랭크 (구간 비율 5% · 가정)": 0.05, "중위 랭크 (35% · 가정)": 0.35, "일반 랭크 (60% · 가정)": 0.60}
    with c1:
        anchor("c5")
        pol = st.radio("정책 선택", list(F.POLICIES), format_func=lambda k: f"{k}안 · {F.POLICIES[k]}{' (권고)' if k == '3' else ''}", index=2, key="fc_c5_pol")
        kb = st.slider("키보드 이용자 비중 (% · 가정)", 5, 95, 50, key="fc_c5_kb")
        n = st.number_input("동시 매칭 대기 인원 (명 · 가정)", 100, 1_000_000, 10_000, step=500, key="fc_c5_n")
        rk = st.selectbox("랭크 구간", list(ranks), index=0, key="fc_c5_rk")
        allow = st.slider("허용 대기시간 (통합 대비 배수)", 1.0, 5.0, 2.0, 0.5, key="fc_c5_allow")
        pref = st.slider("동일 장치 우선 선택 비율 (% · 가정)", 0, 100, 40, key="fc_c5_pref")
    m = F.matching(n, ranks[rk], kb / 100, pref / 100, allow)
    pols = {p["key"]: p for p in d["c_policies"]}

    def risk(x: dict) -> str:
        w = max(x["kb_wait_x"], x["pad_wait_x"])
        return "주의 · 통합 확대" if x["fallback"] else "높음" if w > allow else "주의" if w > allow * 0.7 else "낮음"
    rows = "".join(
        f'<tr class="{"on" if k == pol else ""}"><td><b>{k}안</b> {escape(F.POLICIES[k])}{" <em>권고</em>" if k == "3" else ""}</td>'
        f'<td>{escape(pols[k]["fair"])}</td><td>키보드 {x["kb_pool"]:,.0f} · 패드 {x["pad_pool"]:,.0f}명</td>'
        f'<td class="{"dn" if risk(x) == "높음" else ""}">{risk(x)}<small>통합의 {max(x["kb_wait_x"], x["pad_wait_x"]):.1f}배</small></td><td>{escape(pols[k]["ops"])}</td></tr>'
        for k, x in m["policies"].items())
    msg = {"1": "공정성 체감은 좋아질 수 있지만 소수 장치·상위 랭크의 대기시간이 먼저 흔들릴 위험",
           "2": "선택한 사람만 같은 장치 우선 · 허용 배수에 닿으면 통합으로 확대",
           "3": "매칭 풀은 그대로 · 키보드 조작 개선으로 격차가 줄어드는지 승률·조작 성공률로 검증"}[pol]
    with c2:
        html(f'<div class="fc-demo c"><h4>정책 비교 {b_sim()}</h4><div class="fc-cmp"><table><tr><th>정책</th><th>공정성 체감</th><th>상대 풀</th><th>대기시간 위험</th><th>운영 난이도</th></tr>'
             f'{rows}</table></div><div class="fc-act"><b>{pol}안 선택</b> · {msg}</div>'
             '<div class="src">실제 매칭 알고리즘이 아닌 단순 모델 · 대기시간은 실제 초가 아니라 통합 대비 상대 배수 · 공정성·운영 난이도는 정성 평가</div></div>')
    sub("KPI · 목표·가정 (실제 성과 아님)", b_mock())
    names = {"A": "구단 가치", "B": "강화·훈련코치", "C": "키보드 vs 패드"}
    html('<div class="fc-kpi">' + "".join(
        f'<div class="{t.lower()}"><div class="h">{tr(t)} {names[t]}</div>' + "".join(
            f'<p><b>{escape(a)}</b><span>{escape(b)} · {escape(c)}</span></p>' for a, b, c in d["kpis"][t] if b != "보조") + "</div>" for t in ("A", "B", "C")) + "</div>")
    with st.expander("자세히 보기 · 보조 KPI · 실험 설계 (대조군 · 실험군 · 성공 · 중단)"):
        table(["트랙", "보조 KPI", "대상"], [[tr(t), f"<b>{escape(a)}</b>", escape(c)] for t in ("A", "B", "C") for a, b, c in d["kpis"][t] if b == "보조"])
        table(["트랙", "대조군", "실험군", "대상", "성공 기준 (주요 지표)", "가드레일"],
              [[tr(a), escape(b), f"<b>{escape(c)}</b>", escape(e), escape(f), escape(g)] for a, b, c, e, f, g in d["experiments"]], badge_html=b_mock())
        table(["결과", "기준"], [[f"<b>{escape(a)}</b>", escape(b)] for a, b in d["stop_rules"]])


# ======================================================================
# 06 실행·예산·리스크
def s6(d: dict) -> None:
    head("실행: 1차 C 조작 환경 → 2차 A 재건 → 3차 B 가이드", "예산은 실제 견적이 아닌 기획 추정치", b_mock())
    html('<ol class="fc-order">' + "".join(f'<li class="{t.lower()}"><span>{n}</span>{tr(t)}<b>{escape(k)}</b><small>{escape(w)}</small></li>'
                                           for n, t, k, w in d["priority"]) + "</ol>")
    sub("예산 (기획 추정치)", b_sim())
    mc = d["cost"]["monthly_cost_per_person"]
    rows, tot, eff_t = [], 0.0, 0.0
    for name, eff, why in d["cost"]["items"]:
        tot += eff * mc
        eff_t += eff
        rows.append([f"<b>{escape(name)}</b>", f"{eff}인월", f"<b>{won(eff * mc)}</b>", escape(why)])
    rows.append(["<b>합계</b>", f"{eff_t:g}인월", f"<b>{won(tot)}</b>", "재화 지급 0원 원칙"])
    table(["개선안", "공수", "비용", "산출 근거"], rows)
    st.caption(f"비용 = 공수 × 1인 월 {mc / 1e4:,.0f}만 원 (가정 · 다른 프로젝트와 같은 기준)")
    sub("리스크와 대응", b_interp())
    table(["리스크", "대응"], [[escape(a), escape(b)] for a, b in d["risks"]])
    html('<div class="fc-final"><div class="k">최종 사업PM 판단 ' + b_mock() + '</div>'
         '<b>A 성장 경험 회복 · B 초기 적응 개선 · C 통합 매칭 유지와 조작 환경 개선</b>'
         '<p>쉬운 답(시세 보장·보상 확대·매칭 분리) 대신 <b>게임 경제·공정성·매칭 품질</b>을 함께 지킨다.</p></div>')
    note("한계: 유저 의견은 게시글 제목·유튜브 요약·화면 관측 중심 · 대표 표본 아님")
