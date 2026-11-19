"""재사용 UI 컴포넌트 (HTML 카드, 배지, 공지)."""

from __future__ import annotations

from html import escape

import streamlit as st

from gamepulse.config import HYPOTHESIS_NOTICE, SAMPLE_LABEL, SAMPLE_NOTICE


def _md_bold(text: str) -> str:
    """**굵게** 표기만 HTML 로 변환 (나머지는 escape)."""
    parts = escape(text).split("**")
    return "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def badge(text: str, kind: str = "plain") -> str:
    return f'<span class="gp-badge {kind}">{escape(text)}</span>'


def sample_badge() -> str:
    return badge(SAMPLE_LABEL, "sample")


def hypo_badge() -> str:
    return badge("가설 · 검증 필요", "hypo")


def tier_badge(tier: str) -> str:
    kind = {"North Star": "tier-ns", "핵심": "tier-core", "가드레일": "tier-guard"}.get(tier, "plain")
    return badge(tier, kind)


def notice(text: str) -> None:
    html(f'<div class="gp-notice">{_md_bold(text)}</div>')


def sample_notice() -> None:
    html(f'<div class="gp-notice">{sample_badge()} {_md_bold(SAMPLE_NOTICE)}</div>')


def hypothesis_notice() -> None:
    html(f'<div class="gp-notice">{hypo_badge()} {_md_bold(HYPOTHESIS_NOTICE)}</div>')


def hero(eyebrow: str, title: str, desc: str, quote: str | None = None) -> None:
    q = f'<div class="gp-quote">“{escape(quote)}”</div>' if quote else ""
    html(
        f'<div class="gp-hero"><div class="gp-eyebrow">{escape(eyebrow)}</div>'
        f"<h1>{escape(title)}</h1><p>{escape(desc)}</p>{q}</div>"
    )


def section(title: str, subtitle: str = "", badges: str = "") -> None:
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    html(f'<div class="gp-section"><h3>{escape(title)} {badges}</h3>{sub}</div>')


def card(title: str, body: str = "", items: list[str] | None = None, meta: str = "",
         top: str = "", variant: str = "") -> str:
    """카드 HTML 문자열 반환 (grid() 로 묶어서 출력)."""
    li = "".join(f"<li>{_md_bold(i)}</li>" for i in (items or []))
    ul = f"<ul>{li}</ul>" if li else ""
    p = f"<p>{_md_bold(body)}</p>" if body else ""
    m = f'<div class="gp-meta">{_md_bold(meta)}</div>' if meta else ""
    return f'<div class="gp-card {variant}">{top}<h4>{escape(title)}</h4>{p}{ul}{m}</div>'


def grid(cards: list[str]) -> None:
    html(f'<div class="gp-grid">{"".join(cards)}</div>')


def footer() -> None:
    html(
        '<div class="gp-footer">GamePulse AI · 게임 사업PM 포트폴리오 프로젝트 · '
        "모든 수치와 시뮬레이션은 예시 데이터이며, 언급된 게임 및 상표는 각 권리자에게 있습니다. "
        "본 사이트는 해당 게임사와 관련이 없는 개인 분석물입니다.</div>"
    )
