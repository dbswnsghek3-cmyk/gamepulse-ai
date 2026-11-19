"""예시 데이터 생성기.

⚠ 이 파일이 만드는 모든 데이터는 포트폴리오 시연용 '예시 데이터'입니다.
   실제 이용자 수·매출·이탈률·확률을 의미하지 않습니다.

- 댓글 예시 데이터는 schema.COMMENT_SCHEMA 와 같은 컬럼 구조로 생성되므로,
  나중에 실제 CSV 로 교체해도 같은 분석 코드가 그대로 동작합니다.
- 고정 시드를 사용해 새로고침해도 같은 결과가 나옵니다.
"""

from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

from gamepulse.content.games import GAMES

SAMPLE_SOURCES = ["커뮤니티(예시)", "앱 리뷰(예시)", "SNS(예시)", "설문 주관식(예시)"]
_PREFIX = ["", "", "솔직히 ", "요즘 ", "진짜 ", "업데이트 이후로 "]
_SUFFIX = ["", "", " 개선 부탁드려요.", " 그래서 접속을 덜 하게 됨.", " ㅠㅠ", " 다들 비슷한가요?"]
_NEUTRAL_POSITIVE = [
    ("그래도 친구랑 할 때는 재밌어요", "긍정"),
    ("이번 이벤트는 괜찮았던 것 같아요", "긍정"),
    ("오늘 패치 내용 정리해 주실 분 있나요", "중립"),
    ("주말에 같이 할 사람 구합니다", "중립"),
]


def _seed(*parts) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


def generate_sample_comments(game_id: str, n: int = 360, weeks: int = 12) -> pd.DataFrame:
    """게임별 가상 댓글 데이터 (스키마 호환)."""
    game = GAMES[game_id]
    rng = np.random.default_rng(_seed("comments", game_id))
    complaints = game["complaints"]

    # 주차별로 불만 비중이 조금씩 변하도록 추세를 준다 (예시)
    base_w = np.array([c["weight"] for c in complaints], dtype=float)
    trend = rng.normal(0, 0.035, size=len(complaints))
    end_date = pd.Timestamp("2026-11-15")

    rows = []
    for i in range(n):
        week = int(rng.integers(0, weeks))
        posted = end_date - pd.Timedelta(weeks=weeks - 1 - week) - pd.Timedelta(days=int(rng.integers(0, 7)))
        if rng.random() < 0.1:
            text, sent = _NEUTRAL_POSITIVE[int(rng.integers(0, len(_NEUTRAL_POSITIVE)))]
            rating = int(rng.integers(3, 6))
        else:
            w = np.clip(base_w + trend * (week - weeks / 2) / (weeks / 2), 0.02, None)
            w = w / w.sum()
            c = complaints[int(rng.choice(len(complaints), p=w))]
            s = c["samples"][int(rng.integers(0, len(c["samples"])))]
            text = _PREFIX[int(rng.integers(0, len(_PREFIX)))] + s + _SUFFIX[int(rng.integers(0, len(_SUFFIX)))]
            sent = "부정"
            rating = int(rng.choice([1, 2, 3], p=[0.5, 0.35, 0.15]))
        rows.append(
            {
                "comment_id": f"{game_id}_ex_{i:04d}",
                "game_id": game_id,
                "source": SAMPLE_SOURCES[int(rng.integers(0, len(SAMPLE_SOURCES)))],
                "posted_at": posted.normalize(),
                "text": text,
                "rating": rating,
                "user_segment": rng.choice(["신규", "기존", "복귀"], p=[0.35, 0.5, 0.15]),
                "category": pd.NA,
                "sentiment": pd.NA,
                "url": pd.NA,
            }
        )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 게임별 심층 분석용 예시 데이터
# ----------------------------------------------------------------------

def ow_funnel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "stage": ["첫 접속", "튜토리얼 완료", "첫 빠른 대전", "5판 완료", "10판 완료", "D7 재접속", "D30 재접속"],
            "users": [10000, 7800, 7000, 5200, 4100, 3300, 1800],
        }
    )


def ow_improved_funnel(base: pd.DataFrame, uplift_pp: float) -> pd.DataFrame:
    """각 단계 전환율을 uplift_pp(%p) 만큼 올렸을 때의 퍼널 (시뮬레이션)."""
    users = base["users"].to_numpy(dtype=float)
    out = [users[0]]
    for i in range(1, len(users)):
        rate = min(users[i] / users[i - 1] + uplift_pp / 100, 0.98)
        out.append(out[-1] * rate)
    return base.assign(users=np.round(out).astype(int))


def ow_role_retention() -> pd.DataFrame:
    days = np.arange(1, 31)
    params = {"탱커": (0.55, 0.11, 0.14), "딜러": (0.6, 0.09, 0.2), "지원": (0.58, 0.085, 0.22)}
    rows = []
    for role, (a, b, c) in params.items():
        for d in days:
            rows.append({"day": d, "role": role, "retention": round(100 * (a * np.exp(-b * d) + c), 1)})
    return pd.DataFrame(rows)


def pubg_skill_scores(n_new: int = 3000, n_vet: int = 7000) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(_seed("pubg_skill"))
    new = np.clip(rng.normal(1000, 180, n_new), 300, 2600)
    vet = np.clip(rng.normal(1650, 260, n_vet), 300, 2600)
    return new, vet


def pubg_mismatch(new: np.ndarray, vet: np.ndarray, window: int, expert_cut: int = 1500) -> dict:
    """신규 이용자가 ±window 범위로 매칭될 때 숙련자(expert_cut 이상)와 만날 비율, 후보 풀 크기 (시뮬레이션)."""
    pool = np.sort(np.concatenate([new, vet]))
    experts = np.sort(pool[pool >= expert_cut])
    lo, hi = new - window, new + window
    pool_n = np.searchsorted(pool, hi) - np.searchsorted(pool, lo)
    exp_n = np.searchsorted(experts, hi) - np.searchsorted(experts, lo)
    share = float(np.mean(exp_n / np.maximum(pool_n, 1)))
    pool_ratio = float(np.mean(pool_n) / len(pool))
    return {"expert_share": share * 100, "pool_ratio": pool_ratio * 100}


def pubg_party_retention(mentor_boost: float = 0.0) -> pd.DataFrame:
    base = {
        "솔로": (38, 12),
        "랜덤 스쿼드": (41, 13),
        "지인 스쿼드": (57, 26),
        "멘토 스쿼드(가정)": (52, 22),
    }
    rows = []
    for k, (w1, w4) in base.items():
        b = mentor_boost if "멘토" in k else 0
        rows.append({"party": k, "week": "1주차", "retention": w1 + b})
        rows.append({"party": k, "week": "4주차", "retention": w4 + b * 0.8})
    return pd.DataFrame(rows)


def fc_price_index(weeks: int = 26) -> pd.DataFrame:
    rng = np.random.default_rng(_seed("fc_price"))
    groups = {"상위 카드군": 1.0, "중위 카드군": 0.8, "하위 카드군": 0.6}
    shocks = {9: -0.16, 18: -0.12}  # 가정 이벤트 (예: 신규 카드 출시 가정)
    rows = []
    for g, vol in groups.items():
        v = 100.0
        for w in range(weeks):
            ret = rng.normal(0.004, 0.035 * vol)
            if w in shocks:
                ret += shocks[w] * (1.2 - vol * 0.3)
            if w - 1 in shocks:
                ret += abs(shocks[w - 1]) * 0.25
            v *= 1 + ret
            rows.append({"week": w + 1, "group": g, "index": round(v, 1)})
    df = pd.DataFrame(rows)
    df["change_pct"] = df.groupby("group")["index"].pct_change().mul(100).round(1)
    return df


def fc_churn_curve() -> np.ndarray:
    """최대 연속 실패 횟수(0~10+)별 이탈 의향 (예시 가정 곡선, %)."""
    k = np.arange(0, 11)
    return np.round(8 + 52 / (1 + np.exp(-(k - 4.5) * 1.1)), 1)


def fc_enhance_sim(p_success: float, attempts: int, protect_after: int | None, n_users: int = 6000) -> np.ndarray:
    """이용자별 '최대 연속 실패 횟수' 시뮬레이션. protect_after 회 연속 실패 시 다음 시도 성공 보정."""
    rng = np.random.default_rng(_seed("fc_enh", p_success, attempts))
    rolls = rng.random((n_users, attempts)) < p_success
    max_streak = np.zeros(n_users, dtype=int)
    cur = np.zeros(n_users, dtype=int)
    for t in range(attempts):
        success = rolls[:, t].copy()
        if protect_after:
            success |= cur >= protect_after
        cur = np.where(success, 0, cur + 1)
        max_streak = np.maximum(max_streak, cur)
    return max_streak


def dnf_season_value(carryover: float, seasons: int = 3, weeks_per: int = 20) -> pd.DataFrame:
    """시즌별 체감 성장 가치 지수 (예시 가정 모형)."""
    rows = []
    value = 20.0
    for s in range(seasons):
        start = value
        for w in range(weeks_per):
            progress = 1 - np.exp(-w / 6)
            v = start + (100 - start) * progress
            rows.append({"week": s * weeks_per + w + 1, "season": f"시즌 {s + 1}", "value": round(v, 1)})
        value = v * carryover
    return pd.DataFrame(rows)


def dnf_attempts_until_drop(p: float, pity: int | None, n: int = 20000) -> np.ndarray:
    """목표 아이템을 얻기까지 시도 횟수 (기하분포, 천장 적용 시 상한)."""
    rng = np.random.default_rng(_seed("dnf_drop", p))
    x = rng.geometric(p, size=n)
    if pity:
        x = np.minimum(x, pity)
    return x


def lol_mode_share() -> pd.DataFrame:
    levels = ["1 (낮음)", "2", "3", "4", "5 (높음)"]
    data = {
        "솔로랭크": [62, 54, 43, 31, 19],
        "칼바람 나락": [18, 23, 29, 34, 33],
        "기타 일반 모드": [14, 15, 17, 18, 18],
        "미접속(이탈 위험)": [6, 8, 11, 17, 30],
    }
    rows = []
    for mode, vals in data.items():
        for lv, v in zip(levels, vals):
            rows.append({"fatigue": lv, "mode": mode, "share": v})
    return pd.DataFrame(rows)


def lol_reentry_curve(effects: dict[str, float]) -> pd.DataFrame:
    """피해 경험 후 14일 누적 솔로랭크 재참여율: 대조군 vs 회복 프로그램 (시뮬레이션)."""
    days = np.arange(0, 15)
    base_max, k = 55.0, 0.28
    boost = sum(effects.values())
    rows = []
    for d in days:
        rows.append({"day": d, "group": "현재(대조군)", "rate": round(base_max * (1 - np.exp(-k * d)), 1)})
        rows.append({"day": d, "group": "회복 프로그램 적용", "rate": round(min(base_max + boost, 95) * (1 - np.exp(-(k + boost / 100) * d)), 1)})
    return pd.DataFrame(rows)
