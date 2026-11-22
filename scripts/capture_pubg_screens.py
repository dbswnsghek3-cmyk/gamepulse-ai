"""PUBG 페이지 01~06 탭의 Streamlit 원본 화면을 캡처해 assets/pubg/site/tab-0N.jpg 로 저장한다.

정적 보고서(docs/pubg.html)에 '디자인 확인용 원본 화면'으로 실린다 (export_static.py 가 복사).
Playwright + 설치된 Microsoft Edge 를 쓰고, 앱 실행(Running…)이 끝난 뒤 본문 전체 높이로 찍는다.

사용법 (프로젝트 폴더에서, 먼저 로컬 앱을 띄운 상태로):
    .venv\\Scripts\\python.exe -m streamlit run app.py --server.port 8501 --server.headless true
    .venv\\Scripts\\python.exe scripts\\capture_pubg_screens.py [--url http://localhost:8501]
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "pubg" / "site"
W = 1400

HEIGHT_JS = """() => {
  const b = document.querySelector('[data-testid="stMainBlockContainer"]') || document.querySelector('.block-container');
  return b ? Math.ceil(b.getBoundingClientRect().top + b.scrollHeight + 40) : document.body.scrollHeight;
}"""


def settle(page) -> None:
    """앱 실행 표시(stStatusWidget)가 사라지고 본문이 그려질 때까지 기다린다."""
    page.wait_for_selector(".ow-tabbar, .ow-cover", timeout=120_000)
    for _ in range(3):   # 실행 표시가 잠깐 사라졌다 다시 생기는 경우까지
        page.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=120_000)
        page.wait_for_timeout(1500)
    page.evaluate("document.fonts && document.fonts.ready")
    page.wait_for_timeout(1000)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge", headless=True)
        page = br.new_page(viewport={"width": W, "height": 1000}, device_scale_factor=1)
        for n in ("01", "02", "03", "04", "05", "06"):
            page.goto(f"{args.url}/?page=pubg&tab={n}", wait_until="domcontentloaded")
            settle(page)
            h = int(page.evaluate(HEIGHT_JS))
            page.set_viewport_size({"width": W, "height": max(800, min(h, 16000))})
            page.wait_for_timeout(1500)        # 높이를 바꾼 뒤 차트 다시 그리기
            settle(page)
            png = page.screenshot(full_page=False)
            im = Image.open(io.BytesIO(png)).convert("RGB")
            im.save(OUT / f"tab-{n}.jpg", "JPEG", quality=80, optimize=True, progressive=True)
            print(f"  탭 {n}: {im.width}×{im.height} → {OUT / f'tab-{n}.jpg'}")
            page.set_viewport_size({"width": W, "height": 1000})
        br.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
