"""PUBG: NEW START — 신규 유저 정착(TRACK A) · 성장형 스킨 BM(TRACK B) 사업PM 포트폴리오.

구성 (오버워치 RE:START 와 같은 01~06 탭 · 같은 배지·차트 카드·색 규칙)
- 01 문제·결론 · 02 실제 근거 · 03 원인 가설 · 04 해결책 데모 · 05 KPI·A/B 테스트 · 06 실행·사업 제안
- 공식 사실·가정값·시연 데이터는 data/pubg/newstart.json, 실제 유저 의견은 data/pubg/opinions.csv(Steam 리뷰 직접 분류),
  공개 지표는 data/pubg/steam_monthly.csv. 계산은 gamepulse/sim/newstart_sim.py 한 곳에서 한다.
- TRACK A = 블루, TRACK B = 코랄. 두 트랙을 같은 이탈 원인으로 묶지 않는다.
- 01 첫 화면: 로고(assets/pubg/brand) · 대표 화면(assets/pubg/drop.png) · 신규 정착 80% · BM 20% 비중
- PUBG 실제 게임 화면은 직접 캡처한 assets/pubg/*.png (다른 플레이어 닉네임 가림 사본)만 표시한다. 원본은 _originals/ (git 제외).
  newstart.json screens[].ready=true 인 것만 표시, 없으면 '캡처 대기' 자리 (임의 이미지 생성 금지).
"""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gamepulse.data.overwatch_images import web_jpeg_b64
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


SCREENS: dict[str, dict] = {}   # newstart.json 'screens' (render 에서 채움)
ASSETS = Path(__file__).resolve().parents[2] / "assets" / "pubg"


def slot_html(key: str) -> str:
    """실제 게임 화면 자리 (캡처 대기 카드)."""
    sc = SCREENS.get(key, {"title": key, "where": "", "file": f"{key}.png"})
    return (f'<div class="pg-slot"><span class="pg-slot-k">실제 게임 화면 · 캡처 대기</span><b>{escape(sc["title"])}</b>'
            f'<small>캡처 위치 · {escape(sc["where"])}</small><small class="f">assets/pubg/{escape(sc["file"])}</small></div>')


@st.cache_data(show_spinner=False)
def _jpeg_b64(path: str, mtime: float) -> str:
    return web_jpeg_b64(path, max_w=1400)


def shot(key: str) -> None:
    """캡처가 들어오고 닉네임 가림 처리 후 ready=true 로 바꾼 파일만 표시. 그 전에는 자리만.
    오버워치와 같은 '실제 게임 화면' 프레임(HTML) → 정적 내보내기(docs/)에도 그대로 실린다."""
    sc = SCREENS.get(key, {})
    path = ASSETS / sc.get("file", "-")
    if sc.get("ready") and path.is_file():
        t = escape(sc.get("title", ""))
        html(f'<figure class="ow-shot"><div class="ow-shot-bar"><span class="ow-shot-tag">실제 게임 화면</span>{t}</div>'
             f'<div class="ow-shot-img"><img src="data:image/jpeg;base64,{_jpeg_b64(str(path), path.stat().st_mtime)}" '
             f'alt="{t}" loading="lazy"></div></figure>')
    else:
        html(slot_html(key))


def compare(real_key: str, real_title: str, mock_title: str, mock_fn) -> None:
    """오버워치와 같은 '실제 화면(왼쪽) ↔ 기획 시안(오른쪽)' 비교 배치."""
    left, right = st.columns([1, 1], gap="medium")
    with left:
        html(f'<div class="ow-colh real">현재 · {escape(real_title)}</div>')
        shot(real_key)
    with right:
        html(f'<div class="ow-colh mock">제안 · {escape(mock_title)}</div>')
        mock_fn()


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
@st.cache_data(show_spinner=False)
def _png_b64(path: str, mtime: float) -> str:
    import base64
    return base64.b64encode(Path(path).read_bytes()).decode()


def _cover(ns: dict) -> None:
    """탭 위에 항상 보이는 첫 화면: 로고 · 제목 · 대표 게임 화면 + '문제 → A1 → (서브) B1' 한 줄."""
    cv = ns["cover"]
    logo, drop = ASSETS / "brand" / "pubg_logo.png", ASSETS / "drop.png"
    logo_html = (f'<img class="pg-logo" src="data:image/png;base64,{_png_b64(str(logo), logo.stat().st_mtime)}" alt="PUBG: BATTLEGROUNDS 로고">'
                 if logo.is_file() else "")
    img_html = (f'<figure class="pg-cover-r"><img src="data:image/jpeg;base64,{_jpeg_b64(str(drop), drop.stat().st_mtime)}" '
                f'alt="실제 게임 화면: 낙하 직전 수송기와 섬"><figcaption>{escape(cv["image_credit"])}</figcaption></figure>'
                if drop.is_file() else "")
    html(f'<div class="pg-cover"><div class="pg-cover-l">{logo_html}<div class="pg-cover-k">{escape(cv["title"])}</div>'
         f'<div class="pg-cover-t">{escape(cv["copy"])}</div><div class="pg-cover-s">{escape(cv["subtitle"])}</div></div>{img_html}</div>')
    html('<div class="pg-lead">'
         f'<div class="m"><span>① 신규 유저의 문제</span><b>{escape(cv["problem"])}</b><small>{escape(cv["problem_sub"])}</small></div>'
         f'<div class="m"><span>② 핵심 해결책</span><b>{escape(cv["solution"])}</b><small>{escape(cv["solution_sub"])}</small></div>'
         f'<div class="sub"><span>③ 서브 제안 · BM</span><b>{escape(cv["bm_problem"])}</b><small>{escape(cv["bm_problem_sub"])}</small></div></div>')


def render() -> None:
    ns, ops, steam, pool = load()
    SCREENS.clear()
    SCREENS.update({x["key"]: x for x in ns.get("screens", [])})
    plan = S.plan(ns["experiment"])
    html('<div class="gp-ow-page"></div>')          # 오버워치와 같은 반응형·배경 스타일 범위
    _cover(ns)
    i = tab_nav()
    badge_legend()
    html(f'<div class="ow-pane-mark" data-tab="{SECTIONS[i][0]}"></div>')   # 정적 보고서 탭 경계 표식
    [lambda: s1(ns, ops, plan, pool), lambda: s2(ns, ops, steam, pool), lambda: s3(ns, ops, pool),
     lambda: s4(ns), lambda: s5(ns, plan), lambda: s6(ns, plan)][i]()
    st.caption(f"{ns['disclaimer']} · 자료 확인일 2026-11-20")


GAP_CATS = ["실력 격차·매칭", "봇→실전 전환", "초반 교전·첫 사망"]


def _flow3(steps: list[tuple[str, str, str]], sub_: bool = False) -> str:
    """제목 + 한 줄 설명만 있는 3단계 흐름. steps = [(kind, 제목, 한 줄)]."""
    out = []
    for i, (kind, t, d) in enumerate(steps):
        out.append(f'<div class="pg-step {kind}"><div class="n">{"①②③④"[i]} <span class="kb">{KIND[kind]()}</span></div>'
                   f'<b>{escape(t)}</b><small>{escape(d)}</small></div>')
        if i < len(steps) - 1:
            out.append('<div class="pg-arrow">→</div>')
    return f'<div class="pg-flow{" sub" if sub_ else ""}">{"".join(out)}</div>'


# ======================================================================
# 01 문제·결론 — 하나의 결론: A1을 먼저 검증하고 B1은 작게 병행
def s1(ns: dict, ops: pd.DataFrame, plan: dict, pool: dict) -> None:
    a = ops[ops["track"] == "A"]
    b_ = ops[ops["track"] == "B"]
    gap = int(a["category"].isin(GAP_CATS).sum())
    cost_main = int((b_["category"] == "총비용 부담").sum())
    head("결론: 첫 실전 직후 '다음에 할 행동 1개'를 알려 준다", "신규 유저 정착(A1)이 메인, BM(B1)은 작게 병행하는 서브 제안", b_mock())
    html('<div class="pg-main"><div class="pg-main-l"><div class="pg-h">왜 A1이 먼저인가</div><ul class="pg-why">'
         f'<li>{b_real()} 기본 훈련 17챕터·초심자 훈련소 14일 미션은 이미 있다 → 빈 곳은 <b>훈련 이후 첫 실전</b></li>'
         f'<li>{b_real()} 신규 정착 리뷰 {len(a)}건 중 <b>{gap}건</b>이 숙련자 로비·봇→실전 전환·첫 교전 사망</li>'
         f'<li>{b_hypo()} 패배 후 고칠 행동을 모르면 다음 경기로 이어지기 어렵다</li></ul></div>'
         '<div class="pg-main-r"><div class="pg-h">A1 첫 실전 피드백</div>'
         '<div class="pg-chips"><span>패배 원인 1개</span><i>→</i><span>다음 경기 행동 1개</span><i>→</i><span>성장 확인</span></div>'
         '<p>데스캠·리플레이(기존)는 장면을 다시 보여 줄 뿐, <b>무엇을 바꿀지</b>는 알려 주지 않는다.</p>'
         '<p class="kpi">검증 · 신규 D7 잔존율 A/B 테스트</p></div></div>')
    html('<div class="pg-subbox"><span class="pg-tr b">서브 · BM</span><b>B1 구매 전 총비용 안내</b> '
         '흩어진 가격·확률·교환 정보를 목표 기준 예상 비용 한 화면으로. 가격·확률은 그대로, 구매 전환이 떨어지지 않는지만 검증.</div>')
    with st.expander("자세히 보기 · 판단 근거 · 사업적 의미 · 제외한 아이디어"):
        html("<ul class='pg-ul'>"
             f"<li><b>BM은 왜 '검증'부터인가</b> {b_interp()} BM 리뷰 {len(b_)}건 중 총비용 부담 주분류는 {cost_main}건뿐 → 시급하다고 단정하지 않고, "
             "정보 부족이 구매 판단에 영향을 주는지부터 본다.</li>"
             f"<li><b>무엇으로 판단하나</b> {b_mock()} A1은 D7 유의성 + 실질 효과 +{plan['practical_min']:.1f}%p 이상 + 가드레일, "
             "B1은 구매 전환 비열등과 매출 가드레일을 따로 본다 → 05 탭</li>"
             "<li><b>비용·일정</b>은 06 탭에서만 다룬다.</li>"
             "<li><b>기존 유저 보호</b> 매칭·밸런스·확률은 바꾸지 않는다. 핵 문제는 별도 운영 과제로 분리.</li>"
             "<li><b>규모 참고</b> Steam 월평균 동시접속자는 30만 명 안팎 · 잔존율·이탈률이 아니다 → 신규 잔존은 D7로 따로 측정</li>"
             "<li><b>제외한 아이디어</b> 무기 숙련도(무기별 레벨·메달)가 이미 있어 마이건 성장·킬 수 칭호는 제외 · "
             "기본 훈련·초심자 훈련소·데스캠·리플레이는 기존 기능으로만 다룸 · 이중 가챠는 2026-06(42.1)에 제거된 과거 문제</li></ul>")


# ======================================================================
# 02 실제 근거 — 대표 근거 먼저, 전체 자료는 펼쳐보기
def s2(ns: dict, ops: pd.DataFrame, steam: pd.DataFrame, pool: dict) -> None:
    a = ops[ops["track"] == "A"]
    head("근거: 신규 유저는 '실전 전환 직후' 막힌다", f"Steam 최신 리뷰 {sum(pool['pool'].values()):,}건 중 관련 {len(ops)}건을 직접 분류 · 대표 의견 3건만 먼저", b_real())
    _review_chart(a, pool)
    picks = [x for x in ["A01", "A11", "A17"] if x in set(ops["opinion_id"])]
    q = ops.set_index("opinion_id").loc[picks].reset_index()
    labels = {"A01": "실력 격차", "A11": "봇 → 실전 전환", "A17": "반복 패배"}
    html('<div class="pg-quotes">' + "".join(
        f'<div class="ow-quote neg"><div class="ow-quote-tag">{escape(labels.get(r.opinion_id, r.category))} · 플레이 {escape(r.hours_on_record)}시간</div>'
        f'<div class="ow-quote-t">{escape(r.summary_ko)}</div><div class="ow-quote-o">“{escape(r.quote_original)}”</div>'
        f'<div class="ow-quote-m">Steam 리뷰 · {escape(r.published_date)} · {link(r.source_url, "원문 보기")}</div></div>'
        for r in q.itertuples()) + "</div>")
    note(f"리뷰 {len(ops)}건은 직접 고른 사례다. 전체 이용자 비율로 해석하지 않는다.")

    b_ = ops[ops["track"] == "B"]
    nb = b_.groupby("category").size()
    sub("BM 근거 (서브)")
    html('<div class="pg-bm2">'
         f'<div>{b_interp()} <b>리뷰</b> BM 관련 {len(b_)}건 중 확률·결과 불만 {int(nb.get("확률·결과 불만", 0))}건, '
         f'총비용 부담 {int(nb.get("총비용 부담", 0))}건 → 비용 정보 부족은 근거가 약해 <b>검증 대상</b></div>'
         f'<div>{b_real()} <b>공식 구조</b> 확률은 게임 안 \'확률 보기\'에서만 공개 · 누적 개봉 보상·스크랩 교환은 이미 있다</div></div>')

    with st.expander(f"자세히 보기 · 전체 리뷰 {len(ops)}건 · 실제 게임 화면 {len(SCREENS)}장 · 공식 자료 {len(ns['official'])}건 · 자료 한계"):
        t = st.tabs([f"전체 리뷰 {len(ops)}건", f"게임 화면 {len(SCREENS)}장", f"공식 자료 {len(ns['official'])}건", "기존 기능 vs 제안",
                     "BM 누적 보상 구조", "시장 규모 (참고)", "자료 한계"])
        with t[0]:
            _review_chart(ops, pool, full=True)
            _opinions(ops)
        with t[1]:
            items = list(SCREENS.values())
            for i in range(0, len(items), 2):
                cols = st.columns(2, gap="medium")
                for col, x in zip(cols, items[i:i + 2]):
                    with col:
                        html(f'<div class="pg-slot-w">{tr(x["track"])}<small>{escape(x["use"])}</small></div>')
                        shot(x["key"])
            st.caption("작성자가 직접 캡처한 최신 한국어 화면 · 다른 플레이어 닉네임은 가린 사본만 공개")
        with t[2]:
            table(["날짜 · 트랙", "자료", "확인한 사실", "출처"],
                  [[f"{escape(o['date'])}<br>{tr(o['track'])}", f"<b>{escape(o['title'])}</b>", escape(o["fact"]),
                    (link(o["url"], o["status"]) if o.get("url") else escape(o["status"]))] for o in ns["official"]], badge_html=b_real())
        with t[3]:
            table(["영역", "기존 기능 (실제)", "남은 빈틈", "이번 제안"],
                  [[escape(x["area"]), escape(x["existing"]), escape(x["gap"]), f"<b>{escape(x['new'])}</b>"] for x in ns["existing_vs_new"]],
                  badge_html=b_interp())
        with t[4]:
            _milestone_chart()
        with t[5]:
            _steam_chart(steam)
        with t[6]:
            st.markdown(f"- 리뷰 표본: {pool['source']} · 한국어 {pool['pool']['한국어']}건({pool['period']['한국어']}) · "
                        f"영어 필터 {pool['pool']['영어 필터']}건({pool['period']['영어 필터']}) · 추천 비율 {pool['recommend_rate']['한국어']}% / {pool['recommend_rate']['영어 필터']}%\n"
                        f"- 그중 신규 정착·BM 관련 리뷰 {len(ops)}건을 기획자가 직접 읽고 분류 (AI 자동 분류 아님) · 원문 발췌는 원본과 글자 그대로 대조\n"
                        "- Steam 리뷰는 Steam 이용자만, 리뷰를 쓴 사람만 포함 → 전체 이용자 의견 비율이 아니다\n"
                        f"- 핵 키워드 리뷰 {pool['cheat_keyword_reviews']}건은 별도 운영 리스크로 분리\n"
                        "- Reddit은 수집 환경에서 접근 차단(403), 국내 커뮤니티는 이번 범위에서 수집하지 않음\n"
                        "- 욕설·혐오 표현이 섞인 리뷰는 해당 부분을 빼고 발췌 · 작성자 이름은 저장하지 않음\n"
                        "- 밀수품 상자 1회 가격·확률·교환가는 공개 공식 문서로 확인되지 않아 게임 화면 캡처값을 '예시'로만 계산 (공지 가격 1,800 G-Coin은 단위 미표기·화면과 불일치)")
            st.caption("Steam Charts(steamcharts.com/app/578080) 월평균 동시접속자 · 확인일 2026-11-20")


def _review_chart(ops: pd.DataFrame, pool: dict, full: bool = False) -> None:
    cnt = ops.groupby(["track", "category"]).size().reset_index(name="n").sort_values(["track", "n"], ascending=[True, False])
    colors = [(C_TREAT if c in GAP_CATS else "#93C5FD") if t == "A" else C_CORAL for t, c in zip(cnt["track"], cnt["category"])]
    fig = go.Figure(go.Bar(y=list(cnt["category"]), x=cnt["n"], orientation="h", marker_color=colors, text=[f"{n}건" for n in cnt["n"]],
                           textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x}건<extra></extra>"))
    fig.update_yaxes(autorange="reversed", automargin=True, title="")
    fig.update_xaxes(title="리뷰 수 (건)", range=[0, cnt["n"].max() * 1.35], dtick=1, rangemode="tozero")
    if full:
        a, b = (ops["track"] == "A").sum(), (ops["track"] == "B").sum()
        chart_card(fig, key="pg_rev_all", kind="real", title=f"전체 리뷰 분류 (직접 분류 {len(ops)}건)", unit="건 · 파랑 = 신규 정착, 코랄 = BM",
                   kpis=[("신규 정착", f"{a}건"), ("BM", f"{b}건"), ("긍정 의견 (반대 사례)", f"{(ops['sentiment'] == '긍정').sum()}건")],
                   analysis="신규 정착은 학습 곡선·실력 격차·봇→실전, BM은 확률 결과가 많다", decision="A1은 전환 구간 · B는 검증부터",
                   basis=f"최신 리뷰 {sum(pool['pool'].values()):,}건 중 관련 리뷰 직접 분류 · 비율 아님", height=430, legend=False, cols=("분류", "리뷰 수 (건)"))
        return
    gap = int(ops["category"].isin(GAP_CATS).sum())
    chart_card(fig, key="pg_rev", kind="real", title=f"신규 정착 리뷰 {len(ops)}건 · 어디서 막히나",
               unit="건 · 진한 파랑 = 실전 전환 직후",
               kpis=[("실전 전환 직후", f"{gap}건"), ("학습 곡선", f"{int((ops['category'] == '학습 곡선').sum())}건")],
               analysis="숙련자 로비·봇→실전·첫 교전 사망이 실전 전환 직후에 몰린다", decision="A1은 첫 실전 직후 결과 화면에 둔다",
               basis="직접 분류 · 사례 수 (비율 아님)", height=260, legend=False, cols=("분류", "리뷰 수 (건)"))


def _steam_chart(steam: pd.DataFrame) -> None:
    d = steam.copy()
    d["m"] = pd.to_datetime(d["month"])
    pk = d.loc[d["avg_players"].idxmax()]
    last = d.iloc[-1]
    fig = go.Figure(go.Bar(x=d["m"], y=d["avg_players"], marker_color=[C_TREAT if m == pk["m"] else C_MUTED for m in d["m"]],
                           hovertemplate="%{x|%Y-%m} · %{y:,.0f}명<extra></extra>"))
    fig.update_yaxes(title="월평균 동시접속자 (명)", tickformat=",", rangemode="tozero", range=[0, d["avg_players"].max() * 1.15])
    fig.update_xaxes(title="월", tickformat="%y.%m", dtick="M3")
    chart_card(fig, key="pg_steam", kind="real", title="Steam 월평균 동시접속자 (24개월 · 시장 규모 참고)",
               unit="명 · 파랑 = 최고치",
               kpis=[(f"최고 {pk['m']:%y.%m}", f"{pk['avg_players']:,.0f}명"), (f"최근 {last['m']:%y.%m}", f"{last['avg_players']:,.0f}명")],
               analysis="시즌·이벤트 달에 급증 후 30만 명 안팎으로 회귀", decision="신규 유저 이탈률로 해석하지 않음 · 신규 잔존은 D7로 따로 측정",
               basis="Steam만 포함 (카카오·콘솔 제외) · Steam Charts", height=300, legend=False, cols=("월", "월평균 동시접속자 (명)"))


def _milestone_chart() -> None:
    ms = [(15, "Cargo 티켓 1"), (30, "토큰 150"), (55, "폴리머 900"), (85, "토큰 300"), (115, "설계도 1"), (145, "토큰 450"), (180, "연막탄 스킨")]
    x = [m for m, _ in ms]
    y = [m * 250 for m in x]
    fig = go.Figure(go.Scatter(x=x, y=y, mode="lines+markers+text", line=dict(color=C_CORAL, width=3), marker=dict(size=9, color=C_CORAL),
                               text=[t for _, t in ms], textposition="top left", textfont=dict(size=11),
                               hovertemplate="누적 %{x}회 · %{y:,} G-Coin<extra></extra>"))
    fig.update_yaxes(title="누적 비용 (G-Coin)", tickformat=",", rangemode="tozero", range=[0, 52000])
    fig.update_xaxes(title="누적 개봉 수 (회)", range=[0, 195])
    chart_card(fig, key="pg_ms", kind="real", title="블랙마켓 2026 Cargo 누적 개봉 보상 (다른 상품)",
               unit="G-Coin · Cargo 1회 250 기준",
               kpis=[("Cargo 1회 가격", "250 G-Coin"), ("마지막 보상까지", "180회 · 45,000")],
               analysis="누적 보상 구조는 이미 있다", decision="구조 추가보다 총비용 '안내'를 검증",
               basis="공식 공지 2026-06-17 · 2026-06~07 판매 이벤트 · 시뮬레이터의 큐티 파이 밀수품 상자와 다른 상품이라 가격을 섞지 않음",
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
    st.dataframe(ops[["opinion_id", "track", "category", "tags", "sentiment", "language", "published_date", "recommended",
                      "hours_on_record", "summary_ko", "quote_original", "source_url"]]
                 .rename(columns={"opinion_id": "의견 번호", "track": "트랙", "category": "주 분류", "tags": "보조 분류", "sentiment": "방향",
                                  "language": "언어", "published_date": "작성일", "recommended": "추천 여부", "hours_on_record": "플레이 시간",
                                  "summary_ko": "요약", "quote_original": "원문 발췌", "source_url": "원문"}),
                 hide_index=True, column_config={"원문": st.column_config.LinkColumn("원문", display_text="열기")})


# ======================================================================
# 03 원인 가설 — 3단계 흐름 (제목 + 한 줄) · 근거·검증 방법은 펼쳐보기
def s3(ns: dict, ops: pd.DataFrame, pool: dict) -> None:
    n = ops.groupby("category").size()
    head("원인 가설: 훈련 → 첫 실전 → 성장 체감", "관찰한 사실과 가설을 구분했다. 인과관계는 A/B 테스트로만 판단한다.", b_hypo())
    sub("TRACK A · 신규 유저 정착 (메인)")
    html(_flow3([("real", "훈련 완료", "기본 조작은 배웠지만"),
                 ("interp", "첫 실전에서 좌절", "숙련자와의 실력 격차를 경험"),
                 ("hypo", "성장 체감 부족", "패배 후 무엇을 개선할지 모름")]))
    html(f'<div class="pg-hyp">{b_hypo()} <b>패배 후 개선할 행동을 알지 못하면 다음 경기로 이어지기 어렵다.</b>'
         '<small>검증 · A1 A/B 테스트로 신규 D7 잔존율 비교 (05 탭)</small></div>')
    sub("TRACK B · BM (서브)")
    html(_flow3([("real", "확률형 구매", "확률은 게임 안 페이지에서만 공개"),
                 ("interp", "목표 상품 미획득", "원하는 스킨 대신 다른 보상 반복"),
                 ("hypo", "비용 불확실성", "목표까지 얼마인지 모른 채 구매")], sub_=True))
    html(f'<div class="pg-hyp sub">{b_hypo()} 비용을 미리 알 수 없으면 구매 만족도·재구매가 낮아질 수 있다. '
         '<small>검증된 사실 아님 · B1 A/B의 보조 지표(재구매율·문의율)로 확인</small></div>')
    note("다른 원인(핵·봇 비율·서버 등)은 A/B 무작위 배정으로 두 그룹에 고르게 섞인다 → 기능 효과만 분리된다.")
    with st.expander("근거 및 검증 방법 자세히 보기"):
        t_tags = int(ops["tags"].str.contains("총비용 부담").sum())
        table(["단계", "구분", "근거", "검증 방법"],
              [[f"{tr('A')}① 훈련 완료", KIND["real"](), "기본 훈련 17챕터 · 초심자 훈련소 14일 미션 (공식 패치노트 42.2)", "훈련 완료율 · 첫 일반전 진입률"],
               [f"{tr('A')}② 첫 실전에서 좌절", KIND["interp"](),
                f"리뷰 '실력 격차' {int(n.get('실력 격차·매칭', 0))}건 · '봇→실전 전환' {int(n.get('봇→실전 전환', 0))}건 · '첫 사망' {int(n.get('초반 교전·첫 사망', 0))}건",
                "경기당 봇 비율 · 첫 교전 생존율 · 첫 10경기 순위"],
               [f"{tr('A')}③ 성장 체감 부족", KIND["hypo"](), "가설 · 로그 검증 필요", "첫 3경기 후 재접속 · D7 (A1 A/B)"],
               [f"{tr('B')}① 확률형 구매", KIND["real"](), "큐티 파이 밀수품 상자 판매 · 확률은 게임 안 페이지 (공식 상점 공지 2026-11)", "상점 방문 → 구매 전환"],
               [f"{tr('B')}② 목표 상품 미획득", KIND["interp"](), f"리뷰 '확률·결과' {int(n.get('확률·결과 불만', 0))}건", "구매 후 문의율"],
               [f"{tr('B')}③ 비용 불확실성", KIND["hypo"](), f"'총비용' 주분류 {int(n.get('총비용 부담', 0))}건 · 보조 언급 {t_tags}건 → 근거 약함",
                "B1 A/B: 전환율 · 구매 과정 이탈률"],
               [f"{tr('B')}가설 · 만족도·재구매 하락", KIND["hypo"](), "가설 · 매출 로그 검증 필요", "30일 재구매율 (B1 보조 지표)"]])
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


# ======================================================================
# 04 해결책 데모
def s4(ns: dict) -> None:
    head("A1 첫 실전 피드백: 패배 원인 1개 → 다음 경기 행동 1개 → 성장 확인", "매칭·밸런스·확률은 바꾸지 않는다.", b_mock())
    html('<div class="pg-diff"><div><span class="pg-tag real">이미 있는 기능 (실제)</span>기본 훈련 · 초심자 훈련소 · 데스캠 · 리플레이 · 무기 숙련도'
         '<small>데스캠·리플레이는 사망 장면을 다시 보여 줄 뿐, 무엇을 바꿀지는 알려 주지 않는다.</small></div>'
         '<div><span class="pg-tag mock">이번 제안 (기획 시안)</span>A1 결과 화면의 피드백 카드 1장'
         '<small>기존 로그로 판정한 원인 1개 + 다음 경기 행동 1개만 · 첫 10경기에만 · 언제든 끄기</small></div></div>')
    sub("직접 눌러 보기 · 왼쪽 실제 화면 vs 오른쪽 시안")
    t = st.tabs(["A1 첫 실전 피드백 (메인)", "B1 총비용 시뮬레이터 (서브)", "A2 첫 10경기 성장 기록", "B2 강화 비용 (추정)"])
    with t[0]:
        demo_b(ns)
    with t[1]:
        demo_c(ns)
    with t[2]:
        demo_a(ns)
    with t[3]:
        demo_b2(ns)
    lab = ns["score_labels"]
    with st.expander("자세히 보기 · 후보 6개 비교 (A2·A3·B2·B3 포함) · 평가 점수"):
        table(["안", "판단", "문제", "기존 기능", "차이"],
              [[f"{tr(p['track'])}<b>{p['key']}</b> {escape(p['name'])}", f"<b>{escape(p['decision'])}</b>", escape(p["problem"]),
                escape(p["existing"]), escape(p["diff"])] for p in ns["proposals"]], badge_html=b_mock())
        table(["안", *lab.values(), "합계", "필요 데이터", "위험"],
              [[f"<b>{p['key']}</b> {escape(p['name'])}", *[str(p["scores"][k]) for k in lab], f"<b>{sum(p['scores'].values())}</b>",
                escape(p["data"]), escape(p["risk"])] for p in ns["proposals"]], badge_html=b_interp())


def demo_a(ns: dict) -> None:
    dm = ns["demo_matches"]
    df = pd.DataFrame(dm["rows"], columns=dm["cols"])

    def mock() -> None:
        k = st.select_slider("경기 번호 (예시 계정)", options=list(range(1, 11)), value=5, key="pg_a_match")
        r, r0 = df.iloc[k - 1], df.iloc[0]

        def delta(v, v0, unit):
            return "" if k == 1 else f"<em>{'+' if v - v0 > 0 else ''}{v - v0:,.1f}{unit} vs 1경기</em>"
        dist = "—" if pd.isna(r["engage_dist_m"]) else f"{r['engage_dist_m']:.0f}m"
        html(f'<div class="pg-demo"><h4>{k}경기째 성장 기록 {b_sample()}</h4><div class="pg-metric">'
             f'<div><small>생존 시간</small><b>{r["survive_min"]:.1f}분</b>{delta(r["survive_min"], r0["survive_min"], "분")}</div>'
             f'<div><small>첫 교전</small><b>{"참여" if r["engaged"] else "없음"}</b><small>거리 {dist}</small></div>'
             f'<div><small>팀원과 거리</small><b>{r["team_dist_m"]:.0f}m</b>{delta(r["team_dist_m"], r0["team_dist_m"], "m")}</div></div>'
             f'<div class="act">다음 목표 · {escape(r["goal"])}</div>'
             f'<div class="src">{escape(dm["note"])} · 보상 없음 (훈련소 미션과 구분)</div></div>')
    compare("match_result", "경기 결과 화면 (순위·킬)", "첫 10경기 성장 기록", mock)
    with st.expander("자세히 보기 · 생존 시간 추이 (예시 계정 10경기)"):
        fig = go.Figure(go.Scatter(x=df["match"], y=df["survive_min"], mode="lines+markers", line=dict(color=C_TREAT, width=3)))
        fig.update_xaxes(title="경기 번호", dtick=1)
        fig.update_yaxes(title="생존 시간 (분)", rangemode="tozero", range=[0, df["survive_min"].max() * 1.2])
        chart_card(fig, key="pg_demo_a", kind="sample", title="생존 시간 추이 (예시)", unit="분", kpis=[],
                   analysis=f"1경기 {df['survive_min'].iloc[0]:.1f} → 10경기 {df['survive_min'].iloc[-1]:.1f}분",
                   decision="첫 10경기는 기획 구간 · 최적 경기 수는 데이터로 결정",
                   basis="예시 데이터 · 실제 계정 기록 아님", height=240, legend=False, cols=("경기 번호", "생존 시간 (분)"))


def demo_b(ns: dict) -> None:
    fb = {f["label"]: f for f in ns["demo_feedback"]}

    def mock() -> None:
        lab = st.radio("상황 선택", list(fb), horizontal=True, key="pg_b_sit")
        f = fb[lab]
        html(f'<div class="pg-demo"><h4>첫 실전 피드백 {b_mock()}</h4>'
             f'<div class="src">상황 (예시) · {escape(f["scene"])}</div><div><b>원인</b> {escape(f["problem"])}</div>'
             f'<div class="act">{escape(f["action"])}</div>'
             f'<div class="src">판정 데이터 · {escape(f["data"])} · <b>{escape(f["mvp"])}</b></div></div>')
        st.toggle("피드백 끄기", key="pg_b_off", help="설정에서 언제든 끄고 켤 수 있다 (기획 시안)")
        if st.session_state.get("pg_b_off"):
            st.info("피드백을 껐습니다. 결과 화면은 기존과 같습니다. (기획 시안)")
    compare("deathcam", "데스캠 (장면 재생)", "경기 후 고칠 점 1개", mock)
    note("MVP는 기존 로그로 판정되는 '차량·팀플레이'부터. 엄폐는 신규 로그, 자기장은 필드 확인 후.")


def demo_c(ns: dict) -> None:
    bm = ns["bm_sim"]
    box = {}

    def mock() -> None:
        c1, c2 = st.columns(2)
        box["price"] = c1.number_input("1회 가격 (G-Coin · 예시)", 100, 10000, int(bm["price"]), step=100, key="pg_c_price")
        box["prob"] = c2.slider("목표 스킨 확률 (% · 예시)", 0.1, 10.0, float(bm["prob"]), 0.1, key="pg_c_prob")
        box["out"] = st.container()
    compare("contraband_store", "밀수품 상자 구매 화면", "구매 전 예상 비용 (가격·확률 그대로)", mock)

    # 상세 설정(스크랩·구매 횟수)과 확률 곡선은 접어 둔다. 값은 위 결과 카드에도 반영된다.
    with st.expander("자세히 보기 · 스크랩 교환 조건 · 구매 횟수별 확률 곡선 · 계산식"):
        c1, c2, c3, c4 = st.columns(4)
        per = c1.number_input("1회당 스크랩", 0, 100, int(bm["scrap_per_open"]), key="pg_c_spo")
        ex = c2.number_input("교환 필요 스크랩", 0, 20000, int(bm["exchange_scrap"]), step=100, key="pg_c_ex")
        own = c3.number_input("보유 스크랩", 0, 20000, 0, step=100, key="pg_c_own")
        n = c4.slider("구매 횟수", 1, 400, 100, key="pg_c_n")
        d1, d2, _ = st.columns([1, 1, 2])
        fn = d1.number_input("첫 묶음 횟수 (0 = 할인 미적용)", 0, 100, int(bm.get("first_n", 0)), key="pg_c_fn")
        fp = d2.number_input("첫 묶음 가격 (G-Coin)", 0, 100000, int(bm.get("first_price", 0)), step=100, key="pg_c_fp")
        s = S.crate_summary(box["price"], box["prob"], per, ex, own, n, fn, fp)
        cap = s["cap"]
        tiles([(f"{n}회 안에 얻을 확률", f"{s['within_n'] * 100:.1f}%", f"독립 시행 · {n}회 비용 {s['n_cost']:,.0f} G-Coin"),
               ("교환 확정 (천장)", "없음" if cap is None else f"{s['cap_cost']:,.0f}", "" if cap is None else f"{cap}회 · G-Coin"),
               ("교환 없을 때 기대 비용", f"{s['exp_cost_nocap']:,.0f}", "G-Coin · 1 ÷ p 회")])
        mx = max(n, cap or 0, s["o90"] or 0) + 20
        step = max(1, mx // 40)                       # 곡선 표본을 40개 안팎으로 (데이터 표가 수백 행이 되지 않게)
        curve = [c for c in S.crate_curve(box["prob"], cap, mx) if c[0] % step == 0 or c[0] in (cap, n)]
        fig = go.Figure()
        fig.add_scatter(x=[c[0] for c in curve], y=[c[1] for c in curve], name="교환 없이", line=dict(color=C_CTRL, width=2, dash="dot"))
        fig.add_scatter(x=[c[0] for c in curve], y=[c[2] for c in curve], name="스크랩 교환 포함", line=dict(color=C_CORAL, width=3))
        fig.update_xaxes(title="구매 횟수 (회)", range=[0, mx])
        fig.update_yaxes(title="1번 이상 얻을 확률 (%)", range=[0, 105], ticksuffix="%")
        chart_card(fig, key="pg_demo_c", kind="sim", title="구매 횟수별 획득 확률", unit="% · 코랄 = 교환 포함",
                   kpis=[], analysis=f"{n}회 안에 {s['within_n'] * 100:.1f}%", decision="구매 전에 보여 줘도 전환율이 유지되는지 B1로 검증",
                   basis="P(n회 내) = 1 − (1 − p)^n · 천장 = 교환 스크랩 ÷ 1회당 스크랩", height=280,
                   cols=("구매 횟수 (회)", "획득 확률 (%)"), series="계산")
        st.markdown("- 기대 구매 횟수 = (1 − (1 − p)^K) ÷ p (K = 천장 = 교환 스크랩 ÷ 1회당 스크랩, 교환이 없으면 1 ÷ p)\n"
                    "- 비용 = 첫 구매는 10회 묶음 할인가, 이후 1회 가격 × 추가 횟수 → 기대 비용 = 묶음가 + 1회 가격 × (E[N] − E[min(N, 10)])\n"
                    "- 중복 보상의 분해·토큰 환급은 반영하지 않음 → 실제 부담은 이보다 낮을 수 있다\n"
                    f"- 1회 가격 {bm['price']:,}: {bm['notes']['price']}\n"
                    f"- 첫 10회 {bm['first_price']:,}: {bm['notes']['first']}\n"
                    f"- 확률 {bm['prob']}%: {bm['notes']['prob']}\n"
                    f"- 스크랩 {bm['scrap_per_open']}/회: {bm['notes']['scrap_per_open']} · 교환가 {bm['exchange_scrap']:,}: {bm['notes']['exchange_scrap']}")
    with box["out"]:
        html(f'<div class="pg-demo b"><h4>목표 스킨까지 예상 비용 {b_sample()} {b_sim()}</h4><div class="pg-metric">'
             f'<div><small>기대 비용 (교환 포함)</small><b class="big">{s["exp_cost"]:,.0f}</b><small>G-Coin · 평균 {s["exp_opens"]:.0f}회</small></div>'
             f'<div><small>50% 확률 도달</small><b>{(s["c50"] or 0):,.0f}</b><small>{s["o50"]}회</small></div>'
             f'<div><small>90% 확률 도달</small><b>{(s["c90"] or 0):,.0f}</b><small>{s["o90"]}회</small></div></div>'
             '<div class="src">예시 데이터 · 가격 200·확률 0.9%·교환가 3,000은 게임 화면 캡처값 (공식 문서 미확인) · 출처는 아래 펼쳐보기</div></div>')


def demo_b2(ns: dict) -> None:
    html('<div class="ow-defer"><b>검토 대기</b> 업그레이드 화면이 단계별 필요 재료를 이미 보여 주는지 캡처로 확인한 뒤 결정 · '
         '레벨별 필요량은 공식 미공개라 분해 환급표로 추정</div>')

    def mock() -> None:
        c1, c2 = st.columns(2)
        cur = c1.slider("현재 레벨", 1, 10, 3, key="pg_u_cur")
        tgt = c2.slider("목표 레벨", 1, 10, 10, key="pg_u_tgt")
        c1, c2 = st.columns(2)
        pol = c1.number_input("보유 폴리머", 0, 100000, 5000, step=500, key="pg_u_pol")
        sch = c2.number_input("보유 설계도", 0, 200, 10, key="pg_u_sch")
        u = S.upgrade_need(ns["salvage"], cur, tgt, pol, sch)
        html(f'<div class="pg-demo b"><h4>{cur} → {tgt}레벨 필요 재료 (추정) {b_sim()}</h4><div class="pg-metric">'
             f'<div><small>폴리머</small><b>{u["polymer"]:,}</b><small>부족 {u["short_polymer"]:,}</small></div>'
             f'<div><small>설계도</small><b>{u["schematic"]:,}</b><small>부족 {u["short_schematic"]:,}</small></div></div>'
             '<div class="src">획득 경로 · 성장형 스킨 분해 · 이벤트 패키지 · 누적 개봉 보상 (공식)</div></div>')
        if u["steps"]:
            with st.expander("자세히 보기 · 단계별 추정 필요량"):
                table(["레벨", "폴리머", "설계도"], [[f"{lv - 1}→{lv}", f"{p:,}", str(s)] for lv, p, s in u["steps"]], badge_html=b_sim())
    compare("upgrade", "성장형 스킨 업그레이드 화면", "목표 레벨까지 부족한 재료", mock)
    st.caption("추정 근거: 공식 분해 환급표(2025-03, 34.2)를 '그 레벨까지 누적 투입량'으로 가정. 실제 필요량과 다를 수 있음.")


# ======================================================================
# 05 KPI·A/B 테스트
def s5(ns: dict, plan: dict) -> None:
    ex = ns["experiment"]
    A, B = ex["A"], ex["B"]
    pa, pb, sc = plan["A"], plan["B"], plan["sched"]
    pm = plan["practical_min"]
    head("KPI: A1은 신규 D7, B1은 구매 전환 + 매출 가드레일", "기준값은 모두 가정 · 아래 수치는 실제 실험 결과가 아니다", b_mock())
    html('<div class="pg-main"><div class="pg-main-l"><div class="pg-h">A1 · 주요 KPI <span class="pg-tr a">메인</span></div>'
         f'<div class="pg-big">신규 D7 잔존율</div><ul class="pg-why">'
         f'<li><b>대조군</b> {escape(A["control"])} · <b>실험군</b> {escape(A["treatment"])}</li>'
         f'<li><b>기준</b> {A["base_d7"]:.0f}% 가정 · 신규 계정 50:50 · 배정 기준(ITT)</li>'
         f'<li><b>출시 판단</b> ① 유의 ② 실질 효과 +{pm:.1f}%p 이상 ③ 가드레일 통과</li></ul></div>'
         '<div class="pg-main-r sub"><div class="pg-h">B1 · 보조 실험 <span class="pg-tr b">서브</span></div>'
         f'<div class="pg-big">30일 구매 전환율</div><ul class="pg-why">'
         f'<li>비열등 한계 −{B["ni_margin"]:.1f}%p (기준 {B["base_conv"]:.0f}% 가정)</li>'
         '<li>매출 가드레일: 총매출 −5% 이상 하락 시 중단</li></ul></div></div>')

    d30_base, d30_up = A["base_d7"] / 2, pa["mde"] / 2
    cats = ["신규 D7", "신규 D30", "첫 10경기 완료율"]
    before = [A["base_d7"], d30_base, A["base_m10"]]
    after = [A["base_d7"] + pa["mde"], d30_base + d30_up, A["base_m10"] + pa["m10_mde"]]
    fig = hpair(cats, before, after, xtitle="비율 (%)", names=("대조군 (가정)", "실험군 (가정)"), xmax=max(after) * 1.3)
    chart_card(fig, key="pg_sim_a", kind="sim", title="A1 · 대조군 vs 실험군 (가정 시뮬레이션)", unit="% · 회색 = 대조군, 파랑 = 실험군",
               kpis=[("신규 D7 (설계 목표)", f"{before[0]:.0f}% → <b>{after[0]:.0f}%</b> <em>{pp(pa['mde'])}</em>")],
               analysis=f"설계 목표 +{pa['mde']:.1f}%p = 열람률 {A['participation']}% × 열람자 개선 {A['uplift_viewer']:.0f}%p (가정)",
               decision="유의성·실질 효과·가드레일을 각각 통과해야 확대", basis="실험 전 설계값 · 실제 결과 아님 · D30은 D7 효과의 절반 유지 가정",
               height=300, cols=("지표", "비율 (%)"), series="그룹")

    sub("판정 기준 · 세 가지를 따로 본다", b_mock())
    html('<div class="ow-sig">'
         f'<div><b>① 통계적 유의성</b>A1: D7 차이의 95% 신뢰구간 하한 &gt; 0<br>B1: 전환율 차이의 단측 95% 신뢰 하한 &gt; −{B["ni_margin"]:.1f}%p (비열등)</div>'
         f'<div><b>② 실질적 사업 효과</b>A1: 점추정 ≥ +{pm:.1f}%p (추가 D7 1명당 약 {plan["a1_cost_per_added_practical"] / 1e4:.1f}만 원 이하 · 사전 합의)<br>'
         'B1: 재구매율·구매 후 문의율 중 1개 이상 개선 (보조 · 탐색적)</div>'
         '<div><b>③ 가드레일</b>하나라도 악화되면 확대하지 않음<br>A1: 매칭 대기·신고율·끄기 10% · B1: 총매출 −5% · 고액 결제자 매출 · 환불</div></div>')

    sub("B1 · BM 정책별 기준 대비 매출 영향 (서브)", b_sim())
    sv = S.scenarios(ns["scenarios"])
    html('<div class="pg-callout"><b>B 비용 안내부터 소규모 실험, C 누적 보장은 결과 확인 후 재검토</b>'
         '<small>시나리오 가정에 따른 우선순위다. B의 실제 매출 위험이 더 낮다고 검증된 것은 아니다.</small></div>')
    fig = go.Figure()
    fig.add_vline(x=0, line_width=2, line_color="#1E293B")
    fig.add_annotation(x=0, y=0.5, yref="paper", text="현행 = 0%", showarrow=False, xanchor="left", xshift=6,
                       font=dict(size=12, color="#1E293B"), bgcolor="rgba(255,255,255,0.9)")
    for s in sv[1:]:
        col = C_TREAT if s["key"] == "B" else C_CORAL
        lo, hi = s["low_pct"], s["high_pct"]
        lab = {"B": "B 비용 안내", "C": "C 누적 보장"}.get(s["key"], s["key"])
        full = f"{s['key']} {s['name']}"
        fig.add_trace(go.Scatter(x=[lo, hi], y=[lab, lab], mode="lines+markers+text", line=dict(color=col, width=10),
                                 marker=dict(size=16, color="#FFFFFF", line=dict(color=col, width=3)),
                                 text=[f"{lo:+.0f}%", f"{hi:+.0f}%"], textposition=["middle left", "middle right"],
                                 textfont=dict(size=14, color=col), cliponaxis=False, showlegend=False, name=lab,
                                 hovertemplate=f"{full}<br>가정 범위 {lo:+.1f}% ~ {hi:+.1f}%<extra></extra>"))
    fig.update_xaxes(title="현행 대비 60일 매출 변화 (%)", range=[-30, 20], ticksuffix="%", zeroline=False, dtick=10)
    fig.update_yaxes(title="", autorange="reversed", automargin=True)
    b_, c_ = sv[1], sv[2]
    chart_card(fig, key="pg_sim_b", kind="sim", title="BM 정책별 기준 대비 매출 영향 (가정 시나리오 범위)", unit="% · 선 = 비관 가정 ~ 낙관 가정",
               kpis=[("B 비용·확률 안내", f"{b_['low_pct']:+.0f}% ~ {b_['high_pct']:+.0f}%"), ("C 누적 보장", f"{c_['low_pct']:+.0f}% ~ {c_['high_pct']:+.0f}%")],
               analysis="C는 하한이 더 낮다 (보장 강화로 고액 결제가 줄어든다는 가정)",
               decision="B부터 작게 실험 · C는 B 결과 후 재검토",
               basis="양 끝 = 비관·낙관 가정값으로 계산한 예시 범위 (통계적 신뢰구간 아님) · 전환율·ARPPU·재구매율 모두 근거 없는 가정값 · 예측 아님",
               height=240, legend=False, cols=("정책", "매출 변화 (%)"))

    with st.expander("자세히 보기 · 실험 설계 (표본 · MDE · 기간 · 보조 KPI · 계산식)"):
        tiles([("A1 · 신규 D7 MDE (표본 설계용)", f"+{pa['mde']:.1f}%p", f"기준 {A['base_d7']:.0f}% 가정 · 검정력 80%"),
               ("A1 · 표본", f"{pa['n']:,}명 × 2", f"주당 신규 {A['weekly']:,}명 가정 → {pa['assign_weeks']}주"),
               ("B1 · 비열등 한계", f"−{B['ni_margin']:.1f}%p", f"구매 전환율 기준 {B['base_conv']:.0f}% 가정"),
               ("B1 · 표본", f"{pb['n']:,}명 × 2", f"주당 방문 {B['weekly']:,}명 가정 → {pb['assign_weeks']}주")])
        table(["실험", "대조군 → 실험군", "배정 · 대상", "주요 지표 · 기준", "MDE · 표본", "기간"],
              [[f"{tr('A')}<b>A1 첫 실전 피드백</b>", f"{escape(A['control'])} → {escape(A['treatment'])}", f"{escape(A['unit'])}<br>{escape(A['segment'])}",
                f"신규 D7 (ITT)<br><small>기준 {A['base_d7']:.0f}% 가정</small>",
                f"+{pa['mde']:.1f}%p (열람 {A['participation']}% × {A['uplift_viewer']:.0f}%p)<br>{pa['n']:,}명 × 2",
                f"배정 {sc['a_assign'][0]}~{sc['a_assign'][1]}주 · D7 {sc['a_d7']}주 · D30 {sc['a_d30']}주"],
               [f"{tr('B')}<b>B1 구매 전 총비용 안내</b>", f"{escape(B['control'])} → {escape(B['treatment'])}", f"{escape(B['unit'])}<br>{escape(B['segment'])}",
                f"30일 구매 전환율<br><small>기준 {B['base_conv']:.0f}% 가정</small>",
                f"비열등 한계 −{B['ni_margin']:.1f}%p<br>{pb['n']:,}명 × 2",
                f"배정 {sc['b_assign'][0]}주 · 전환 {sc['b_conv']}주 · 재구매 {sc['b_repurchase']}주"]], badge_html=b_mock())
        table(["트랙", "보조 KPI", "가드레일"],
              [[tr("A"), "D1·D30 · 첫 3경기 후 재접속 · 첫 10경기 완료율 · 피드백 열람률 · 스쿼드 재참여율", escape(" · ".join(A["guardrails"]))],
               [tr("B"), "ARPPU · 총매출 · 30일 재구매율 · 구매 과정 이탈률 · 문의·불만", escape(" · ".join(B["guardrails"]))]])
        st.markdown(f"- MDE(+{pa['mde']:.1f}%p)는 표본 크기를 정하는 설계값이다. 성공 조건이 아니므로, MDE보다 작아도 ①을 통과하고 ②(+{pm:.1f}%p) 이상이면 의미 있는 효과로 본다.\n"
                    f"- A1 MDE(배정 기준) = 피드백 열람률 {A['participation']}% × 열람자 개선 {A['uplift_viewer']}%p = +{pa['mde']:.1f}%p\n"
                    f"- 우월성 표본: 두 비율 차이 양측 검정 α {ex['alpha']} · 검정력 {ex['power']:.0%}\n"
                    f"- 비열등성 표본: 한쪽 검정 α {ex['alpha']} · 검정력 {ex['power']:.0%} · n = (z₁₋α + z₁₋β)² × 2p(1−p) ÷ 한계²\n"
                    f"- 배정 주수 = ⌈두 그룹 표본 합 ÷ 주당 대상⌉ · D7 판정 = 마지막 배정일 + 7일 · 전환 판정 = 배정 + {B['window_days']}일")
    with st.expander("자세히 보기 · BM 시나리오 가정값과 산출식"):
        table(["시나리오", "전환율 (%)", "ARPPU (G-Coin)", "재구매율 (%)", "60일 매출 (백만)", "현행 대비"],
              [[f"<b>{s['key']}</b> {escape(s['name'])}", f"{s['conv'][0]}~{s['conv'][1]}", f"{s['arppu'][0]:,}~{s['arppu'][1]:,}",
                f"{s['repurchase'][0]}~{s['repurchase'][1]}", f"{s['low']['total'] / 1e6:,.1f}~{s['high']['total'] / 1e6:,.1f}",
                f"{s['low_pct']:+.1f}%~{s['high_pct']:+.1f}%"] for s in sv], badge_html=b_sim())
        st.caption(f"60일 매출 = 방문자 × 전환율 × ARPPU + 구매자 × 재구매율 × ARPPU × {ns['scenarios']['repurchase_arppu_ratio']} · "
                   f"비관 = 각 범위의 낮은 값, 낙관 = 높은 값 · {ns['scenarios']['note']}")


# ======================================================================
# 06 실행·사업 제안 — 결론 중심 (문제 정의는 반복하지 않음)
def s6(ns: dict, plan: dict) -> None:
    sc = plan["sched"]
    pm = plan["practical_min"]
    head(f"실행 제안: A1 먼저 검증, B1은 작게 병행 · {sc['decision'] + 2}주 파일럿", f"준비 2주 + 운영 {sc['decision']}주", b_mock())
    html('<div class="pg-main"><div class="pg-main-l"><div class="pg-h">A1 첫 실전 피드백 <span class="pg-tr a">먼저</span></div>'
         '<p>막힘 지점(첫 실전 직후)에 바로 닿고, 기존 로그로 판정할 수 있으며 매칭을 건드리지 않는다.</p></div>'
         '<div class="pg-main-r sub"><div class="pg-h">B1 구매 전 총비용 안내 <span class="pg-tr b">병행</span></div>'
         '<p>가격·확률을 그대로 두어 매출 위험이 작을 것으로 예상(검증 전) · 적은 비용으로 검증한다.</p></div></div>')
    sub("비용·인력 가정", b_sim())
    c = ns["experiment"]["cost"]
    tiles([("A1 개발·운영", f"{c['A1_effort']}인월", f"≈ {plan['a1_cost'] / 1e4:,.0f}만 원 · 클라이언트 UI·데이터·QA"),
           ("B1 개발·운영", f"{c['B1_effort']}인월", f"≈ {plan['b1_cost'] / 1e4:,.0f}만 원 · 상점 UI·법무 검토"),
           ("A1 추가 D7 1명당", f"{plan['a1_cost_per_added']:,.0f}원", f"분기 신규 {ns['experiment']['quarter_new']:,}명 × MDE · 가정")])
    sub("실행 일정", b_mock())
    weeks = [("준비 (−2~0주)", "텔레메트리 판정 규칙 · 피드백 문구 검수 · 상점 패널 · 법무 · 실험 배정 점검"),
             (f"{sc['a_assign'][0]}~{sc['a_assign'][1]}주", "A1 배정 (신규 50:50) · B1 배정 (상점 방문 50:50)"),
             (f"{sc['a_d7']}~{sc['a_d30']}주", f"{sc['a_d7']}주 A1 D7 판정 · {sc['b_conv']}주 B1 전환 판정 · {sc['a_d30']}주 A1 D30 확인"),
             (f"{sc['a_d30'] + 1}~{sc['decision']}주", f"{sc['b_repurchase']}주 B1 재구매 확인 · {sc['decision']}주 확대·수정·중단 결정")]
    html('<div class="ow-timeline pg-tl">' + "".join(
        f'<div class="ow-tl"><div class="ow-tl-d">{escape(p)}</div><div class="ow-tl-b">{escape(w)}</div></div>' for p, w in weeks) + "</div>")
    sub("성공 · 수정 · 중단 조건", b_mock())
    table(["결과", "A1 첫 실전 피드백", "B1 총비용 안내"],
          [["<b>확대</b>", "①②③ 모두 통과", "① 비열등 + ③ 매출 가드레일 통과"],
           ["<b>수정</b>", f"① 유의 · ② 미달 (+{pm:.1f}%p 미만) → 일부 코호트만", "③ 일부 경계선 → 노출 범위 축소"],
           ["<b>연장</b>", "판단 불가 → 노출 위치 수정 후 1회 재실험", "판단 불가 → 표본 추가"],
           ["<b>중단</b>", f"효과 상한 &lt; +{pm:.1f}%p · 또는 ③ 악화", "비열등 실패 · 또는 총매출 −5%"]])
    sub("주요 위험", b_interp())
    table(["위험", "대응"], [[escape(r["risk"]), escape(r["response"])] for r in ns["risks"]])
    html(f'<div class="ow-conclusion"><div class="ow-conclusion-k">최종 사업PM 제안 {b_mock()}</div>'
         '<b>매칭·확률은 그대로, 정보만 더해 A1을 먼저 검증한다.</b><br>'
         'A2·B2는 결과를 본 뒤 검토하고, A3(스쿼드 적응)·B3(누적 보장 강화)는 보류한다.</div>')
    with st.expander(f"자세히 보기 · 후보 우선순위 계산 · 주차별 일정 · PPT 구성"):
        order = sorted(ns["proposals"], key=lambda p: (p["decision"] != "MVP", -sum(p["scores"].values())))
        table(["순서", "안", "판단", "점수 합", "이유"],
              [[str(i + 1), f"{tr(p['track'])} <b>{p['key']}</b> {escape(p['name'])}", f"<b>{escape(p['decision'])}</b>",
                str(sum(p["scores"].values())), escape(ns["mvp_reason"].get(p["key"], p["risk"]))] for i, p in enumerate(order)], badge_html=b_interp())
        html(gantt(sc))
        html("<ol>" + "".join(f"<li>{escape(x)}</li>" for x in ns["ppt"]) + "</ol>")
    note("한계: 리뷰는 사례이고 기준값은 가정이다. 인과는 A/B 테스트로만 판단한다.")
