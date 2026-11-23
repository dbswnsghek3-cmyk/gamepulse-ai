"""던전앤파이터 · 랜덤 보상 vs 누적 보장 병행 비교 (가정 기반 몬테카를로 · UI 와 분리).

모든 확률·배율·보상은 사용자가 넣는 가정값이며 실제 던파 확률이 아니다.

- 현행(A): 클리어 1회 보상 = 기본 1 × (확률 p 로 배율 M, 아니면 1)
- 누적 보장 병행(B): A 와 같은 확률 보상 + '천장' K — 배율이 K회 연속 안 나오면 다음 클리어는 배율 확정
  · 공급 중립(옵션): B 의 평균 총보상이 A 와 같도록 B 보상 전체를 같은 비율로 낮춘다 → 재화 공급량 변화 0
- 이용자 수 n 명을 같은 난수열(mulberry32, 시드 고정)로 시뮬레이션 → 정적 페이지 JS 와 같은 결과
- 출력: 평균 총보상 · 표준편차 · 하위 10%(P10) · 최저 · 목표(= A 의 평균) 도달 비율 · 공급량 변화
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
    return {"mean": mean, "sd": sd, "p10": s[int(n * 0.1)], "p50": s[n // 2], "p90": s[int(n * 0.9)], "min": s[0]}


def simulate(clears: int, p: float, mult: float, pity: int, neutral: bool, players: int = 2000, seed: int = 20261123) -> dict:
    """p 는 0~1, pity = 천장 K (0 이면 천장 없음)."""
    rnd = _mulberry32(seed)
    a_tot, b_tot = [], []
    for _ in range(players):
        a = b = 0.0
        miss = 0
        for _ in range(clears):
            u = rnd()
            hit = u < p
            a += mult if hit else 1.0
            if not hit and pity and miss >= pity:      # K회 연속 미당첨 → 이번 클리어 배율 확정
                hit = True
            b += mult if hit else 1.0
            miss = 0 if hit else miss + 1
        a_tot.append(a)
        b_tot.append(b)
    A = _stats(a_tot)
    scale = A["mean"] / (sum(b_tot) / players) if neutral else 1.0
    b_tot = [x * scale for x in b_tot]
    B = _stats(b_tot)
    goal = A["mean"]
    return {"A": A, "B": B, "goal": goal, "scale": scale,
            "reach_a": sum(x >= goal for x in a_tot) / players * 100, "reach_b": sum(x >= goal for x in b_tot) / players * 100,
            "supply_pct": (B["mean"] / A["mean"] - 1) * 100, "expected_per_clear": (1 - p) + p * mult}
