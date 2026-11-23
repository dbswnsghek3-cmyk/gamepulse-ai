"""던전앤파이터 — 어려운 던전을 클리어했는데, 왜 성장했다는 느낌이 없을까? (사업PM 포트폴리오 · 01~06 탭)

- 01 문제 정의 · 02 근거 (공식·언론 사실 + 유저 자료 대기) · 03 원인 (A 시즌제 · B 랜덤 보상) · 04 해결 (C)
  · 05 시뮬레이터·KPI·실험 · 06 사업적 판단·예산·리스크
- 사실·가설·시안: data/dnf/dnf.json · 계산: gamepulse/sim/dnf_sim.py (정적 페이지 JS 와 같은 난수열·같은 식)
- 친구 인터뷰·유튜브 댓글·게임 화면 캡처 원본은 아직 없음 → 실제 유저 근거 영역은 '대기' 상태로 두고 만들어내지 않는다
- 디자인은 FC 온라인 컴포넌트 재사용 · 표지는 던파 전용 빨간색
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import streamlit as st

from gamepulse.sim import dnf_sim as D
from gamepulse.ui.components import html
from gamepulse.views.fconline import conclude, lead, sol_card, tr, won
from gamepulse.views.overwatch import b_hypo, b_interp, b_mock, b_real, b_sim, badge_legend, head, link, sub, table

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "dnf"
SECTIONS = [("01", "문제 정의"), ("02", "근거"), ("03", "원인"), ("04", "해결 전략"), ("05", "시뮬레이터·KPI"), ("06", "사업적 판단")]
TAB_LABELS = [f"{n} {t}" for n, t in SECTIONS]
TAB_KEY = "df_tab"


@st.cache_data(show_spinner=False)
def load() -> dict:
    return json.loads((DATA / "dnf.json").read_text(encoding="utf-8"))


def _tab_from_query() -> str:
    q = str(st.query_params.get("tab", ""))
    return next((lab for lab in TAB_LABELS if lab.startswith(q.zfill(2)[:2])), TAB_LABELS[0]) if q else TAB_LABELS[0]


def _sync_tab_param() -> None:
    st.query_params["page"] = "dnf"
    st.query_params["tab"] = str(st.session_state.get(TAB_KEY, TAB_LABELS[0]))[:2]


def tab_nav() -> int:
    if st.session_state.get(TAB_KEY) not in TAB_LABELS:
        st.session_state[TAB_KEY] = _tab_from_query()
    sel = st.radio("섹션 선택", TAB_LABELS, key=TAB_KEY, horizontal=True, label_visibility="collapsed", on_change=_sync_tab_param)
    return TAB_LABELS.index(sel)


def anchor(k: str) -> None:
    html(f'<div class="fc-anchor" data-k="{k}"></div>')


def render() -> None:
    d = load()
    cv = d["cover"]
    html('<div class="gp-ow-page"></div>')
    html(f'<div class="fc-hero solo dnf"><div class="fc-hero-t"><div class="k">{escape(cv["kicker"])}</div>'
         f'<div class="q" role="heading" aria-level="1">{escape(cv["title"])}<br>{escape(cv["title2"])}</div>'
         f'<div class="s">{escape(cv["subtitle"])}</div></div></div>')
    i = tab_nav()
    badge_legend()
    html(f'<div class="ow-pane-mark" data-tab="{SECTIONS[i][0]}"></div>')
    [s1, s2, s3, s4, s5, s6][i](d)
    st.caption(f"{d['disclaimer']} · 자료 확인일 {d['checked_at']}")


# ======================================================================
def s1(d: dict) -> None:
    it = d["intro"]
    html(f'<div class="fc-intro dnf"><b>던전앤파이터란?</b><p>{escape(it["line"])}</p><ol>'
         + "".join(f"<li>{tr(t)}{escape(x)}</li>" for t, x in it["topics"]) + "</ol></div>")
    html('<div class="df-wait">게임 화면 캡처 대기 · 원본을 받으면 이 자리에 한 장 크게 넣습니다 (다른 게임 이미지 재사용 안 함)</div>')
    head("문제: 클리어는 했는데 성장이 쌓이지 않는다", "세 문제는 아직 가설 · 사실과 해석을 구분", b_hypo())
    html('<div class="fc-why">' + "".join(
        f'<div><span>{escape(k)} · {escape(n)}</span><b>{escape(p)}</b><small>{escape(s)}</small></div>' for k, n, p, s in d["problems"]) + "</div>")
    conclude("확률 보상은 남기고, 운이 나쁜 날에도 성장 진척이 쌓이게 한다.")


def s2(d: dict) -> None:
    head("근거: 공식 발표와 구조는 확인 · 유저 근거는 자료 대기", "확인한 것만 사실로 표시", b_real())
    sub("공식 발표·구조 (확인함)", b_real())
    html('<div class="fc-evs two">' + "".join(
        f'<div class="fc-ev {"off" if "공식" in o["kind"] else ""}"><span class="t">{escape(o["kind"])} · {escape(o["use"])}</span><b>{escape(o["fact"])}</b>'
        f'<small>{escape(o["date"])} · {link(o["url"], o["src"] + " ↗")}</small></div>' for o in d["official"]) + "</div>")
    html(f'<div class="fc-excl">{escape(d["unverified"])}</div>')
    sub("실제 유저 근거 (자료 대기 · 임시)", b_hypo())
    html(f'<div class="df-wait">{escape(d["status"]["note"])}</div>')
    table(["자료", "구분 · 다루는 방식", "필요한 것"], [[f"<b>{escape(a)}</b>", escape(b), escape(c)] for a, b, c in d["pending"]])
    st.caption("원본 없이 의견 개수·비율·인용을 만들지 않는다 · 친구 1명의 경험은 정성 인터뷰로만 표시")


def s3(d: dict) -> None:
    a = d["a"]
    head("원인: A 시즌이 바뀌면 가치가 약해지고, B 같은 노력에도 보상이 운에 갈린다", "인과는 실험으로만 판단", b_hypo())
    lead("A", "시즌제와 성장 가치", "시즌제를 부정하지 않고 장점과 부작용을 함께")
    html('<div class="fc-two"><div><b>장점</b><ul>' + "".join(f"<li>{escape(x)}</li>" for x in a["pros"]) + "</ul></div>"
         '<div><b>부작용 (가설)</b><ul>' + "".join(f"<li>{escape(x)}</li>" for x in a["cons"]) + "</ul></div></div>")
    html(f'<div class="fc-cav">{b_real()} {escape(a["official"])}</div>')
    lead("B", "랜덤 보상과 성취감 (핵심)", "구조는 사실 · 체감과 이탈은 가설")
    html('<div class="fc-flow3 df4">' + '<i>→</i>'.join(
        f'<div><span>{escape(k)}</span><b>{escape(n)}</b><small>{escape(t)}</small></div>' for n, k, t in d["b_flow"]) + "</div>")


def s4(d: dict) -> None:
    head("해결: 확률 보상 + 누적 성장 보장", "확률을 없애지 않고, 운이 나쁜 유저도 진척을 체감하게 (기획 시안)", b_mock())
    lead("C", "성취감 회복 전략", "기존 확정·교환 장치와 겹치지 않는 부분만")
    html('<div class="fc-sols">' + "".join(sol_card(x, "c") for x in d["solutions"]) + "</div>")
    conclude("확률의 설렘은 그대로, 클리어할 때마다 내 장비 진척은 반드시 쌓인다.")


def sim_html(r: dict) -> str:
    A, B = r["A"], r["B"]

    def row(n, a, b, better_low=False, fmt="{:,.1f}"):
        diff = b - a
        cls = "up" if (diff < 0 if better_low else diff > 0) else ("dn" if diff else "")
        return f'<tr><td>{n}</td><td>{fmt.format(a)}</td><td><b>{fmt.format(b)}</b></td><td class="{cls}">{diff:+,.1f}</td></tr>'
    return (f'<div class="fc-demo"><h4>현행 랜덤 vs 누적 보장 병행 {b_sim()}</h4><div class="fc-cmp"><table>'
            '<tr><th>지표 (이용자 2,000명 가정)</th><th>현행 랜덤</th><th>보장 병행</th><th>차이</th></tr>'
            + row("평균 총보상", A["mean"], B["mean"]) + row("보상 편차 (표준편차)", A["sd"], B["sd"], better_low=True)
            + row("하위 10% 누적 보상", A["p10"], B["p10"]) + row("최저 누적 보상", A["min"], B["min"])
            + row("목표 도달 비율 (%)", r["reach_a"], r["reach_b"]) + '</table></div>'
            f'<div class="fc-m two"><div><small>보상 재화 공급량 변화</small><b class="{"dn" if r["supply_pct"] > 5 else "up"}">{r["supply_pct"]:+.1f}%</b>'
            f'<em>가드레일 ±5% (제안값)</em></div><div><small>1회 기대 보상 (현행)</small><b>{r["expected_per_clear"]:.2f}</b><em>기본 보상 = 1</em></div></div>'
            f'<div class="fc-act">{_insight(r)}</div>'
            '<div class="src">이 시뮬레이터는 C-2 천장 방식 · 가정 기반 시뮬레이션 · 확률·배율은 실제 던파 수치가 아님 · 목표 = 현행 평균 총보상 · 같은 난수열(시드 고정)</div></div>')


def _insight(r: dict) -> str:
    A, B = r["A"], r["B"]
    if B["p10"] < A["p10"]:
        return "<b>천장만으로는 부족</b> · 공급 중립이면 하위 10%가 오히려 줄어든다 → 클리어마다 확정 진척을 주는 <b>C-1</b>을 대표안으로"
    if r["supply_pct"] > 5:
        return "<b>공급 과열 주의</b> · 재화 공급이 가드레일(+5%)을 넘는다 → 공급 중립 조정 또는 K를 늘린다"
    return "<b>불운 구간 축소</b> · 하위 10%·최저 보상이 오르고 편차가 줄어든다 · 공급 변화는 가드레일 안"


def s5(d: dict) -> None:
    head("시뮬레이터·KPI: 운이 나쁜 구간이 얼마나 줄어드는지 본다", "모든 수치는 가정", b_mock())
    sub("현행 랜덤 보상 vs 누적 보장 병행", b_sim())
    c1, c2 = st.columns([1, 1.45], gap="medium")
    with c1:
        anchor("d1")
        n = st.slider("클리어 횟수", 10, 200, 50, 5, key="df_n")
        p = st.slider("고배율 확률 (% · 가정)", 1, 30, 5, key="df_p")
        m = st.slider("고배율 보상 배율 (× · 가정)", 2, 20, 10, key="df_m")
        k = st.slider("누적 보장 조건: K회 연속 미당첨 시 확정 (0 = 없음)", 0, 100, 30, 5, key="df_k")
        neutral = st.checkbox("공급 중립 (평균 총보상을 현행과 같게 조정)", True, key="df_neu")
    r = D.simulate(n, p / 100, m, k, neutral)
    with c2:
        html(sim_html(r))
    sub("KPI", b_mock())
    table(["지표", "구분", "정의"], [[f"<b>{escape(a)}</b>", escape(b), escape(c)] for a, b, c in d["kpis"]])
    with st.expander("실험 설계 · 대조군·실험군 · 성공·중단 기준 (제안값)"):
        st.markdown("\n".join(f"- {x}" for x in d["experiment"]))


def s6(d: dict) -> None:
    c = d["cost"]
    eff = sum(x[1] for x in c["items"])
    head(f"사업적 판단: {d['decision']}", "실제 매출·잔존 자료가 없어 효과를 확정하지 않는다", b_mock())
    sub("대표 전략 한눈에 · C-1 진척 게이지", b_mock())
    table(["단계", "내용"], [
        ["<b>문제</b>", "같은 고난도 클리어에도 보상이 운에 갈려 성장 체감이 약해진다 (가설)"],
        ["<b>근거</b>", "공식: 미카엘라 하드 '플레이 동력 상실' 지적 인정 · 구조: 등급만 확정·부위는 확률 · 유저 근거: <b>자료 대기</b>"],
        ["<b>해결책</b>", "클리어마다 지정 부위 게이지 +1 · 확률 보상 유지 · 교환 불가"],
        ["<b>비용</b>", f"{eff:g}인월 × {c['monthly'] / 1e4:,.0f}만 원 = <b>{won(eff * c['monthly'])}</b> (가정)"],
        ["<b>KPI</b>", "고난도 반복 클리어율 · 누적 목표 달성률 · D30 · 공급량 가드레일 ±5%"],
        ["<b>실험</b>", "계정 단위 무작위 50:50 · 명성 구간 층화 · 교환 불가로 시세 영향 차단"],
        ["<b>사업적 판단</b>", f"<b>{escape(d['decision'])}</b>"]])
    with st.expander("자세히 보기 · 예산 (인월 시나리오) · 리스크와 대응"):
        table(["항목", "공수", "금액"], [[escape(a), f"{b:g}인월", won(b * c["monthly"])] for a, b in c["items"]]
              + [["<b>합계</b>", f"<b>{eff:g}인월</b>", f"<b>{won(eff * c['monthly'])}</b>"]], badge_html=b_sim())
        table(["리스크", "대응"], [[escape(a), f"<b>{escape(b)}</b>"] for a, b in d["risks"]], badge_html=b_interp())
