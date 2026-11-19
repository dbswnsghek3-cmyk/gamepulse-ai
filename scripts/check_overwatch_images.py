"""오버워치 이미지 슬롯 검증 상태를 출력한다.

사용: python scripts/check_overwatch_images.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamepulse.data.overwatch_images import all_status, load_manifest  # noqa: E402

m = load_manifest()
print(f"기준일 {m.get('reference_date')} · 최소 촬영일 {m.get('min_capture_date')} · 공식 영웅 수 {m.get('official_hero_count')}")
for sid, st in all_status(m).items():
    print(f"[{'적용' if st.ok else '대기'}] {sid} ({st.slot.get('title')}) -> {st.slot.get('file')}")
    for r in st.reasons:
        print(f"    - {r}")
