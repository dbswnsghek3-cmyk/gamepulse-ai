"""Streamlit 기본 HTML 의 언어 선언을 한국어·번역 금지로 바꾼다 (수동 실행·점검용 도구).

앱(app.py)이 시작될 때 gamepulse/ui/translate_guard.ensure() 로 자동 적용되므로 보통은 실행할 필요가 없다.
배경과 동작은 gamepulse/ui/translate_guard.py 참고.

사용
  python scripts/patch_streamlit_html.py           # 적용
  python scripts/patch_streamlit_html.py --check   # 상태 확인
  python scripts/patch_streamlit_html.py --revert  # 원본 복구
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamepulse.ui.translate_guard import apply, check, revert  # noqa: E402

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    print(revert() if arg == "--revert" else check()[1] if arg == "--check" else apply()[1])
