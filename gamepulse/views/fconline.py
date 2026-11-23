"""FC 온라인 — 축구 게임인가, 주식 게임인가? (사업PM 포트폴리오 · 01~06 탭)

- 01 문제 정의 · 02 실제 유저 근거 · 03 원인 (게임 화면) · 04 해결 전략 · 05 데모·KPI·실험 · 06 실행·예산·리스크
- 사실·가정·시안: data/fconline/fc.json · 계산: gamepulse/sim/fc_sim.py (정적 페이지 JS 와 같은 식)
- 게임 화면: assets/fconline/*.jpg (작성자 캡처 · 내 닉네임·레벨·클럽명·상대 닉네임 블러 · 파일 자체에 적용). 원본은 _originals/ (git 제외)
- 화면 배치: 주제별 갤러리 = 큰 이미지 1장 + 좌우 넘기기 + 번호 + 클릭 확대 (CSS :target · 정적 페이지는 JS 로 보강) · 파일 없으면 슬라이드 생략
- 유저 근거: 원문을 직접 연 글만 집계 · 원문 발췌는 따옴표, 나머지는 '요약' · 작성자 이름 미저장 · 댓글 수·비율 없음
- 데모 2개(A·C)는 입력 칸 첫머리에 fc-anchor 표식 → 정적 페이지에서 JS 조작판으로 교체
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import streamlit as st

from gamepulse.data.overwatch_images import web_jpeg_b64
from gamepulse.sim import fc_sim as F
from gamepulse.ui.components import _md_bold, html
from gamepulse.ui.gallery import gallery_html
from gamepulse.views.overwatch import b_hypo, b_interp, b_mock, b_real, b_sim, badge_legend, head, link, sub, table  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
DATA, ASSETS = ROOT / "data" / "fconline", ROOT / "assets" / "fconline"
SECTIONS = [("01", "문제 정의"), ("02", "실제 유저 근거"), ("03", "원인 · 게임 화면"), ("04", "해결 전략"),
            ("05", "데모·KPI·실험"), ("06", "실행·예산·리스크")]
TAB_LABELS = [f"{n} {t}" for n, t in SECTIONS]
TAB_KEY = "fc_tab"
CREDIT = "작성자 캡처 · 계정 정보 블러 · © NEXON·EA"


@st.cache_data(show_spinner=False)
def load() -> dict:
    return json.loads((DATA / "fc.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _img(name: str, mtime: float, max_w: int = 1600) -> str:
    return web_jpeg_b64(str(ASSETS / name), max_w=max_w)


def gallery(key: str, items: list[list[str]]) -> None:
    """큰 이미지 1장씩 · 좌우 넘기기 · 번호 · 클릭 확대. 파일이 없는 슬라이드는 빼고, 하나도 없으면 영역을 그리지 않는다."""
    slides = []
    for it in items:
        f = ASSETS / it[0]
        if f.is_file():
            img = (f'<img src="data:image/jpeg;base64,{_img(it[0], f.stat().st_mtime)}" alt="실제 게임 화면: {escape(it[1])}" '
                   f'title="{escape(it[1])} · 클릭하면 확대" loading="lazy">')
            slides.append((img, it[2], it[3] if len(it) > 3 else CREDIT))
    out = gallery_html(key, slides)
    if out:
        html(out)


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


def lead(t: str, title: str, line: str = "") -> None:
    html(f'<div class="fc-lead {t.lower()}">{tr(t)}<b>{escape(title)}</b><span>{escape(line)}</span></div>')


def conclude(text: str) -> None:
    html(f'<div class="fc-pm"><span>사업PM 결론</span><b>{escape(text)}</b></div>')


def ev_card(e: dict, cls: str = "") -> str:
    """근거 카드 3요소: 유저 의견 요약 한 줄 · 작성일과 출처 · 사업PM 해석 한 줄."""
    return (f'<div class="fc-ev {cls}"><b>{escape(e["line"])}</b>'
            f'<small>{escape(e["date"])} · {link(e["url"], e["src"] + " ↗")}</small><p>→ {escape(e["pm"])}</p></div>')


# ----------------------------------------------------------------------
def _cover(d: dict) -> None:
    cv = d["cover"]
    html(f'<div class="fc-hero solo"><div class="fc-hero-t"><div class="k">{escape(cv["kicker"])}</div>'
         f'<div class="q" role="heading" aria-level="1">{escape(cv["title"])}</div><div class="s">{escape(cv["subtitle"])}</div></div></div>')


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
    it = d["intro"]   # 게임 소개: 메인 화면 1장은 여기(01)에만
    html(f'<div class="fc-intro"><b>FC 온라인이란?</b><p>{escape(it["line"])}</p><ol>'
         + "".join(f"<li>{tr(t)}{escape(x)}</li>" for t, x in it["topics"]) + "</ol></div>")
    gallery("intro", [it["img"]])
    head("문제: 노력의 가치 · 첫 강화 · 조작의 공정성", "세 문제 모두 '떠나는 계기'가 될 수 있다", b_real())
    gallery("squad", [d["squad_img"]])
    html('<div class="fc-why">'
         '<div><span>A · 구단 가치 · 대표 기획</span><b>8강 카드 그래프 <em>6,260만 → 약 1,900만 BP</em></b><small>작성자 캡처 · 10/24~11/22 시세 그래프</small></div>'
         '<div><span>B · 강화·훈련코치 · 보조 기획</span><b>7→8강 성공 확률 <em>7%</em></b><small>공식 확률 공지 · 인벤 11-05 연속 실패 글</small></div>'
         '<div><span>C · 키보드 vs 패드 · 차별화 기획</span><b>상위 1만 1ON1 키보드 <em>54.6%</em> · 패드 <em>45.4%</em></b><small>공식 데이터센터 11/21 · 분리 매칭 찬반 공존</small></div></div>')


# ======================================================================
# 02 실제 유저 근거
def s2(d: dict) -> None:
    ev, yt = d["evidence"], d["youtube"]
    head("근거: 확인한 원문과 공식 데이터만", "카드 = 유저 의견 요약 · 작성일·출처 · 사업PM 해석 · 사례이지 비율 아님", b_real())
    lead("A", "구단 가치 하락", "화폐 단위 변경(8/20) 영향 사례는 제외")
    html('<div class="fc-evs two">' + "".join(ev_card(e, "a") for e in ev["A"]) + "</div>")
    o = ev["A_official"]
    html(f'<div class="fc-ev off"><span class="t">운영사 공식 대응 · 개인 의견 아님</span><b>{escape(o["line"])}</b>'
         f'<small>{escape(o["date"])} · {link(o["url"], o["src"] + " ↗")}</small><p>→ {escape(o["pm"])}</p></div>')
    lead("B", "강화 실패", "이후 접속 중단 여부는 미확인")
    html('<div class="fc-evs two">' + "".join(ev_card(e, "b") for e in ev["B"]) + "</div>")
    lead("C", "키보드 vs 패드", "공식 데이터센터 + 유튜브 댓글 캡처 10장 요약")
    gallery("c", d["galleries"]["C"])
    urls = {i + 1: v[1] for i, v in enumerate(yt["videos"])}
    cls = {"조작 불만": "kb", "분리 찬성": "kb", "분리 반대": "pad", "제3의 의견": "alt"}
    html('<div class="fc-evs c3">' + "".join(
        f'<div class="fc-ev {cls[g]}"><b>{escape(t)}</b>'
        f'<small>{escape(g)} · {link(urls[s], f"유튜브 {s} ↗")}</small><p>→ {escape(pm)}</p></div>'
        for (g, t, s), pm in zip(yt["cards"], ev["C_pm"])) + "</div>")
    with st.expander("자세히 보기 · 근거 집계표 · 인벤 C 게시글 제목 · 공식 자료 · 자료 한계"):
        x = ev["A_extra"]
        html(f'<div class="fc-ev off"><span class="t">A 보조 참고 · 집계 제외</span><b>{escape(x["line"])}</b>'
             f'<small>{escape(x["date"])} · {link(x["url"], x["src"] + " ↗")}</small><p>→ {escape(x["pm"])}</p></div>')
        table(["트랙", "확인", "자료", "미확인 · 제외"], [[f"<b>{escape(a)}</b>", f"<b>{escape(b)}</b>", escape(c), escape(e)] for a, b, c, e in d["counts"]],
              badge_html=b_real())
        table(["구분", "인벤 게시글 제목 (원문 그대로)", "날짜"],
              [[escape(o["side"]), link(o["url"], o["title"]), escape(o["date"])] for o in d["opinions"] if o["side"] != "강화"], badge_html=b_real())
        table(["날짜", "자료", "확인한 사실", "출처"],
              [[escape(o["date"]), f"<b>{escape(o['title'])}</b>", escape(o["fact"]), link(o["url"], "열기")] for o in d["official"]], badge_html=b_real())
        st.markdown("- 원문 발췌(따옴표)는 직접 연 게시글 문장 그대로 · 나머지는 분석자 요약\n"
                    "- A4는 GPT를 활용한 이용자 분석글이라 사실이 아닌 **이용자 의견**으로만 사용\n"
                    "- 유튜브: 작성자가 캡처한 댓글 10장 요약 · 원문 인용·닉네임·댓글 수·비율 없음 · A·B 근거로 쓰지 않음\n"
                    "- 대표 표본이 아니므로 '많다·적다'를 말하지 않는다")


# ======================================================================
# 03 원인 · 게임 화면
def s3(d: dict) -> None:
    cs = d["c_sides"]
    head("원인: A 자산 급락 · B 늦은 적응 · C 조작 조건 갈등", "인과는 실험으로만 판단", b_hypo())
    lead("A", "열심히 키운 구단, 왜 내 노력의 가치는 떨어질까?", "자산 급락 → 성장 박탈감")
    gallery("a", d["galleries"]["A"])
    pc = d["price_check"]
    with st.expander("자세히 보기 · 가격 사례 검증 (카드 · 시즌 · 강화 · 기준 · 시점 · 단위)"):
        table(pc["head"], [[f"<b>{escape(r[0])}</b>", *[escape(x) for x in r[1:]]] for r in pc["rows"]], badge_html=b_real())
        st.markdown(f"- {pc['note']}")
    lead("B", "강화 한 번의 실패가 떠나는 계기가 될 수 있다", "늦은 코치 세팅 → 초기 이탈")
    gallery("b", d["galleries"]["B"])
    lead("C", "키보드 vs 패드, 같은 경기인데 공정한가?", "조작의 자유인가, 경쟁의 형평성인가?")

    html('<div class="fc-vs2"><div class="kb"><div class="h">⌨️ 키보드 측</div><ul>' + "".join(f"<li>{escape(x)}</li>" for x in cs["keyboard"])
         + '</ul></div><div class="mid">VS</div><div class="pad"><div class="h">🎮 패드 측</div><ul>'
         + "".join(f"<li>{escape(x)}</li>" for x in cs["pad"]) + "</ul></div></div>")
    html(f'<div class="fc-third">{escape(cs["third"])}</div>')


# ======================================================================
# 04 해결 전략
def sol_card(x: dict, t: str) -> str:
    """해결책 카드: 문제 · 변경 · 검증 · 위험 (+ 기존 기능 중복 확인)."""
    rows = "".join(f"<dt>{lab}</dt><dd>{_md_bold(x[k])}</dd>" for lab, k in (("문제", "p"), ("변경", "c"), ("검증", "v"), ("위험", "r")))
    dup = f'<p class="dup">기존 기능 확인 · {escape(x["dup"])}</p>' if x.get("dup") else ""
    return f'<div class="fc-sol {t}"><div class="h"><span>{escape(x["k"])}</span><b>{escape(x["name"])}</b></div><dl>{rows}</dl>{dup}</div>'


def s4(d: dict) -> None:
    ap, so, role = d["a_plan"], d["solutions"], d["role"]
    head("해결: 시세 보장·보상 확대·매칭 분리 대신", "A 대표 · C 차별화 · B 보조 (기획 시안)", b_mock())
    lead("A", f"{role['A']} · 구단 가치 하락 원인 분석 + 보유 자산 기반 재건", "데모는 05 탭")
    html('<div class="fc-flow3">' + '<i>→</i>'.join(f'<div><span>{escape(a)}</span><b>{escape(b)}</b><small>{escape(c)}</small></div>' for a, b, c in d["a_flow"]) + "</div>")
    html('<div class="fc-sols">' + "".join(sol_card(x, "a") for x in so["A"]) + "</div>")
    with st.expander("자세히 보기 · 기존 기능과 차별화 · 경제 부작용 검토"):
        table(["구분", "하는 일", "범위"], [[f"<b>{escape(a)}</b>", escape(b), escape(c)] for a, b, c in ap["diff"]])
        table(["부작용", "대응"], [[escape(a), f"<b>{escape(b)}</b>"] for a, b in ap["side"]], badge_html=b_interp())
    conclude("시세를 보장하는 대신, 다시 성장할 수 있는 경로를 제공한다.")
    lead("C", f"{role['C']} · 통합 매칭 유지 + 키보드 입력 판정 개선", "유저 의견에서 출발한 검증 가설 · 결함으로 확정된 것 아님")
    html('<div class="fc-sols">' + "".join(sol_card(x, "c") for x in so["C"]) + "</div>")
    html(f'<div class="fc-excl">{escape(d["c_excluded"])}</div>')
    with st.expander("자세히 보기 · 실행 순서 · 유저 근거 → 결정"):
        html('<div class="fc-planc"><b>실행 순서</b><ol>' + "".join(f"<li>{escape(x)}</li>" for x in d["c_plan"]) + f'</ol><small>{escape(d["c_not"])}</small></div>')
        html('<div class="fc-facts why">' + "".join(f'<div><span>{escape(a)}</span><b>{escape(b)}</b><small>{escape(c)}</small></div>' for a, b, c in d["c_why"]) + "</div>")
        st.markdown(f"- {d['c_why_note']}")
    conclude("매칭을 나누기보다, 같은 경기에서 납득할 수 있는 조작 환경을 만든다.")
    lead("B", f"{role['B']} · 강화 실패 · 훈련코치 초기 적응", "두 문제를 하나의 원인으로 묶지 않음 · 강화 시뮬레이터 없음")
    html('<div class="fc-sols">' + "".join(sol_card(x, "b") for x in so["B"]) + "</div>")
    with st.expander("자세히 보기 · 훈련코치 현황 · 기존 지원과 중복 확인"):
        table(["구분", "확인한 내용", "출처"], [[f"<b>{escape(a)}</b>", escape(b), escape(c)] for a, b, c in d["b_facts"]], badge_html=b_real())
        table(["기존 제도 · 제안", "역할", "확인"], [[f"<b>{escape(a)}</b>", escape(b), escape(c)] for a, b, c in d["existing"]], badge_html=b_real())
    conclude("보상을 무조건 늘리기보다, 경쟁에 적응하는 시간을 줄인다.")


# ======================================================================
# 05 데모·KPI·실험
def a_demo_html(r: dict, names: list[str]) -> str:
    mx = max((x["loss"] for x in r["rows"]), default=0) or 1
    e = lambda v: bp(v * 1e8)  # noqa: E731
    bars = "".join(
        f'<div class="bar"><span>{escape(names[x["i"]])}</span><div class="t"><i class="mk" style="width:{x["market"] / mx * 100:.1f}%"></i>'
        f'<i class="own" style="width:{x["own"] / mx * 100:.1f}%"></i></div><em class="{"sw" if x["swap"] else ""}">{x["share"]:.0f}% · '
        f'{"교체" if x["swap"] else "유지"}{" (추천)" if x["rec"] else ""}</em></div>' for x in r["rows"])
    res = (f'남은 BP {e(r["left"])}' if r["left"] >= 0 else f'<span class="dn">부족 {e(r["gap"])}</span>')
    return (f'<div class="fc-demo"><h4>구단 가치 분석·재건 {b_sim()}</h4><div class="fc-m">'
            f'<div><small>구단 가치</small><b>{e(r["now"])}</b><em class="dn">−{r["drop_pct"]:.0f}% · 고점 {e(r["peak"])}</em></div>'
            f'<div><small>A-1 · 시장 요인 · 개별 요인</small><b>{r["market"] / r["loss"] * 100 if r["loss"] else 0:.0f}% · {r["own"] / r["loss"] * 100 if r["loss"] else 0:.0f}%</b><em>하락분 구성</em></div>'
            f'<div><small>고점 회복에 필요한 상승</small><b class="up">+{r["recover_pct"]:.0f}%</b><em>시세 회복은 보장 불가</em></div></div>'
            f'<div class="fc-bars"><div class="lg"><i class="mk"></i>시장 요인 <i class="own"></i>개별 요인 · 막대 = 선수별 하락액</div>{bars}</div>'
            f'<div class="fc-m two"><div><small>A-2 · ① 전원 유지</small><b>{e(r["now"])}</b><em>지출 0 · 경기력 그대로</em></div>'
            f'<div><small>A-2 · ② 선택안 (교체 {r["n_swap"]}명)</small><b>{e(r["after"])}</b><em>순비용 {e(r["net"])} · {res}</em></div></div>'
            f'<ol class="fc-path"><li><b>진단</b> 개별 하락이 큰 선수 {r["n_rec"]}명 (추천 교체)</li>'
                        f'<li><b>교체</b> 판매 수익 {e(r["sale"])} → 대체 비용 {e(r["cost"])}</li>'
            f'<li><b>이벤트 연계</b> {"부족분 " + e(r["gap"]) + " → 진행 중 이벤트·패스 보상으로 채울 단계 목표" if r["gap"] > 0 else "보유 BP 안에서 가능 · 추가 목표 없음"} (BP 지급 아님)</li></ol>'
            '<div class="src">가상 선수 · 모든 값은 가정 · 대체 비용 = 고점 × (1 − 시장 하락률)</div></div>')


C_EXP = {"c1": ("C-1 · 대각선·연속 입력 성공률", 78, 86, "입력 성공률"),
         "c2": ("C-2 · 입력-패스 방향 일치율", 84, 88, "방향 일치율")}
VERDICT = {"확대": "격차가 목표만큼 줄고 패드·매칭 지표 악화 없음 → 적용 범위 확대",
           "수정": "격차는 줄었지만 목표(30%) 미달 → 판정 조건 수정 후 재실험",
           "중단": "격차가 줄지 않거나 패드·매칭 지표 악화 → 중단 · 의견은 수비 AI·밸런스 과제로"}


def c_exp_html(r: dict, metric: str) -> str:
    def row(n, a, b, cls=""):
        return f'<tr class="{cls}"><td>{n}</td><td>{a}</td><td><b>{b}</b></td></tr>'
    v = r["verdict"]
    return (f'<div class="fc-demo c"><h4>실험 판정 · {escape(metric)} {b_sim()}</h4><div class="fc-cmp"><table>'
            '<tr><th>구분</th><th>현행 (대조군)</th><th>실험군</th></tr>'
            + row("키보드", f'{r["kb0"]:.0f}%', f'{r["kb1"]:.0f}%') + row("패드", f'{r["pad0"]:.0f}%', f'{r["pad1"]:.0f}%')
            + row("격차 (패드 − 키보드)", f'{r["gap0"]:.0f}%p', f'{r["gap1"]:.0f}%p', "on")
            + f'</table></div><div class="fc-m two"><div><small>격차 축소율 (목표 30% · 예시)</small><b class="{"up" if r["cut"] > 0 else "dn"}">{r["cut"]:.0f}%</b></div>'
            f'<div><small>가드레일 · 패드 −1%p · 포기율 +0.5%p</small><b class="{"up" if r["guard"] else "dn"}">{"통과" if r["guard"] else "위반"}</b></div></div>'
            f'<div class="fc-act {"rec" if v == "확대" else ""}"><b>판정: {v}</b> · {VERDICT[v]}</div>'
            '<div class="src">모든 값은 가정 · 실제 유저 데이터 아님 · 매칭은 통합 그대로 (분리 매칭은 최종안에서 제외)</div></div>')


def s5(d: dict) -> None:
    head("데모·KPI: 직접 계산하고, 판단 기준을 정한다", "수치는 모두 가정 · 실제 성과 아님", b_mock())
    ad = d["a_demo"]
    sub("A · 구단 가치 분석·재건 시뮬레이터", b_sim())
    c1, c2 = st.columns([1, 1.45], gap="medium")
    with c1:
        anchor("a1")
        mk = st.slider("시장 전체 하락률 (% · 가정)", 0, 80, ad["market"], key="fc_a_mk")
        drops = [st.slider(f"{nm} 하락률 (고점 {pk:g}억)", 0, 90, int(round((1 - now / pk) * 100)), key=f"fc_a_p{i}")
                 for i, (nm, pk, now) in enumerate(ad["players"])]
        hold = st.number_input("보유 BP (억 · 가정)", 0.0, 1000.0, float(ad["hold"]), step=0.1, key="fc_a_hold")
        fee = st.slider("판매 수수료율 (% · 가정)", 0, 60, ad["fee"], key="fc_a_fee")
    players = [(pk, pk * (1 - dr / 100)) for (_, pk, _), dr in zip(ad["players"], drops)]
    names = [p[0] for p in ad["players"]]
    rec = [x["rec"] for x in F.rebuild(players, mk / 100, hold, fee / 100)["rows"]]
    with c1:
        pick = st.multiselect("A-2 · 교체할 선수 (기본값 = 추천)", names, default=[n for n, x in zip(names, rec) if x], key="fc_a_swap")
    r = F.rebuild(players, mk / 100, hold, fee / 100, [n in pick for n in names])
    with c2:
        html(a_demo_html(r, names))
    sub("C · 조작 개선 실험 비교 (통합 매칭 유지)", b_sim())
    c1, c2 = st.columns([1, 1.45], gap="medium")
    with c1:
        anchor("c5")
        ex = st.radio("실험", list(C_EXP), format_func=lambda k: C_EXP[k][0], key="fc_c5_ex")
        kb0 = st.slider("키보드 현행 (% · 가정)", 40, 100, C_EXP[ex][1], key=f"fc_c5_kb_{ex}")
        pad0 = st.slider("패드 현행 (% · 가정)", 40, 100, C_EXP[ex][2], key=f"fc_c5_pad_{ex}")
        up = st.slider("실험 후 키보드 변화 (+%p · 가정)", 0, 15, 4, key="fc_c5_up")
        pc = st.slider("실험 후 패드 변화 (%p · 가정)", -5, 5, 0, key="fc_c5_pc")
        qc = st.slider("매칭 포기율 변화 (%p · 가정)", -1.0, 2.0, 0.0, 0.1, key="fc_c5_qc")
    with c2:
        html(c_exp_html(F.control_exp(kb0, pad0, up, pc, qc), C_EXP[ex][3]))
    sub("KPI", b_mock())
    names = {"A": "구단 가치", "B": "강화·훈련코치", "C": "키보드 vs 패드"}
    html('<div class="fc-kpi">' + "".join(f'<div class="{t.lower()}"><div class="h">{tr(t)} {names[t]}</div>'
                                          + "".join(f"<p><b>{escape(a)}</b></p>" for a in d["kpis"][t]) + "</div>" for t in ("A", "B", "C")) + "</div>")
    with st.expander("실험 설계 · 대조군·실험군 · 성공·중단 기준 (목표·예시)", expanded=False):
        table(["트랙", "대조군", "실험군", "대상", "성공 기준", "중단 기준"],
              [[tr(a), escape(b), f"<b>{escape(c)}</b>", escape(e), escape(f), f'<span class="dn">{escape(g)}</span>'] for a, b, c, e, f, g in d["experiments"]], badge_html=b_mock())
        table(["결과", "기준"], [[f"<b>{escape(a)}</b>", escape(b)] for a, b in d["stop_rules"]])
        st.markdown("**교란 요인 통제**\n" + "\n".join(f"- {x}" for x in d["confounders"])
                    + "\n- 목표치는 모두 제안값 · 실제 기준값은 파일럿 전 과거 로그로 확정")


# ======================================================================
# 06 실행·예산·리스크
def budget_rows(d: dict) -> tuple[list[list[str]], float, float]:
    mc = d["cost"]["monthly_cost_per_person"]
    rows, tot, eff_t = [], 0.0, 0.0
    for name, eff, reuse, new in d["cost"]["items"]:
        tot += eff * mc
        eff_t += eff
        rows.append([f"<b>{escape(name)}</b>", f"{eff:g}인월", f"{mc / 1e4:,.0f}만", f"<b>{won(eff * mc)}</b>", escape(reuse), escape(new)])
    return rows, tot, eff_t


def s6(d: dict) -> None:
    head("실행: 1차 C → 2차 A → 3차 B", "예산은 실제 견적이 아닌 기획 추정치", b_mock())
    html('<ol class="fc-order">' + "".join(f'<li class="{t.lower()}"><span>{n}</span>{tr(t)}<b>{escape(k)}</b><small>{escape(w)}</small></li>'
                                           for n, t, k, w in d["priority"]) + "</ol>")
    sub("예산 (기획 추정치)", b_sim())
    rows, tot, eff_t = budget_rows(d)
    mc = d["cost"]["monthly_cost_per_person"]
    rows.append(["<b>합계</b>", f"<b>{eff_t:g}인월</b>", "", f"<b>{won(tot)}</b>", "재화 지급 0원", ""])
    table(["항목", "공수", "단가 (1인월)", "금액", "기존 기능 활용", "신규 개발"], rows)
    st.caption(f"검산: {eff_t:g}인월 × {mc / 1e4:,.0f}만 원 = {won(eff_t * mc)} (단가는 가정 · 다른 프로젝트와 같은 기준)")
    sub("리스크와 대응", b_interp())
    table(["리스크", "대응"], [[escape(a), f"<b>{escape(b)}</b>"] for a, b in d["risks"]])
    html('<div class="fc-final"><b>A 성장 경험 회복 · B 초기 적응 개선 · C 통합 매칭 유지와 조작 환경 개선</b></div>')
