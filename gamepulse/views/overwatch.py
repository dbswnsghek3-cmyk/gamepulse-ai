"""오버워치 페이지 — PROJECT RE:START (채용 담당자가 3~5분 안에 핵심을 보도록 구성).

구성
- 표지: 제목 → 핵심 문제 → 핵심 해결 큰 카드 → 01~06 이동 메뉴 → 최신 영웅 선택 화면(크게)
- 01 문제 정의: 문제 문장 · PM 의사결정 요약 · 근거 3단계(관찰 사실/이용자 의견/검증 전 가설) · 사업PM 관점 중요성
- 02 실제 근거: 게임 화면 · 유저 의견(표본·분류 기준) · 공식 업데이트 · 이용 지표
- 03 원인 가설 · 04 개선안(A·B·C 사양 카드 · 단계적 출시 · 실제 화면 vs 기획 시안)
- 05 KPI·A/B 테스트(정의·단계적 실험·MDE·표본·일정·판단 기준·가정 시뮬레이션) · 06 실행·제안
- 가정값은 data/overwatch/restart.json 'experiment' 한 곳에서 읽어 KPI 목표·표본·시뮬레이션·일정을 일치시킨다.

배지 (텍스트로도 구분): 실제 자료 · 분석자 해석 · 검증 전 가설 · 기획 시안 · 가정 시뮬레이션 · 예시 데이터

이미지 원칙
- 게임 화면은 data/overwatch/image_manifest.json 검증(한국어 UI·최신 패치 이후 촬영·출처·16:9·54명)을
  통과한 파일만 표시한다. 통과 전에는 '최신 한국어 스크린샷 필요' 자리를 보여 준다.
- 실제 화면은 남색 실선 프레임 + '실제 게임 화면' 태그, 기획 시안은 주황 점선 + '기획 시안 · 실제 게임에 없음' 리본.
- 다른 플레이어 닉네임은 manifest 의 blur 영역을 표시할 때만 가린다 (원본 파일은 그대로).
- 캐릭터 그림을 임의로 만들지 않는다. 영웅은 공식 영웅 페이지의 이름으로만 표시한다.
- React DOM 과 충돌하지 않도록 DOM 을 직접 조작하는 스크립트를 쓰지 않는다 (정적 마크업 + Streamlit 위젯만 사용).
"""

from __future__ import annotations

import math
import os
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from gamepulse.config import COLORS as C
from gamepulse.content.games import GAMES
from gamepulse.data.overwatch_data import (COLLECTED_AT, OPINION_CATEGORIES, STEAM_SOURCE, USER_TYPES, OverwatchDataError,
                                          load_json, load_opinions, load_pcbang, load_steam, load_timeline, opinion_codes)
from gamepulse.data.overwatch_images import all_status, load_manifest, web_jpeg_b64
from gamepulse.sim.restart_sim import (CohortInput, SimInput, experiment_plan, rice_table, run,
                                       sample_size_two_proportions, validate_base)
from gamepulse.ui.charts import PLOTLY_CONFIG, style
from gamepulse.ui.components import badge, html
from gamepulse.views import game_page
from gamepulse.views.deep_dives import DEEP_DIVES

SECTIONS = [("01", "문제와 결론", "무엇이 왜 문제인가"), ("02", "실제 근거", "화면·의견·공식 자료"),
            ("03", "원인 가설", "다른 원인까지 검토"), ("04", "개선안 체험", "A·B·C 직접 눌러 보기"),
            ("05", "KPI·A/B 테스트", "성과 판단 기준"), ("06", "실행·제안", "일정·확대·중단 조건")]
TAB_LABELS = [f"{n} {t}" for n, t, _ in SECTIONS]
TAB_KEY = "ow_tab"


def _tab_from_query() -> str:
    q = str(st.query_params.get("tab", ""))
    return next((lab for lab in TAB_LABELS if lab.startswith(q.zfill(2)[:2])), TAB_LABELS[0]) if q else TAB_LABELS[0]


def _sync_tab_param() -> None:
    st.query_params["page"] = "overwatch"
    st.query_params["tab"] = str(st.session_state.get(TAB_KEY, TAB_LABELS[0]))[:2]


def tab_nav() -> int:
    """01~06 탭 전환: 고른 섹션 하나만 그린다 (스크롤 이동 없음). 주소 ?tab=04 로 바로 열 수 있다."""
    if st.session_state.get(TAB_KEY) not in TAB_LABELS:
        st.session_state[TAB_KEY] = _tab_from_query()
    sel = st.radio("섹션 선택", TAB_LABELS, key=TAB_KEY, horizontal=True, label_visibility="collapsed",
                   on_change=_sync_tab_param)
    return TAB_LABELS.index(sel)
LEARNING_CODES = {"영웅·스킬 학습 부담", "상대 영웅 대응 이해 부족", "복귀 적응·변경점 파악", "전투 중 정보 과부하"}


# ----------------------------------------------------------------------
# 표시 헬퍼 · 배지는 색상과 텍스트 모두로 구분
def b_real() -> str:
    return badge("실제 자료", "k-real")


def b_interp() -> str:
    return badge("분석자 해석", "k-interp")


def b_hypo() -> str:
    return badge("검증 전 가설", "k-hypo")


def b_mock() -> str:
    return badge("기획 시안", "k-mock")


def b_sim() -> str:
    return badge("가정 시뮬레이션", "k-sim")


def b_sample() -> str:
    return badge("예시 데이터", "k-sample")


KIND = {"real": b_real, "interp": b_interp, "hypo": b_hypo, "mock": b_mock, "sim": b_sim, "sample": b_sample}


def b_plan() -> str:  # 실행 계획·제안도 실제로 시행된 것이 아니므로 '기획 시안'
    return b_mock()


def section(i: int) -> None:
    n, title, desc = SECTIONS[i]
    html(f'<div class="ow-sec" id="ow-s{n}"><div class="ow-sec-n">{n}</div><div class="ow-sec-t"><h2>{escape(title)}</h2>'
         f'<p>{escape(desc)}</p></div><a class="ow-sec-top" href="#ow-nav" target="_self">↑ 메뉴</a></div>')


def nav() -> None:
    items = "".join(
        f'<a class="ow-nav-i{" hot" if n == "04" else ""}" href="#ow-s{n}" target="_self">'
        f'<b>{n}</b><span>{escape(t)}<small>{escape(d)}</small></span></a>' for n, t, d in SECTIONS)
    html(f'<nav class="ow-nav" id="ow-nav" aria-label="섹션 이동">{items}</nav>')


def badge_legend() -> None:
    """배지 뜻은 한 줄로: '실제 자료'만 사실, 나머지는 해석·가설·제안·가정 계산."""
    html(f'<div class="ow-badges"><span>{b_real()} 만 확인된 사실</span>'
         f'<span>{b_hypo()} {b_mock()} {b_sim()} 은 검증 전 · 실적 아님</span></div>')


def link(url: str, text: str) -> str:
    return f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">{escape(text)}</a>'


def head(title: str, lead: str = "", tag: str = "") -> None:
    p = f"<p>{escape(lead)}</p>" if lead else ""
    html(f'<div class="ow-head"><h3>{escape(title)} {tag}</h3>{p}</div>')


def sub(title: str, tag: str = "") -> None:
    html(f'<div class="ow-sub">{escape(title)} {tag}</div>')


def note(text: str) -> None:
    html(f'<div class="ow-line">{escape(text)}</div>')


def tiles(items: list[tuple[str, str, str]]) -> None:
    html('<div class="ow-tiles">' + "".join(
        f'<div class="ow-tile"><div class="ow-tile-l">{escape(l)}</div><div class="ow-tile-v">{v}</div>'
        f'<div class="ow-tile-s">{s}</div></div>' for l, v, s in items) + "</div>")


def table(headers: list[str], rows: list[list[str]], badge_html: str = "", cls: str = "") -> None:
    """표: 배지를 표 바로 위에 붙이고, 모바일에서는 좌우 스크롤 안내를 보여 준다."""
    if not rows:
        st.info("표시할 자료가 없습니다.")
        return
    th = "".join(f"<th>{escape(h)}</th>" for h in headers)
    # data-label: 모바일에서는 행을 카드로 쌓고 각 칸 앞에 열 이름을 표시 (가로 스크롤·글자 잘림 방지)
    body = "".join("<tr>" + "".join(f'<td data-label="{escape(h, quote=True)}">{c}</td>' for h, c in zip(headers, r)) + "</tr>"
                   for r in rows)
    top = f'<div class="ow-table-b">{badge_html}</div>' if badge_html else ""
    html(f'{top}<div class="gp-table-wrap"><table class="gp-table ow-table {cls}"><tr>{th}</tr>{body}</table></div>')


def bullets(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{escape(x)}</li>" for x in items) + "</ul>"


def legend_bottom(fig: go.Figure, xtitle: bool = True) -> go.Figure:
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.25 if xtitle else -0.12, x=0, title_text=""),
                      margin=dict(b=40))
    return fig


def plot(fig: go.Figure) -> None:
    st.plotly_chart(fig, config=PLOTLY_CONFIG)


# 차트 색상 규칙 (모든 차트 공통)
#   실제 자료 강조 = 파랑 · 실제 자료 보조 = 연회색
#   대조군·도입 전·현재(가정) = 회색 · 실험군·도입 후·적용(가정) = 파랑
C_TREAT, C_CTRL, C_MUTED = "#2563EB", "#94A3B8", "#CBD5E1"


def chart_card(fig: go.Figure, *, key: str, kind: str, title: str, unit: str, kpis: list[tuple[str, str]],
               analysis: str, decision: str, basis: str, height: int = 360, legend: bool = True,
               cols: tuple[str, str] = ("항목", "값"), series: str = "구분") -> None:
    """차트 1개 = 배지·제목·단위 → 핵심 수치 → 차트 → 분석 결과 · 사업PM 의사결정 · 비교 기준.

    kpis 의 값(value)은 HTML 을 허용한다(호출하는 쪽에서 숫자만 넣음).
    cols = (범주 열 이름, 값 열 이름): 정적 보고서의 '차트 데이터 표' 열 제목으로 쓰인다 (layout.meta).
    """
    fig.update_layout(meta={"table": {"category": cols[0], "value": cols[1], "series": series, "title": title}})
    with st.container(border=True, key=f"owc_{key}"):
        chips = "".join(f'<div class="ow-kpi"><div class="ow-kpi-v">{v}</div><div class="ow-kpi-l">{escape(l)}</div></div>'
                        for l, v in kpis)
        html(f'<div class="ow-chart-h"><div class="ow-chart-t">{KIND[kind]()} {escape(title)}</div>'
             f'<div class="ow-chart-u">{escape(unit)}</div></div>' + (f'<div class="ow-kpis">{chips}</div>' if chips else ""))
        style(fig, None, height)
        fig.update_layout(title=None, margin=dict(l=8, r=20, t=44 if legend else 12, b=44),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="", font=dict(size=12)),
                          showlegend=legend, font=dict(size=13))
        plot(fig)
        # 차트 아래는 '사업PM 판단' 한 줄 + 해석·비교 기준 작은 한 줄 (핵심 수치는 차트 위 칩과 중복되므로 합침)
        html(f'<div class="ow-chart-f2"><div class="pm"><b>사업PM 판단</b><span>{escape(decision)}</span></div></div>'
             f'<div class="ow-chart-b">{escape(analysis)} · 기준: {escape(basis)}</div>')


def pp(x: float, digits: int = 1) -> str:
    """%p 변화 폭 표기 (+/− 부호 포함)."""
    return f"{x:+.{digits}f}%p"


def hpair(cats: list[str], before: list[float], after: list[float], *, xtitle: str, names: tuple[str, str],
          xmax: float | None = None) -> go.Figure:
    """대조군(회색) vs 실험군(파랑) 가로 막대 쌍. 변화 폭은 행 이름에 붙여 모바일에서도 겹치지 않게 한다."""
    labels = [f"{c}  <b>{pp(a - b)}</b>" for c, b, a in zip(cats, before, after)]
    fig = go.Figure()
    fig.add_bar(y=labels, x=before, name=names[0], orientation="h", marker_color=C_CTRL,
                text=[f"{v:.1f}%" for v in before], textposition="outside", cliponaxis=False)
    fig.add_bar(y=labels, x=after, name=names[1], orientation="h", marker_color=C_TREAT,
                text=[f"{v:.1f}%" for v in after], textposition="outside", cliponaxis=False)
    top = xmax if xmax is not None else max(before + after) * 1.25
    fig.update_layout(barmode="group", bargap=0.28, bargroupgap=0.06, uniformtext=dict(minsize=11, mode="show"))
    fig.update_yaxes(autorange="reversed", automargin=True, title="", tickfont=dict(size=13))
    fig.update_xaxes(title=xtitle, range=[0, top], ticksuffix="%", rangemode="tozero")
    return fig


def fmt_int(x) -> str:
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:,.0f}"


def fmt_won(x) -> str:
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:,.0f}원"


def pct(x) -> str:
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.1f}%"


def code_counts(v: pd.DataFrame) -> pd.Series:
    """복수 코딩 집계: 주 분류 + 보조 분류 (합계가 표본 수보다 클 수 있음)."""
    codes = [c for _, r in v.iterrows() for c in opinion_codes(r)]
    return pd.Series(codes, dtype=object).value_counts().reindex(OPINION_CATEGORIES, fill_value=0)


def image_slot(sid: str, statuses: dict) -> None:
    """검증을 통과한 한국어 스크린샷만 표시. 아니면 필요한 이미지를 안내하는 16:9 자리."""
    stt = statuses.get(sid)
    if stt is None:
        return
    if stt.ok:
        st.image(str(stt.path), caption=stt.caption, width="stretch")
        return
    reasons = "".join(f"<li>{escape(r)}</li>" for r in stt.reasons[:4])
    html(f'<div class="ow-slot"><div class="ow-slot-in"><div class="ow-slot-k">최신 한국어 스크린샷 필요</div>'
         f'<div class="ow-slot-t">{escape(stt.slot.get("title", ""))}</div>'
         f'<div class="ow-slot-d">{escape(stt.slot.get("need", ""))}</div>'
         f'<div class="ow-slot-f">assets/overwatch/{escape(stt.slot.get("file", ""))}</div>'
         f'<ul class="ow-slot-r">{reasons}</ul></div></div>')


# ----------------------------------------------------------------------
# 실제 게임 화면 (이미지 중심)
# 표시 박스 좌표는 원본 1920×1080 픽셀 기준. 화면에서 직접 확인한 사실만 적는다 (기획자 관찰).
SHOT_W, SHOT_H = 1920, 1080
SHOT_NOTES: dict[str, dict] = {
    "hero_select": {"label": "영웅 선택 화면 (훈련장)",
        "marks": [("돌격", "", (90, 762, 573, 921), ""), ("공격", "", (597, 762, 1323, 921), ""),
                  ("지원", "", (1344, 762, 1833, 921), "right")],
        "facts": ["영웅 선택 화면 하단에 54명의 초상화가 역할별로 한 번에 나열된다",
                  "초상화에는 이름이 없고, 고른 영웅(시온)만 이름이 표시된다"],
    },
    "match_select": {"label": "영웅 선택 화면 (실제 경기)",
        "marks": [("남은 시간", "0:01", (40, 250, 310, 330), "below"),
                  ("팀 조합", "팀원 영웅이 함께 표시", (262, 487, 1650, 757), ""),
                  ("영웅 설명", "한 줄", (1455, 184, 1868, 224), "right below")],
        "facts": ["실제 경기에서는 '팀 구성까지 남은 시간' 안에 영웅을 골라야 한다 (캡처 시점 0:01)",
                  "고른 영웅의 설명은 우측 상단 한 줄뿐이다 — 정크랫: '적을 처치하면 잠깐 동안 재장전 속도가 증가합니다'",
                  "팀원이 고른 영웅을 보며 조합을 맞춰야 해, 낯선 영웅이 많을수록 판단할 것이 늘어난다"],
    },
    "returning_menu": {"label": "복귀 시 메인 화면",
        "marks": [("이벤트", "군림", (90, 195, 615, 525), ""),
                  ("도전 과제", "", (1482, 120, 1887, 468), "right below"),
                  ("이벤트·패스·상점", "", (102, 780, 1842, 933), "")],
        "facts": ["접속하면 이벤트 '군림' 배너와 이벤트·배틀 패스·상점 카드가 가장 크게 보인다",
                  "우측에는 발굴 입문·일일·주간 도전 과제가 표시된다",
                  "이 화면에는 마지막 접속 이후 바뀐 점(신규 영웅·역할 변경)을 요약한 안내가 따로 보이지 않는다"],
    },
    "skill_detail": {"label": "영웅 정보·스킬 설명",
        "marks": [("무기·궁극기", "", (60, 180, 630, 600), ""), ("기술 3 · 지속 능력", "", (667, 180, 1215, 720), ""),
                  ("특전 4", "2·3레벨 선택", (1275, 180, 1875, 690), "right")],
        "facts": ["영웅 1명 설명에 무기 1 · 궁극기 1 · 기술 3 · 지속 능력 1 · 특전 4, 모두 10개 항목이 있다 (시온 기준)",
                  "54명이면 익힐 항목이 수백 개다. 특전은 경기 중 레벨에 따라 고르는 선택지라 상대 영웅의 변수도 늘어난다",
                  "이 화면은 영웅을 직접 골라 찾아 들어가야 하며, '방금 나를 처치한 기술'을 따로 보여 주지는 않는다"],
    },
    "mission_screen": {"label": "도전 과제 화면",
        "marks": [("안내", "AI 상대·사용자 지정 게임 제외", (60, 326, 740, 372), ""),
                  ("남은 기간", "18일", (1610, 205, 1875, 282), "right"),
                  ("경기 수 과제", "5~20회 · 승리 시 2배", (102, 382, 1827, 660), "right"),
                  ("잠김", "선행 과제 필요", (102, 663, 1827, 938), "below")],
        "facts": ["이벤트 도전 과제 8개가 모두 '게임 N회 완료 (승리 시 진척도 두 배)' 형식이다",
                  "대부분의 도전 과제는 사용자 지정 게임·AI 상대 연습에서 완료할 수 없다고 안내한다",
                  "기술 사용·역할 목표처럼 '배우는 행동'을 기준으로 한 과제는 이 화면에 없다"],
    },
    "combat_scene": {"label": "전투 화면",
        "marks": [("처치 기록", "", (1530, 72, 1892, 160), "right below"),
                  ("처치 알림", "상대 이름만", (870, 750, 1050, 795), "below"),
                  ("내 기술", "", (1505, 915, 1870, 1028), "right")],
        "facts": ["처치되면 화면 가운데에 'OOO에게 죽음' 알림과 우측 상단 처치 기록이 뜬다",
                  "누구에게 당했는지는 보이지만, 어떤 기술에 당했고 어떻게 대응하면 되는지는 이 화면에 없다"],
    },
}


@st.cache_data(show_spinner=False, max_entries=48)
def _b64(path: str, mtime: float, blur: tuple, crop: tuple | None, max_w: int) -> str:
    return web_jpeg_b64(path, blur, crop, max_w)


def _src(stt, max_w: int = 1600) -> str:
    return _b64(str(stt.path), stt.path.stat().st_mtime, tuple(tuple(b) for b in stt.slot.get("blur", [])), None, max_w)


def _pct(v: float, total: int) -> str:
    return f"{v / total * 100:.2f}%"


def shot_html(sid: str, statuses: dict, *, marks: bool = True, facts: bool = True, title: str | None = None,
              lead: str = "", size: str = "", tag: str = "실제 게임 화면", mark_desc: dict | None = None,
              max_w: int = 1600) -> str:
    """검증 통과한 실제 스크린샷을 '실제 게임 화면' 프레임으로 감싼 HTML. 미통과 시 빈 문자열."""
    stt = statuses.get(sid)
    if stt is None or not stt.ok:
        return ""
    note_ = dict(SHOT_NOTES.get(sid, {}))
    if mark_desc:
        note_["marks"] = [(lab, mark_desc.get(lab, desc), box, cls) for lab, desc, box, cls in note_.get("marks", [])]
    boxes = ""
    if marks:
        for i, (lab, desc, (x0, y0, x1, y1), cls) in enumerate(note_.get("marks", []), 1):
            d = f" <b>{escape(desc)}</b>" if desc else ""
            boxes += (f'<div class="ow-mark {cls}" style="left:{_pct(x0, SHOT_W)};top:{_pct(y0, SHOT_H)};'
                      f'width:{_pct(x1 - x0, SHOT_W)};height:{_pct(y1 - y0, SHOT_H)}"><span><i>{i}</i>{escape(lab)}{d}</span></div>')
    # 사진 아래에는 짧은 설명(10~20자)만. 촬영일·출처는 탭 맨 아래 '이미지 출처 및 촬영 정보'에 한 번만 표시한다.
    _FIGS.append((sid, stt))
    num = len(_FIGS)
    title_ = escape(title or stt.slot.get("title", ""))
    cap = f"<figcaption>{lead}</figcaption>" if lead else ""
    return (f'<figure class="ow-shot {size}"><div class="ow-shot-bar"><span class="ow-shot-tag">그림 {num}</span>{title_}</div>'
            f'<div class="ow-shot-img"><img src="data:image/jpeg;base64,{_src(stt, max_w)}" alt="{title_}" loading="lazy">{boxes}</div>'
            f'{cap}</figure>')


_FIGS: list = []   # 현재 탭에 표시된 실제 게임 화면 (그림 번호 · 출처 표기용)


def shot_facts(sids: list[str]) -> None:
    """화면별 관찰 사실(긴 설명)은 펼쳐보기 안에 보존."""
    rows = [(sid, SHOT_NOTES[sid]) for sid in sids if sid in SHOT_NOTES]
    if not rows:
        return
    with st.expander("화면별 관찰 사실 (자세히)"):
        html("".join(f'<div class="ow-facts"><b>{escape(n.get("label", sid))}</b>'
                     + "".join(f"<span>{i}. {escape(lab)}{' · ' + escape(desc) if desc else ''}</span>"
                               for i, (lab, desc, _, _) in enumerate(n.get("marks", []), 1))
                     + bullets(n.get("facts", [])) + "</div>" for sid, n in rows))


def image_credits() -> None:
    """탭 하단에 이미지 출처·촬영 정보를 한 번만. 값이 다른 이미지는 그림 번호별로 나눠 적는다."""
    if not _FIGS:
        return
    groups: dict = {}
    for i, (sid, stt) in enumerate(_FIGS, 1):
        s = stt.slot
        k = (s.get("source") or "-", s.get("captured_at") or "확인 안 됨", s.get("game_version") or "버전 미기재")
        groups.setdefault(k, []).append(i)
    blurred = [i for i, (_, stt) in enumerate(_FIGS, 1) if stt.slot.get("blur")]
    lines = "".join(
        f"<li>그림 {', '.join(map(str, nums))} · {escape(src)} · 촬영 {escape(cap)} (파일 전송 시각 기준) · {escape(ver)} · 한국어 UI</li>"
        for (src, cap, ver), nums in groups.items())
    if blurred:
        lines += f"<li>다른 플레이어 닉네임 가림: 그림 {', '.join(map(str, blurred))}</li>"
    html(f'<div class="ow-credits"><b>이미지 출처 및 촬영 정보</b><ul>{lines}</ul></div>')


def shot(sid: str, statuses: dict, **kw) -> None:
    """실제 스크린샷 표시. 검증 전이면 '최신 한국어 스크린샷 필요' 자리."""
    h = shot_html(sid, statuses, **kw)
    if h:
        html(h)
    else:
        image_slot(sid, statuses)


def real_vs_mock_key() -> None:
    html('<div class="ow-key"><span class="k-real">실제 게임 화면 (현재 · 직접 캡처)</span>'
         '<span class="k-mock">기획 시안 (제안 기능 · 실제 게임에 없음)</span></div>')


def col_head(kind: str, text: str) -> None:
    html(f'<div class="ow-colh {kind}">{escape(text)}</div>')


def hero_grid(heroes: dict, cutoff: str | None = None) -> None:
    chips = []
    for h in heroes["heroes"]:
        cls, mark = "", ""
        if h.get("new_2026") and (cutoff is None or h["new_2026"] > cutoff):
            cls, mark = "new", f'<small>{h["new_2026"][5:]}</small>'
        elif h.get("recent_catchup") and cutoff is None:
            cls = "recent"
        if h.get("role_changed") and (cutoff is None or h["role_changed"] > cutoff):
            cls += " changed"
        chips.append(f'<span class="ow-hero {cls}">{escape(h["name"])}{mark}</span>')
    html(f'<div class="ow-heroes">{"".join(chips)}</div>')


# ======================================================================
def render() -> None:
    g = GAMES["overwatch"]
    try:
        kp, rs, heroes = load_json("korea_publishing.json"), load_json("restart.json"), load_json("heroes.json")
        steam, pc, ops, tl = load_steam(), load_pcbang(), load_opinions(), load_timeline()
    except OverwatchDataError as e:
        st.error(f"오버워치 자료를 불러오지 못했습니다: {e}")
        return
    manifest = load_manifest()
    statuses = all_status(manifest)

    html('<div class="gp-ow-page"></div>')  # 오버워치 전용 반응형 CSS 범위 표식
    plan = experiment_plan(rs["experiment"])
    _cover(rs, ops, plan)

    # 01~06 탭 전환: 선택한 섹션 하나만 표시 (나머지 5개는 그리지 않음)
    i = tab_nav()
    badge_legend()
    html(f'<div class="ow-pane-mark" data-tab="{SECTIONS[i][0]}"></div>')  # 정적 보고서가 탭 경계를 찾는 표식
    _FIGS.clear()
    [lambda: _s1_summary(rs, ops, statuses, plan, heroes),
     lambda: _s2_evidence(rs, kp, steam, pc, ops, statuses),
     lambda: _s3_hypothesis(rs, ops),
     lambda: _s4_experience(rs, ops, heroes, tl, statuses, plan),
     lambda: _s5_kpi(rs, plan),
     lambda: _s6_execution(rs, g, statuses, plan)][i]()
    image_credits()


# ----------------------------------------------------------------------
def _cover(rs: dict, ops: pd.DataFrame, plan: dict) -> None:
    """탭 위에 항상 보이는 부분: 제목 한 줄 + '문제 → 해결 → 검증할 이유' 카드 하나."""
    cv = rs["cover"]
    v = ops[ops["verified"]]
    learn = sum(bool(set(opinion_codes(r)) & LEARNING_CODES) for _, r in v.iterrows())
    mde = plan["seg"]["복귀"]["mde"]["D7"]
    html(f'<div class="ow-cover"><div class="ow-cover-t">{escape(cv["title"])}</div>'
         f'<div class="ow-cover-c">{escape(cv["copy"])}</div></div>')
    html('<div class="ow-hero3">'
         f'<div><span>문제</span><b>{escape(cv["problem"])}</b><small>{escape(cv.get("problem_sub", ""))}</small></div>'
         f'<div><span>해결</span><b>{escape(cv["solution"])}</b><small>{escape(cv.get("solution_sub", ""))}</small></div>'
         f'<div><span>검증할 이유</span><b>의견 {len(v)}건 중 {learn}건이 학습·적응 어려움</b>'
         f'<small>복귀 D7 +{mde:.1f}%p를 기준으로 단계적 A/B 테스트</small></div></div>')


def _hero_block(heroes: dict, statuses: dict) -> None:
    """01 탭: 문제를 설명하는 핵심 이미지(최신 영웅 선택 화면) + 역할별 수. 확대·목록은 펼쳐보기."""
    n_all = len(heroes["heroes"])
    n_new = sum(1 for h in heroes["heroes"] if h.get("new_2026"))
    n_recent = sum(1 for h in heroes["heroes"] if h.get("recent_catchup"))
    stt = statuses.get("hero_select")
    roles = (stt.slot.get("role_counts") or {}) if stt else {}
    # 역할별 수(돌격·공격·지원)는 이미지 위 표시로만 보여 주고 별도 숫자 카드는 두지 않는다 (중복 제거)
    shot("hero_select", statuses, size="hero", facts=False,
         title=f"최신 영웅 선택 화면 · 한 화면에 {sum(roles.values()) or n_all}명",
         lead="초상화에 이름이 없고, 고른 영웅만 이름 표시",
         mark_desc={k: f"{v}명" for k, v in roles.items()})
    if stt is not None and stt.ok and roles and sum(roles.values()) != n_all:
        st.warning(f"화면에서 센 영웅 {sum(roles.values())}명이 영웅 목록 {n_all}명과 다릅니다. image_manifest.json 을 확인하세요.")
    with st.expander(f"자세히 보기 · 초상화 확대 · 공식 영웅 {n_all}명 이름"):
        if stt is not None and stt.ok:
            zoom = _b64(str(stt.path), stt.path.stat().st_mtime, tuple(tuple(b) for b in stt.slot.get("blur", [])),
                        (80, 760, 1840, 930), 1760)
            html('<div class="ow-zoom"><div class="ow-zoom-h"><span><span class="ow-shot-tag">실제 게임 화면</span> 영웅 초상화 영역 확대</span>'
                 '<span>초상화에는 이름이 없다 · 고른 영웅만 이름 표시</span></div>'
                 f'<img src="data:image/jpeg;base64,{zoom}" alt="영웅 선택 화면 초상화 영역 확대"></div>')
        tiles([
            ("공식 영웅 수", f"{n_all}명", f'{b_real()} {link(heroes["source"], "공식 영웅 페이지")} · {heroes["checked_at"]} 기준'),
            ("2026년 신규 영웅", f"{n_new}명", f'{b_real()} 공식 패치노트'),
            ("블리자드 복귀 요약의 '최근 영웅'", f"{n_recent}명", f'{b_real()} 시즌 1 공지 기사'),
        ])
        hero_grid(heroes)
        html('<div class="ow-legend"><span class="ow-hero new">2026 신규</span><span class="ow-hero recent">복귀 요약 소개</span>'
             '<span class="ow-hero changed">역할 변경</span><span class="ow-legend-t">영웅 수가 늘었다는 사실만으로 이탈 원인을 단정하지 않습니다.</span></div>')
    if n_all != heroes.get("official_count", n_all):
        st.warning(f"영웅 목록 {n_all}명이 공식 집계 {heroes.get('official_count')}명과 다릅니다. heroes.json 을 확인하세요.")


def _decision_cards(rs: dict, plan: dict, n_new: int) -> str:
    """PM 의사결정 요약 5개 카드. 비용·효과는 가정값으로 계산하고 배지로 표시."""
    ex, rice = rs["experiment"], {x["key"]: x for x in rs["rice"]["items"]}
    r = plan["seg"]["복귀"]
    q = plan["quarter"]
    mcost = ex["cost"]["monthly_cost_per_person"]
    a_cost = rice["A"]["effort"] * mcost
    a_added = q["added_d7"]["A"]          # 분기 복귀 유입 × MDE (05 실험 설계와 같은 가정)
    sc = plan["sched"]
    cards = [
        ("왜 먼저인가", b_real(), f"2026년 신규 영웅 {n_new}명 출시(실적)에 연 10명 계획(공식 발표) → 변경점이 매 시즌 쌓인다."),
        ("무엇으로 판단", b_mock(), f"복귀 D7 잔존율 · 최소 개선 폭 +{r['mde']['D7']:.1f}%p (배정 기준)."),
        ("비용 대비 효과", b_sim(),
         f"A {a_cost / 1e4:,.0f}만 원 ÷ 분기 추가 D7 {a_added:,.0f}명 ≈ 1명당 {a_cost / a_added:,.0f}원."),
        ("확대·중단 기준", b_mock(), f"{sc['e1_d7']}주차 D7이 유의하고 MDE 이상이면 확대, 아니면 수정·중단."),
    ]
    return ('<div class="ow-dec">' + "".join(
        f'<div class="ow-dec-i"><div class="ow-dec-q">{escape(q)} <span class="ow-dec-b">{b}</span></div>'
        f'<div class="ow-dec-a">{escape(a)}</div></div>' for q, b, a in cards) + "</div>")


# ======================================================================
# 01 문제 정의
def _s1_summary(rs: dict, ops: pd.DataFrame, statuses: dict, plan: dict, heroes: dict) -> None:
    s = rs["summary"]
    v = ops[ops["verified"]]
    ret = v[v["user_type"] == "복귀"]
    ret_learning = sum(bool(set(opinion_codes(r)) & LEARNING_CODES) for _, r in ret.iterrows())
    all_learning = sum(bool(set(opinion_codes(r)) & LEARNING_CODES) for _, r in v.iterrows())
    # 상단 카드(문제 → 해결)와 겹치는 문제 정의·결론 박스는 두지 않는다. 해결안 3개 → 의사결정 → 화면 → 근거 순서
    sub("막히는 지점 3곳 → 해결안 3가지", b_mock())
    core = sorted([x for x in rs["strategies"] if x["core"]], key=lambda x: x.get("phase", ""))
    html('<div class="ow-map">' + "".join(
        f'<div class="ow-map-i"><div class="ow-map-p"><span>문제</span>{escape(x["problem"])}</div><div class="ow-map-a">→</div>'
        f'<div class="ow-map-s"><span>{x["key"]} · {escape(x.get("phase", ""))}</span><b>{escape(x["name"])}</b>'
        f'<small>{escape(x["tagline"])}</small></div></div>' for x in core) + "</div>")

    sub("PM 의사결정 요약")
    html(_decision_cards(rs, plan, sum(1 for h in heroes["heroes"] if h.get("new_2026"))))

    sub("문제를 보여 주는 화면", b_real())
    _hero_block(heroes, statuses)

    # 근거 3단계(사실·의견·가설)는 02·03 탭과 겹치므로 기본 화면에서는 접어 둔다
    exp = st.expander("자세히 보기 · 근거 3단계 · 사업PM 관점 · 첫 전투까지의 화면 4장")
    layers = []
    for L in s["evidence_layers"]:
        items = list(L["items"])
        if not items:  # 이용자 의견은 데이터에서 직접 계산
            items = [f"의견 {len(v)}건 중 학습·적응 어려움 {all_learning}건",
                     f"복귀 유저 {len(ret)}건 중 {ret_learning}건",
                     "전체 이용자 대표 표본은 아님"]
        layers.append(f'<div class="ow-layer {L["kind"]}"><div class="ow-layer-h">{KIND[L["kind"]]()} {escape(L["title"])}</div>'
                      f'{bullets(items)}</div>')
    with exp:
        html(f'<div class="ow-layers">{"".join(layers)}</div>')
        html('<div class="ow-why">' + "".join(
            f'<div class="ow-why-i">{KIND[w["kind"]]()}<span>{escape(w["text"])}</span></div>' for w in s["why_pm"]) + "</div>")
        steps = [
            ("returning_menu", "① 메인 화면", "변경점 안내 없음"),
            ("match_select", "② 영웅 선택", "시간 제한, 설명 한 줄"),
            ("skill_detail", "③ 스킬 확인", "영웅 1명 = 설명 10개"),
            ("combat_scene", "④ 전투", "상대 이름만, 대응법 없음"),
        ]
        cards = [shot_html(sid, statuses, marks=False, facts=False, max_w=800, title=ttl, lead=escape(problem))
                 for sid, ttl, problem in steps]
        if all(cards):
            html(f'<div class="ow-journey">{"".join(cards)}</div>')
        else:
            for sid, _, _ in steps:
                image_slot(sid, statuses)


# ======================================================================
# 2 실제 근거
def _s2_evidence(rs: dict, kp: dict, steam: pd.DataFrame, pc: pd.DataFrame, ops: pd.DataFrame, statuses: dict) -> None:
    head("근거: 의견 · 지표 · 화면")
    v = ops[ops["verified"]]
    _opinion_chart(v)                       # 핵심 차트 1 · 실제 자료
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        _steam_chart(steam)                 # 핵심 차트 2 · 실제 자료
    with c2:
        _pc_chart(pc)                       # 핵심 차트 3 · 실제 자료
    html('<div class="ow-limits"><b>읽는 법</b>'
         f'<span>의견 {len(v)}건 = 자발적 게시글 · 비율·이탈 원인 아님</span>'
         '<span>Steam·PC방 = 시장 반응 참고 · 복귀 이탈과 인과 연결 안 함</span>'
         '<span>원인 확인은 05의 A/B 테스트로</span></div>')
    t = st.tabs([f"유저 의견 {len(v)}건", "게임 화면", "공식 업데이트", "지표 원자료"])
    with t[0]:
        _opinions(rs, ops)
    with t[1]:
        sub("직접 캡처한 최신 한국어 화면", b_real())
        caps = {"match_select": "제한 시간 안에 영웅 선택", "returning_menu": "변경점 안내가 보이지 않음",
                "skill_detail": "영웅 1명 = 설명 10개", "mission_screen": "과제 = 경기 횟수",
                "combat_scene": "상대 이름만 표시"}
        shot("match_select", statuses, size="wide", lead=caps["match_select"])
        pairs = [("returning_menu", "skill_detail"), ("mission_screen", "combat_scene")]
        for a, b in pairs:
            ha, hb = shot_html(a, statuses, max_w=1200, lead=caps[a]), shot_html(b, statuses, max_w=1200, lead=caps[b])
            if ha and hb:
                html(f'<div class="ow-grid2">{ha}{hb}</div>')
            else:
                shot(a, statuses, lead=caps[a])
                shot(b, statuses, lead=caps[b])
        st.caption("파란 상자·번호는 설명용 표시이며 화면은 수정하지 않았습니다.")
        shot_facts(["match_select", "returning_menu", "skill_detail", "mission_screen", "combat_scene"])

    with t[2]:
        sub("블리자드의 기존 지원")
        html('<div class="ow-timeline">' + "".join(
            f'<div class="ow-tl"><div class="ow-tl-d">{escape(o["date"])}</div><div class="ow-tl-t">{escape(o["title"])}</div>'
            f'<div class="ow-tl-b">{escape(o["fact"])}</div><div class="ow-tl-s">{link(o["url"], "공식 원문")}</div></div>'
            for o in rs["official"]) + "</div>")
        note("RE:START는 기존 지원을 대체하지 않고 보완한다.")
        with st.expander("자세히 보기 · 기존 기능의 한계 · 넥슨 퍼블리싱 범위"):
            table(["기능", "한계 또는 확인이 필요한 부분"], [[escape(o["title"]), escape(o["limit"])] for o in rs["official"]], badge_html=b_interp())
            st.markdown("**역할 구분** — 넥슨: 한국 PC 버전(Steam 제외) 퍼블리싱·라이브 운영·PC방 / 블리자드: 게임 개발·글로벌 운영·Steam·콘솔")
            src = {x["id"]: x for x in kp["sources"]}
            table(["항목", "확인 내용", "출처"],
                  [[escape(i["topic"]), escape(i["official"]), " · ".join(link(src[k]["url"], src[k]["kind"]) for k in i["source_ids"])]
                   for i in kp["items"]], badge_html=b_real())
            st.caption(f"블리자드 공식 사이트·언론 보도 기준 · 확인일 {COLLECTED_AT}")

    with t[3]:
        _metric_sources(pc)


def _steam_chart(steam: pd.DataFrame) -> None:
    if steam.empty:
        st.info("Steam 자료를 불러오지 못했습니다.")
    else:
        last = steam.iloc[-1]
        d = steam.tail(12).reset_index(drop=True)
        pk = d.loc[d["avg_players"].idxmax()]
        first = d.iloc[0]
        colors = [C_TREAT if m == pk["month"] else C_MUTED for m in d["month"]]
        fig = go.Figure(go.Bar(x=d["month"], y=d["avg_players"], marker_color=colors,
                               text=[f"{v / 1000:,.0f}천" for v in d["avg_players"]], textposition="outside", cliponaxis=False,
                               hovertemplate="%{x|%Y-%m} · 월평균 %{y:,.0f}명<extra></extra>"))
        fig.update_yaxes(title="월평균 동시접속자 (명)", tickformat=",", rangemode="tozero", range=[0, d["avg_players"].max() * 1.18])
        fig.update_xaxes(title="월", tickformat="%y.%m", dtick="M1")
        chart_card(fig, key="steam", kind="real", title="Steam 월평균 동시접속자 (12개월)",
                   unit="명 · 파랑 = 최고치",
                   kpis=[(f"최고 {pk['month']:%Y년 %m월}", f"{pk['avg_players']:,.0f}명"),
                         (f"최근 {last['month']:%Y년 %m월}", f"{last['avg_players']:,.0f}명"),
                         ("최고치 대비 최근", f"{(last['avg_players'] / pk['avg_players'] - 1) * 100:+.0f}%")],
                   analysis=f"{pk['month']:%y.%m} 최고 → 최근 {last['avg_players'] / pk['avg_players'] * 100:.0f}% 수준 · 감소 원인은 이 자료로 알 수 없음",
                   decision="유입 규모 참고용 · 이탈 원인 근거로 쓰지 않음",
                   basis=f"{first['month']:%y.%m}~{last['month']:%y.%m} 같은 출처 · Steam만 포함",
                   height=300, legend=False, cols=("월", "월평균 동시접속자 (명)"))


def _pc_chart(pc: pd.DataFrame) -> None:
    tracker = st.radio("집계원", ["게임트릭스", "더로그"], horizontal=True, key="ow_pc_tracker")
    q = pc[pc["plottable"] & (pc["tracker"] == tracker)]
    if q.empty:
        st.info("선택한 집계원의 자료가 없습니다.")
    else:
        daily, weekly = q[q["granularity"] == "일간"], q[q["granularity"] != "일간"]
        cut = pd.Timestamp("2026-08-12")
        before, after = q[q["period_start"] < cut], q[q["period_start"] >= cut]
        fig = go.Figure()
        fig.add_scatter(x=daily["period_start"], y=daily["share_pct"], mode="markers", name="일간 점유율",
                        marker=dict(size=12, color=[C_CTRL if t < cut else C_TREAT for t in daily["period_start"]],
                                    line=dict(color="white", width=1)),
                        customdata=daily[["rank"]], hovertemplate="%{x|%m-%d} · %{y:.2f}% (%{customdata[0]}위)<extra></extra>")
        for j, r in enumerate(weekly.itertuples()):
            fig.add_scatter(x=[r.period_start, r.period_end], y=[r.share_pct] * 2, mode="lines", name="주간 점유율",
                            line=dict(color=C["sky"], width=8), showlegend=j == 0, legendgroup="w",
                            hovertemplate=f"{r.granularity} · {r.share_pct:.2f}% ({int(r.rank)}위)<extra></extra>")
        fig.add_vline(x=cut, line_dash="dot", line_color=C["navy"])
        fig.add_annotation(x=cut, y=12, text="넥슨 서비스 개시 8/12", showarrow=False, xanchor="left", xshift=4,
                           font=dict(size=11, color=C["navy"]))
        fig.update_yaxes(title="PC방 점유율 (%)", range=[0, 12.5], ticksuffix="%")
        fig.update_xaxes(title="기준일 (2026년)", range=[pd.Timestamp("2026-03-15"), pd.Timestamp("2026-10-31")], tickformat="%m월")
        # 비교 기준: 같은 집계원·같은 단위(일간)의 '서비스 직전 마지막 값' vs '서비스 후 마지막 값'
        db, da = daily[daily["period_start"] < cut], daily[daily["period_start"] >= cut]
        kp, analysis = [], "서비스 전후를 같은 단위(일간)로 비교할 자료가 부족하다."
        if not db.empty and not da.empty:
            b0, a0 = db.sort_values("period_start").iloc[-1], da.sort_values("period_start").iloc[-1]
            diff = a0["share_pct"] - b0["share_pct"]
            kp = [(f"서비스 직전 {b0['period_start']:%m/%d} (일간)", f"{b0['share_pct']:.2f}%"),
                  (f"서비스 후 {a0['period_start']:%m/%d} (일간)", f"{a0['share_pct']:.2f}%"),
                  ("변화 폭 (일간끼리)", f"<b>{pp(diff, 2)}</b>")]
            earlier = before[before["share_pct"] > b0["share_pct"]]
            caveat = (f"{earlier.iloc[0]['period_start']:%m/%d} 값 {earlier.iloc[0]['share_pct']:.1f}%가 더 높음" if not earlier.empty
                      else "이벤트·시즌 겹침")
            analysis = f"일간 {b0['share_pct']:.2f}% → {a0['share_pct']:.2f}% ({pp(diff, 2)}) · {caveat}"
        if not kp:   # 전후 비교가 안 될 때만 기간 최고값을 칩으로 (칩은 최대 3개)
            mx = q.loc[q["share_pct"].idxmax()]
            rk = f" · {int(mx['rank'])}위" if pd.notna(mx["rank"]) else ""
            kp.append((f"기간 최고 {mx['period_start']:%m/%d}{rk}", f"{mx['share_pct']:.1f}%"))
        chart_card(fig, key="pc", kind="real", title=f"한국 PC방 점유율 ({tracker})",
                   unit="% · 회색 = 서비스 전, 파랑 = 후 · 가로선 = 주간",
                   kpis=kp, analysis=analysis,
                   decision="시장 반응 참고 · PC방 연계(D)는 A 검증 후 판단",
                   basis=f"같은 집계원·같은 단위(일간)끼리 비교",
                   height=300, cols=("기준일", "PC방 점유율 (%)"), series="집계 단위")


def _metric_sources(pc: pd.DataFrame) -> None:
    with st.expander("자세히 보기 · 출처와 해석 주의"):
        st.markdown(f"출처: [{STEAM_SOURCE['name']}]({STEAM_SOURCE['url']}) · 확인일 {COLLECTED_AT}")
        st.caption("Battle.net·넥슨 클라이언트·콘솔 이용자는 빠져 있다. 2026년 2월 급증은 시즌 1과 명칭 변경 시기가 겹쳐 원인을 하나로 볼 수 없다.")
    with st.expander("자세히 보기 · 원자료와 집계 기준"):
        st.caption("두 집계원은 표본 PC방이 달라 같은 날에도 순위가 다르다(9/13 더로그 2위, 게임트릭스 5위). PC방 이벤트·신규 시즌이 겹쳐 상승 원인을 단정할 수 없고, 계약 발표 이전 수치는 확보하지 못했다.")
        st.dataframe(
            pc[["tracker", "period_start", "granularity", "rank", "share_pct", "source_publisher", "source_url", "status"]]
            .rename(columns={"tracker": "집계원", "period_start": "기준일", "granularity": "단위", "rank": "순위",
                             "share_pct": "점유율(%)", "source_publisher": "보도 매체", "source_url": "원문", "status": "상태"}),
            hide_index=True, column_config={"원문": st.column_config.LinkColumn("원문", display_text="열기"),
                                            "기준일": st.column_config.DateColumn(format="YYYY-MM-DD")})


def _opinion_chart(v: pd.DataFrame) -> None:
    cnt = code_counts(v)
    learn = int(sum(bool(set(opinion_codes(r)) & LEARNING_CODES) for _, r in v.iterrows()))
    top_cat, top_n = cnt.idxmax(), int(cnt.max())
    colors = [C_TREAT if c in LEARNING_CODES else C_MUTED for c in cnt.index]
    fig = go.Figure(go.Bar(y=cnt.index, x=cnt.values, orientation="h", marker_color=colors, text=[f"{x}건" for x in cnt.values],
                           textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x}건<extra></extra>"))
    fig.update_yaxes(autorange="reversed", automargin=True, title="")
    fig.update_xaxes(title="언급 수 (건)", range=[0, max(cnt.max(), 1) * 1.3 + 1], rangemode="tozero")
    chart_card(fig, key="op", kind="real", title=f"문제 유형별 언급 수 (의견 {len(v)}건)",
               unit="건 · 중복 집계 · 파랑 = 학습·적응 관련",
               kpis=[(f"1위 · {top_cat}", f"{top_n}건"), ("학습·적응 어려움을 언급한 의견", f"{learn}<small> / {len(v)}건</small>"),
                     ("반대 사례 · 긍정적인 학습 경험", f"{int(cnt.get('긍정적인 학습 경험', 0))}건")],
               analysis=f"1위 '{top_cat}' {top_n}건 · 매칭 {int(cnt.get('매칭·실력 차이', 0))}건도 존재",
               decision="A·C 우선 검증, 매칭·비매너는 함께 추적",
               basis=f"자발적 게시글 · 전체 이용자 비율 아님",
               height=380, legend=False, cols=("문제 유형", "언급 수 (건)"))


def _opinion_card(r) -> str:
    tone = {"부정": "neg", "중립": "neu", "긍정": "pos"}.get(r["sentiment"], "neu")
    plat = "인벤" if "인벤" in r["platform"] else ("디시인사이드" if "디시" in r["platform"] else "블리자드 포럼")
    tags = " · ".join(opinion_codes(r))
    return (f'<div class="ow-quote {tone}"><div class="ow-quote-tag">{escape(r["sentiment"])} · {escape(r["user_type"])} · {escape(tags)}</div>'
            f'<div class="ow-quote-t">{escape(r["summary_ko"])}</div>'
            f'<div class="ow-quote-o">“{escape(r["quote_original"])}”</div>'
            f'<div class="ow-quote-m">{plat} · {escape(r["published_date"])} · {link(r["source_url"], "원문 보기")}</div></div>')


def _sample_card(v, plat, utype, n_ko, n_en) -> None:
    html('<div class="ow-sample"><div class="ow-sample-h">표본과 분류 기준</div><div class="ow-sample-g">'
         f'<div><b>표본 구성</b>{bullets([" · ".join(f"{k} {n}" for k, n in plat.items()), " · ".join(f"{k} {n}" for k, n in utype.items()), f"한국어 {n_ko} · 영어 {n_en}"])}</div>'
         '<div><b>중복 제거·검증</b>' + bullets(["원문 링크를 열어 내용을 직접 확인한 글만 '검증 완료'",
                                              "같은 작성자로 추정되는 글은 1건만 집계",
                                              "주제와 무관하거나 원문을 확인할 수 없는 글은 제외 (아래 목록)"]) + '</div>'
         '<div><b>분류 방법</b>' + bullets(["기획자가 직접 분류 (AI 자동 분류 아님)",
                                          "주 분류 1개 + 보조 분류 복수 → 합계가 의견 수보다 많음",
                                          "긍정·중립 의견과 반대 사례도 그대로 포함"]) + '</div>'
         f'<div><b>해석 한계 {b_interp()}</b>' + bullets(["자발적 게시글이라 전체 이용자를 대표하는 통계 표본이 아니다",
                                                       "불편을 겪은 사람의 글이 더 많을 수 있다",
                                                       "언급 수는 '문제의 존재'를 보여 줄 뿐 '비율'이나 '이탈 원인'을 뜻하지 않는다"]) + '</div>'
         '</div></div>')


def _opinions(rs: dict, ops: pd.DataFrame) -> None:
    v = ops[ops["verified"]]
    other = ops[~ops["verified"]]
    if v.empty:
        st.info("검증된 유저 의견이 없습니다.")
        return
    n_ko, n_en = int((v["language"] == "한국어").sum()), int((v["language"] == "영어").sum())
    plat = v["platform"].map(lambda p: "인벤" if "인벤" in p else ("디시인사이드" if "디시" in p else "블리자드 포럼")).value_counts()
    utype = v["user_type"].value_counts()
    with st.expander("자세히 보기 · 표본 구성·중복 제거·분류 기준"):
        tiles([
            ("검증 완료 의견", f"{len(v)}건", f"목표 50건 · 한국어 {n_ko} · 영어 {n_en}"),
            ("부정 · 중립 · 긍정", " · ".join(str(int((v['sentiment'] == s).sum())) for s in ["부정", "중립", "긍정"]), "기획자 분류"),
            ("미검증·제외", f"{len(other)}건", "Reddit·유튜브 미확인, 중복·주제 무관"),
        ])
        _sample_card(v, plat, utype, n_ko, n_en)

    sub("대표 의견")
    c1, c2 = st.columns(2)
    view = c1.selectbox("보기", ["대표 의견 6건"] + OPINION_CATEGORIES, key="ow_op_view")
    tone = c2.selectbox("의견 방향", ["전체", "부정", "중립", "긍정"], key="ow_op_tone")
    if view == "대표 의견 6건":
        q = v[v["opinion_id"].isin(rs["rep_opinions"])]
    else:
        q = v[v.apply(lambda r: view in opinion_codes(r), axis=1)]
    if tone != "전체":
        q = q[q["sentiment"] == tone]
    q = q.sort_values("published_date", ascending=False)
    per = 4   # 한 화면 4건 (나머지는 페이지 이동 · 전체 표는 아래 펼쳐보기)
    pages = max(1, math.ceil(len(q) / per))
    page = st.number_input(f"페이지 (총 {pages}쪽 · {len(q)}건)", 1, pages, 1, key=f"ow_op_page_{view}_{tone}") if pages > 1 else 1
    chunk = q.iloc[(page - 1) * per: page * per]
    if chunk.empty:
        st.info("조건에 맞는 의견이 없습니다.")
    else:
        html(f'<div class="ow-grid2">{"".join(_opinion_card(r) for _, r in chunk.iterrows())}</div>')

    with st.expander(f"전체 의견 표 {len(v)}건 · 검색"):
        kw = st.text_input("검색어 (요약·원문 발췌)", key="ow_f_kw")
        t = v
        if kw.strip():
            k = kw.strip()
            t = t[t["summary_ko"].str.contains(k, case=False, regex=False) | t["quote_original"].str.contains(k, case=False, regex=False)]
        st.dataframe(
            t[["opinion_id", "platform", "published_date", "user_type", "sentiment", "issue_category", "issue_tags",
               "summary_ko", "quote_original", "source_url", "collected_date"]]
            .rename(columns={"opinion_id": "의견 번호", "platform": "플랫폼", "published_date": "작성일", "user_type": "유형",
                             "sentiment": "방향", "issue_category": "주 분류", "issue_tags": "보조 분류", "summary_ko": "요약",
                             "quote_original": "원문 발췌", "source_url": "원문", "collected_date": "확인일"}),
            hide_index=True, column_config={"원문": st.column_config.LinkColumn("원문", display_text="열기")})

    with st.expander("표본의 한계 · 미검증·제외 자료"):
        st.markdown("- 인벤·디시인사이드·블리자드 포럼의 자발적 게시글이라 불편을 겪은 사람의 글이 많을 수 있다. 전체 이용자 설문이 아니다.\n"
                    "- 분류와 의견 방향은 AI 모델이 아닌 기획자가 판단했다. 유형은 작성자가 밝힌 경우만 표시하고 나머지는 '미상'이다.\n"
                    "- 같은 작성자로 추정되는 글은 1건만 셌다. 닉네임을 저장하지 않아 다른 글이 같은 사람일 가능성은 남아 있다.\n"
                    "- Reddit은 수집 환경에서 접근이 차단됐고, 유튜브는 댓글을 불러올 수 없어 0건이다.")
        for r in other.itertuples():
            st.markdown(f"- `{r.opinion_id}` {r.platform} · [{r.source_url}]({r.source_url}) — {r.verification_status} · {r.note}")


# ======================================================================
# 3 원인 가설과 반대 해석
def _s3_hypothesis(rs: dict, ops: pd.DataFrame) -> None:
    p = rs["problem"]
    v = ops[ops["verified"]]
    cnt = code_counts(v) if not v.empty else pd.Series(dtype=int)
    head("학습 부담 → 이탈은 아직 가설", "관찰 → 해석 → 가설 순서로 근거가 약해진다. 단계마다 확인할 지표를 정했다.", b_hypo())
    steps = []
    for i, f in enumerate(p["flow"]):
        codes = set(f.get("codes", []))
        n = sum(bool(set(opinion_codes(r)) & codes) for _, r in v.iterrows()) if codes else 0
        ev = f"{escape(f['basis'])}" + (f" · 관련 의견 {n}건" if n else "")
        steps.append(f'<div class="ow-step {f.get("kind", "hypo")}"><div class="ow-step-n">{i + 1} {KIND[f.get("kind", "hypo")]()}</div>'
                     f'<div class="ow-step-t">{escape(f["step"])}</div>'
                     f'<div class="ow-step-d">{escape(f["desc"])}</div><div class="ow-step-b">근거 · {ev}</div>'
                     f'<div class="ow-step-c">검증 · {escape(f.get("check", ""))}</div></div>')
        if i < len(p["flow"]) - 1:
            steps.append('<div class="ow-step-a">→</div>')
    html(f'<div class="ow-flow">{"".join(steps)}</div>')
    note(p["verify"])

    sub("다른 원인도 함께 확인")
    cards = []
    for a in p["alternatives"]:
        if a.get("ids"):
            n = f"관련 의견 {len(a['ids'])}건"
        else:
            n = f"관련 의견 {int(cnt.get(a['category'], 0))}건" if a.get("category") else "관련 의견 없음"
        cards.append(f'<div class="ow-alt"><div class="ow-alt-t">{escape(a["cause"])}</div><div class="ow-alt-n">{n}</div>'
                     f'<div class="ow-alt-d">{escape(a["evidence"])}</div><div class="ow-alt-c">확인: {escape(a["check"])}</div></div>')
    html(f'<div class="ow-grid3">{"".join(cards)}</div>')
    note("A/B 테스트는 무작위 배정이라 위 원인들이 두 그룹에 고르게 섞인다 → 기능 효과만 분리된다.")


# ======================================================================
# 4 개선안 체험 (A·B·C 기획 시안) + 비교·우선순위
def _spec_cards(rs: dict) -> str:
    """A·B·C 사양 카드 (기본 화면): 대상 · 문제 · 핵심 해결책 3줄. 흐름·KPI·난이도는 _spec_detail() 펼쳐보기."""
    out = []
    for s in [x for x in rs["strategies"] if x["core"]]:
        rows = [("대상", escape(s["target"])), ("문제", escape(s.get("problem", ""))), ("핵심 해결책", escape(s["tagline"]))]
        out.append(f'<div class="ow-spec k{s["key"]}"><div class="ow-spec-h"><span class="ow-spec-key">{s["key"]}</span>'
                   f'<div><div class="ow-spec-n">{escape(s["name"])}</div><div class="ow-spec-p">{escape(s.get("phase", ""))}</div></div></div>'
                   + "".join(f'<div class="ow-spec-r"><span>{k}</span><div>{v}</div></div>' for k, v in rows) + "</div>")
    return f'<div class="ow-specs">{"".join(out)}</div>'


def _spec_detail(rs: dict) -> None:
    """A·B·C 흐름 · 핵심 KPI · 구현 난이도 (접어 두는 상세)."""
    table(["개선안", "흐름", "핵심 KPI", "구현 난이도"],
          [[f"<b>{s['key']}</b> {escape(s['name'])}", " → ".join(escape(f) for f in s.get("flow_short", s["flow"][:3])),
            escape(s["kpis"][0]), escape(s.get("feasibility", ""))]
           for s in sorted([x for x in rs["strategies"] if x["core"]], key=lambda x: x.get("phase", ""))], badge_html=b_mock())


def _phases(plan: dict) -> str:
    sc = plan["sched"]
    steps = [("1단계", "A 복귀 브리핑", f"{sc['e1_assign'][0]}~{sc['e1_assign'][1]}주차 실험 · {sc['e1_d7']}주차 D7 판정", "go"),
             ("2단계", "C 학습 미션", f"{sc['e2_assign'][0]}~{sc['e2_assign'][1]}주차 실험 · {sc['e2_d7']}주차 D7 판정", "go"),
             ("3단계", "B 학습 카드 수동형", f"{sc['e3'][0]}~{sc['e3'][1]}주차 사용성 검증 (선행 지표만)", "go"),
             ("별도 검토", "B 자동 원인 분석 · D PC방", "기술 검증·협력사 협의 후 결정", "hold")]
    return '<div class="ow-phase">' + "".join(
        f'<div class="ow-phase-i {c}"><div class="ow-phase-k">{k}</div><div class="ow-phase-t">{escape(t)}</div>'
        f'<div class="ow-phase-d">{escape(d)}</div></div>' for k, t, d, c in steps) + "</div>"


def _s4_experience(rs: dict, ops: pd.DataFrame, heroes: dict, tl: pd.DataFrame, statuses: dict, plan: dict) -> None:
    head("A 먼저, C·B는 단계적으로", "영웅·밸런스·매칭은 바꾸지 않는다.", b_mock())
    html(_spec_cards(rs))
    with st.expander("자세히 보기 · 흐름·핵심 KPI·구현 난이도 · 출시 순서"):
        _spec_detail(rs)
        html(_phases(plan))
        st.caption("하나씩 출시해 효과를 따로 측정한다.")

    sub("직접 눌러 보기 · 왼쪽 실제 화면 vs 오른쪽 시안")
    t = st.tabs(["A 복귀 브리핑", "B 전투 학습 카드", "C 첫 10경기 미션", "전략 상세·우선순위"])
    with t[0]:
        _proto_a(heroes, tl, statuses)
    with t[1]:
        _proto_b(heroes, statuses)
    with t[2]:
        _proto_c(statuses)
    with t[3]:
        _strategy_detail(rs, ops, plan)


LAST_ACCESS = {"2026년 1월 (시즌 1 이전)": "2026-01-31", "2026년 7월": "2026-07-31", "2026년 9월": "2026-09-30"}


def _a_reset() -> None:
    st.session_state["ow_a_step"] = 0


def _a_set(step: int) -> None:
    st.session_state["ow_a_step"] = step


def _proto_a(heroes: dict, tl: pd.DataFrame, statuses: dict) -> None:
    sub("A · 놓친 변경점만 3분 요약", b_mock())
    html('<div class="ow-vs"><div><b>기존 기능</b> 블리자드 시즌 1 공지 기사 속 복귀 요약 (웹 기사, 일괄 안내)</div>'
         '<div><b>제안 기능</b> 게임 접속 시 내 마지막 접속일 기준으로 놓친 것만 안내</div></div>')
    left, right = st.columns([1, 1], gap="medium")
    with left:
        col_head("real", "현재 · 접속하면 보이는 메인 화면")
        shot("returning_menu", statuses, facts=False, max_w=1200,
             lead="변경점 안내가 보이지 않음")
    with right:
        col_head("mock", "제안 · 접속 직후 복귀 브리핑")
        _proto_a_body(heroes, tl)


def _proto_a_body(heroes: dict, tl: pd.DataFrame) -> None:
    last = st.radio("예시 계정의 마지막 접속 시점", list(LAST_ACCESS), horizontal=True, key="ow_a_last", on_change=_a_reset)
    cutoff = LAST_ACCESS[last]
    new = [h for h in heroes["heroes"] if h.get("new_2026") and h["new_2026"] > cutoff]
    changed = [h for h in heroes["heroes"] if h.get("role_changed") and h["role_changed"] > cutoff]
    sys_rows = tl[tl["date"].notna() & (tl["type"] == "시스템") & tl["status"].str.startswith("공식") & (tl["date"] > pd.Timestamp(cutoff))]
    sys_rows = sys_rows.sort_values("date")
    total = len(new) + len(changed) + len(sys_rows)
    step = st.session_state.get("ow_a_step", 0)

    html(f'<div class="ow-proto coral"><div class="ow-proto-bar"><span>RE:START 복귀 브리핑</span>{b_mock()}</div>'
         f'<div class="ow-proto-h">다시 오신 것을 환영합니다</div>'
         f'<div class="ow-proto-s">마지막 접속 이후 <b>{total}개</b>가 바뀌었습니다 · 예상 3분</div>'
         f'<div class="ow-proto-chips"><span>신규 영웅 {len(new)}</span><span>바뀐 영웅 {len(changed)}</span><span>새 시스템 {len(sys_rows)}</span></div></div>')

    if step == 0:
        c1, c2 = st.columns(2)
        c1.button("3분 요약 보기", key="ow_a_start", type="primary", on_click=_a_set, args=(1,), width="stretch")
        c2.button("나중에 보기", key="ow_a_later", on_click=_a_set, args=(-1,), width="stretch")
    elif step == -1:
        st.info("메뉴 > 복귀 브리핑에서 언제든 다시 볼 수 있습니다. (기획 시안)")
        st.button("다시 열기", key="ow_a_reopen", on_click=_a_set, args=(0,))
    else:
        cards = {
            1: ("1/3 · 새로 나온 영웅", "".join(f'<span class="ow-hero new">{escape(h["name"])}<small>{h["new_2026"][5:]}</small></span>' for h in new)
                or "<p>이 기간에 새로 나온 영웅이 없습니다.</p>"),
            2: ("2/3 · 바뀐 영웅", "".join(f'<span class="ow-hero changed">{escape(h["name"])} · 공격 → 지원</span>' for h in changed)
                or "<p>역할이 바뀐 영웅이 없습니다.</p>"),
            3: ("3/3 · 새 시스템", "<ul>" + "".join(f"<li><b>{r.date:%m-%d}</b> {escape(r.title)}</li>" for r in sys_rows.itertuples()) + "</ul>"
                if len(sys_rows) else "<p>새 시스템 변경이 없습니다.</p>"),
        }
        if step <= 3:
            title, body = cards[step]
            html(f'<div class="ow-proto-card mock coral"><div class="ow-proto-card-t">{title}</div><div class="ow-heroes small">{body}</div>'
                 f'<div class="ow-proto-card-s">출처: 공식 패치노트·공식 영웅 페이지</div></div>')
            c1, c2, c3 = st.columns(3)
            c1.button("이전", key="ow_a_prev", on_click=_a_set, args=(max(step - 1, 0),), width="stretch")
            c2.button("다음" if step < 3 else "완료", key="ow_a_next", type="primary", on_click=_a_set, args=(step + 1,), width="stretch")
            c3.button("건너뛰기", key="ow_a_skip", on_click=_a_set, args=(-1,), width="stretch")
        else:
            st.success("브리핑 완료 · 이제 빠른 대전으로 감각을 되찾아 보세요. (기획 시안)")
            st.button("처음으로", key="ow_a_restart", on_click=_a_set, args=(0,))


def _proto_b(heroes: dict, statuses: dict) -> None:
    sub("B · 어려웠던 상대 대응 카드", b_mock())
    html('<div class="ow-vs"><div><b>기존 기능</b> 경기 중·연습장에서 스킬에 마우스를 올리면 키워드 정의 확인 (2026-02 공식)</div>'
         '<div><b>제안 기능 (MVP · 수동형)</b> 경기 후, 어려웠던 상대를 유저가 직접 골라 핵심 기술과 대처 선택지 확인</div></div>')
    left, right = st.columns([1, 1], gap="medium")
    with left:
        col_head("real", "현재 · 처치당한 직후 전투 화면")
        shot("combat_scene", statuses, facts=False, max_w=1200,
             lead="상대 이름만 표시, 대응법 없음")
    with right:
        col_head("mock", "제안 · 경기 직후 전투 학습 카드 (수동형)")
        _proto_b_body(heroes)
    html('<div class="ow-defer"><b>MVP 제외</b> \'나를 처치한 기술\' 자동 표시는 블리자드와 데이터 범위·정확도 확인 후 결정</div>')
    sub("카드 내용의 출처", b_real())
    shot("skill_detail", statuses, facts=False, size="wide",
         lead="영웅마다 직접 열어 봐야 함")


def _proto_b_body(heroes: dict) -> None:
    sk = {s["hero"]: s for s in heroes.get("skills_verified", [])}
    if not sk:
        st.info("스킬 자료가 없습니다.")
        return
    c1, c2 = st.columns(2)
    hero = c1.selectbox("어려웠던 상대 영웅 (유저가 선택)", list(sk), key="ow_b_hero")
    skill = c2.selectbox("확인할 기술", sk[hero]["skills"], key="ow_b_skill")
    html(f'<div class="ow-proto dark"><div class="ow-proto-bar"><span>전투 학습 카드 · 수동형</span>{b_mock()}</div>'
         f'<div class="ow-proto-s">선택한 상대 <b>{escape(hero)}</b> · 핵심 기술 1개와 대처 선택지</div>'
         f'<div class="ow-skill"><div class="ow-skill-icon">스킬<br>이미지<br>자리</div><div>'
         f'<div class="ow-skill-n">{escape(skill)}</div>'
         f'<div class="ow-skill-d">기술 특징 · 공식 영웅 페이지 설명 연동 예정 <small>(검증 전 미입력)</small></div>'
         f'<div class="ow-skill-tip">대응 예시 · 혼자 정면으로 맞서지 말고 아군 근처에서 싸우기 <small>(예시 문구 · 게임 디자인 검수 필요)</small></div>'
         f'</div></div><div class="ow-proto-card-s">기술 이름: {link(sk[hero]["source"], "공식 패치노트")} 표기</div></div>')
    c1, c2 = st.columns(2)
    if c1.button("연습해 보기", key="ow_b_practice", type="primary", width="stretch"):
        st.info("연습장으로 이동해 이 기술을 상대해 보는 흐름입니다. 실제 게임 연동은 블리자드 개발 협업이 필요합니다. (기획 시안)")
    if c2.button("다시 보지 않기", key="ow_b_off", width="stretch"):
        st.info("설정에서 카드 표시를 끄거나 하루 표시 횟수를 줄일 수 있습니다. (기획 시안)")


# (경기 구간, 학습 목표, [(미션, 학습 확인 방법)])  · 'N판 플레이' 같은 횟수 조건은 쓰지 않는다
MISSIONS = [
    (1, 3, "역할·기술 이해", [("주력 영웅의 기술 3개를 한 경기 안에서 모두 사용", "경기 후 기술 한 줄 요약 카드 확인"),
                         ("역할 목표 1회 달성 (예: 돌격 거점 진입 · 지원 아군 치유)", "역할 패시브 설명 확인")]),
    (4, 6, "상대 대응", [("어려웠던 상대 1명을 학습 카드(B)로 확인", "대처 선택지 중 1개 고르기"),
                      ("같은 상대를 다시 만난 경기에서 직전보다 오래 생존", "경기 후 결과 비교 표시")]),
    (7, 10, "팀 플레이", [("아군과 함께 목표 지점에 진입", "팀 목표 설명 확인"),
                       ("아군 요청(핑)에 맞춰 위치·역할 조정 1회", "요청 응답 기록 확인")]),
]
MISSION_RULES = ["'N판 플레이' 같은 횟수 조건 없음 · 승패와 무관", "미션마다 학습 목표와 확인 방법을 1:1로 연결",
                 "같은 행동 보상은 하루 1회 · 보상은 외형 위주", "언제든 끄기 · 다시 켜기"]


def _proto_c(statuses: dict) -> None:
    sub("C · 학습 행동 미션 (첫 10경기)", b_mock())
    html('<div class="ow-vs"><div><b>기존 기능</b> 신규 유저 전 영웅 즉시 개방, 경쟁전은 일반전 20승 후 개방 (2025-08 공식)</div>'
         '<div><b>제안 기능</b> 영웅 선택은 그대로, 학습 목표와 연결된 선택형 미션으로 학습 순서 제안</div></div>')
    left, right = st.columns([1, 1], gap="medium")
    with left:
        col_head("real", "현재 · 이벤트 도전 과제 화면")
        shot("mission_screen", statuses, facts=False, max_w=1200,
             lead="과제 = 경기 횟수, 학습 과제 없음")
    with right:
        col_head("mock", "제안 · 첫 10경기 학습 미션")
        _proto_c_body()
    html('<div class="ow-rules"><b>설계 원칙 · 단순 횟수 채우기 방지</b>' + bullets(MISSION_RULES) + "</div>")


def _proto_c_body() -> None:
    c1, c2 = st.columns([3, 1])
    n = c1.slider("진행한 경기 수 (예시)", 0, 10, 4, key="ow_c_n")
    off = c2.toggle("미션 끄기", key="ow_c_off")
    if off:
        st.info("미션을 껐습니다. 언제든 다시 켤 수 있고 알림 빈도도 조절할 수 있습니다. (기획 시안)")
        return
    segs = "".join(f'<span class="{"on" if i <= n else ""}">{i}</span>' for i in range(1, 11))
    blocks = []
    for a, b, name, items in MISSIONS:
        done = n >= b
        active = a <= n + 1 <= b and not done
        state = "완료" if done else ("진행 중" if active else "대기")
        cls = "done" if done else ("active" if active else "")
        blocks.append(f'<div class="ow-mission {cls}"><div class="ow-mission-h">{a}~{b}경기 · 학습 목표: {escape(name)}<span>{state}</span></div>'
                      + "".join(f'<div class="ow-mission-i">{"✓" if done else "○"} {escape(x)}<small>확인: {escape(c)}</small></div>'
                                for x, c in items) + "</div>")
    html(f'<div class="ow-proto narrow"><div class="ow-proto-bar"><span>첫 10경기 학습 미션</span>{b_mock()}</div>'
         f'<div class="ow-progress">{segs}</div><div class="ow-grid3">{"".join(blocks)}</div>'
         f'<div class="ow-proto-card-s">보상 예시: 외형 아이템 (확정 아님 · 경쟁 밸런스에 영향 없는 보상만 검토)</div></div>')


def _strategy_detail(rs: dict, ops: pd.DataFrame, plan: dict) -> None:
    rc = rs["rice"]
    # 도달(Reach)은 05 실험 설계와 같은 분기 유입·참여율 가정에서 계산 (기준값 혼재 방지)
    items = pd.DataFrame(rice_table(rc["items"], plan["quarter"]["reach"]))
    items = items.sort_values("score", ascending=False)
    order = " → ".join(items["key"])
    sub(f"RICE 순서 {order}", b_sim())
    opmap = ops[ops["verified"]].set_index("opinion_id")
    score = dict(zip(items["key"], items["score"]))
    for s in rs["strategies"]:
        tag = "핵심" if s["core"] else "추가 검토"
        html(f'<div class="ow-strat{"" if s["core"] else " ext"}"><div class="ow-strat-k">전략 {s["key"]} · {tag} · RICE {score.get(s["key"], 0):,.0f}</div>'
             f'<div class="ow-strat-n">{escape(s["name"])}</div><div class="ow-strat-t">{escape(s["tagline"])}</div>'
             f'<div class="ow-strat-kpi">핵심 KPI · {escape(" · ".join(s["kpis"]))}</div></div>')
        with st.expander(f"자세히 보기 · 전략 {s['key']} {s['name']}"):
            rows = [["대상 유저", escape(s["target"])], ["진입 시점", escape(s["entry"])],
                    ["작동 흐름", bullets(s["flow"])], ["기존 기능과 차이", escape(s["vs_existing"])],
                    ["유저 선택권", escape(s["control"])], ["검증할 가설", escape(s["hypothesis"])],
                    ["기대 효과", escape(s["effect"])], ["개발 난이도", escape(s["difficulty"])],
                    ["운영 비용", escape(s["op_cost"])], ["예상 부작용", bullets(s["side_effects"])],
                    ["대응", bullets(s["responses"])], ["우선순위 이유", escape(s["priority_reason"])]]
            if s.get("owner"):
                rows.insert(0, ["담당", escape(s["owner"])])
            refs = [f'{link(opmap.loc[o, "source_url"], o)} {escape(opmap.loc[o, "summary_ko"][:40])}…' for o in s["from_opinions"] if o in opmap.index]
            rows.append(["근거 의견", "<br>".join(refs) if refs else "—"])
            table(["항목", "내용"], rows, badge_html=b_mock())

    name = {s["key"]: s["name"] for s in rs["strategies"]}
    items["label"] = items["key"] + " " + items["key"].map(name)
    top, second = items.iloc[0], items.iloc[1]
    fig = go.Figure(go.Bar(y=items["label"], x=items["score"], orientation="h",
                           marker_color=[C_TREAT if k == top["key"] else C_MUTED for k in items["key"]],
                           text=items["score"].round(0).astype(int).map("{:,}점".format), textposition="outside", cliponaxis=False))
    fig.update_yaxes(autorange="reversed", automargin=True, title="")
    fig.update_xaxes(title="RICE 점수 (점)", range=[0, items["score"].max() * 1.3], rangemode="tozero")
    chart_card(fig, key="rice", kind="sim", title="전략별 RICE 점수",
               unit="점 · 도달×영향×확신÷노력 · 파랑 = 1순위",
               kpis=[(f"1순위 {top['label']}", f"{top['score']:,.0f}점"),
                     (f"2순위 {second['label']}", f"{second['score']:,.0f}점"),
                     ("1순위 ÷ 2순위", f"{top['score'] / second['score']:.2f}배")],
               analysis=f"A {top['score']:,.0f}점 1위 · 도달 최대, 노력 최소",
               decision="A → C → B 순서로 출시, D는 보류",
               basis=f"도달 = 분기 유입 × 참여율 · 05와 같은 가정값",
               height=300, legend=False, cols=("전략", "RICE 점수 (점)"))
    with st.expander("자세히 보기 · RICE 산식과 가정값"):
        st.caption(f"{rc['formula']} · {rc['notes']}")
        table(["전략", "도달 (분기·명)", "영향", "확신", "노력 (인월)", "점수", "근거"],
              [[escape(x.label), f"{x.reach:,.0f}<br><small>{escape(x.reach_basis)}</small>", str(x.impact), str(x.confidence),
                str(x.effort), f"<b>{x.score:,.0f}</b>", escape(x.why)] for x in items.itertuples()], badge_html=b_sim())

    cmp_ = rs["comparison"]
    sub("대안 비교", b_interp())
    df = pd.DataFrame(cmp_["criteria"])
    fig = go.Figure()
    fig.add_bar(y=df["name"], x=df["restart"], name="RE:START (제안)", orientation="h", marker_color=C_TREAT,
                text=[f"{v}점" for v in df["restart"]], textposition="outside", cliponaxis=False)
    fig.add_bar(y=df["name"], x=df["alt"], name=f"{cmp_['alt_name']} (대안)", orientation="h", marker_color=C_CTRL,
                text=[f"{v}점" for v in df["alt"]], textposition="outside", cliponaxis=False)
    fig.update_layout(barmode="group")
    fig.update_yaxes(autorange="reversed", automargin=True, title="")
    fig.update_xaxes(range=[0, 5.8], dtick=1, title="유리함 (점)")
    tot_r, tot_a = int(df["restart"].sum()), int(df["alt"].sum())
    chart_card(fig, key="cmp", kind="interp", title=f"RE:START vs {cmp_['alt_name']}",
               unit="1~5점 · 높을수록 유리 · 파랑 = 제안안",
               kpis=[("RE:START 합계", f"{tot_r}<small> / {5 * len(df)}점</small>"),
                     (f"{cmp_['alt_name']} 합계", f"{tot_a}<small> / {5 * len(df)}점</small>"),
                     ("차이가 가장 큰 기준", escape(df.loc[(df['restart'] - df['alt']).idxmax(), 'name']))],
               analysis=f"합계 {tot_r} vs {tot_a}점 · 개발 난이도는 같음",
               decision="선택 자유를 지키는 RE:START 선택",
               basis="같은 5개 기준·같은 척도 · 정성 평가",
               height=380, cols=("평가 기준", "점수 (1~5점)"), series="안")
    with st.expander("자세히 보기 · 평가 근거"):
        st.caption(cmp_["alt_desc"] + " · " + cmp_["note"])
        table(["기준", "RE:START", cmp_["alt_name"], "근거"],
              [[escape(c["name"]), str(c["restart"]), str(c["alt"]), escape(c["why"])] for c in cmp_["criteria"]], badge_html=b_interp())


# ======================================================================
# 5 KPI와 A/B 테스트
def _timeline(plan: dict) -> str:
    """주차별 실험 일정표 (배정 · D7 판정 · D30 확인)."""
    sc = plan["sched"]
    W = sc["decision"]
    rows = [
        ("실험 1 · A (복귀)", {**{w: ("assign", "배정") for w in range(sc["e1_assign"][0], sc["e1_assign"][1] + 1)},
                             sc["e1_d7"]: ("d7", "D7 판정"), sc["e1_d30"]: ("d30", "D30 확인")}),
        ("실험 2 · C (신규)", {**{w: ("assign", "배정") for w in range(sc["e2_assign"][0], sc["e2_assign"][1] + 1)},
                             sc["e2_d7"]: ("d7", "D7 판정"), sc["e2_m10"]: ("m10", "10경기"), sc["e2_d30"]: ("d30", "D30 확인")}),
        ("실험 3 · B 수동형", {w: ("small", "사용성") for w in range(sc["e3"][0], sc["e3"][1] + 1)}),
        ("의사결정", {sc["e1_d7"]: ("dec", "A 1차"), sc["e1_d30"]: ("dec", "A 확정"), W: ("dec", "최종")}),
    ]
    head_ = "".join(f"<th>{w}주</th>" for w in range(1, W + 1))
    body = "".join(f"<tr><th>{escape(n)}</th>" + "".join(
        f'<td class="{cells[w][0]}">{escape(cells[w][1])}</td>' if w in cells else "<td></td>" for w in range(1, W + 1)) + "</tr>"
        for n, cells in rows)
    return f'<div class="gp-table-wrap"><table class="ow-gantt"><tr><th>준비 2주 이후</th>{head_}</tr>{body}</table></div>'


def _s5_kpi(rs: dict, plan: dict) -> None:
    ab, ex = rs["ab_test"], rs["experiment"]
    seg, sc, m10 = plan["seg"], plan["sched"], plan["m10"]
    r, nw = seg["복귀"], seg["신규"]
    head("주요 지표: D7 잔존율 (배정 기준)", "목표 = 최소 의미 있는 개선 폭(MDE) · 기준값은 모두 가정", b_mock())
    sub("KPI 정의")
    tgt = {"MDE": lambda k: (f"+{r['mde']['D7']:.1f}%p (기준 {r['base']['D7']:.0f}% 가정)" if "복귀" in k["name"]
                             else f"+{nw['mde']['D7']:.1f}%p (기준 {nw['base']['D7']:.0f}% 가정)"),
           "MDE30": lambda k: f"+{r['mde']['D30']:.1f}%p (배정 기준)",
           "M10": lambda k: f"+{m10['mde']:.1f}%p (기준 {m10['base']:.1f}% 가정)"}
    tiles([("복귀 D7 (실험 1 주요)", f"+{r['mde']['D7']:.1f}%p", f"기준 {r['base']['D7']:.0f}% 가정"),
           ("신규 D7 (실험 2 주요)", f"+{nw['mde']['D7']:.1f}%p", f"기준 {nw['base']['D7']:.0f}% 가정"),
           ("D30 (보조)", f"+{r['mde']['D30']:.1f}%p", f"배정 기준"),
           ("첫 10경기 완료율 (선행)", f"+{m10['mde']:.1f}%p", f"기준 {m10['base']:.1f}% 가정")])
    html('<div class="ow-defbox"><div><b>D7 잔존율</b> Day 7 <u>당일</u> 접속 (11/1 복귀 → 11/8)</div>'
         '<div><b>7일 내 재방문율</b> Day 1~7 중 <u>하루라도</u> 접속</div>'
         '<div class="ow-defbox-n">재방문율은 항상 D7 이상이라 섞어 비교하지 않는다. 주요 지표는 D7.</div></div>')
    with st.expander(f"KPI 정의 전체 · 분자·분모·측정 시점 ({len(rs['kpi_defs'])}개)"):
        table(["구분", "지표", "확인 가능 여부"],
              [[b_real(), "Steam 동시접속자 · 한국 PC방 점유율", "공개 자료 (Steam 한정 · 한국 PC방 표본)"],
               [badge("내부 데이터 필요", "pending"), "DAU · D7 · D30 · 경기 완료율", "넥슨·블리자드 로그 필요 · 기준값은 모두 가정"]])
        table(["지표 · 역할", "계산 (분자 ÷ 분모)", "측정 시점", "목표 (MDE)"],
              [[f"<b>{escape(k['name'])}</b><span class='ow-tag'>{escape(k['role'])}</span><br><small>{escape(k['target_users'])}</small>",
                f"<span class='ow-num'>{escape(k['numerator'])}</span><span class='ow-den'>÷ {escape(k['denominator'])}</span>",
                escape(k["timing"]), f"<b>{escape(tgt[k['target']](k) if k['target'] in tgt else k['target'])}</b>"]
               for k in rs["kpi_defs"]], badge_html=b_mock(), cls="ow-kpi-table")

    sub("실험 설계: 기능 1개씩")
    exp_rows = []
    for e in ex["experiments"]:
        if e["id"] == "1":
            size = f"+{r['mde']['D7']:.1f}%p ({r['base']['D7']:.0f}→{r['base']['D7'] + r['mde']['D7']:.0f}%) · 그룹당 {r['n']:,}명"
            when = f"배정 {sc['e1_assign'][0]}~{sc['e1_assign'][1]}주 · D7 {sc['e1_d7']}주 · D30 {sc['e1_d30']}주"
        elif e["id"] == "2":
            size = f"+{nw['mde']['D7']:.1f}%p ({nw['base']['D7']:.0f}→{nw['base']['D7'] + nw['mde']['D7']:.0f}%) · 그룹당 {nw['n']:,}명"
            when = f"배정 {sc['e2_assign'][0]}~{sc['e2_assign'][1]}주 · D7 {sc['e2_d7']}주 · D30 {sc['e2_d30']}주"
        elif e["id"] == "3":
            size, when = "잔존 효과 판단 안 함", f"{sc['e3'][0]}~{sc['e3'][1]}주"
        else:
            size, when = "실험 1·3 결과 후 별도 산정", "조건 충족 시"
        exp_rows.append([f"<b>실험 {e['id']}</b><br>{escape(e['name'])}<br><small>{escape(e['why'])}</small>",
                         f"{escape(e['segment'])}<br><small>배정 {escape(e['split'])}</small>",
                         f"<b>{escape(e['primary'])}</b><br><small>보조: {escape(e['secondary'])}</small>",
                         escape(size), escape(when)])
    table(["실험 · 이유", "대상 · 배정", "주요 지표 (1개)", "MDE · 필요 표본 (가정)", "일정 (주차)"], exp_rows, badge_html=b_mock())
    note(f"기능을 묶으면 효과를 구분할 수 없어 1개씩 실험한다 · α {ex['alpha']} · 검정력 {ex['power']:.0%} · 배정 기준(ITT)")
    with st.expander(f"자세히 보기 · 표본 산정 근거 · 주차별 일정표 (준비 2주 + 운영 {sc['decision']}주)"):
        tiles([("복귀 D7 표본 (실험 1)", f"{r['n']:,}명 × 2", f"주당 유입 {r['weekly']:,.0f}명 가정 → 배정 {r['assign_weeks']}주"),
               ("신규 D7 표본 (실험 2)", f"{nw['n']:,}명 × 2", f"주당 유입 {nw['weekly']:,.0f}명 가정 → 배정 {nw['assign_weeks']}주"),
               ("검정 조건", f"α {ex['alpha']} · 검정력 {ex['power']:.0%}", "양측 두 비율 차이 검정 · 배정 기준(ITT)")])
        html(_timeline(plan))
        st.caption(f"D30 관측 종료 {sc['e1_d30']}·{sc['e2_d30']}주차 · 운영 일정은 06 탭 '파일럿 일정'과 같습니다.")

    sub("유의성 ≠ 사업 효과", b_interp())
    html('<div class="ow-sig">'
         '<div><b>통계적 유의성</b>효과 추정치의 95% 신뢰구간 하한이 0보다 큰가 → 우연이 아닐 가능성</div>'
         f'<div><b>사업적 효과</b>점추정이 MDE(+{r["mde"]["D7"]:.1f}%p) 이상인가, 개발·운영비 대비 추가 잔존 인원이 충분한가</div>'
         '<div><b>판단</b>둘 다 충족하고 안전 지표가 나빠지지 않을 때만 확대. 유의하지만 작으면 조건부 확대</div></div>')
    note("보수적 기준: 실제 효과가 정확히 MDE면 확대 확률은 약 50%다. 효과 없는 기능을 넓히는 오판을 줄이는 쪽을 택했다.")

    with st.expander("자세히 보기 · 판단 기준 4단계 · 측정 방법 · 즉시 중단 기준 · 표본 계산기"):
        table(["결과", "판단 기준"], [[f"<b>{escape(d['result'])}</b>", escape(d["rule"])] for d in rs["decision_rules"]], badge_html=b_mock())
        st.markdown(f"**측정 방법** — {ab['method']}  \n**배정** — {ab['unit']}  \n**즉시 중단** — {ab['stop_rule']}")
        st.caption("아래 계산기의 기본값은 실험 1(복귀 D7)과 같습니다. 값을 바꾸면 필요 표본과 배정 기간이 다시 계산됩니다.")
        c1, c2, c3 = st.columns(3)
        base = c1.number_input("대조군 D7 (%, 가정)", 1.0, 99.0, float(r["base"]["D7"]), step=1.0, key="ab_base")
        mde = c2.number_input("MDE · 배정 기준 (%p)", 0.1, 30.0, float(round(r["mde"]["D7"], 2)), step=0.1, key="ab_mde")
        part = c3.slider("기능 참여율 (%, 가정)", 1, 100, int(r["participation"]), key="ab_part")
        c1, c2, c3 = st.columns(3)
        alpha = c1.selectbox("유의수준", [0.01, 0.05, 0.10], index=1, key="ab_alpha")
        power = c2.selectbox("검정력", [0.8, 0.9], index=0, key="ab_power")
        weekly = c3.number_input("주당 유입 (명, 가정)", 100, 10_000_000, int(r["weekly"]), step=1000, key="ab_weekly")
        n_itt = sample_size_two_proportions(base / 100, min(base + mde, 99.9) / 100, alpha, power)
        tiles([("참여자 기준 필요 개선 폭", f"+{mde / part * 100:.1f}%p", f"{b_sim()} MDE ÷ 참여율"),
               ("그룹당 필요 표본", "—" if n_itt is None else f"{n_itt:,}명", f"{b_sim()} 두 비율 차이 검정"),
               ("배정 기간", "—" if n_itt is None else f"{math.ceil(2 * n_itt / weekly)}주", f"{b_sim()} 두 그룹 합 ÷ 주당 유입")])

    sub("가정 시뮬레이션", b_sim())
    note(f"기본값 = 위 실험 설계 (참여율 {r['participation']}% × 개선 폭 {ex['uplift']['D7']}%p = +{r['mde']['D7']:.1f}%p)")
    top = st.container()
    chart = st.container()
    with st.expander("시뮬레이션 상세 설정 (가정값)"):
        st.markdown("**코호트**")
        c1, c2 = st.columns(2)
        coh, fn, upd = ex["cohorts"], ex["funnel"], ex["uplift"]   # 실험 설계와 같은 가정값 (restart.json 'experiment')
        n_new = c1.number_input("신규 코호트 (명)", 0, 10_000_000, int(coh["신규"]["size"]), step=1000, key="rs_n_new")
        n_ret = c2.number_input("복귀 코호트 (명)", 0, 10_000_000, int(coh["복귀"]["size"]), step=1000, key="rs_n_ret")
        c1, c2 = st.columns(2)
        b_new = {d: c1.number_input(f"신규 {d} (%)", 0.0, 100.0, float(coh["신규"]["base"][d]), step=1.0, key=f"rs_new_{d}")
                 for d in ("D1", "D7", "D30")}
        b_ret = {d: c2.number_input(f"복귀 {d} (%)", 0.0, 100.0, float(coh["복귀"]["base"][d]), step=1.0, key=f"rs_ret_{d}")
                 for d in ("D1", "D7", "D30")}
        c1, c2 = st.columns(2)
        p_new = c1.slider("신규 미션 참여율 (%)", 0, 100, int(coh["신규"]["participation"]), key="rs_p_new")
        p_ret = c2.slider("복귀 브리핑 시작률 (%)", 0, 100, int(coh["복귀"]["participation"]), key="rs_p_ret")
        st.markdown("**참여자 개선 폭 (%p)** · 참여율을 곱한 값이 배정 기준 효과(MDE)")
        c1, c2, c3 = st.columns(3)
        uplift = {"D1": c1.slider("D1", 0.0, 20.0, float(upd["D1"]), 0.5, key="rs_u1"),
                  "D7": c2.slider("D7", 0.0, 20.0, float(upd["D7"]), 0.5, key="rs_u7"),
                  "D30": c3.slider("D30", 0.0, 20.0, float(upd["D30"]), 0.5, key="rs_u30")}
        st.markdown("**적응 퍼널 (%)**")
        c1, c2 = st.columns(2)
        f_first = c1.slider("접속 → 첫 경기", 0, 100, int(fn["first"]), key="rs_f1")
        f_3 = c2.slider("첫 경기 → 3경기", 0, 100, int(fn["m3"]), key="rs_f3")
        c1, c2 = st.columns(2)
        f_10 = c1.slider("3경기 → 10경기", 0, 100, int(fn["m10"]), key="rs_f10")
        c2.caption("퍼널은 KPI '첫 10경기 완료율'과 같이 신규 코호트만으로 계산합니다. D7은 위 잔존율 하나로만 봅니다.")
        c1, c2 = st.columns(2)
        fu3 = c1.slider("참여자 3경기 개선 (%p)", 0.0, 30.0, float(fn["up3"]), 0.5, key="rs_fu3")
        fu10 = c2.slider("참여자 10경기 개선 (%p)", 0.0, 30.0, float(fn["up10"]), 0.5, key="rs_fu10")
        ld0 = ex["leading"]   # 선행 지표·PC방 가정값 (KPI 표의 기준선과 같음)
        c1, c2 = st.columns(2)
        brief_comp = c1.slider("브리핑 완료율 (%)", 0, 100, int(ld0["briefing_completion"]), key="rs_bc")
        card_use = c2.slider("카드 사용률 (%)", 0, 100, int(ld0["card_usage"]), key="rs_cu")
        st.markdown("**PC방 이벤트(D) · 비용**")
        c1, c2 = st.columns(2)
        pc_reach = c1.slider("PC방 대상 비율 (%)", 0, 100, int(ld0["pc_reach"]), key="rs_pcr")
        pc_part = c2.slider("PC방 참여율 (%)", 0, 100, int(ld0["pc_participation"]), key="rs_pcp")
        c1, c2 = st.columns(2)
        pc_comp = c1.slider("미션 완료율 (%)", 0, 100, int(ld0["pc_completion"]), key="rs_pcc")
        pc_rev = c2.slider("7일 재방문율 (%)", 0, 100, int(ld0["pc_revisit"]), key="rs_pcv")
        c1, c2 = st.columns(2)
        pc_friend = c1.slider("친구 동반율 (%)", 0, 100, int(ld0["pc_companion"]), key="rs_pcf")
        reward = c2.number_input("1인당 보상 (원)", 0, 1_000_000, 3000, step=500, key="rs_rw")
        abc_effort = sum(x["effort"] for x in rs["rice"]["items"] if x["key"] in ("A", "B", "C"))
        c1, c2 = st.columns(2)
        fixed = c1.number_input("이벤트 고정비 (원)", 0, 10_000_000_000, 20_000_000, step=1_000_000, key="rs_fx")
        effort = c2.number_input("A~C 개발·운영 공수 (인월 · RICE 노력 합계)", 0.0, 500.0, float(abc_effort), step=1.0, key="rs_eff")
        c1, c2 = st.columns(2)
        mcost = c1.number_input("1인 월 비용 (원)", 0, 100_000_000, int(ex["cost"]["monthly_cost_per_person"]), step=500_000, key="rs_mc")
        hc, months = effort, 1.0     # 인월 = 인력 × 개월 → 공수를 그대로 쓴다
        f_d7 = int(fn["d7_of_10"])   # 퍼널 마지막 단계는 표시하지 않음 (D7 기준 혼재 방지)
        st.markdown("**DAU 가정**")
        c1, c2 = st.columns(2)
        base_dau = c1.number_input("코호트 외 활성 유저 (명/일)", 0, 100_000_000, 100_000, step=10_000, key="rs_bd")
        act = c2.slider("잔존 유저 일일 접속 확률 (%)", 1, 100, 50, key="rs_act")
        c1, c2 = st.columns(2)
        arrive = c1.slider("유입 기간 (일)", 1, 60, 14, key="rs_arr")
        horizon = c2.slider("관측 기간 (일)", 30, 180, 90, step=10, key="rs_hz")

    errs = [f"신규: {e}" for e in validate_base(b_new)] + [f"복귀: {e}" for e in validate_base(b_ret)]
    if errs:
        with top:
            for e in errs:
                st.error(e)
            st.info("시뮬레이션 상세 설정에서 D1 ≥ D7 ≥ D30 이 되도록 고쳐 주세요.")
        return

    inp = SimInput(
        cohorts=[CohortInput("신규", int(n_new), b_new, p_new), CohortInput("복귀", int(n_ret), b_ret, p_ret)],
        uplift=uplift, funnel_first=f_first, funnel_3=f_3, funnel_10=f_10, funnel_d7_of_10=f_d7,
        funnel_uplift_3=fu3, funnel_uplift_10=fu10, briefing_completion=brief_comp, card_usage=card_use,
        pc_reach=pc_reach, pc_participation=pc_part, pc_completion=pc_comp, pc_revisit=pc_rev, pc_companion=pc_friend,
        reward_cost=reward, event_fixed_cost=fixed, headcount=hc, months=months, monthly_cost_per_person=mcost,
        base_dau=base_dau, active_prob=act, arrival_days=arrive, horizon=horizon, funnel_cohort="신규")
    res = run(inp)
    r, f, pcb, cs, ld = res.retention, res.funnel, res.pcbang, res.costs, res.leading
    total = n_new + n_ret
    f_total = n_new                                  # 퍼널 = 신규 코호트 (KPI 정의와 같은 대상)
    per_q = plan["quarter"]["weeks"] * 7 / max(arrive, 1)   # 코호트(유입 기간) → 분기 환산 배수

    def rate(day, col):
        return r.loc[r["day"] == day, col].sum() / total * 100 if total else float("nan")

    with top:
        for w in res.warnings:
            st.warning(w)
    m10_b = f.loc[3, "base"] / f_total * 100 if f_total else float("nan")
    m10_n = f.loc[3, "improved"] / f_total * 100 if f_total else float("nan")
    with chart:
        # 코호트별 D7·D30을 '도입 전(대조군 가정) vs 도입 후(실험군 가정)' 한 쌍씩 비교
        cats, before, after = [], [], []
        for d in ["D7", "D30"]:
            for coh in ["복귀", "신규"]:
                row = r[(r["cohort"] == coh) & (r["day"] == d)].iloc[0]
                cats.append(f"{coh} {d}")
                before.append(row["base_rate"])
                after.append(row["new_rate"])
            cats.append(f"전체 {d}")
            before.append(rate(d, "base_users"))
            after.append(rate(d, "new_users"))
        fig = hpair(cats, before, after, xtitle="잔존율 (%)",
                    names=("도입 전 · 대조군 (가정 기준값)", "도입 후 · 실험군 (가정)"))
        ri, ni = cats.index("복귀 D7"), cats.index("신규 D7")
        chart_card(fig, key="sim", kind="sim", title="D7·D30 잔존율: 도입 전 vs 후",
                   unit="% · 회색 = 대조군, 파랑 = 실험군 · 이름 옆 = 변화 폭",
                   kpis=[("복귀 D7 (실험 1 주요 지표)", f"{before[ri]:.1f}% → <b>{after[ri]:.1f}%</b> <em>{pp(after[ri] - before[ri])}</em>"),
                         ("신규 D7 (실험 2 주요 지표)", f"{before[ni]:.1f}% → <b>{after[ni]:.1f}%</b> <em>{pp(after[ni] - before[ni])}</em>"),
                         ("첫 10경기 완료율", f"{m10_b:.1f}% → <b>{m10_n:.1f}%</b> <em>{pp(m10_n - m10_b)}</em>")],
                   analysis=f"D7 복귀 {pp(after[ri] - before[ri])} · 신규 {pp(after[ni] - before[ni])} (참여율 × 개선 폭)",
                   decision="이 폭을 MDE로, 유의하게 넘을 때만 확대",
                   basis="같은 코호트 전후 · 전체 = 인원 가중 평균",
                   height=520, cols=("코호트 · 지표", "잔존율 (%)"), series="그룹")

    dd = res.dau.pivot(index="day", columns="scenario", values="dau")
    dau_b, dau_n = dd.iloc[-1]["현재 가정"], dd.iloc[-1]["RE:START 적용 가정"]
    added_q = cs["added_d7"] * per_q
    # 핵심 차트: 첫 10경기 퍼널 · 90일 DAU (가정 시뮬레이션) — 접지 않고 잔존율 차트 바로 아래 2열로 표시
    c1, c2 = chart.columns(2, gap="medium")
    with c1:
        keep = f["stage"] != "D7 재접속(10경기 완료자 중)"   # D7은 잔존율 차트 하나로만 본다
        fv = f[keep].reset_index(drop=True)
        stages = list(fv["stage"])
        fb = (fv["base"] / f_total * 100).tolist() if f_total else [0] * len(fv)
        fn_ = (fv["improved"] / f_total * 100).tolist() if f_total else [0] * len(fv)
        fig = hpair(stages, fb, fn_, xtitle="접속 대비 (%)", names=("도입 전 · 대조군 (가정)", "도입 후 · 실험군 (가정)"),
                    xmax=118)
        chart_card(fig, key="funnel", kind="sim", title="신규 첫 10경기 퍼널: 도입 전 vs 후",
                   unit="신규 접속 대비 % · 회색 = 대조군, 파랑 = 실험군",
                   kpis=[("10경기 완료 (신규 접속 대비)", f"{m10_b:.1f}% → <b>{m10_n:.1f}%</b> <em>{pp(m10_n - m10_b)}</em>"),
                         ("10경기 완료 인원", f"{f.loc[3, 'base']:,.0f} → <b>{f.loc[3, 'improved']:,.0f}</b>명")],
                   analysis=f"10경기 완료 {pp(m10_n - m10_b)} · 첫 경기까지는 같음",
                   decision="완료율만 오르고 D7이 그대로면 미션 수정",
                   basis=f"신규 {f_total:,}명(가정) · KPI와 같은 대상",
                   height=400, cols=("단계", "신규 접속 대비 (%)"), series="그룹")
    with c2:
        fig = go.Figure()
        cur, app = res.dau[res.dau["scenario"] == "현재 가정"], res.dau[res.dau["scenario"] != "현재 가정"]
        fig.add_scatter(x=cur["day"], y=cur["dau"], name="현재 · 대조군 (가정)", line=dict(color=C_CTRL, width=3))
        fig.add_scatter(x=app["day"], y=app["dau"], name="RE:START 적용 · 실험군 (가정)", line=dict(color=C_TREAT, width=2, dash="dot"))
        fig.update_yaxes(title="DAU (명)", tickformat=",", rangemode="tozero", range=[0, res.dau["dau"].max() * 1.1])
        fig.update_xaxes(title="코호트 유입 시작 후 경과일 (일)")
        chart_card(fig, key="dau", kind="sim", title=f"DAU 시나리오 ({horizon}일)",
                   unit="명/일 · 세로축 0부터",
                   kpis=[(f"{horizon}일차 DAU 차이", f"<b>{dau_n - dau_b:+,.0f}</b>명"),
                         ("전체 DAU 대비", f"{(dau_n / dau_b - 1) * 100:+.2f}%")],
                   analysis=f"{horizon}일차 차이 {dau_n - dau_b:+,.0f}명 · 전체 DAU엔 거의 안 보임",
                   decision="DAU 대신 코호트 잔존율로 판단",
                   basis="잔존 곡선만 다르게 적용 · Steam과 무관",
                   height=400, cols=("경과일 (일)", "DAU (명)"), series="시나리오")

    with st.expander("자세히 보기 · 보조 수치 · PC방(D) · 계산식"):
        tiles([
            ("브리핑 완료 (코호트 · 가정)", f"{fmt_int(ld['briefing_completed'])}명", f"{b_sim()} 복귀 × 시작률 × 완료율 {brief_comp}%"),
            ("카드 사용 (코호트 · 가정)", f"{fmt_int(ld['card_users'])}명", f"{b_sim()} 신규+복귀 × 사용률 {card_use}%"),
            ("PC방 이벤트 참여 (D · 가정)", f"{fmt_int(pcb['users'].iloc[1])}명", f"{b_sim()} 신규+복귀 × 대상 {pc_reach}% × 참여 {pc_part}%"),
            ("총 이벤트 비용 (D · 별도)", fmt_won(cs["event_cost"]), f"{b_sim()} 참여자 × 보상 + 고정비 · 효과는 잔존율에 미반영"),
            ("추가 D7 잔존 1명당 개발·운영비 (A~C · 분기)", fmt_won(cs["dev_cost"] / added_q if added_q else float("nan")),
             f"{b_sim()} {effort:g}인월 × 월 비용 ÷ 분기 추가 D7 {added_q:,.0f}명"),
            (f"{horizon}일차 DAU 차이 (가정)", f"{dau_n - dau_b:+,.0f}명", f"{b_sim()} 가정 모형"),
        ])
        tgt0 = pcb["users"].iloc[0] or 1
        share = (pcb["users"] / tgt0 * 100).tolist()
        fig = go.Figure(go.Bar(y=pcb["stage"], x=share, orientation="h", marker_color=[C_MUTED] + [C_TREAT] * (len(pcb) - 1),
                               text=[f"{u:,.0f}명 · {s:.0f}%" for u, s in zip(pcb["users"], share)], textposition="outside", cliponaxis=False))
        fig.update_yaxes(autorange="reversed", automargin=True, title="", tickfont=dict(size=13))
        fig.update_xaxes(title="이벤트 대상 대비 비율 (%)", range=[0, 135], ticksuffix="%", rangemode="tozero")
        chart_card(fig, key="pcfunnel", kind="sim", title="D · PC방 이벤트 퍼널 (추가 검토안)",
                   unit="이벤트 대상 대비 %",
                   kpis=[("7일 내 재방문 (가정)", f"{pcb['users'].iloc[-1]:,.0f}명"),
                         ("재방문 1명당 이벤트비", fmt_won(cs["cost_per_revisit"]))],
                   analysis=f"재방문 {pcb['users'].iloc[-1]:,.0f}명 · 1명당 {fmt_won(cs['cost_per_revisit'])}",
                   decision="MVP 제외, A~C 결과 후 결정",
                   basis="효과는 잔존율에 미반영 · 대조군 없음",
                   height=320, legend=False, cols=("단계", "이벤트 대상 대비 (%)"))
        st.markdown("**KPI 연결 구조 (가설)**")
        table(["개선 방향", "전략", "확인할 지표"],
              [[escape(k["lever"]), escape(k["strategies"]), escape(" · ".join(k["leading"]))] for k in rs["kpi_chain"]], badge_html=b_hypo())
        st.markdown(f"""**계산식**
- 개선 후 잔존율 = 기존 잔존율 + 참여율 × 개선 폭 (참여율은 한 번만 곱하고 D1 ≥ D7 ≥ D30 으로 보정)
- 전체 잔존율 = (신규 잔존 인원 + 복귀 잔존 인원) ÷ (신규 + 복귀 코호트)
- 적응 퍼널 = 이전 단계 × 전환율. 3·10경기 전환율에만 가중 참여율({cs['p_avg']:.1f}%) × 개선 폭을 더함
- 브리핑·카드·PC방 지표는 관측용이라 잔존율에 더하지 않음
- 추가 D7 잔존 1명당 개발·운영비 = A~C 공수(인월) × 1인 월 비용 ÷ 분기 추가 D7 잔존 인원 (코호트 결과 × 분기 환산 {per_q:.1f}배 · D 이벤트 비용 제외)
- RICE 도달 = 분기 유입 × 참여·사용률 · 의사결정 카드·RICE·비용이 모두 같은 분기({plan['quarter']['weeks']}주) 유입 가정을 쓴다
- 적응 퍼널 = 신규 코호트만 (KPI '첫 10경기 완료율'과 같은 대상) · D7은 잔존율 차트 하나로만 판단
- DAU = 코호트 외 활성 유저 + Σ 일별 유입 × 잔존 곡선 × 일일 접속 확률 (Steam 수치와 무관)
- 기존 유저는 실험 대상이 아니며 불만·신고율로만 관찰
""")


# ======================================================================
# 06 실행 계획과 최종 제안
def _s6_execution(rs: dict, g: dict, statuses: dict, plan: dict) -> None:
    sc = plan["sched"]
    head(f"A부터 단계 출시 · {sc['decision'] + 2}주 파일럿 (준비 2주 + 운영 {sc['decision']}주)", "", b_mock())
    sub("우선순위와 이유")
    rice = pd.DataFrame(rice_table(rs["rice"]["items"], plan["quarter"]["reach"])).sort_values("score", ascending=False)
    sname = {s["key"]: s for s in rs["strategies"]}
    order = {"A": "1순위 · 먼저", "C": "2순위", "B": "3순위 · 수동형부터", "D": "보류"}
    table(["순서", "개선안", "RICE", "이유", "구현 난이도"],
          [[f"<b>{order.get(x.key, '')}</b>", f"{x.key} {escape(sname[x.key]['name'])}", f"{x.score:,.0f}점",
            escape(x.why), escape(sname[x.key].get("feasibility", ""))] for x in rice.itertuples()], badge_html=b_sim())

    mv = rs["mvp"]
    with st.expander("자세히 보기 · MVP 포함·제외 범위"):   # 우선순위 표와 겹쳐 접어 둠
        html(f'<div class="ow-grid2"><div class="ow-card plain"><div class="ow-card-k">MVP 포함</div>{bullets(mv["in"])}</div>'
             f'<div class="ow-card plain"><div class="ow-card-k">이번에는 제외 · 별도 검토</div>{bullets(mv["out"])}</div></div>')

    sub("현실적인 제약과 대응", b_interp())
    table(["제약·리스크", "대응"], [[escape(x["risk"]), escape(x["response"])] for x in rs["risks"]])

    pl = rs["pilot"]
    sub(f"파일럿 일정 · 준비 2주 → 운영 1~{sc['decision']}주", b_mock())
    weeks = [("준비 (-2~0주)", "이벤트 로그 설계 · 실험 배정 점검 · 기능 스위치 · CS 안내 문구"),
             (f"{sc['e1_assign'][0]}~{sc['e1_assign'][1]}주", "실험 1 · A 복귀 브리핑 배정 (복귀 유저 50:50)"),
             (f"{sc['e2_assign'][0]}~{sc['e2_assign'][1]}주", f"실험 2 · C 학습 미션 배정 (신규 유저) · {sc['e1_d7']}주차 A의 D7 1차 판정"),
             (f"{sc['e3'][0]}~{sc['e3'][1]}주", f"실험 3 · B 수동형 사용성 검증 · {sc['e1_d30']}주차 A의 D30 확인 → A 확대 여부 확정"),
             (f"{sc['decision']}주", "C의 D30 확인 · 확대·수정·중단 최종 결정 · 실험 4(A×B) 진행 여부 결정")]
    html('<div class="ow-timeline">' + "".join(
        f'<div class="ow-tl"><div class="ow-tl-d">{escape(p)}</div><div class="ow-tl-b">{escape(w)}</div></div>'
        for p, w in weeks) + "</div>")
    with st.expander("자세히 보기 · 담당 부서 · 이벤트 로그 · 출시 전 점검 · 롤백 기준"):  # 리스크 표는 위에 표시
        table(["담당", "역할"], [[escape(o["team"]), escape(o["role"])] for o in pl["owners"]], badge_html=b_mock())
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**필요한 이벤트 로그**")
            for x in pl["logs"]:
                st.markdown(f"- {x}")
            st.markdown("**출시 전 점검**")
            for x in pl["checklist"]:
                st.markdown(f"- {x}")
        with c2:
            st.markdown("**롤백 기준**")
            for x in pl["rollback"]:
                st.markdown(f"- {x}")

    r = plan["seg"]["복귀"]
    html(f'<div class="ow-conclusion"><div class="ow-conclusion-k">최종 제안 {b_mock()}</div>'
         f'<b>영웅 선택은 그대로, A 복귀 브리핑부터 {sc["decision"] + 2}주 파일럿 (준비 2주 + 운영 {sc["decision"]}주).</b><br>'
         f'D7이 MDE(+{r["mde"]["D7"]:.1f}%p) 이상 유의하게 오르고 안전 지표가 괜찮을 때만 C·B로 넓히고, '
         '자동 원인 분석·PC방(D)은 그 결과를 본 뒤 결정한다.</div>')

    sub("한계")
    note(rs["summary"]["limit"])
    pending = [s for s in statuses.values() if not s.ok]
    if pending:
        st.caption(f"게임 화면 {len(pending)}종은 최신 한국어 스크린샷 검증 전이라 자리만 표시했습니다. (assets/overwatch/README.md 참고)")
    st.caption(f"{rs['disclaimer']} · 자료 확인일 {COLLECTED_AT}")

    # v0.1 예시 분석(보호 매칭·역할별 잔존율·그룹 플레이·별도 온보딩 퍼널·KPI)은 RE:START와 기준값이 달라 공개 본문에서 제외.
    # 내용은 삭제하지 않고 gamepulse/content/games.py · views/deep_dives.py · views/game_page.py 에 보관하며,
    # 로컬에서 환경변수 GAMEPULSE_SHOW_ARCHIVE=1 로 실행할 때만 아래 보관함을 표시한다. (archive/README.md 참고)
    if os.getenv("GAMEPULSE_SHOW_ARCHIVE") != "1":
        return
    with st.expander("보관함 · v0.1 분석 (가상 예시 데이터 · 비공개)"):
        st.caption("초기 버전의 예시 데이터 화면입니다. 실제 유저 의견이 아니며 RE:START와 기준값이 다릅니다.")
        t = st.tabs(["문제 정의", "불만 유형(가상)", "원인 가설", "개선 전략", "KPI", "심층 분석"])
        with t[0]:
            game_page._problem(g)
        with t[1]:
            game_page._complaints(g)
        with t[2]:
            game_page._hypotheses(g)
        with t[3]:
            game_page._strategies(g)
        with t[4]:
            game_page._kpis(g)
        with t[5]:
            DEEP_DIVES["overwatch"]()
