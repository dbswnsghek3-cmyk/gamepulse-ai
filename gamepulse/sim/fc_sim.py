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


def rebuild(players: list[tuple[float, float]], market_drop: float, hold: float, fee: float,
            swaps: list[bool] | None = None) -> dict:
    """players = [(고점, 현재)] · market_drop·fee 0~1 · hold = 보유 BP (같은 단위).
    swaps = 선수별 교체 선택 (None 이면 추천값 = 개별 요인 > 시장 요인).
    교체 시: 판매 수익 = 현재가 × (1 − 수수료) · 대체 선수 비용 = 고점 × (1 − 시장 하락률)
            (= 시장과 같이만 내린 같은 급 선수의 현재가로 가정) · 순비용 = 대체 비용 − 판매 수익"""
    rows, peak_t, now_t, mk_t, own_t = [], 0.0, 0.0, 0.0, 0.0
    for i, (peak, now) in enumerate(players):
        loss = max(0.0, peak - now)
        mk = min(loss, peak * market_drop)
        own = loss - mk
        rec = own > mk
        sw = rec if swaps is None else bool(swaps[i])
        sale = now * (1 - fee) if sw else 0.0
        repl = peak * (1 - market_drop) if sw else 0.0
        rows.append({"i": i, "peak": peak, "now": now, "loss": loss, "market": mk, "own": own, "rec": rec, "swap": sw,
                     "sale": sale, "repl": repl, "net": repl - sale, "after": repl if sw else now})
        peak_t, now_t, mk_t, own_t = peak_t + peak, now_t + now, mk_t + mk, own_t + own
    loss_t = mk_t + own_t
    for r in rows:
        r["share"] = r["loss"] / loss_t * 100 if loss_t > 0 else 0.0
    swap = [r for r in rows if r["swap"]]
    sale = sum(r["sale"] for r in swap)
    cost = sum(r["repl"] for r in swap)
    net = cost - sale
    left = hold - net
    after = sum(r["after"] for r in rows)
    drop = loss_t / peak_t if peak_t > 0 else 0.0
    return {"rows": rows, "peak": peak_t, "now": now_t, "loss": loss_t, "market": mk_t, "own": own_t, "drop_pct": drop * 100,
            "recover_pct": recover_pct(drop), "n_swap": len(swap), "n_keep": len(rows) - len(swap), "sale": sale,
            "cost": cost, "net": net, "left": left, "gap": max(0.0, -left), "after": after,
            "budget": hold + sale, "n_rec": sum(r["rec"] for r in rows)}


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


# ----------------------------------------------------------------------
# C 조작 개선 실험 판정 (통합 매칭 유지 · 모든 입력은 가정)
#   격차 = 패드 − 키보드 (%p) · 축소율 = (현행 격차 − 실험 격차) ÷ 현행 격차
#   확대: 축소율 ≥ 목표 · 패드 변화 ≥ −1%p · 매칭 포기율 변화 ≤ +0.5%p
#   중단: 격차가 줄지 않음 · 패드 −1%p 미만 · 매칭 포기율 +0.5%p 초과 → 그 외는 수정
def control_exp(kb: float, pad: float, kb_up: float, pad_chg: float, quit_chg: float, target: float = 30.0) -> dict:
    gap0 = pad - kb
    kb1, pad1 = min(100.0, kb + kb_up), max(0.0, min(100.0, pad + pad_chg))
    gap1 = pad1 - kb1
    cut = (gap0 - gap1) / gap0 * 100 if gap0 > 0 else 0.0
    guard = pad_chg >= -1 and quit_chg <= 0.5
    verdict = "확대" if cut >= target and guard else "중단" if cut <= 0 or not guard else "수정"
    return {"kb0": kb, "pad0": pad, "kb1": kb1, "pad1": pad1, "gap0": gap0, "gap1": gap1, "cut": cut, "guard": guard, "verdict": verdict}
