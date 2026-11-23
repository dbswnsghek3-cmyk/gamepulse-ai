"""FC 온라인 포트폴리오 계산 모듈 (UI 와 분리 · 정적 페이지 JS 와 같은 식).

1) 구단 가치 변동 (A1)
   - 현재 가치 = 초기 가치 × (1 − 하락률)
   - 원래 가치로 돌아가는 데 필요한 상승률 = 하락률 ÷ (1 − 하락률)   예) 50% 하락 → 100% 상승 필요
   - 시장 대비 상대 가치 = (1 − 내 하락률) ÷ (1 − 시장 하락률) − 1   (시장 전체가 같이 내렸는지 구분)
2) 강화 리스크 (B1)
   - 실제 성공 확률 = 공식 표 확률(부스트 100% 기준) × 부스트 게이지 비율          (공식 공지 F1)
   - 성공 시 자산 = 성공 가치 − 비용 · 실패 시 자산 = 실패(복구) 가치 − 비용 (보호 사용 시 등급 유지 = 현재 가치)
   - 기대값 = p × 성공 시 자산 + (1 − p) × 실패 시 자산 · 시도 전 자산(현재 가치) 대비 변화로 표시
3) 입력 장치 매칭 풀 (C5) — 실제 매칭 알고리즘이 아닌 단순 모델
   - 같은 랭크 구간에서 동시에 매칭을 기다리는 인원 N × 구간 비율 r = 통합 매칭 풀
   - 완전 분리: 내 장치 비율만큼만 상대 풀 (키보드 N·r·k, 패드 N·r·(1−k))
   - 선택형: 동일 장치 우선을 고른 비율 s 만큼만 같은 장치 상대, 나머지는 통합
   - 상대 대기시간 배수 ≈ 통합 풀 ÷ 정책 풀 (도착률이 풀 크기에 비례한다는 가정 · 실제 시간 아님)
"""

from __future__ import annotations


# ----------------------------------------------------------------------
def value_change(v0: float, my_drop: float, market_drop: float) -> dict:
    """v0 원 단위, 하락률은 0~1."""
    v1 = v0 * (1 - my_drop)
    need = my_drop / (1 - my_drop) if my_drop < 1 else float("inf")
    rel = (1 - my_drop) / (1 - market_drop) - 1 if market_drop < 1 else float("nan")
    return {"now": v1, "loss": v0 - v1, "recover_pct": need * 100, "vs_market_pct": rel * 100,
            "market_only": v0 * (1 - market_drop)}


def recovery_curve(step: int = 5) -> list[tuple[int, float]]:
    """(하락률 %, 회복에 필요한 상승률 %) — 0~80%."""
    return [(d, d / (100 - d) * 100) for d in range(0, 85, step)]


# ----------------------------------------------------------------------
def enhance(value: float, cost: float, p_table: float, gauge: float, v_success: float, v_fail: float,
            protect: bool = False, protect_cost: float = 0.0) -> dict:
    """p_table·gauge 는 %. 모든 가치는 BP. 보호 사용 시 실패해도 현재 등급(= value) 유지, 보호 비용 추가."""
    p = max(0.0, min(1.0, p_table / 100 * gauge / 100))
    c = cost + (protect_cost if protect else 0.0)
    fail_v = value if protect else v_fail
    win = v_success - c - value          # 시도 전(현재 가치) 대비 변화
    lose = fail_v - c - value
    ev = p * win + (1 - p) * lose
    return {"p": p * 100, "cost": c, "win": win, "lose": lose, "ev": ev, "max_loss": -lose if lose < 0 else 0.0,
            "breakeven_p": (-lose) / (win - lose) * 100 if win > lose else float("nan")}


# ----------------------------------------------------------------------
POLICIES = {"1": "완전 분리 매칭", "2": "통합 유지 + 조작 밸런스 개선", "3": "선택형 동일 장치 우선 매칭"}


def matching(n_queue: int, rank_share: float, kb_share: float, prefer: float, allow: float = 2.0) -> dict:
    """rank_share·kb_share·prefer 는 0~1, allow 는 허용 대기 배수.
    반환: 정책별 키보드·패드 유저(3안은 '동일 장치 우선'을 고른 유저)의 상대 풀과 대기시간 배수(통합 = 1.0).
    3안은 허용 배수에 닿으면 통합으로 넓히므로 대기 배수의 상한 = allow, 넓힘이 생기면 fallback=True."""
    base = n_queue * rank_share
    out = {}
    for key in POLICIES:
        if key == "1":
            kb, pad = base * kb_share, base * (1 - kb_share)
        elif key == "2":
            kb = pad = base
        else:   # 선택형: '우선'을 고른 사람끼리 먼저 → 그 풀만 계산 (보수적) · 고르지 않은 유저는 통합 그대로
            kb = base * kb_share * prefer if prefer > 0 else base
            pad = base * (1 - kb_share) * prefer if prefer > 0 else base
        kx = base / kb if kb > 0 else float("inf")
        px = base / pad if pad > 0 else float("inf")
        fb = key == "3" and max(kx, px) > allow
        if key == "3":
            kx, px = min(kx, allow), min(px, allow)
        out[key] = {"kb_pool": kb, "pad_pool": pad, "kb_wait_x": kx, "pad_wait_x": px, "fallback": fb}
    return {"base": base, "policies": out}
