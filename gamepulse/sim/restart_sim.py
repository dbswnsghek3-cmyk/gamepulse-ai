"""PROJECT RE:START KPI 시뮬레이터 (순수 계산 함수).

⚠ 모든 입력값과 결과는 가정에 따른 가상 시뮬레이션이며, 실제 오버워치 성과가 아닙니다.

계산 원칙
1) 효과는 '참여자'에게만 한 번 적용한다.
   개선 후 잔존율 = 기존 잔존율 + 참여율 × 참여자 개선 폭(%p)
   → 참여율과 효과를 곱하는 지점은 이 식 하나뿐이며, 다른 단계에서 다시 곱하지 않는다.
2) 잔존율은 0~100% 범위로 자르고, D1 ≥ D7 ≥ D30 관계를 강제한다. (보정이 일어나면 경고)
3) PC방 이벤트는 '참여 채널 퍼널'로만 계산하고, 잔존율에 별도로 더하지 않는다. (중복 가산 방지)
4) DAU 는 코호트 잔존 인원을 그대로 쓰지 않는다.
   DAU(t) = 기존 활성 이용자(가정, 고정) + Σ 유입일별 (일일 유입 인원 × 잔존 곡선 R(경과일) × 잔존자 일일 접속 확률)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import NormalDist

import numpy as np
import pandas as pd

DAYS = ("D1", "D7", "D30")


@dataclass
class CohortInput:
    name: str
    size: int
    base: dict[str, float]          # {"D1": %, "D7": %, "D30": %}
    participation: float            # 0~100 (%)


@dataclass
class SimInput:
    cohorts: list[CohortInput]
    uplift: dict[str, float]        # 참여자 개선 폭 %p {"D1","D7","D30"}
    # 적응 퍼널 (조건부 전환율 %, 이전 단계 대비)
    funnel_first: float = 85.0
    funnel_3: float = 70.0
    funnel_10: float = 55.0
    funnel_d7_of_10: float = 60.0
    funnel_uplift_3: float = 8.0
    funnel_uplift_10: float = 10.0
    # PC방 이벤트
    pc_reach: float = 25.0          # 코호트 중 PC방 이벤트 대상 비율 %
    pc_participation: float = 30.0  # 대상 중 참여율 %
    pc_completion: float = 60.0     # 참여자 중 미션 완료율 %
    pc_revisit: float = 50.0        # 참여자 중 7일 내 재방문율 %
    pc_companion: float = 40.0      # 참여자 중 친구 동반 플레이 비율 %
    # 선행 지표 (잔존율 계산에는 쓰지 않는 관측용 지표)
    briefing_completion: float = 70.0   # 복귀 참여자(브리핑 시작자) 중 완료율 %
    card_usage: float = 30.0            # 전체 코호트 중 학습 카드 이용률 %
    reward_cost: float = 3000.0     # 참여자 1인당 보상 비용(원)
    event_fixed_cost: float = 20_000_000.0
    # 개발·운영
    headcount: float = 5.0
    months: float = 3.0
    monthly_cost_per_person: float = 6_000_000.0
    # DAU
    base_dau: float = 100_000.0
    active_prob: float = 50.0       # 잔존자가 특정일에 접속할 확률 %
    arrival_days: int = 14
    horizon: int = 90
    funnel_cohort: str | None = None  # 지정하면 적응 퍼널을 이 코호트(예: '신규')만으로 계산 (KPI '첫 10경기 완료율'과 같은 대상)


@dataclass
class SimResult:
    retention: pd.DataFrame                 # cohort, day, base_rate, new_rate, base_users, new_users, added
    funnel: pd.DataFrame                    # stage, base, improved
    pcbang: pd.DataFrame                    # stage, users
    dau: pd.DataFrame                       # day, scenario, dau
    costs: dict[str, float]
    warnings: list[str] = field(default_factory=list)
    leading: dict[str, float] = field(default_factory=dict)   # 선행 지표 인원 (관측용, 잔존율에 미반영)


def validate_base(base: dict[str, float]) -> list[str]:
    errs = []
    for d in DAYS:
        if not 0 <= base[d] <= 100:
            errs.append(f"{d} 잔존율은 0~100% 사이여야 합니다.")
    if not base["D1"] >= base["D7"] >= base["D30"]:
        errs.append("기존 잔존율은 D1 ≥ D7 ≥ D30 이어야 합니다.")
    return errs


def apply_uplift(base: dict[str, float], participation: float, uplift: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    """개선 후 잔존율 = 기존 + 참여율 × 개선 폭. 범위·단조성 보정."""
    p = participation / 100
    raw = {d: base[d] + p * uplift[d] for d in DAYS}
    out = {d: min(max(raw[d], 0.0), 100.0) for d in DAYS}
    warns = []
    if out["D7"] > out["D1"]:
        out["D7"] = out["D1"]
        warns.append("개선 후 D7 이 D1 보다 커져 D7 = D1 로 보정했습니다. (D7 개선 폭을 줄이세요)")
    if out["D30"] > out["D7"]:
        out["D30"] = out["D7"]
        warns.append("개선 후 D30 이 D7 보다 커져 D30 = D7 로 보정했습니다. (D30 개선 폭을 줄이세요)")
    if any(raw[d] > 100 for d in DAYS):
        warns.append("개선 후 잔존율이 100%를 넘어 100%로 제한했습니다.")
    return out, warns


def retention_curve(rates: dict[str, float], horizon: int) -> np.ndarray:
    """R(t), t=0..horizon. (0,100%)→(1,D1)→(7,D7)→(30,D30) 로그-선형 보간, 30일 이후 7→30일 감소 속도로 외삽."""
    eps = 1e-4
    pts_t = np.array([0, 1, 7, 30], dtype=float)
    pts_r = np.array([1.0, rates["D1"] / 100, rates["D7"] / 100, rates["D30"] / 100])
    logs = np.log(np.maximum(pts_r, eps))
    t = np.arange(horizon + 1, dtype=float)
    r = np.exp(np.interp(t, pts_t, logs))
    slope = (logs[3] - logs[2]) / 23
    late = t > 30
    r[late] = np.exp(logs[3] + slope * (t[late] - 30))
    return np.clip(r, 0, 1)


def _dau_series(cohorts: list[CohortInput], rates_by_cohort: dict[str, dict[str, float]], inp: SimInput) -> np.ndarray:
    h, a = inp.horizon, inp.active_prob / 100
    total = np.full(h + 1, inp.base_dau, dtype=float)
    for c in cohorts:
        r = retention_curve(rates_by_cohort[c.name], h)
        daily = c.size / max(inp.arrival_days, 1)
        for s in range(min(inp.arrival_days, h + 1)):
            total[s:] += daily * r[: h + 1 - s] * a
    return total


def sample_size_two_proportions(p1: float, p2: float, alpha: float = 0.05, power: float = 0.8) -> int | None:
    """양측 검정, 두 비율 차이 검정의 그룹당 필요 표본 수. p 는 0~1."""
    if not (0 < p1 < 1 and 0 < p2 < 1) or p1 == p2:
        return None
    nd = NormalDist()
    za, zb = nd.inv_cdf(1 - alpha / 2), nd.inv_cdf(power)
    pbar = (p1 + p2) / 2
    num = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(num / (p2 - p1) ** 2)


def _week(day: float) -> int:
    """시작일을 Day 1 로 셀 때 해당 날짜가 속한 주차 (1주차 = Day 1~7)."""
    return max(1, math.ceil(day / 7))


def experiment_plan(cfg: dict) -> dict:
    """가정값(cfg = restart.json 'experiment')에서 MDE·표본·배정 기간·관측 완료 주차를 계산한다.

    - MDE(배정 기준 ITT) = 참여율 × 참여자 개선 폭  → KPI 목표, 표본 계산, 시뮬레이션이 모두 이 값을 쓴다.
    - 배정 주수 = ceil(두 그룹 표본 합 ÷ 주당 유입)   · 주당 유입 = 코호트 크기 ÷ (코호트 기간 / 7)
    - 실험 1(복귀 A) → 배정이 끝난 다음 주에 실험 2(신규 C) 시작 (대상이 겹치지 않음)
    - D7·D30 관측 완료 = 마지막 배정일 + 7 / + 30 일
    """
    alpha, power = cfg["alpha"], cfg["power"]
    up = cfg["uplift"]
    seg = {}
    for name, c in cfg["cohorts"].items():
        p = c["participation"] / 100
        mde = {d: p * up[d] for d in DAYS}
        base = c["base"]["D7"] / 100
        n = sample_size_two_proportions(base, base + mde["D7"] / 100, alpha, power)
        weekly = c["size"] / (cfg["cohort_days"] / 7)
        seg[name] = {"mde": mde, "n": n, "weekly": weekly, "assign_weeks": math.ceil(2 * n / weekly) if n else None,
                     "base": c["base"], "participation": c["participation"], "size": c["size"]}

    f = cfg["funnel"]
    p_avg = cfg["cohorts"]["신규"]["participation"] / 100   # KPI '첫 10경기 완료율'은 신규 계정 기준
    m10_base = f["first"] * f["m3"] * f["m10"] / 1e4
    m10_new = f["first"] * min(f["m3"] + p_avg * f["up3"], 100) * min(f["m10"] + p_avg * f["up10"], 100) / 1e4
    m10_mde = m10_new - m10_base

    r, n_ = seg["복귀"], seg["신규"]
    a1 = r["assign_weeks"]
    s2 = a1 + 1                                   # 실험 2 시작 주차
    a2 = n_["assign_weeks"]
    e1_last, e2_last = a1 * 7, (s2 - 1 + a2) * 7  # 마지막 배정일 (Day)
    sched = {
        "e1_assign": (1, a1), "e1_d7": _week(e1_last + 7), "e1_d30": _week(e1_last + 30),
        "e2_assign": (s2, s2 - 1 + a2), "e2_d7": _week(e2_last + 7), "e2_m10": _week(e2_last + 14), "e2_d30": _week(e2_last + 30),
    }
    sched["e3"] = (sched["e2_d7"], sched["e2_d7"] + 3)
    sched["decision"] = max(sched["e1_d30"], sched["e2_d30"], sched["e3"][1])

    # 분기(period_weeks) 환산: RICE 도달 · 비용 대비 효과가 같은 기간·같은 유입 가정을 쓰도록
    weeks = cfg.get("period_weeks", 13)
    q_in = {k: v["weekly"] * weeks for k, v in seg.items()}
    lead = cfg["leading"]
    reach = {   # 도달 = 분기 유입 × 기능을 실제로 쓰는 비율 (가정)
        "A": q_in["복귀"] * seg["복귀"]["participation"] / 100,
        "C": q_in["신규"] * seg["신규"]["participation"] / 100,
        "B": (q_in["복귀"] + q_in["신규"]) * lead["card_usage"] / 100,
        "D": (q_in["복귀"] + q_in["신규"]) * lead["pc_reach"] / 100 * lead["pc_participation"] / 100,
    }
    added_q = {"A": q_in["복귀"] * seg["복귀"]["mde"]["D7"] / 100, "C": q_in["신규"] * seg["신규"]["mde"]["D7"] / 100}
    return {"seg": seg, "m10": {"base": m10_base, "new": m10_new, "mde": m10_mde}, "sched": sched, "p_avg": p_avg * 100,
            "quarter": {"weeks": weeks, "inflow": q_in, "reach": reach, "added_d7": added_q}}


def rice_table(items: list[dict], reach: dict[str, float]) -> list[dict]:
    """RICE = 도달 × 영향 × 확신 ÷ 노력. 도달은 experiment_plan 의 분기 도달(가정)을 쓴다."""
    out = []
    for x in items:
        r = reach[x["key"]]
        out.append({**x, "reach": r, "score": r * x["impact"] * x["confidence"] / x["effort"]})
    return out


def run(inp: SimInput) -> SimResult:
    warnings: list[str] = []
    rows, rates_base, rates_new = [], {}, {}
    for c in inp.cohorts:
        errs = validate_base(c.base)
        if errs:
            raise ValueError(f"[{c.name}] " + " ".join(errs))
        new, w = apply_uplift(c.base, c.participation, inp.uplift)
        warnings += [f"[{c.name}] {x}" for x in w]
        rates_base[c.name], rates_new[c.name] = c.base, new
        for d in DAYS:
            bu, nu = c.size * c.base[d] / 100, c.size * new[d] / 100
            rows.append({"cohort": c.name, "day": d, "base_rate": c.base[d], "new_rate": new[d],
                         "base_users": bu, "new_users": nu, "added": nu - bu})
    retention = pd.DataFrame(rows)

    # 적응 퍼널: 참여율 가중 평균으로 조건부 전환율에 한 번만 효과 적용
    total = sum(c.size for c in inp.cohorts)
    fc = [c for c in inp.cohorts if inp.funnel_cohort is None or c.name == inp.funnel_cohort]
    f_total = sum(c.size for c in fc)
    p_avg = sum(c.size * c.participation for c in fc) / f_total / 100 if f_total else 0.0
    conv_b = [inp.funnel_first, inp.funnel_3, inp.funnel_10, inp.funnel_d7_of_10]
    conv_i = [inp.funnel_first, min(inp.funnel_3 + p_avg * inp.funnel_uplift_3, 100),
              min(inp.funnel_10 + p_avg * inp.funnel_uplift_10, 100), inp.funnel_d7_of_10]
    stages = ["접속", "첫 경기", "3경기 완료", "10경기 완료", "D7 재접속(10경기 완료자 중)"]

    def chain(conv):
        vals = [float(f_total)]
        for cv in conv:
            vals.append(vals[-1] * cv / 100)
        return vals

    funnel = pd.DataFrame({"stage": stages, "base": chain(conv_b), "improved": chain(conv_i)})

    # PC방 이벤트 퍼널 (잔존율에 가산하지 않음)
    target = total * inp.pc_reach / 100
    part = target * inp.pc_participation / 100
    pcbang = pd.DataFrame({
        "stage": ["PC방 이벤트 대상", "이벤트 참여", "적응 미션 완료", "7일 내 재방문"],
        "users": [target, part, part * inp.pc_completion / 100, part * inp.pc_revisit / 100],
    })

    ret_size = sum(c.size for c in inp.cohorts if c.name == "복귀")
    ret_part = sum(c.size * c.participation / 100 for c in inp.cohorts if c.name == "복귀")
    leading = {
        "briefing_started": ret_part,
        "briefing_completed": ret_part * inp.briefing_completion / 100,
        "card_users": total * inp.card_usage / 100,
        "pc_returning": ret_size * inp.pc_reach / 100 * inp.pc_participation / 100,
        "pc_companion": part * inp.pc_companion / 100,
        "pc_revisit": part * inp.pc_revisit / 100,
    }

    event_cost = part * inp.reward_cost + inp.event_fixed_cost
    dev_cost = inp.headcount * inp.months * inp.monthly_cost_per_person
    added_d7 = float(retention.loc[retention["day"] == "D7", "added"].sum())
    costs = {
        "event_cost": event_cost,
        "dev_cost": dev_cost,
        "total_cost": event_cost + dev_cost,
        "cost_per_participant": event_cost / part if part > 0 else float("nan"),
        "cost_per_revisit": event_cost / (part * inp.pc_revisit / 100) if part * inp.pc_revisit > 0 else float("nan"),
        "cost_per_added_d7": (event_cost + dev_cost) / added_d7 if added_d7 > 0 else float("nan"),
        # A~C 개발·운영비만으로 계산 (D PC방 이벤트는 효과를 잔존율에 더하지 않으므로 비용도 제외)
        "cost_per_added_d7_dev": dev_cost / added_d7 if added_d7 > 0 else float("nan"),
        "added_d7": added_d7,
        "p_avg": p_avg * 100,
    }

    days = np.arange(inp.horizon + 1)
    dau = pd.concat([
        pd.DataFrame({"day": days, "scenario": "현재 가정", "dau": _dau_series(inp.cohorts, rates_base, inp)}),
        pd.DataFrame({"day": days, "scenario": "RE:START 적용 가정", "dau": _dau_series(inp.cohorts, rates_new, inp)}),
    ])
    return SimResult(retention, funnel, pcbang, dau, costs, warnings, leading)
