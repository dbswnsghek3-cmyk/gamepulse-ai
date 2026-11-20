"""브라우저 자동 번역 방지: Streamlit 이 처음 보내는 index.html 을 lang="ko" translate="no" 로 고친다.

배경
- Streamlit 기본 HTML 은 <html lang="en"> 이다. Chrome 이 한국어 화면을 '영어 페이지'로 보고 번역하면
  텍스트 노드가 <font> 로 바뀌어 React DOM 과 어긋나고 'removeChild' 오류나 수치 미갱신이 생길 수 있다.
- 실행 뒤 스크립트로 DOM 을 바꾸는 방법은 React 와 충돌할 수 있어 쓰지 않는다.

이전 방식의 문제
- scripts/patch_streamlit_html.py 를 손으로 실행해야 했다. Streamlit Community Cloud 는 배포할 때마다
  패키지를 새로 설치하므로 패치가 사라져 사이드바에 '패치 미적용' 경고가 떴다.

현재 방식
- 앱이 시작될 때 ensure() 가 한 번 자동으로 적용한다 (프로세스당 1회, 실패해도 앱은 계속 실행).
- Streamlit 은 index.html 을 요청마다 디스크에서 읽으므로, 적용 이후의 모든 페이지 로드에 반영된다.
- 예상한 태그가 없으면(버전 변경 등) 파일을 건드리지 않고 상태만 남긴다.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

MARK = "<!-- gamepulse: lang=ko notranslate -->"
OLD_HTML = '<html lang="en">'
NEW_HTML = '<html lang="ko" translate="no" class="notranslate">'
META = '<meta name="google" content="notranslate" />'


def index_path() -> Path:
    import streamlit

    return Path(streamlit.__file__).parent / "static" / "index.html"


def is_patched(text: str) -> bool:
    return MARK in text and NEW_HTML in text


def apply() -> tuple[bool, str]:
    """(적용 상태, 설명). 여러 번 실행해도 결과가 같다. 원본은 index.html.orig 로 백업."""
    p = index_path()
    text = p.read_text(encoding="utf-8")
    if is_patched(text):
        return True, f"이미 적용됨: {p}"
    if OLD_HTML not in text:
        return False, f'변경하지 않음: <html lang="en"> 태그를 찾지 못함 ({p}) · Streamlit 버전 확인 필요'
    backup = p.with_suffix(".html.orig")
    if not backup.exists():
        shutil.copy2(p, backup)
    new = text.replace(OLD_HTML, NEW_HTML, 1)
    new = new.replace('<meta charset="UTF-8" />', f'<meta charset="UTF-8" />\n    {META}\n    {MARK}', 1)
    tmp = p.with_suffix(".html.tmp")
    tmp.write_text(new, encoding="utf-8")
    tmp.replace(p)   # 원자적 교체: 읽는 도중 반쯤 쓰인 파일이 전송되지 않게
    return True, f"적용 완료: {p}"


def revert() -> str:
    p = index_path()
    backup = p.with_suffix(".html.orig")
    if not backup.exists():
        return "백업 파일이 없어 복구하지 않았습니다."
    shutil.copy2(backup, p)
    return f"원본 복구: {p}"


def check() -> tuple[bool, str]:
    p = index_path()
    ok = is_patched(p.read_text(encoding="utf-8"))
    return ok, ("적용됨" if ok else "미적용") + f": {p}"


def ensure() -> tuple[bool, str]:
    """앱 시작 시 호출. 어떤 예외도 밖으로 내보내지 않는다 (읽기 전용 설치 등)."""
    try:
        ok, msg = apply()
    except Exception as e:  # noqa: BLE001 — 번역 방지 실패가 앱 실행을 막으면 안 된다
        ok, msg = False, f"적용 실패: {type(e).__name__}: {e}"
    (log.info if ok else log.warning)("translate guard · %s", msg)
    return ok, msg
