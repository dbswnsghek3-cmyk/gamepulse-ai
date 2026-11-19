"""오버워치 페이지 — PROJECT RE:START (시각·체험 중심).

구성
- 표지: 최신 영웅 선택 화면(크게) + 역할별 영웅 수 + 초상화 영역 확대 + 공식 영웅 54명 목록(펼치기)
- 1 문제와 결론: 복귀 유저가 첫 전투까지 거치는 실제 화면 4장
- 2 실제 근거: 게임 화면(주석 표시) · 유저 의견 · 공식 업데이트 · 이용 지표
- 3 원인 가설 · 4 개선안 체험(왼쪽 실제 화면 vs 오른쪽 A·B·C 기획 시안)과 우선순위
- 5 KPI·A/B 테스트·가정 시뮬레이션 · 6 실행·제안

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
from gamepulse.sim.restart_sim import CohortInput, SimInput, run, sample_size_two_proportions, validate_base
from gamepulse.ui.charts import PLOTLY_CONFIG, style
from gamepulse.ui.components import badge, html
from gamepulse.views import game_page
from gamepulse.views.deep_dives import DEEP_DIVES

TABS = ["1 문제와 결론", "2 실제 근거", "3 원인 가설", "4 개선안 체험", "5 KPI·A/B 테스트", "6 실행·제안"]
LEARNING_CODES = {"영웅·스킬 학습 부담", "상대 영웅 대응 이해 부족", "복귀 적응·변경점 파악", "전투 중 정보 과부하"}


# ----------------------------------------------------------------------
# 표시 헬퍼
def b_real() -> str:
    return badge("실제 자료", "press")


def b_sim() -> str:
    return badge("가정 시뮬레이션", "sim")


def b_hypo() -> str:
    return badge("가설", "hypo")


def b_plan() -> str:
    return badge("기획 제안", "pm")


def b_mock() -> str:
    return badge("기획 시안", "sim")


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


def table(headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        st.info("표시할 자료가 없습니다.")
        return
    th = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    html(f'<div class="gp-table-wrap"><table class="gp-table"><tr>{th}</tr>{body}</table></div>')


def bullets(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{escape(x)}</li>" for x in items) + "</ul>"


def legend_bottom(fig: go.Figure, xtitle: bool = True) -> go.Figure:
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.25 if xtitle else -0.12, x=0, title_text=""),
                      margin=dict(b=40))
    return fig


def plot(fig: go.Figure) -> None:
    st.plotly_chart(fig, config=PLOTLY_CONFIG)


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
    "hero_select": {
        "marks": [("돌격", "", (90, 762, 573, 921), ""), ("공격", "", (597, 762, 1323, 921), ""),
                  ("지원", "", (1344, 762, 1833, 921), "right")],
        "facts": ["영웅 선택 화면 하단에 54명의 초상화가 역할별로 한 번에 나열된다",
                  "초상화에는 이름이 없고, 고른 영웅(시온)만 이름이 표시된다"],
    },
    "match_select": {
        "marks": [("남은 시간", "0:01", (40, 250, 310, 330), "below"),
                  ("팀 조합", "팀원 영웅이 함께 표시", (262, 487, 1650, 757), ""),
                  ("영웅 설명", "한 줄", (1455, 184, 1868, 224), "right below")],
        "facts": ["실제 경기에서는 '팀 구성까지 남은 시간' 안에 영웅을 골라야 한다 (캡처 시점 0:01)",
                  "고른 영웅의 설명은 우측 상단 한 줄뿐이다 — 정크랫: '적을 처치하면 잠깐 동안 재장전 속도가 증가합니다'",
                  "팀원이 고른 영웅을 보며 조합을 맞춰야 해, 낯선 영웅이 많을수록 판단할 것이 늘어난다"],
    },
    "returning_menu": {
        "marks": [("이벤트", "군림", (90, 195, 615, 525), ""),
                  ("도전 과제", "", (1482, 120, 1887, 468), "right below"),
                  ("이벤트·패스·상점", "", (102, 780, 1842, 933), "")],
        "facts": ["접속하면 이벤트 '군림' 배너와 이벤트·배틀 패스·상점 카드가 가장 크게 보인다",
                  "우측에는 발굴 입문·일일·주간 도전 과제가 표시된다",
                  "이 화면에는 마지막 접속 이후 바뀐 점(신규 영웅·역할 변경)을 요약한 안내가 따로 보이지 않는다"],
    },
    "skill_detail": {
        "marks": [("무기·궁극기", "", (60, 180, 630, 600), ""), ("기술 3 · 지속 능력", "", (667, 180, 1215, 720), ""),
                  ("특전 4", "2·3레벨 선택", (1275, 180, 1875, 690), "right")],
        "facts": ["영웅 1명 설명에 무기 1 · 궁극기 1 · 기술 3 · 지속 능력 1 · 특전 4, 모두 10개 항목이 있다 (시온 기준)",
                  "54명이면 익힐 항목이 수백 개다. 특전은 경기 중 레벨에 따라 고르는 선택지라 상대 영웅의 변수도 늘어난다",
                  "이 화면은 영웅을 직접 골라 찾아 들어가야 하며, '방금 나를 처치한 기술'을 따로 보여 주지는 않는다"],
    },
    "mission_screen": {
        "marks": [("안내", "AI 상대·사용자 지정 게임 제외", (60, 326, 740, 372), ""),
                  ("남은 기간", "18일", (1610, 205, 1875, 282), "right"),
                  ("경기 수 과제", "5~20회 · 승리 시 2배", (102, 382, 1827, 660), "right"),
                  ("잠김", "선행 과제 필요", (102, 663, 1827, 938), "below")],
        "facts": ["이벤트 도전 과제 8개가 모두 '게임 N회 완료 (승리 시 진척도 두 배)' 형식이다",
                  "대부분의 도전 과제는 사용자 지정 게임·AI 상대 연습에서 완료할 수 없다고 안내한다",
                  "기술 사용·역할 목표처럼 '배우는 행동'을 기준으로 한 과제는 이 화면에 없다"],
    },
    "combat_scene": {
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
    items = ""
    if marks and note_.get("marks"):
        items += "<ol>" + "".join(f"<li><b>{escape(lab)}</b>{' · ' + escape(desc) if desc else ''}</li>"
                                  for lab, desc, _, _ in note_["marks"]) + "</ol>"
    if facts and note_.get("facts"):
        items += bullets(note_["facts"])
    lead_ = f"<div>{lead}</div>" if lead else ""
    blur_note = " · 다른 플레이어 닉네임은 가림 처리" if stt.slot.get("blur") else ""
    title_ = escape(title or stt.slot.get("title", ""))
    return (f'<figure class="ow-shot {size}"><div class="ow-shot-bar"><span class="ow-shot-tag">{escape(tag)}</span>{title_}</div>'
            f'<div class="ow-shot-img"><img src="data:image/jpeg;base64,{_src(stt, max_w)}" alt="{title_}" loading="lazy">{boxes}</div>'
            f'<figcaption>{lead_}{items}<div class="ow-shot-src">{escape(stt.caption)}{blur_note}</div></figcaption></figure>')


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
    _cover(rs, heroes, statuses, manifest)

    t = st.tabs(TABS)
    with t[0]:
        _s1_summary(rs, ops, statuses)
    with t[1]:
        _s2_evidence(rs, kp, steam, pc, ops, statuses)
    with t[2]:
        _s3_hypothesis(rs, ops)
    with t[3]:
        _s4_experience(rs, ops, heroes, tl, statuses)
    with t[4]:
        _s5_kpi(rs)
    with t[5]:
        _s6_execution(rs, g, statuses)


# ----------------------------------------------------------------------
def _cover(rs: dict, heroes: dict, statuses: dict, manifest: dict) -> None:
    cv = rs["cover"]
    n_all = len(heroes["heroes"])
    n_new = sum(1 for h in heroes["heroes"] if h.get("new_2026"))
    n_recent = sum(1 for h in heroes["heroes"] if h.get("recent_catchup"))
    html(f'<div class="ow-cover"><div class="ow-cover-t">{escape(cv["title"])}</div>'
         f'<div class="ow-cover-c">{escape(cv["copy"])}</div><div class="ow-cover-s">{escape(cv["subtitle"])}</div></div>')

    # 최신 영웅 선택 화면을 가장 크게: 영웅 수가 많다는 점이 한눈에 보이도록
    stt = statuses.get("hero_select")
    roles = (stt.slot.get("role_counts") or {}) if stt else {}
    shot("hero_select", statuses, size="hero", facts=False,
         title=f"최신 영웅 선택 화면 · 한 화면에 {sum(roles.values()) or n_all}명",
         mark_desc={k: f"{v}명" for k, v in roles.items()})
    if stt is not None and stt.ok and roles:
        html('<div class="ow-count">'
             f'<div><div class="ow-count-v">{sum(roles.values())}명</div><div class="ow-count-l">선택 화면에 나열된 영웅 (직접 셈)</div></div>'
             + "".join(f'<div><div class="ow-count-v">{v}</div><div class="ow-count-l">{escape(k)}</div></div>' for k, v in roles.items())
             + "</div>")
        zoom = _b64(str(stt.path), stt.path.stat().st_mtime, tuple(tuple(b) for b in stt.slot.get("blur", [])),
                    (80, 760, 1840, 930), 1760)
        html('<div class="ow-zoom"><div class="ow-zoom-h"><span><span class="ow-shot-tag">실제 게임 화면</span> 영웅 초상화 영역 확대</span>'
             '<span>초상화에는 이름이 없다 · 고른 영웅만 이름 표시</span></div>'
             f'<img src="data:image/jpeg;base64,{zoom}" alt="영웅 선택 화면 초상화 영역 확대"></div>')
        if sum(roles.values()) != n_all:
            st.warning(f"화면에서 센 영웅 {sum(roles.values())}명이 영웅 목록 {n_all}명과 다릅니다. image_manifest.json 을 확인하세요.")
    tiles([
        ("공식 영웅 수", f"{n_all}명", f'{b_real()} {link(heroes["source"], "공식 영웅 페이지")} · {heroes["checked_at"]} 기준'),
        ("2026년 신규 영웅", f"{n_new}명", f'{b_real()} 공식 패치노트'),
        ("블리자드 복귀 요약의 '최근 영웅'", f"{n_recent}명", f'{b_real()} 시즌 1 공지 기사'),
    ])
    note("영웅 수가 늘었다는 사실만으로 이탈 원인을 단정하지 않습니다.")
    with st.expander(f"공식 영웅 {n_all}명 이름 · 2026 신규·역할 변경 표시"):
        hero_grid(heroes)
        html('<div class="ow-legend"><span class="ow-hero new">2026 신규</span><span class="ow-hero recent">복귀 요약 소개</span>'
             '<span class="ow-hero changed">역할 변경</span><span class="ow-legend-t">영웅 수가 늘었다는 사실만으로 이탈 원인을 단정하지 않습니다.</span></div>')
    if n_all != heroes.get("official_count", n_all):
        st.warning(f"영웅 목록 {n_all}명이 공식 집계 {heroes.get('official_count')}명과 다릅니다. heroes.json 을 확인하세요.")
    html(f'<div class="ow-ps"><div class="ow-p"><span>핵심 문제</span>{escape(cv["problem"])}</div>'
         f'<div class="ow-arrow">→</div><div class="ow-s"><span>핵심 해결</span>{escape(cv["solution"])}</div></div>')


# ======================================================================
# 1 문제와 결론
def _s1_summary(rs: dict, ops: pd.DataFrame, statuses: dict) -> None:
    s = rs["summary"]
    v = ops[ops["verified"]]
    ret = v[v["user_type"] == "복귀"]
    ret_learning = sum(bool(set(opinion_codes(r)) & LEARNING_CODES) for _, r in ret.iterrows())
    head(s["headline"], s["lead"])

    sub("복귀 유저가 첫 전투까지 거치는 실제 화면", b_real())
    steps = [
        ("returning_menu", "메인 화면", "이벤트·상점이 먼저 보이고, 그동안 바뀐 점을 요약한 안내는 보이지 않는다"),
        ("match_select", "영웅 선택", "남은 시간 안에 54명 중 한 명을 골라야 하고, 영웅 설명은 한 줄뿐이다"),
        ("skill_detail", "스킬 확인", "영웅 1명에 설명 항목 10개. 낯선 상대 영웅은 직접 찾아봐야 한다"),
        ("combat_scene", "전투", "처치되면 상대 이름만 뜨고, 어떻게 대응할지는 알려 주지 않는다"),
    ]
    cards = []
    for i, (sid, ttl, problem) in enumerate(steps, 1):
        cards.append(shot_html(sid, statuses, marks=False, facts=False, max_w=800,
                               title=f"{ttl}", lead=f'<span class="ow-journey-n">{i}</span> {escape(problem)}'))
    if all(cards):
        html(f'<div class="ow-journey">{"".join(cards)}</div>')
        note("각 화면에서 확인한 사실은 '2 실제 근거 > 게임 화면' 탭에 표시해 두었다. 문제 문장은 화면 관찰에 근거한 기획자 해석이다.")
    else:
        for sid, _, _ in steps:
            image_slot(sid, statuses)

    tiles([
        ("검증한 유저 의견", f"{len(v)}건", f'{b_real()} 원문 링크 확인'),
        ("복귀 유저 의견 중 학습·적응 어려움", f"{ret_learning} / {len(ret)}건", f'{b_real()} 기획자 분류'),
    ])
    html(f'<div class="ow-conclusion"><div class="ow-conclusion-k">결론</div>{escape(s["conclusion"])}</div>')
    core = [x for x in rs["strategies"] if x["core"]]
    html('<div class="ow-list">' + "".join(
        f'<div class="ow-list-i"><b>{x["key"]}</b><span><strong>{escape(x["name"])}</strong> — {escape(x["tagline"])}</span></div>'
        for x in core) + "</div>")
    note("각 개선안은 '4 개선안 체험' 탭에서 직접 눌러 볼 수 있습니다.")


# ======================================================================
# 2 실제 근거
def _s2_evidence(rs: dict, kp: dict, steam: pd.DataFrame, pc: pd.DataFrame, ops: pd.DataFrame, statuses: dict) -> None:
    head("게임 화면·공식 업데이트·이용 지표·유저 의견에서 확인한 사실", "", b_real())
    t = st.tabs(["게임 화면", "유저 의견", "공식 업데이트", "이용 지표"])
    with t[0]:
        sub("최신 한국어 클라이언트에서 직접 확인한 화면", badge("기획자 관찰", "pm"))
        note("주황 상자는 설명을 위해 덧붙인 표시이고, 화면 자체는 수정하지 않았다 (다른 플레이어 닉네임만 가림).")
        shot("match_select", statuses, size="hero")
        pairs = [("returning_menu", "skill_detail"), ("mission_screen", "combat_scene")]
        for a, b in pairs:
            ha, hb = shot_html(a, statuses, max_w=1200), shot_html(b, statuses, max_w=1200)
            if ha and hb:
                html(f'<div class="ow-grid2">{ha}{hb}</div>')
            else:
                shot(a, statuses)
                shot(b, statuses)
    with t[1]:
        _opinions(rs, ops)

    with t[2]:
        sub("블리자드는 신규 유저 지원을 이미 늘려 왔다")
        html('<div class="ow-timeline">' + "".join(
            f'<div class="ow-tl"><div class="ow-tl-d">{escape(o["date"])}</div><div class="ow-tl-t">{escape(o["title"])}</div>'
            f'<div class="ow-tl-b">{escape(o["fact"])}</div><div class="ow-tl-s">{link(o["url"], "공식 원문")}</div></div>'
            for o in rs["official"]) + "</div>")
        note("신규 유저 전 영웅 개방(2025)과 복귀 요약 기사·키워드 설명(2026)이 있어, RE:START는 이를 보완·확장하는 방향으로 잡았다.")
        with st.expander("자세히 보기 · 기존 기능의 한계 · 넥슨 퍼블리싱 범위"):
            table(["기능", "한계 또는 확인이 필요한 부분"], [[escape(o["title"]), escape(o["limit"])] for o in rs["official"]])
            st.markdown("**역할 구분** — 넥슨: 한국 PC 버전(Steam 제외) 퍼블리싱·라이브 운영·PC방 / 블리자드: 게임 개발·글로벌 운영·Steam·콘솔")
            src = {x["id"]: x for x in kp["sources"]}
            table(["항목", "확인 내용", "출처"],
                  [[escape(i["topic"]), escape(i["official"]), " · ".join(link(src[k]["url"], src[k]["kind"]) for k in i["source_ids"])]
                   for i in kp["items"]])
            st.caption(f"블리자드 공식 사이트·언론 보도 기준 · 확인일 {COLLECTED_AT}")

    with t[3]:
        if steam.empty:
            st.info("Steam 자료를 불러오지 못했습니다.")
        else:
            last = steam.iloc[-1]
            sub("Steam 접속자는 시즌 1 때 크게 늘었다", b_real())
            d = steam.tail(12)
            fig = go.Figure(go.Bar(x=d["month"], y=d["avg_players"], marker_color=C["blue"],
                                   hovertemplate="%{x|%Y-%m} · 월평균 %{y:,.0f}명<extra></extra>"))
            fig.update_yaxes(title="월평균 동시접속자(명)", tickformat=",")
            fig.update_xaxes(title="", tickformat="%y.%m")
            plot(style(fig, "Steam 월평균 동시접속자 · 최근 12개월", height=340))
            note(f"{last['month']:%Y년 %m월} 월평균 {last['avg_players']:,.0f}명. 전 세계 Steam 이용자만 집계한 값으로, 전체 이용자나 한국 유저 수가 아니다.")
            with st.expander("자세히 보기 · 출처와 해석 주의"):
                st.markdown(f"출처: [{STEAM_SOURCE['name']}]({STEAM_SOURCE['url']}) · 확인일 {COLLECTED_AT}")
                st.caption("Battle.net·넥슨 클라이언트·콘솔 이용자는 빠져 있다. 2026년 2월 급증은 시즌 1과 명칭 변경 시기가 겹쳐 원인을 하나로 볼 수 없다.")

        sub("한국 PC방 점유율은 넥슨 서비스 이후 올랐다", b_real())
        tracker = st.radio("집계원", ["게임트릭스", "더로그"], horizontal=True, key="ow_pc_tracker")
        q = pc[pc["plottable"] & (pc["tracker"] == tracker)]
        if q.empty:
            st.info("선택한 집계원의 자료가 없습니다.")
        else:
            daily, weekly = q[q["granularity"] == "일간"], q[q["granularity"] != "일간"]
            fig = go.Figure()
            fig.add_scatter(x=daily["period_start"], y=daily["share_pct"], mode="markers", name="일간",
                            marker=dict(size=11, color=C["navy"]), customdata=daily[["rank"]],
                            hovertemplate="%{x|%m-%d} · %{y:.2f}% (%{customdata[0]}위)<extra></extra>")
            for j, r in enumerate(weekly.itertuples()):
                fig.add_scatter(x=[r.period_start, r.period_end], y=[r.share_pct] * 2, mode="lines", name="주간",
                                line=dict(color=C["sky"], width=8), showlegend=j == 0, legendgroup="w",
                                hovertemplate=f"{r.granularity} · {r.share_pct:.2f}% ({int(r.rank)}위)<extra></extra>")
            fig.add_vline(x=pd.Timestamp("2026-08-12"), line_dash="dot", line_color=C["blue"])
            fig.update_yaxes(title="점유율(%)", range=[0, 12.5])
            fig.update_xaxes(title="", range=[pd.Timestamp("2026-03-15"), pd.Timestamp("2026-10-31")], tickformat="%m월")
            plot(legend_bottom(style(fig, f"PC방 점유율 · {tracker} 기준", height=340), xtitle=False))
        note("한국 PC방 표본 기준의 지역 지표로, 전 세계 이용 지표와는 다르다. 점선은 넥슨 서비스 개시일(8/12).")
        with st.expander("자세히 보기 · 원자료와 집계 기준"):
            st.caption("두 집계원은 표본 PC방이 달라 같은 날에도 순위가 다르다(9/13 더로그 2위, 게임트릭스 5위). PC방 이벤트·신규 시즌이 겹쳐 상승 원인을 단정할 수 없고, 계약 발표 이전 수치는 확보하지 못했다.")
            st.dataframe(
                pc[["tracker", "period_start", "granularity", "rank", "share_pct", "source_publisher", "source_url", "status"]]
                .rename(columns={"tracker": "집계원", "period_start": "기준일", "granularity": "단위", "rank": "순위",
                                 "share_pct": "점유율(%)", "source_publisher": "보도 매체", "source_url": "원문", "status": "상태"}),
                hide_index=True, column_config={"원문": st.column_config.LinkColumn("원문", display_text="열기"),
                                                "기준일": st.column_config.DateColumn(format="YYYY-MM-DD")})


def _opinion_card(r) -> str:
    tone = {"부정": "neg", "중립": "neu", "긍정": "pos"}.get(r["sentiment"], "neu")
    plat = "인벤" if "인벤" in r["platform"] else ("디시인사이드" if "디시" in r["platform"] else "블리자드 포럼")
    tags = " · ".join(opinion_codes(r))
    return (f'<div class="ow-quote {tone}"><div class="ow-quote-tag">{escape(r["sentiment"])} · {escape(r["user_type"])} · {escape(tags)}</div>'
            f'<div class="ow-quote-t">{escape(r["summary_ko"])}</div>'
            f'<div class="ow-quote-o">“{escape(r["quote_original"])}”</div>'
            f'<div class="ow-quote-m">{plat} · {escape(r["published_date"])} · {link(r["source_url"], "원문 보기")}</div></div>')


def _opinions(rs: dict, ops: pd.DataFrame) -> None:
    v = ops[ops["verified"]]
    other = ops[~ops["verified"]]
    if v.empty:
        st.info("검증된 유저 의견이 없습니다.")
        return
    n_ko, n_en = int((v["language"] == "한국어").sum()), int((v["language"] == "영어").sum())
    sub("영웅·스킬을 익히는 어려움이 가장 많이 언급됐다", b_real())
    tiles([
        ("검증 완료 의견", f"{len(v)}건", f"목표 50건 · 한국어 {n_ko} · 영어 {n_en}"),
        ("부정 · 중립 · 긍정", " · ".join(str(int((v['sentiment'] == s).sum())) for s in ["부정", "중립", "긍정"]), "기획자 분류"),
        ("미검증·제외", f"{len(other)}건", "Reddit·유튜브 미확인, 중복·주제 무관"),
    ])

    cnt = code_counts(v)
    fig = go.Figure(go.Bar(y=cnt.index, x=cnt.values, orientation="h", marker_color=C["blue"], text=cnt.values,
                           textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x}건<extra></extra>"))
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig.update_xaxes(title="언급 수(건, 복수 분류)", range=[0, max(cnt.max(), 1) * 1.25 + 1])
    plot(style(fig, f"문제 유형별 언급 수 (의견 n={len(v)})", height=360))
    note(f"한 의견에 여러 문제가 있으면 모두 세어 합계({int(cnt.sum())}건)가 의견 수보다 많다. 자발적 게시글이라 전체 이용자 비율이 아니다.")

    sub("댓글 카드로 보기")
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
    per = 6
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
            .rename(columns={"opinion_id": "ID", "platform": "플랫폼", "published_date": "작성일", "user_type": "유형",
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
    head("학습 부담이 반복 패배로 이어지는지 확인이 필요하다", "", b_hypo())
    steps = []
    for i, f in enumerate(p["flow"]):
        steps.append(f'<div class="ow-step"><div class="ow-step-n">{i + 1}</div><div class="ow-step-t">{escape(f["step"])}</div>'
                     f'<div class="ow-step-d">{escape(f["desc"])}</div><div class="ow-step-b">{escape(f["basis"])}</div></div>')
        if i < len(p["flow"]) - 1:
            steps.append('<div class="ow-step-a">→</div>')
    html(f'<div class="ow-flow">{"".join(steps)}</div>')

    sub("다른 원인도 함께 본다")
    cards = []
    for a in p["alternatives"]:
        n = f"관련 의견 {int(cnt.get(a['category'], 0))}건" if a.get("category") else "관련 의견 없음"
        cards.append(f'<div class="ow-alt"><div class="ow-alt-t">{escape(a["cause"])}</div><div class="ow-alt-n">{n}</div>'
                     f'<div class="ow-alt-d">{escape(a["evidence"])}</div><div class="ow-alt-c">확인: {escape(a["check"])}</div></div>')
    html(f'<div class="ow-grid3">{"".join(cards)}</div>')
    note(p["verify"])


# ======================================================================
# 4 개선안 체험 (A·B·C 기획 시안) + 비교·우선순위
def _s4_experience(rs: dict, ops: pd.DataFrame, heroes: dict, tl: pd.DataFrame, statuses: dict) -> None:
    head("A·B·C를 직접 눌러 보세요", "왼쪽은 지금의 실제 게임 화면, 오른쪽은 게임에 없는 제안 기능의 기획 시안입니다. 시안 속 수치는 예시입니다.", b_mock())
    real_vs_mock_key()
    t = st.tabs(["A 복귀 브리핑", "B 전투 학습 카드", "C 첫 10경기 미션", "전략 상세·우선순위"])
    with t[0]:
        _proto_a(heroes, tl, statuses)
    with t[1]:
        _proto_b(heroes, statuses)
    with t[2]:
        _proto_c(statuses)
    with t[3]:
        _strategy_detail(rs, ops)


LAST_ACCESS = {"2026년 1월 (시즌 1 이전)": "2026-01-31", "2026년 7월": "2026-07-31", "2026년 9월": "2026-09-30"}


def _a_reset() -> None:
    st.session_state["ow_a_step"] = 0


def _a_set(step: int) -> None:
    st.session_state["ow_a_step"] = step


def _proto_a(heroes: dict, tl: pd.DataFrame, statuses: dict) -> None:
    sub("마지막 접속 이후 바뀐 것만 3분 안에", b_mock())
    html('<div class="ow-vs"><div><b>기존 기능</b> 블리자드 시즌 1 공지 기사 속 복귀 요약 (웹 기사, 일괄 안내)</div>'
         '<div><b>제안 기능</b> 게임 접속 시 내 마지막 접속일 기준으로 놓친 것만 안내 (기획 시안)</div></div>')
    left, right = st.columns([1, 1], gap="medium")
    with left:
        col_head("real", "현재 · 접속하면 보이는 메인 화면")
        shot("returning_menu", statuses, facts=False, max_w=1200,
             lead="이벤트·상점 위주로 구성돼, 그동안 바뀐 점은 직접 찾아봐야 한다 (기획자 관찰)")
    with right:
        col_head("mock", "제안 · 접속 직후 복귀 브리핑")
        _proto_a_body(heroes, tl)
    note("측정: 브리핑 시작률·완료율·건너뛰기 단계, 복귀 D7 잔존율")


def _proto_a_body(heroes: dict, tl: pd.DataFrame) -> None:
    last = st.radio("예시 계정의 마지막 접속 시점", list(LAST_ACCESS), horizontal=True, key="ow_a_last", on_change=_a_reset)
    cutoff = LAST_ACCESS[last]
    new = [h for h in heroes["heroes"] if h.get("new_2026") and h["new_2026"] > cutoff]
    changed = [h for h in heroes["heroes"] if h.get("role_changed") and h["role_changed"] > cutoff]
    sys_rows = tl[tl["date"].notna() & (tl["type"] == "시스템") & tl["status"].str.startswith("공식") & (tl["date"] > pd.Timestamp(cutoff))]
    sys_rows = sys_rows.sort_values("date")
    total = len(new) + len(changed) + len(sys_rows)
    step = st.session_state.get("ow_a_step", 0)

    html(f'<div class="ow-proto"><div class="ow-proto-bar"><span>RE:START 복귀 브리핑</span>{b_mock()}</div>'
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
            html(f'<div class="ow-proto-card mock"><div class="ow-proto-card-t">{title}</div><div class="ow-heroes small">{body}</div>'
                 f'<div class="ow-proto-card-s">출처: 공식 패치노트·공식 영웅 페이지</div></div>')
            c1, c2, c3 = st.columns(3)
            c1.button("이전", key="ow_a_prev", on_click=_a_set, args=(max(step - 1, 0),), width="stretch")
            c2.button("다음" if step < 3 else "완료", key="ow_a_next", type="primary", on_click=_a_set, args=(step + 1,), width="stretch")
            c3.button("건너뛰기", key="ow_a_skip", on_click=_a_set, args=(-1,), width="stretch")
        else:
            st.success("브리핑 완료 · 이제 빠른 대전으로 감각을 되찾아 보세요. (기획 시안)")
            st.button("처음으로", key="ow_a_restart", on_click=_a_set, args=(0,))


def _proto_b(heroes: dict, statuses: dict) -> None:
    sub("방금 진 상대의 기술과 대처법을 경기 직후에", b_mock())
    html('<div class="ow-vs"><div><b>기존 기능</b> 경기 중·연습장에서 스킬에 마우스를 올리면 키워드 정의 확인 (2026-02 공식)</div>'
         '<div><b>제안 기능</b> 경기 후, 여러 번 진 상대의 기술과 대처법을 카드로 안내 (기획 시안 · 게임에 없음)</div></div>')
    left, right = st.columns([1, 1], gap="medium")
    with left:
        col_head("real", "현재 · 처치당한 직후 전투 화면")
        shot("combat_scene", statuses, facts=False, max_w=1200,
             lead="'OOO에게 죽음'만 뜨고, 어떤 기술에 당했는지·어떻게 대응할지는 없다 (기획자 관찰)")
    with right:
        col_head("mock", "제안 · 경기 직후 전투 학습 카드")
        _proto_b_body(heroes)
    sub("카드에 담을 설명의 출처 · 현재 영웅 정보 화면", b_real())
    shot("skill_detail", statuses, facts=False,
         lead="지금은 이 화면을 영웅별로 직접 열어야 한다. B 카드는 여기의 공식 설명 중 '나를 처치한 기술'만 골라 경기 직후 보여 준다.")
    note("측정: 카드 사용률, 카드 확인 후 30분 안에 다음 경기 시작률")


def _proto_b_body(heroes: dict) -> None:
    sk = {s["hero"]: s for s in heroes.get("skills_verified", [])}
    if not sk:
        st.info("스킬 자료가 없습니다.")
        return
    c1, c2 = st.columns(2)
    hero = c1.selectbox("방금 상대한 영웅 (예시)", list(sk), key="ow_b_hero")
    skill = c2.selectbox("확인할 기술", sk[hero]["skills"], key="ow_b_skill")
    html(f'<div class="ow-proto dark"><div class="ow-proto-bar"><span>전투 학습 카드</span>{b_mock()}</div>'
         f'<div class="ow-proto-s">이번 경기에서 <b>{escape(hero)}</b>에게 3번 처치됐어요 <small>(예시 데이터)</small></div>'
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


MISSIONS = [
    (1, 3, "역할·스킬 이해", ["주력 영웅의 기술 3개를 모두 사용하기", "역할 목표 1회 달성하기"]),
    (4, 6, "상대 영웅 대응", ["전투 학습 카드 1회 확인하기", "자주 진 상대를 만나 생존하기"]),
    (7, 10, "팀 플레이", ["아군과 함께 목표 지점 점령하기", "칭찬 기능 사용하기"]),
]


def _proto_c(statuses: dict) -> None:
    sub("승패가 아닌 행동으로 채우는 첫 10경기", b_mock())
    html('<div class="ow-vs"><div><b>기존 기능</b> 신규 유저 전 영웅 즉시 개방, 경쟁전은 일반전 20승 후 개방 (2025-08 공식)</div>'
         '<div><b>제안 기능</b> 영웅 선택은 그대로 두고 학습 순서만 제안하는 선택형 미션 (기획 시안)</div></div>')
    left, right = st.columns([1, 1], gap="medium")
    with left:
        col_head("real", "현재 · 이벤트 도전 과제 화면")
        shot("mission_screen", statuses, facts=False, max_w=1200,
             lead="이 화면의 과제는 모두 '게임 N회 완료 (승리 시 2배)' 형식이고, 배우는 행동을 기준으로 한 과제는 없다 (기획자 관찰)")
    with right:
        col_head("mock", "제안 · 첫 10경기 적응 미션")
        _proto_c_body()
    note("측정: 첫 10경기 완료율, 신규 D30 잔존율, 미션 끄기 비율")


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
        blocks.append(f'<div class="ow-mission {cls}"><div class="ow-mission-h">{a}~{b}경기 · {escape(name)}<span>{state}</span></div>'
                      + "".join(f'<div class="ow-mission-i">{"✓" if done else "○"} {escape(x)}</div>' for x in items) + "</div>")
    html(f'<div class="ow-proto narrow"><div class="ow-proto-bar"><span>첫 10경기 적응 미션</span>{b_mock()}</div>'
         f'<div class="ow-progress">{segs}</div><div class="ow-grid3">{"".join(blocks)}</div>'
         f'<div class="ow-proto-card-s">보상 예시: 외형 아이템 (확정 아님 · 경쟁 밸런스에 영향 없는 보상만 검토)</div></div>')


def _strategy_detail(rs: dict, ops: pd.DataFrame) -> None:
    rc = rs["rice"]
    items = pd.DataFrame(rc["items"])
    items["score"] = items["reach"] * items["impact"] * items["confidence"] / items["effort"]
    items = items.sort_values("score", ascending=False)
    order = " → ".join(items["key"])
    sub(f"실행 순서는 {order}", b_plan())
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
            table(["항목", "내용"], rows)

    name = {s["key"]: s["name"] for s in rs["strategies"]}
    items["label"] = items["key"] + " " + items["key"].map(name)
    fig = go.Figure(go.Bar(y=items["label"], x=items["score"], orientation="h", marker_color=C["blue"],
                           text=items["score"].round(0).astype(int).map("{:,}".format), textposition="outside", cliponaxis=False))
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig.update_xaxes(title="RICE 점수 (가정값으로 계산)", range=[0, items["score"].max() * 1.3])
    plot(style(fig, "전략별 RICE 점수 (기획자 가정)", height=300))
    note("복귀 의견 근거가 가장 많은 A를 먼저, 운영 비용과 협력사 변수가 큰 D는 A~C 결과를 본 뒤 결정한다.")
    with st.expander("자세히 보기 · RICE 산식과 가정값"):
        st.caption(f"{rc['formula']} · {rc['notes']}")
        table(["전략", "도달", "영향", "확신", "노력(인월)", "점수", "근거"],
              [[escape(x.label), f"{x.reach:,}", str(x.impact), str(x.confidence), str(x.effort), f"{x.score:,.0f}", escape(x.why)]
               for x in items.itertuples()])

    cmp_ = rs["comparison"]
    sub(f"대안 비교: {cmp_['alt_name']} vs RE:START", badge("기획자 정성 평가", "pm"))
    df = pd.DataFrame(cmp_["criteria"])
    fig = go.Figure()
    fig.add_bar(y=df["name"], x=df["restart"], name="RE:START", orientation="h", marker_color=C["blue"])
    fig.add_bar(y=df["name"], x=df["alt"], name=cmp_["alt_name"], orientation="h", marker_color=C["sky"])
    fig.update_layout(barmode="group")
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig.update_xaxes(range=[0, 5.5], dtick=1, title="유리함 (1~5점, 정성 평가)")
    plot(legend_bottom(style(fig, "선택 기준별 비교", height=380)))
    note(cmp_["decision"])
    with st.expander("자세히 보기 · 평가 근거"):
        st.caption(cmp_["alt_desc"] + " · " + cmp_["note"])
        table(["기준", "RE:START", cmp_["alt_name"], "근거"],
              [[escape(c["name"]), str(c["restart"]), str(c["alt"]), escape(c["why"])] for c in cmp_["criteria"]])


# ======================================================================
# 5 KPI와 A/B 테스트
def _s5_kpi(rs: dict) -> None:
    ab = rs["ab_test"]
    head("복귀 유저의 D7 잔존율로 효과를 판단한다", "목표값은 실적이 아니라 실험으로 검증할 가설이다.")
    table(["구분", "지표", "확인 가능 여부"],
          [[b_real(), "Steam 동시접속자 · 한국 PC방 점유율", "공개 자료 (Steam 한정 · 한국 PC방 표본)"],
           [badge("내부 데이터 필요", "pending"), "DAU · D7 · D30 · 경기 완료율", "넥슨·블리자드 로그 필요 · 아래 수치는 가정"]])
    with st.expander("KPI 정의 (대상 · 분모 · 측정 시점)", expanded=False):
        table(["지표", "대상", "분모", "분자", "측정 시점", "역할", "목표(가설)"],
              [[f"<b>{escape(k['name'])}</b>", escape(k["target_users"]), escape(k["denominator"]), escape(k["numerator"]),
                escape(k["timing"]), escape(k["role"]), escape(k["target"])] for k in rs["kpi_defs"]])

    sub("A/B 테스트 설계", b_plan())
    table(["세그먼트", "실험군", "대조군"], [[escape(x["name"]), escape(x["treatment"]), escape(x["control"])] for x in ab["segments"]])
    tiles([("주요 성공 지표", escape(ab["primary"]), "세그먼트별로 판단"),
           ("안전 지표", "불만·신고율", escape(" · ".join(ab["guardrails"][1:]))),
           ("기간", "약 6주", escape(ab["duration"]))])
    with st.expander("자세히 보기 · 측정 방법 · 판단·중단 기준 · 필요 표본"):
        st.markdown(f"**측정 방법** — {ab['method']}  \n**배정** — {ab['unit']}  \n**즉시 중단** — {ab['stop_rule']}")
        table(["결과", "판단 기준"], [[f"<b>{escape(d['result'])}</b>", escape(d["rule"])] for d in rs["decision_rules"]])
        c1, c2, c3 = st.columns(3)
        base = c1.number_input("대조군 D7 (%)", 1.0, 99.0, 20.0, step=1.0, key="ab_base")
        eff = c2.number_input("참여자 개선 폭 (%p)", 0.5, 50.0, 6.0, step=0.5, key="ab_eff")
        part = c3.slider("참여율 (%)", 1, 100, 40, key="ab_part")
        c1, c2 = st.columns(2)
        alpha = c1.selectbox("유의수준", [0.01, 0.05, 0.10], index=1, key="ab_alpha")
        power = c2.selectbox("검정력", [0.8, 0.9], index=0, key="ab_power")
        itt = eff * part / 100
        n_itt = sample_size_two_proportions(base / 100, min(base + itt, 99.9) / 100, alpha, power)
        tiles([("배정 기준 기대 효과", f"+{itt:.2f}%p", f"{b_sim()} 참여율 × 개선 폭"),
               ("그룹당 필요 표본", "—" if n_itt is None else f"{n_itt:,}명", f"{b_sim()} 두 비율 차이 검정")])

    sub("가정 시뮬레이션: 도입 전후 비교", b_sim())
    top = st.container()
    chart = st.container()
    with st.expander("시뮬레이션 상세 설정 (가정값)"):
        st.markdown("**코호트**")
        c1, c2 = st.columns(2)
        n_new = c1.number_input("신규 코호트 (명)", 0, 10_000_000, 10_000, step=1000, key="rs_n_new")
        n_ret = c2.number_input("복귀 코호트 (명)", 0, 10_000_000, 20_000, step=1000, key="rs_n_ret")
        c1, c2 = st.columns(2)
        b_new = {d: c1.number_input(f"신규 {d} (%)", 0.0, 100.0, val, step=1.0, key=f"rs_new_{d}")
                 for d, val in (("D1", 40.0), ("D7", 20.0), ("D30", 10.0))}
        b_ret = {d: c2.number_input(f"복귀 {d} (%)", 0.0, 100.0, val, step=1.0, key=f"rs_ret_{d}")
                 for d, val in (("D1", 50.0), ("D7", 30.0), ("D30", 15.0))}
        c1, c2 = st.columns(2)
        p_new = c1.slider("신규 미션 참여율 (%)", 0, 100, 40, key="rs_p_new")
        p_ret = c2.slider("복귀 브리핑 시작률 (%)", 0, 100, 35, key="rs_p_ret")
        st.markdown("**참여자 개선 폭 (%p)**")
        c1, c2, c3 = st.columns(3)
        uplift = {"D1": c1.slider("D1", 0.0, 20.0, 5.0, 0.5, key="rs_u1"),
                  "D7": c2.slider("D7", 0.0, 20.0, 6.0, 0.5, key="rs_u7"),
                  "D30": c3.slider("D30", 0.0, 20.0, 4.0, 0.5, key="rs_u30")}
        st.markdown("**적응 퍼널 (%)**")
        c1, c2 = st.columns(2)
        f_first = c1.slider("접속 → 첫 경기", 0, 100, 85, key="rs_f1")
        f_3 = c2.slider("첫 경기 → 3경기", 0, 100, 70, key="rs_f3")
        c1, c2 = st.columns(2)
        f_10 = c1.slider("3경기 → 10경기", 0, 100, 55, key="rs_f10")
        f_d7 = c2.slider("10경기 → D7 재접속", 0, 100, 60, key="rs_fd7")
        c1, c2 = st.columns(2)
        fu3 = c1.slider("참여자 3경기 개선 (%p)", 0.0, 30.0, 8.0, 0.5, key="rs_fu3")
        fu10 = c2.slider("참여자 10경기 개선 (%p)", 0.0, 30.0, 10.0, 0.5, key="rs_fu10")
        c1, c2 = st.columns(2)
        brief_comp = c1.slider("브리핑 완료율 (%)", 0, 100, 70, key="rs_bc")
        card_use = c2.slider("카드 사용률 (%)", 0, 100, 30, key="rs_cu")
        st.markdown("**PC방 이벤트(D) · 비용**")
        c1, c2 = st.columns(2)
        pc_reach = c1.slider("PC방 대상 비율 (%)", 0, 100, 25, key="rs_pcr")
        pc_part = c2.slider("PC방 참여율 (%)", 0, 100, 30, key="rs_pcp")
        c1, c2 = st.columns(2)
        pc_comp = c1.slider("미션 완료율 (%)", 0, 100, 60, key="rs_pcc")
        pc_rev = c2.slider("7일 재방문율 (%)", 0, 100, 50, key="rs_pcv")
        c1, c2 = st.columns(2)
        pc_friend = c1.slider("친구 동반율 (%)", 0, 100, 40, key="rs_pcf")
        reward = c2.number_input("1인당 보상 (원)", 0, 1_000_000, 3000, step=500, key="rs_rw")
        c1, c2 = st.columns(2)
        fixed = c1.number_input("이벤트 고정비 (원)", 0, 10_000_000_000, 20_000_000, step=1_000_000, key="rs_fx")
        hc = c2.number_input("개발·운영 인력 (명)", 0.0, 200.0, 5.0, step=1.0, key="rs_hc")
        c1, c2 = st.columns(2)
        months = c1.number_input("기간 (개월)", 0.0, 36.0, 3.0, step=0.5, key="rs_mo")
        mcost = c2.number_input("1인 월 비용 (원)", 0, 100_000_000, 6_000_000, step=500_000, key="rs_mc")
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
        base_dau=base_dau, active_prob=act, arrival_days=arrive, horizon=horizon)
    res = run(inp)
    r, f, pcb, cs, ld = res.retention, res.funnel, res.pcbang, res.costs, res.leading
    total = n_new + n_ret

    def rate(day, col):
        return r.loc[r["day"] == day, col].sum() / total * 100 if total else float("nan")

    with top:
        for w in res.warnings:
            st.warning(w)
        tiles([
            ("D7 잔존율 · 전체", f"{pct(rate('D7', 'base_users'))} → <b>{pct(rate('D7', 'new_users'))}</b>", f"{b_sim()} 신규+복귀 인원 가중"),
            ("D30 잔존율 · 전체", f"{pct(rate('D30', 'base_users'))} → <b>{pct(rate('D30', 'new_users'))}</b>", f"{b_sim()} 신규+복귀 인원 가중"),
            ("첫 10경기 완료율", f"{pct(f.loc[3, 'base'] / total * 100 if total else float('nan'))} → "
                                f"<b>{pct(f.loc[3, 'improved'] / total * 100 if total else float('nan'))}</b>", f"{b_sim()} 접속자 대비"),
        ])
    with chart:
        # 카드의 '전체' 수치와 같은 시나리오를 그래프에도 함께 표시 (코호트별 + 전체)
        long = r.melt(id_vars=["cohort", "day"], value_vars=["base_rate", "new_rate"], var_name="s", value_name="rate")
        long = long[long["day"].isin(["D7", "D30"])]
        if total:
            for d in ["D7", "D30"]:
                for s_, col in [("base_rate", "base_users"), ("new_rate", "new_users")]:
                    long = pd.concat([long, pd.DataFrame([{"cohort": "전체", "day": d, "s": s_, "rate": rate(d, col)}])])
        long["구분"] = long["cohort"] + " · " + long["s"].map({"base_rate": "도입 전", "new_rate": "도입 후"})
        fig = px.bar(long, x="day", y="rate", color="구분", barmode="group", text=long["rate"].round(1),
                     color_discrete_sequence=[C["sky"], C["blue"], "#C9D3E3", C["navy"], "#FBD9B0", C["warn"]],
                     labels={"day": "", "rate": "잔존율(%)"})
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_yaxes(range=[0, max(60, long["rate"].max() * 1.25)])
        style(fig, "[가정] D7·D30 도입 전후 · 신규 / 복귀 / 전체", height=440)
        fig.update_layout(plot_bgcolor="#FFFBF5")
        legend_bottom(fig)
        fig.update_layout(legend=dict(y=-0.3))  # 범례 6개가 x축 글자와 겹치지 않게
        plot(fig)
        note("위 카드의 수치는 그래프의 '전체'(신규+복귀 인원 가중 평균)와 같은 시나리오다. 실제 효과는 A/B 테스트로 판단한다.")

    with st.expander("자세히 보기 · 추가 지표 · 퍼널 · DAU · 비용 · 계산식"):
        dd = res.dau.pivot(index="day", columns="scenario", values="dau")
        tiles([
            ("브리핑 완료", f"{fmt_int(ld['briefing_completed'])}명", f"{b_sim()} 복귀 × 시작률 × 완료율"),
            ("카드 사용", f"{fmt_int(ld['card_users'])}명", f"{b_sim()} 전체 × 사용률"),
            ("PC방 복귀 유저 (D)", f"{fmt_int(ld['pc_returning'])}명", f"{b_sim()} 복귀 × 대상 × 참여율"),
            ("총 이벤트 비용 (D)", fmt_won(cs["event_cost"]), f"{b_sim()} 참여자 × 보상 + 고정비"),
            ("추가 D7 잔존 1명당 비용", fmt_won(cs["cost_per_added_d7"]), f"{b_sim()} (이벤트비+인건비) ÷ 추가 잔존"),
            (f"{horizon}일차 DAU 차이", f"{dd.iloc[-1]['RE:START 적용 가정'] - dd.iloc[-1]['현재 가정']:+,.0f}명", f"{b_sim()} 가정 모형"),
        ])
        fig = go.Figure()
        fig.add_trace(go.Funnel(name="도입 전", y=f["stage"], x=f["base"].round(), marker_color=C["sky"], textinfo="value"))
        fig.add_trace(go.Funnel(name="도입 후", y=f["stage"], x=f["improved"].round(), marker_color=C["blue"], textinfo="value"))
        fig.update_yaxes(automargin=True)
        plot(legend_bottom(style(fig, "[가정] 적응 퍼널 (명)", height=380), xtitle=False))
        fig = px.line(res.dau, x="day", y="dau", color="scenario", color_discrete_sequence=[C["sky"], C["blue"]],
                      labels={"day": "경과일", "dau": "DAU(명)", "scenario": ""})
        fig.update_yaxes(tickformat=",")
        plot(legend_bottom(style(fig, "[가정] DAU 시나리오", height=340)))
        fig = go.Figure(go.Funnel(y=pcb["stage"], x=pcb["users"].round(), marker_color=C["navy"], textinfo="value+percent initial"))
        fig.update_yaxes(automargin=True)
        plot(style(fig, "[가정] PC방 이벤트 퍼널 (명)", height=320))
        st.markdown("**KPI 연결 구조 (가설)**")
        table(["개선 방향", "전략", "확인할 지표"],
              [[escape(k["lever"]), escape(k["strategies"]), escape(" · ".join(k["leading"]))] for k in rs["kpi_chain"]])
        st.markdown(f"""**계산식**
- 개선 후 잔존율 = 기존 잔존율 + 참여율 × 개선 폭 (참여율은 한 번만 곱하고 D1 ≥ D7 ≥ D30 으로 보정)
- 전체 잔존율 = (신규 잔존 인원 + 복귀 잔존 인원) ÷ (신규 + 복귀 코호트)
- 적응 퍼널 = 이전 단계 × 전환율. 3·10경기 전환율에만 가중 참여율({cs['p_avg']:.1f}%) × 개선 폭을 더함
- 브리핑·카드·PC방 지표는 관측용이라 잔존율에 더하지 않음
- DAU = 코호트 외 활성 유저 + Σ 일별 유입 × 잔존 곡선 × 일일 접속 확률 (Steam 수치와 무관)
- 기존 유저는 실험 대상이 아니며 불만·신고율로만 관찰
""")


# ======================================================================
# 6 실행 계획과 최종 제안
def _s6_execution(rs: dict, g: dict, statuses: dict) -> None:
    head("A와 C로 8주 파일럿을 시작한다", "B는 게임 데이터 협업 범위가 정해지면 수동형부터 붙이고, D는 파일럿 결과를 보고 결정한다.", b_plan())
    mv = rs["mvp"]
    html(f'<div class="ow-grid2"><div class="ow-card plain"><div class="ow-card-k">MVP 포함</div>{bullets(mv["in"])}</div>'
         f'<div class="ow-card plain"><div class="ow-card-k">이번에는 제외</div>{bullets(mv["out"])}</div></div>')

    pl = rs["pilot"]
    sub("8주 파일럿 일정", badge("가정", "pm"))
    html('<div class="ow-timeline">' + "".join(
        f'<div class="ow-tl"><div class="ow-tl-d">{escape(w["period"])}</div><div class="ow-tl-b">{escape(w["work"])}</div></div>'
        for w in pl["weeks"]) + "</div>")
    with st.expander("자세히 보기 · 담당 부서 · 이벤트 로그 · 출시 전 점검 · 롤백 기준"):
        table(["담당", "역할"], [[escape(o["team"]), escape(o["role"])] for o in pl["owners"]])
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
            st.markdown("**주요 리스크와 대응**")
            for x in rs["risks"]:
                st.markdown(f"- {x['risk']} → {x['response']}")

    html('<div class="ow-conclusion"><div class="ow-conclusion-k">최종 제안</div>'
         '영웅 선택은 그대로 두고, 복귀 브리핑(A)과 첫 10경기 미션(C)으로 복귀·신규 유저의 첫 주를 돕는다. '
         '8주 파일럿에서 D7 잔존율이 개선되고 불만·신고율이 나빠지지 않으면 전투 학습 카드(B)와 PC방 이벤트(D)로 넓힌다.</div>')

    sub("분석의 한계")
    note(rs["summary"]["limit"])
    pending = [s for s in statuses.values() if not s.ok]
    if pending:
        st.caption(f"게임 화면 {len(pending)}종은 최신 한국어 스크린샷 검증 전이라 자리만 표시했습니다. (assets/overwatch/README.md 참고)")
    st.caption(f"{rs['disclaimer']} · 자료 확인일 {COLLECTED_AT}")

    with st.expander("부록 · v0.1 분석 (가상 예시 데이터)"):
        st.caption("초기 버전의 예시 데이터 화면입니다. 실제 유저 의견이 아닙니다.")
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
