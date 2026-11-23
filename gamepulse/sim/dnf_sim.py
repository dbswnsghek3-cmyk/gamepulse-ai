"""던전앤파이터 · 현행 확률 보상 vs B 진척 게이지(제안) vs 천장(비교) — 가정 기반 몬테카를로 (UI 와 분리).

모든 확률·배율·보상은 사용자가 넣는 가정값이며 실제 던파 확률이 아니다.

- 현행(A): 클리어 1회 보상 = 기본 1 × (확률 p 로 고배율 M, 아니면 1) · 1회 기대 보상 E = (1-p) + p·M
- B 진척 게이지(04 탭 대표안): 기대 미만 클리어마다 게이지 +1 (연속일 필요 없음) → K칸이 차면 그 클리어 보상을
  '기대 배율 하한 E'까지 올려 준다 · 확률·고배율은 그대로 → 운의 재미 유지, 운이 나쁜 날도 쌓임
- 천장(비교·반례): K회 '연속' 기대 미만이면 다음 클리어를 고배율 M으로 확정 (기존 장치와 겹치고 공급 충격이 큼)
- 공급 중립(옵션): 늘어난 보상만큼 '고배율 보상 크기'를 줄여 평균 총보상을 현행과 같게 맞춘다
  (모든 이용자 보상을 일괄 축소하면 혜택을 못 받은 하위 이용자가 손해 → 그 방식은 쓰지 않는다)
- 같은 난수열(mulberry32, 시드 고정) · 정적 페이지 JS(scripts/dnf_static_demos.py)와 같은 식
"""

from __future__ import annotations

import math


def _mulberry32(seed: int):
    a = seed & 0xFFFFFFFF

    def rnd() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rnd


def _stats(xs: list[float]) -> dict:
    s = sorted(xs)
    n = len(s)
    mean = sum(s) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in s) / n)
    return {"mean": mean, "sd": sd, "p10": s[int(n * 0.1)], "p50": s[n // 2], "min": s[0]}


def simulate(clears: int, p: float, mult: float, gauge: int, neutral: bool, players: int = 2000, seed: int = 20261123) -> dict:
    """p 는 0~1 · gauge = K (0 이면 장치 없음) · neutral = 고배율 크기 조정으로 공급 중립."""
    rnd = _mulberry32(seed)
    E = (1 - p) + p * mult
    a_tot, bh, bg, ch = [], [], [], []      # 현행 총보상 · B 고배율 횟수 · B 게이지 보장 횟수 · 천장 고배율 횟수
    for _ in range(players):
        a = 0.0
        hb = gb = hc = 0
        g = miss = 0
        for _ in range(clears):
            hit = rnd() < p
            a += mult if hit else 1.0
            # B 진척 게이지 (누적)
            if hit:
                hb += 1
            else:
                g += 1
                if gauge and g >= gauge:
                    gb += 1
                    g = 0
            # 천장 (연속)
            forced = (not hit) and gauge and miss >= gauge
            if hit or forced:
                hc += 1
                miss = 0
            else:
                miss += 1
        a_tot.append(a)
        bh.append(hb)
        bg.append(gb)
        ch.append(hc)
    A = _stats(a_tot)
    tot_a = sum(a_tot)
    base = clears * players
    sb = sc = 1.0                             # 고배율 보너스(M-1) 조정 비율
    if neutral:
        hb_sum, gb_sum, hc_sum = sum(bh), sum(bg), sum(ch)
        sb = max(0.0, (tot_a - base - gb_sum * (E - 1)) / (hb_sum * (mult - 1))) if hb_sum else 1.0
        sc = max(0.0, (tot_a - base) / (hc_sum * (mult - 1))) if hc_sum else 1.0
    b_tot = [clears + h * (mult - 1) * sb + k * (E - 1) for h, k in zip(bh, bg)]
    c_tot = [clears + h * (mult - 1) * sc for h in ch]
    B, C = _stats(b_tot), _stats(c_tot)
    goal = A["mean"]
    reach = lambda xs: sum(x >= goal - 1e-9 for x in xs) / players * 100  # noqa: E731
    return {"A": A, "B": B, "C": C, "goal": goal, "E": E,
            "reach_a": reach(a_tot), "reach_b": reach(b_tot), "reach_c": reach(c_tot),
            "supply_b": (B["mean"] / A["mean"] - 1) * 100, "supply_c": (C["mean"] / A["mean"] - 1) * 100,
            "jack_b": 1 + (mult - 1) * sb, "jack_c": 1 + (mult - 1) * sc, "mult": mult,
            "fills_b": sum(bg) / players}
