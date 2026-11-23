"""큰 이미지 1장씩 보여 주는 갤러리 (FC 온라인 · PUBG 공용).

- 좌우 넘기기(스와이프 · 화살표) · 번호(1 / 3) · 클릭 확대 · 이미지 아래 설명 한 줄
- Streamlit: CSS 만으로 동작 (:target 확대 · 앵커 이동). 정적 페이지: 해시가 탭 전환에 쓰이므로 공용 PAGE_JS 가 링크 이동을 막고 JS 로 처리
- 슬라이드가 하나도 없으면 빈 문자열 → 영역을 그리지 않는다
"""

from __future__ import annotations

from html import escape


def gallery_html(key: str, slides: list[tuple[str, str, str]]) -> str:
    """slides = [(이미지 또는 이미지가 든 HTML, 설명 한 줄, 출처 한 줄)]."""
    n = len(slides)
    if not n:
        return ""
    out = []
    for i, (media, cap, credit) in enumerate(slides):
        nav = ""
        if n > 1:
            pv, nx = (i - 1) % n, (i + 1) % n
            nav = (f'<div class="nav"><a href="#g-{key}-{pv}" data-go="{pv}" aria-label="이전 이미지">‹</a>'
                   f'<a href="#g-{key}-{nx}" data-go="{nx}" aria-label="다음 이미지">›</a></div>')
        out.append(
            f'<figure class="fc-gal-s" id="z-{key}-{i}"><span class="anc" id="g-{key}-{i}"></span>'
            f'<a class="zin" href="#z-{key}-{i}" data-zoom title="클릭하면 크게 보기">{media}</a>'
            f'<a class="zout" href="#g-{key}-{i}" data-close>✕ 닫기</a>{nav}'
            f'<figcaption><span class="n">{i + 1} / {n}</span><b>{escape(cap)}</b><small>{escape(credit)}</small></figcaption></figure>')
    return f'<div class="fc-gal" data-gal="{key}"><div class="tr">{"".join(out)}</div></div>'


def pair_html(key: str, slides: list[tuple[str, str, str]]) -> str:
    """이미지 2장 나란히 (PC 좌우 · 모바일 위아래) · 번호 ①② · 클릭 확대 (갤러리와 같은 확대 마크업·JS 재사용)."""
    if not slides:
        return ""
    marks = "①②③④"
    out = []
    for i, (media, cap, credit) in enumerate(slides):
        out.append(
            f'<figure class="fc-gal-s" id="z-{key}-{i}"><span class="anc" id="g-{key}-{i}"></span>'
            f'<a class="zin" href="#z-{key}-{i}" data-zoom title="클릭하면 크게 보기">{media}</a>'
            f'<a class="zout" href="#g-{key}-{i}" data-close>✕ 닫기</a>'
            f'<figcaption><span class="n">{marks[i] if i < len(marks) else i + 1}</span><b>{escape(cap)}</b><small>{escape(credit)}</small></figcaption></figure>')
    return f'<div class="fc-gal df-pair" data-gal="{key}"><div class="tr">{"".join(out)}</div></div>'
