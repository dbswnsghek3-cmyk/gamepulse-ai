"""던전앤파이터 — 어려운 던전을 클리어했는데, 왜 성장했다는 느낌이 없을까? (사업PM 포트폴리오 · 01~06 탭)

- 01 문제 정의 (게임 소개 · 2026 시즌 상황 · 핵심 질문) · 02 유저 의견·검증 한계 · 03 원인 (현상 → 근거 → 체감 → 가설)
  · 04 개선안 (A 성장 가치 · B 불운 진척 게이지 · C 다음 시즌 기대) · 05 시뮬레이터·KPI·실험 · 06 실행 로드맵·사업적 판단
- 사실·가설·시안: data/dnf/dnf.json · 계산: gamepulse/sim/dnf_sim.py (정적 페이지 JS 와 같은 난수열·같은 식)
- 근거 원본: DNF_GamePulse_OneShot/01_original_evidence (공개 금지 · .gitignore) → 공개용은 assets/dnf/evidence (아이디·아바타 블러, 문구 원문 그대로)
- 친구 카톡은 개인정보가 있어 이미지를 공개하지 않고 원문 문구만 인용 · 1명의 정성 인터뷰로만 표시
- 디자인은 FC 온라인 컴포넌트 재사용 · 표지는 던파 전용 빨간색 + 로고
"""

from __future__ import annotations

import base64
import json
from html import escape
from pathlib import Path

import streamlit as st

from gamepulse.data.overwatch_images import web_jpeg_b64
from gamepulse.sim import dnf_sim as D
from gamepulse.ui.components import html
from gamepulse.ui.gallery import gallery_html
from gamepulse.views.fconline import conclude, lead, sol_card, tr, won
from gamepulse.views.overwatch import b_hypo, b_interp, b_mock, b_real, b_sim, badge_legend, head, link, sub, table

ROOT = Path(__file__).resolve().parents[2]
DATA, ASSETS = ROOT / "data" / "dnf", ROOT / "assets" / "dnf"
SECTIONS = [("01", "문제 정의"), ("02", "유저 의견·한계"), ("03", "원인"), ("04", "개선안"), ("05", "시뮬레이터·KPI"), ("06", "로드맵·판단")]
TAB_LABELS = [f"{n} {t}" for n, t in SECTIONS]
TAB_KEY = "df_tab"


@st.cache_data(show_spinner=False)
def load() -> dict:
    return json.loads((DATA / "dnf.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _img(rel: str, mtime: float) -> str:
    return web_jpeg_b64(str(ASSETS / rel), max_w=1400)


@st.cache_data(show_spinner=False)
def _png(rel: str, mtime: float) -> str:
    return base64.b64encode((ASSETS / rel).read_bytes()).decode()


def gallery(key: str, items: list[list[str]], folder: str = "evidence") -> None:
    slides = []
    for f, cap, credit in items:
        p = ASSETS / folder / f
        if p.is_file():
            slides.append((f'<img src="data:image/jpeg;base64,{_img(f"{folder}/{f}", p.stat().st_mtime)}" alt="{escape(cap)}" loading="lazy">', cap, credit))
    out = gallery_html(key, slides)
    if out:
        html(out)


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


def vlink(d: dict, v: str, extra: str = "") -> str:
    name, _, url = d["videos"][v]
    return link(url, f"{name} ↗") + (f" · {escape(extra)}" if extra else "")


def render() -> None:
    d = load()
    cv = d["cover"]
    lp = ASSETS / cv["logo"]
    logo = (f'<img class="df-logo" src="data:image/png;base64,{_png(cv["logo"], lp.stat().st_mtime)}" alt="던전앤파이터 로고">'
            if lp.is_file() else "")
    html('<div class="gp-ow-page"></div>')
    html(f'<div class="fc-hero solo dnf"><div class="df-hero-in"><div class="fc-hero-t"><div class="k">{escape(cv["kicker"])}</div>'
         f'<div class="q" role="heading" aria-level="1">{escape(cv["title"])}<br>{escape(cv["title2"])}</div>'
         f'<div class="s">{escape(cv["subtitle"])}</div></div>{logo}</div><div class="df-credit">{escape(cv["logo_credit"])}</div></div>')
    i = tab_nav()
    badge_legend()
    html(f'<div class="ow-pane-mark" data-tab="{SECTIONS[i][0]}"></div>')
    [s1, s2, s3, s4, s5, s6][i](d)
    st.caption(f"{d['disclaimer']} · 자료 확인일 {d['checked_at']}")


# ======================================================================
def fig(im: dict, cls: str = "") -> None:
    """공식 이미지 1장을 크게 (최대 1100px) · 출처 링크."""
    p = ASSETS / im["file"]
    if not p.is_file():
        html(f'<div class="df-wait">실제 화면 확보 필요 · {link(im["url"], "공식 자료 ↗")}</div>')
        return
    html(f'<figure class="df-fig {cls}"><img src="data:image/jpeg;base64,{_img(im["file"], p.stat().st_mtime)}" alt="{escape(im["cap"])}">'
         f'<figcaption><b>{escape(im["cap"])}</b> · {link(im["url"], im["credit"] + " ↗")}</figcaption></figure>')


def s1(d: dict) -> None:
    it = d["intro"]
    fig(d["hero_img"], "hero")
    html(f'<div class="fc-intro dnf"><b>던전앤파이터란?</b><p>{escape(it["line"])}</p></div>')
    html('<div class="fc-evs">' + "".join(
        f'<div class="fc-ev off"><span class="t">{escape(k)} · 공식·보도</span><b>{escape(v)}</b><small>{link(u, s + " ↗")}</small></div>'
        for k, v, s, u in it["season"]) + "</div>")
    html(f'<div class="fc-pm"><span>핵심 질문</span><b>{escape(it["question"])}</b></div>')
    head("문제: 클리어는 했는데 성장이 쌓이지 않는다", "세 문제 모두 가설 · 근거는 02 탭", b_hypo())
    html('<div class="fc-why">' + "".join(
        f'<div><span>{escape(k)} · {escape(n)}</span><b>{escape(p)}</b><small>{escape(s)}</small></div>' for k, n, p, s in d["problems"]) + "</div>")


def s2(d: dict) -> None:
    head("근거: 핵심 유저 의견 5개 → 사업PM 해석 → 개선 전략", "원문 발췌는 문구를 바꾸지 않음 · 아이디 비공개 · 정성 근거", b_real())
    html(f'<div class="fc-cav">{escape(d["opinion_scope"])}</div>')
    sols = {x["k"]: x["name"] for x in d["solutions"]}
    cards = []
    for o in d["key_opinions"]:
        qs = "".join(
            f'<div class="q"><q>{escape(t)}</q><small>원문 발췌 · '
            + (f'{escape(cap)} (1명 · 통계 아님)' if v == "friend" else f'유튜브 댓글 · {vlink(d, v, cap)}')
            + '</small></div>' for t, v, cap in o["quotes"])
        merged = f'<em class="mg">{escape(o["merged"])}</em>' if o["merged"] else ""
        cards.append(f'<div class="df-op {o["sol"].lower()}"><div class="h"><span class="no">{o["no"]}</span><b>{escape(o["theme"])}</b>{merged}'
                     f'<span class="to">→ 개선안 {o["sol"]}</span></div>{qs}<div class="pm"><span>사업PM 해석</span>{escape(o["pm"])}</div></div>')
    html('<div class="df-ops">' + "".join(cards) + "</div>")
    sub("핵심 의견 → 사업PM 해석 → 개선 전략", b_interp())
    links = {"A": "①", "B": "②·③", "C": "④·⑤"}
    table(["핵심 의견", "사업PM 해석", "개선 전략 (04 탭)"], [
        [links["A"], "받은 성장의 의미가 다음 시즌으로 이어지지 않는다", f"<b>A. {escape(sols['A'])}</b>"],
        [links["B"], "운이 나쁜 클리어에는 쌓이는 것이 없다", f"<b>B. {escape(sols['B'])}</b>"],
        [links["C"], "시즌제는 수용 · 반복 피로와 다음 시즌 기대 부족", f"<b>C. {escape(sols['C'])}</b>"]])
    conclude("유저 의견은 문제를 찾는 출발점 · 효과 판단은 로그와 실험(05 탭)으로 한다.")
    with st.expander("자세히 보기 · 원문 캡처 (아이디·아바타 블러) · 지인 인터뷰 원문 · 보조 자료 · 검증 한계"):
        gallery("dfev", d["evidence_images"])
        f = d["friend"]
        st.markdown(f"**지인 인터뷰 · {f['label']}**")
        table(["상황", "원문", "해석 (분석자)"], [[escape(a), f"<b>“{escape(b)}”</b>", escape(c)] for a, b, c in f["items"]])
        st.caption(f["note"])
        st.markdown("**보조 배경 자료 (영상 제작자 2차 자료 · 원자료 미확인)**")
        gallery("dfsec", d["secondary"])
        st.markdown("\n".join(f"- {x}" for x in d["limits"]))
        st.markdown("\n".join(f"- {n} · [{t}]({u})" for n, t, u in d["videos"].values()))


def _chain(rows: list[tuple[str, str, str]]) -> None:
    """원인 → 기존 시스템의 한계 → 차별화 → 검증: 한 줄씩 (카드 나열 대신)."""
    html('<ol class="df-chain">' + "".join(f'<li><span>{escape(k)}</span><p>{escape(t)} <small>{escape(src)}</small></p></li>' for k, t, src in rows) + "</ol>")


def s3(d: dict) -> None:
    head("원인: 운이 나쁜 클리어는 '쌓이는 것'이 없고, 다음 시즌을 기다릴 이유가 약하다", "원인 → 기존 시스템의 한계 → 차별화 → 검증", b_hypo())
    lead("B", "고난도 보상과 성취감 (핵심)", "구조는 공식 사실 · 체감과 이탈은 가설")
    fig(d["reward_img"], "sm")
    _chain([("원인", "상급 던전은 주 2개 클리어 보상 · 보상은 기대 배율에 따른 확률 → 클리어해도 결과가 운에 갈린다", "공식 가이드"),
            ("기존 한계", "기대 배율은 '평균'을 올릴 뿐, 이번 클리어의 운 나쁜 결과는 보정하지 않는다 · 조율의 경계는 별도 재료가 필요", "공식 가이드 · 분석자 비교"),
            ("체감", "'레어 장비 4~5개'면 의욕이 떨어진다는 댓글 (핵심 의견 ②)", "유저 의견 · 정성"),
            ("검증", "불운한 클리어가 반복된 계정의 다음 주 재도전율이 낮은가 → 로그로 확인 (가설)", "검증 필요")])
    lead("A", "시즌 성장 가치", "시즌제 자체가 아니라 '받은 성장의 수명'")
    fig(d["equip_img"])
    _chain([("원인", "시즌마다 최상위 장비가 바뀐다 · 유일 장비는 다음 시즌에도 위상 유지 예고", "공식 · 방송 보도"),
            ("기존 한계", "무기고·통합 변환은 장비·세트를 보존하지만, '내 시즌을 돌아보고 다음 목표를 정하는' 화면은 확인 못함", "공식 · 분석자 비교"),
            ("체감", "이벤트로 받은 장비가 다음 시즌에 의미를 잃는다 (핵심 의견 ①)", "유저 의견 · 정성"),
            ("검증", "시즌 전환 후 복귀 계정의 D7·D30과 첫 목표 달성률 비교 (가설)", "검증 필요")])
    lead("C", "다음 시즌 기대", "시즌 리셋은 수용 · 기대할 이야기와 반복 피로가 과제")
    html('<div class="fc-cav">유저 근거: 핵심 의견 ④·⑤ · 지인 인터뷰는 스토리 쪽 의견에 동의하지 않음 → 의견이 갈리는 지점으로 남겨 둔다</div>')
    with st.expander("자세히 보기 · 확인한 공식 자료"):
        table(["날짜", "자료", "확인한 사실"], [[escape(o["date"]), link(o["url"], o["src"]), escape(o["fact"])] for o in d["official"]], badge_html=b_real())


def s4(d: dict) -> None:
    head("개선안: 확률은 그대로, 성장과 기대는 쌓이게", "기존 공식 장치와 겹치지 않는 부분만 (기획 시안)", b_mock())
    html('<div class="fc-sols">' + "".join(sol_card(x, x["k"].lower()) for x in d["solutions"][:2]) + "</div>")
    html('<div class="fc-sols one">' + sol_card(d["solutions"][2], "c") + "</div>")
    sub("B 불운 진척 게이지 · 화면 시안", b_mock())
    html('<div class="df-mock"><span class="tag">GamePulse AI 제안 시안 · 실제 게임 화면 아님</span>'
         '<h5>상급 던전 클리어 결과</h5><div class="res"><span>이번 보상: 기대 배율 미만</span><b>진척 게이지 +1</b></div>'
         '<div class="bar"><i></i></div><div class="cap"><span>불운 진척도 7 / 10</span><span>10칸이 차면 다음 보상 = 기대 배율 하한 보장</span></div>'
         '<div class="note">확률·고배율은 그대로 · 연속 실패가 아니어도 쌓임 · 교환 불가 · 주간 상한 · 수치는 예시</div></div>')
    with st.expander("자세히 보기 · 기존 공식 장치와 중복 확인"):
        fig(d["convert_img"], "sm")
        table(["기존 장치", "하는 일", "B 불운 진척 게이지와의 차이"], [[f"<b>{escape(a)}</b>", escape(b), escape(c)] for a, b, c in d["existing"]], badge_html=b_real())
    conclude("운의 재미는 남기고, 플레이한 만큼의 성취는 반드시 쌓이게 한다.")


def sim_html(r: dict, note: str) -> str:
    A, B, C = r["A"], r["B"], r["C"]

    def f(x):
        return f"{x:,.1f}"

    def row(n, a, b, c, better_low=False):
        def cell(v):
            d = v - a
            cls = "up" if (d < 0 if better_low else d > 0) else ("dn" if abs(d) > 1e-9 else "")
            return f'<td class="{cls}"><b>{f(v)}</b> <small>({d:+,.1f})</small></td>'
        return f"<tr><td>{n}</td><td>{f(a)}</td>{cell(b)}{cell(c)}</tr>"
    sup = lambda v: f'<b class="{"dn" if abs(v) > 5 else "up"}">{v:+.1f}%</b>'  # noqa: E731
    return (f'<div class="fc-demo"><h4>현행 vs B 불운 진척 게이지 (제안) vs 천장 (비교) {b_sim()}</h4><div class="fc-cmp"><table>'
            '<tr><th>지표 (이용자 2,000명 · 가정)</th><th>현행</th><th>B 불운 진척 게이지</th><th>천장 (비교)</th></tr>'
            + row("하위 10% 누적 보상", A["p10"], B["p10"], C["p10"]) + row("최저 누적 보상", A["min"], B["min"], C["min"])
            + row("평균 총보상", A["mean"], B["mean"], C["mean"]) + row("보상 편차 (표준편차)", A["sd"], B["sd"], C["sd"], True)
            + f'<tr><td>보상 재화 공급량 변화</td><td>—</td><td>{sup(r["supply_b"])}</td><td>{sup(r["supply_c"])}</td></tr>'
            + f'<tr><td>고배율 보상 크기 (×)</td><td>{r["mult"]:g}</td><td><b>{r["jack_b"]:.1f}</b></td><td><b>{r["jack_c"]:.1f}</b></td></tr>'
            + '</table></div>'
            f'<div class="fc-act">{_insight(r)}</div>'
            f'<div class="src">{escape(note)}</div></div>')


def _insight(r: dict) -> str:
    A, B, C = r["A"], r["B"], r["C"]
    if B["p10"] < A["p10"]:
        return "<b>B도 하위 10%가 줄어듦</b> · 이 설정은 개선안으로 쓰지 않는다"
    msg = (f"<b>B 불운 진척 게이지</b> · 하위 10% {A['p10']:.1f} → {B['p10']:.1f} · 공급 {r['supply_b']:+.1f}% · 고배율 ×{r['jack_b']:.1f} "
           + ("→ 가드레일(±5%) 안에서 운이 나쁜 구간만 보완" if abs(r["supply_b"]) <= 5 else "→ 공급이 가드레일(±5%)을 넘음: K를 늘리거나 공급 중립을 켠다"))
    if abs(r["supply_c"]) > 5:
        msg += f"<br><b>천장 (반례)</b> · 공급 {r['supply_c']:+.1f}% → 재화 공급 과열"
    elif r["jack_c"] < r["mult"] * 0.8:
        msg += f"<br><b>천장 (반례)</b> · 공급을 맞추려면 고배율이 ×{r['mult']:g} → ×{r['jack_c']:.1f}로 줄어 확률 보상의 설렘이 크게 약해짐"
    return msg


def s5(d: dict) -> None:
    head("시뮬레이터·KPI: 운이 나쁜 구간이 얼마나 줄어드는지 본다", "모든 수치는 가정 · 실제 던파 확률이 아님", b_mock())
    sub("대표 KPI 4개", b_mock())
    html('<div class="df-kpi">' + "".join(f'<div><span>{escape(t)}</span><b>{escape(n)}</b><small>{escape(x)}</small></div>' for t, n, x in d["kpi_main"]) + "</div>")
    sub("B 불운 진척 게이지 시뮬레이션 · 천장 방식과 비교", b_sim())
    c1, c2 = st.columns([1, 1.6], gap="medium")
    with c1:
        anchor("d1")
        n = st.slider("주간 클리어 누적 횟수", 10, 200, 50, 5, key="df_n")
        p = st.slider("기대 이상 결과 확률 (% · 가정)", 1, 30, 5, key="df_p")
        m = st.slider("기대 이상 결과의 보상 배율 (× · 가정)", 2, 20, 10, key="df_m")
        k = st.slider("게이지 칸 수 K: 기대 미만 클리어 K번마다 1회 하한 보장 (0 = 없음)", 0, 50, 10, 5, key="df_k")
        neutral = st.checkbox("공급 중립 (고배율 보상 크기를 줄여 평균을 현행과 같게)", False, key="df_neu")
    r = D.simulate(n, p / 100, m, k, neutral)
    with c2:
        html(sim_html(r, d["sim_note"]))
    with st.expander("자세히 보기 · 개선안별 전체 KPI · 실험 설계 (대조군·실험군 · 성공·롤백 기준)"):
        table(["개선안", "KPI"], [[tr(a), escape(b)] for a, b in d["kpis"]])
        st.markdown("\n".join(f"- {x}" for x in d["experiment"]))
        st.caption("이전 버전의 '평균 공급을 맞추려고 모든 이용자 보상을 일괄 축소'하는 방식은 하위 10%를 59.0 → 56.4로 낮춰 폐기 · "
                   "공급 중립은 고배율 보상 크기만 조정하도록 바꿈")


def s6(d: dict) -> None:
    c = d["cost"]
    eff = sum(x[1] for x in c["items"])
    head(f"사업적 판단: {d['decision']}", "실제 매출·잔존 자료가 없어 효과를 확정하지 않는다", b_mock())
    sub("실행 로드맵", b_mock())
    html('<ol class="fc-order">' + "".join(f'<li class="c"><span>{escape(w)}</span><b>{escape(k)}</b><small>{escape(x)}</small></li>'
                                           for w, k, x in d["roadmap"]) + "</ol>")
    sub("대표 전략 한눈에 · B 불운 진척 게이지", b_mock())
    table(["단계", "내용"], [
        ["<b>문제</b>", "어려운 던전·레이드를 클리어해도 결과가 운에 갈려 노력이 체감되지 않는다 (가설)"],
        ["<b>근거</b>", "공식: 상급 던전 기대 보상 배율·확률 보상 · 미카엘라 하드 동력 상실 지적 인지 · 유저: 핵심 의견 ②·③ (유튜브 댓글 2건) · 지인 인터뷰 1명"],
        ["<b>해결책</b>", "기대 미만 클리어가 K번 쌓이면 1회 기대 배율 하한 보장 (연속일 필요 없음) · 확률·고배율은 그대로 · 교환 불가 · 천장 방식은 공급 과열로 제외"],
        ["<b>비용</b>", f"{eff:g}인월 × {c['monthly'] / 1e4:,.0f}만 원 = <b>{won(eff * c['monthly'])}</b> (전체 · 가정)"],
        ["<b>KPI</b>", "주간 고난도 재도전율 · 보상 만족도 · 하위 10% 누적 보상 · 가드레일: 재화 공급량 ±5%"],
        ["<b>실험</b>", "계정 10% 무작위 · 명성 구간 층화 · 롤백 기준 사전 합의"],
        ["<b>사업적 판단</b>", f"<b>{escape(d['decision'])}</b>"]])
    with st.expander("자세히 보기 · 예산 (인월 시나리오) · 리스크와 대응"):
        table(["항목", "공수", "금액"], [[escape(a), f"{b:g}인월", won(b * c["monthly"])] for a, b in c["items"]]
              + [["<b>합계</b>", f"<b>{eff:g}인월</b>", f"<b>{won(eff * c['monthly'])}</b>"]], badge_html=b_sim())
        table(["리스크", "대응"], [[escape(a), f"<b>{escape(b)}</b>"] for a, b in d["risks"]], badge_html=b_interp())
