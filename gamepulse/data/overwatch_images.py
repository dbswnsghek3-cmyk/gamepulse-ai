"""오버워치 게임 이미지 슬롯 검증.

data/overwatch/image_manifest.json 의 규칙을 모두 통과한 이미지만 화면에 표시한다.
통과하지 못하면 이유 목록을 돌려주고, 화면에는 '최신 한국어 스크린샷 필요' 자리가 나온다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "overwatch" / "image_manifest.json"


@dataclass
class SlotStatus:
    slot: dict
    path: Path
    ok: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def caption(self) -> str:
        s = self.slot
        return f"출처: {s.get('source') or '-'} · 촬영일 {s.get('captured_at') or '-'} · {s.get('game_version') or '버전 미기재'} · 한국어 UI"


def load_manifest(path: Path = MANIFEST) -> dict:
    if not path.exists():
        return {"slots": [], "official_hero_count": 0, "min_capture_date": "", "folder": "assets/overwatch"}
    return json.loads(path.read_text(encoding="utf-8"))


def _aspect_ok(path: Path, aspect: str) -> tuple[bool, str]:
    if aspect != "16:9":
        return True, ""
    try:
        from PIL import Image

        with Image.open(path) as im:
            w, h = im.size
    except Exception as e:  # 손상 파일 등
        return False, f"이미지를 열 수 없음 ({e.__class__.__name__})"
    ratio = w / h if h else 0
    if abs(ratio - 16 / 9) / (16 / 9) > 0.03:
        return False, f"비율이 16:9가 아님 ({w}×{h})"
    return True, ""


def check_slot(slot: dict, manifest: dict) -> SlotStatus:
    path = ROOT / manifest.get("folder", "assets/overwatch") / slot.get("file", "")
    reasons = []
    if not path.exists():
        reasons.append(f"파일 없음: {manifest.get('folder')}/{slot.get('file')}")
    if slot.get("language") != "ko":
        reasons.append("한국어 UI 확인 필요 (language = ko)")
    cap, min_cap = slot.get("captured_at", ""), manifest.get("min_capture_date", "")
    if not cap or (min_cap and cap < min_cap):
        reasons.append(f"{min_cap} 이후 촬영 확인 필요")
    if slot.get("id") == "hero_select" and slot.get("heroes_checked", 0) != manifest.get("official_hero_count"):
        reasons.append(f"영웅 {manifest.get('official_hero_count')}명 전원 표시 확인 필요")
    if not slot.get("source"):
        reasons.append("출처·사용 권한 기록 필요")
    if not slot.get("verified"):
        reasons.append("검증 완료 표시 필요 (verified = true)")
    if path.exists():
        ok_ratio, msg = _aspect_ok(path, slot.get("aspect", ""))
        if not ok_ratio:
            reasons.append(msg)
    return SlotStatus(slot, path, not reasons, reasons)


def all_status(manifest: dict | None = None) -> dict[str, SlotStatus]:
    m = manifest or load_manifest()
    return {s["id"]: check_slot(s, m) for s in m.get("slots", [])}


def web_jpeg_b64(path: str, blur: tuple = (), crop: tuple | None = None, max_w: int = 1600, quality: int = 84) -> str:
    """화면 표시용 JPEG(base64). 원본 PNG는 건드리지 않는다.

    blur: 다른 플레이어 닉네임 등 가릴 영역 ((x0, y0, x1, y1), ...) · 원본 픽셀 기준
    crop: 확대해서 보여 줄 영역 (x0, y0, x1, y1) · 원본 픽셀 기준
    """
    import base64
    import io

    from PIL import Image, ImageFilter

    with Image.open(path) as src:
        im = src.convert("RGB")
    for box in blur:
        x0, y0, x1, y1 = (int(v) for v in box)
        region = im.crop((x0, y0, x1, y1))
        small = region.resize((max(1, (x1 - x0) // 10), max(1, (y1 - y0) // 10)), Image.BILINEAR)
        im.paste(small.resize(region.size, Image.NEAREST).filter(ImageFilter.GaussianBlur(3)), (x0, y0))
    if crop:
        im = im.crop(tuple(int(v) for v in crop))
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")
