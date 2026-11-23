"""FC 온라인 포트폴리오 계산 모듈 (UI 와 분리 · 정적 페이지 JS 와 같은 식).

1) A 구단 가치 분석·재건 (가상 선수 5명 · 모든 입력은 가정)
   - 선수별 하락 = 고점 − 현재
   - 시장 요인 = min(하락, 고점 × 시장 전체 하락률) · 개별 요인 = 하락 − 시장 요인
   - 개별 요인 > 시장 요인 → '교체 검토', 아니면 '유지' (시장 전체가 내린 선수는 능력치가 그대로라 유지)
   - 재편 예산 = 보유 BP + 교체 검토 선수 현재가 × (1 − 판매 수수료율)
   - 이벤트 목표 = max(0, 교체 검토 선수 고점 합 − 재편 예산)  ← BP 지급이 아니라 기존 이벤트·패스로 채울 목표
   - 원래 가치로 돌아가는 데 필요한 상승률 = 하락률 ÷ (1 − 하락률)
2) C 입력 장치 매칭 정책 (실제 매칭 알고리즘·이용자 수·대기시간이 아닌 비율 모델)
   - 상대 풀 = 통합 매칭(=100%) 대비 내가 만날 수 있는 상대 비율
   - 1안 완전 분리: 키보드 k, 패드 1−k
   - 2안 선택형: '동일 장치 우선'을 고른 비율 s 의 유저는 k·s, (1−k)·s 안에서 먼저 찾음 · 고르지 않은 유저는 100%
   - 3안 통합 유지: 100%
   - 풀 축소 위험: 가장 작은 풀 < 40% 높음 · < 70% 주의 · 그 외 낮음 (모델 안의 구분선일 뿐 실제 기준 아님)
"""

from __future__ import annotations


# ----------------------------------------------------------------------
def recover_pct(drop: float) -> float:
    """drop 0~1 → 원래 가치 회복에 필요한 상승률(%)."""
    return drop / (1 - drop) * 100 if drop < 1 else float("inf")


def rebuild(players: list[tuple[float, float]], market_drop: float, hold: float, fee: float) -> dict:
    """players = [(고점, 현재)] · market_drop·fee 0~1 · hold = 보유 BP (같은 단위)."""
    rows, peak_t, now_t, mk_t, own_t = [], 0.0, 0.0, 0.0, 0.0
    for i, (peak, now) in enumerate(players):
        loss = max(0.0, peak - now)
        mk = min(loss, peak * market_drop)
        own = loss - mk
        rows.append({"i": i, "peak": peak, "now": now, "loss": loss, "market": mk, "own": own, "swap": own > mk})
        peak_t, now_t, mk_t, own_t = peak_t + peak, now_t + now, mk_t + mk, own_t + own
    loss_t = mk_t + own_t
    for r in rows:
        r["share"] = r["loss"] / loss_t * 100 if loss_t > 0 else 0.0
    swap = [r for r in rows if r["swap"]]
    sale = sum(r["now"] for r in swap) * (1 - fee)
    budget = hold + sale
    target = sum(r["peak"] for r in swap)
    drop = loss_t / peak_t if peak_t > 0 else 0.0
    return {"rows": rows, "peak": peak_t, "now": now_t, "loss": loss_t, "market": mk_t, "own": own_t, "drop_pct": drop * 100,
            "recover_pct": recover_pct(drop), "n_swap": len(swap), "n_keep": len(rows) - len(swap), "sale": sale,
            "budget": budget, "target": target, "gap": max(0.0, target - budget),
            "cover_pct": budget / target * 100 if target > 0 else 100.0}


# ----------------------------------------------------------------------
POLICIES = {"1": "완전 분리 매칭", "2": "선택형 우선 매칭", "3": "통합 유지 + 입력 판정 개선"}


def pool_risk(min_pct: float) -> str:
    return "높음" if min_pct < 40 else "주의" if min_pct < 70 else "낮음"


def matching(kb_share: float, prefer: float) -> dict:
    """kb_share·prefer 0~1 → 정책별 상대 풀(통합 = 100%)과 풀 축소 위험."""
    out = {}
    for key in POLICIES:
        if key == "1":
            kb, pad = kb_share * 100, (1 - kb_share) * 100
        elif key == "2":
            kb, pad = (kb_share * prefer * 100, (1 - kb_share) * prefer * 100) if prefer > 0 else (100.0, 100.0)
        else:
            kb = pad = 100.0
        m = min(kb, pad)
        out[key] = {"kb": kb, "pad": pad, "min": m, "risk": pool_risk(m)}
    return out
