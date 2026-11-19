"""Streamlit 기본 HTML 의 언어 선언을 한국어·번역 금지로 바꾼다.

배경
- Streamlit 이 처음 보내는 index.html 은 <html lang="en"> 이다.
- Chrome 은 첫 로드 시 이 선언을 보고 한국어 화면을 '영어 페이지'로 판단해 번역할 수 있다.
- 번역기가 텍스트 노드를 <font> 로 바꾸면 React 가 관리하는 DOM 과 어긋나
  'removeChild' NotFoundError 나 수치 미갱신이 생길 수 있다.
- 앱 실행 뒤 스크립트로 lang 을 바꾸는 것만으로는 첫 판단을 되돌리지 못할 수 있어,
  처음 전송되는 HTML 자체를 고친다.

범위: 이 프로젝트의 가상환경(.venv) 안 streamlit/static/index.html 한 파일.
원본은 index.html.orig 로 백업하며, 여러 번 실행해도 결과가 같다.

사용
  python scripts/patch_streamlit_html.py           # 적용
  python scripts/patch_streamlit_html.py --check   # 상태 확인
  python scripts/patch_streamlit_html.py --revert  # 원본 복구
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

MARK = "<!-- gamepulse: lang=ko notranslate -->"
OLD_HTML = '<html lang="en">'
NEW_HTML = '<html lang="ko" translate="no" class="notranslate">'
META = '<meta name="google" content="notranslate" />'


def index_path() -> Path:
    import streamlit

    return Path(streamlit.__file__).parent / "static" / "index.html"


def is_patched(text: str) -> bool:
    return MARK in text and NEW_HTML in text


def apply() -> str:
    p = index_path()
    text = p.read_text(encoding="utf-8")
    if is_patched(text):
        return f"이미 적용됨: {p}"
    if OLD_HTML not in text:
        return f"변경하지 않음: 예상한 <html lang=\"en\"> 태그를 찾지 못했습니다 ({p}). Streamlit 버전을 확인하세요."
    backup = p.with_suffix(".html.orig")
    if not backup.exists():
        shutil.copy2(p, backup)
    text = text.replace(OLD_HTML, NEW_HTML, 1)
    text = text.replace('<meta charset="UTF-8" />', f'<meta charset="UTF-8" />\n    {META}\n    {MARK}', 1)
    p.write_text(text, encoding="utf-8")
    return f"적용 완료: {p}"


def revert() -> str:
    p = index_path()
    backup = p.with_suffix(".html.orig")
    if not backup.exists():
        return "백업 파일이 없어 복구하지 않았습니다."
    shutil.copy2(backup, p)
    return f"원본 복구: {p}"


def check() -> str:
    p = index_path()
    return ("적용됨" if is_patched(p.read_text(encoding="utf-8")) else "미적용") + f": {p}"


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    print(revert() if arg == "--revert" else check() if arg == "--check" else apply())
