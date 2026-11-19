"""게임별 심층 분석 · 시뮬레이션 (모두 예시 데이터)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from gamepulse.config import COLORS as C
from gamepulse.data import sample
from gamepulse.ui.charts import PLOTLY_CONFIG, style
from gamepulse.ui.components import notice, sample_badge, section


def _plot(fig):
    st.plotly_chart(fig, config=PLOTLY_CONFIG)


# ----------------------------------------------------------------------
def overwatch():
    section("신규 이용자 온보딩 퍼널", "첫 접속부터 D30 재접속까지 어디에서 가장 많이 멈추는가?", sample_badge())
    base = sample.ow_funnel()
    uplift = st.slider("온보딩 개선으로 각 단계 전환율이 오른다고 가정 (%p)", 0, 10, 3, key="ow_uplift")
    improved = sample.ow_improved_funnel(base, uplift)

    fig = go.Figure()
    fig.add_trace(go.Funnel(name="현재(예시)", y=base["stage"], x=base["users"], marker_color=C["sky"], textinfo="value+percent initial"))
    fig.add_trace(go.Funnel(name="개선 시뮬레이션", y=improved["stage"], x=improved["users"], marker_color=C["blue"], textinfo="value+percent initial"))
    _plot(style(fig, "온보딩 퍼널: 현재 vs 개선 시뮬레이션 (예시 데이터)", height=460))

    c1, c2, c3 = st.columns(3)
    d30_b, d30_i = base["users"].iloc[-1], improved["users"].iloc[-1]
    c1.metric("D30 재접속(현재·예시)", f"{d30_b / base['users'].iloc[0] * 100:.1f}%")
    c2.metric("D30 재접속(시뮬레이션)", f"{d30_i / base['users'].iloc[0] * 100:.1f}%", f"{(d30_i - d30_b) / base['users'].iloc[0] * 100:+.1f}%p")
    rates = base["users"].iloc[1:].to_numpy() / base["users"].iloc[:-1].to_numpy()
    worst = base["stage"].iloc[1:].iloc[int(np.argmin(rates))]
    c3.metric("가장 큰 이탈 구간(예시)", worst)

    section("역할별 잔존 곡선", "가설 H2: 고부담 역할을 처음 맡은 이용자의 잔존이 더 낮은가?", sample_badge())
    fig2 = px.line(sample.ow_role_retention(), x="day", y="retention", color="role",
                   labels={"day": "첫 접속 후 경과일", "retention": "잔존율(%)", "role": "첫 주 주력 역할"})
    _plot(style(fig2, "첫 주 주력 역할별 잔존율 (예시 데이터)"))
    notice("해석 예시: 곡선 간 격차가 실제 데이터에서도 확인된다면, 탱커 역할 대상 온보딩·보상이 우선순위가 됩니다. 확인되지 않으면 H2 는 기각합니다.")


# ----------------------------------------------------------------------
def pubg():
    section("신규 vs 숙련 이용자 실력 분포", "가설 H2: 매칭 허용 범위가 넓을수록 신규 이용자가 숙련자를 더 자주 만난다.", sample_badge())
    new, vet = sample.pubg_skill_scores()
    window = st.slider("매칭 허용 실력 범위 (± 점수, 예시 단위)", 100, 800, 400, step=50, key="pubg_window")
    m = sample.pubg_mismatch(new, vet, window)

    fig = go.Figure()
    fig.add_histogram(x=vet, name="숙련 이용자(예시)", marker_color=C["navy"], opacity=0.65, nbinsx=50)
    fig.add_histogram(x=new, name="신규 이용자(예시)", marker_color=C["blue"], opacity=0.75, nbinsx=50)
    fig.add_vline(x=1500, line_dash="dot", line_color=C["gray"], annotation_text="숙련 기준(가정)")
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="실력 점수(예시)")
    fig.update_yaxes(title="이용자 수")
    _plot(style(fig, "실력 점수 분포 (예시 데이터)"))

    c1, c2 = st.columns(2)
    c1.metric("신규 이용자의 상대 중 숙련자 비율(시뮬레이션)", f"{m['expert_share']:.1f}%")
    c2.metric("매칭 후보 풀 크기(전체 대비, 대기시간 대리지표)", f"{m['pool_ratio']:.1f}%")
    notice("트레이드오프: 범위를 좁히면 신규 이용자의 숙련자 조우는 줄지만, 후보 풀이 작아져 대기시간이 늘 수 있습니다. → **숙련자 대기시간을 가드레일 KPI**로 둡니다.")

    section("파티 유형별 잔존율", "가설 H3: 지인·멘토와 함께한 신규 이용자가 더 오래 남는가?", sample_badge())
    boost = st.slider("멘토 프로그램 품질 개선 효과 가정 (%p)", 0, 10, 0, key="pubg_mentor")
    df = sample.pubg_party_retention(boost)
    fig2 = px.bar(df, x="party", y="retention", color="week", barmode="group",
                  labels={"party": "파티 유형", "retention": "잔존율(%)", "week": ""},
                  color_discrete_sequence=[C["sky"], C["blue"]])
    style(fig2, "신규 이용자 파티 유형별 잔존율 (예시 데이터)")
    fig2.update_layout(legend=dict(y=-0.62), height=420)  # 좁은 화면에서 기울어진 x축 글자와 범례가 겹치지 않게
    _plot(fig2)


# ----------------------------------------------------------------------
def fconline():
    section("카드군별 이적시장 가격 지수", "급락 구간과 이후 접속 감소의 관계를 보기 위한 기준 데이터", sample_badge())
    df = sample.fc_price_index()
    threshold = st.slider("급락 알림 기준 (주간 하락률 %)", 3, 20, 8, key="fc_th")
    fig = px.line(df, x="week", y="index", color="group", labels={"week": "주차", "index": "가격 지수 (1주차=100 기준)", "group": ""})
    alerts = df[df["change_pct"] <= -threshold]
    fig.add_scatter(x=alerts["week"], y=alerts["index"], mode="markers", name="급락 알림 발생",
                    marker=dict(size=11, color=C["warn"], symbol="triangle-down"))
    for w in (10, 19):
        fig.add_vline(x=w, line_dash="dot", line_color=C["gray"])
    fig.add_annotation(x=10, y=1.02, yref="paper", text="가정 이벤트", showarrow=False, font=dict(size=11, color=C["gray"]))
    _plot(style(fig, "카드군별 가격 지수 추이 (예시 데이터)", height=420))
    st.caption(f"기준 {threshold}% 이상 하락 시 알림 → 26주 동안 {len(alerts)}회 발생 (예시). 알림이 너무 잦으면 불안을 키울 수 있으므로 기준값 자체도 실험 대상입니다.")

    section("강화 연속 실패 시뮬레이션", "가설 H2: 연속 실패가 임계점을 넘으면 이탈 의향이 급증한다. 보호 장치를 넣으면?", sample_badge())
    c1, c2, c3 = st.columns(3)
    p = c1.slider("강화 성공 확률 가정 (%)", 10, 80, 40, step=5, key="fc_p") / 100
    attempts = c2.slider("이용자당 시도 횟수", 5, 40, 20, key="fc_n")
    protect = c3.slider("보호 장치: N회 연속 실패 시 다음 시도 보정 (0=없음)", 0, 8, 4, key="fc_protect")

    curve = sample.fc_churn_curve()
    base = sample.fc_enhance_sim(p, attempts, None)
    prot = sample.fc_enhance_sim(p, attempts, protect or None)
    cap = len(curve) - 1

    def dist(x):
        v = np.minimum(x, cap)
        return pd.Series(v).value_counts(normalize=True).reindex(range(cap + 1), fill_value=0) * 100

    fig2 = go.Figure()
    fig2.add_bar(x=list(range(cap + 1)), y=dist(base), name="현재(보호 없음)", marker_color=C["sky"])
    fig2.add_bar(x=list(range(cap + 1)), y=dist(prot), name="보호 장치 적용", marker_color=C["blue"])
    fig2.add_scatter(x=list(range(cap + 1)), y=curve, name="이탈 의향 곡선(가정)", yaxis="y2",
                     mode="lines+markers", line=dict(color=C["navy"], width=2))
    fig2.update_layout(barmode="group", yaxis2=dict(overlaying="y", side="right", title="이탈 의향(%, 가정)", range=[0, 70], showgrid=False))
    fig2.update_xaxes(title="최대 연속 실패 횟수 (10 = 10회 이상)", dtick=1)
    fig2.update_yaxes(title="이용자 비율(%)")
    _plot(style(fig2, "최대 연속 실패 분포와 이탈 의향 (예시 시뮬레이션)", height=420))

    e_base = float(np.mean(curve[np.minimum(base, cap)]))
    e_prot = float(np.mean(curve[np.minimum(prot, cap)]))
    m1, m2 = st.columns(2)
    m1.metric("평균 이탈 의향(현재·시뮬레이션)", f"{e_base:.1f}%")
    m2.metric("평균 이탈 의향(보호 장치·시뮬레이션)", f"{e_prot:.1f}%", f"{e_prot - e_base:+.1f}%p", delta_color="inverse")


# ----------------------------------------------------------------------
def dnf():
    section("시즌 전환과 체감 성장 가치", "가설 H1: 이전 시즌 성장의 계승 비율이 낮을수록 '초기화' 체감이 커진다.", sample_badge())
    carry = st.slider("시즌 전환 시 성장 가치 계승 비율 (가정, %)", 0, 80, 25, step=5, key="dnf_carry") / 100
    a = sample.dnf_season_value(0.25).assign(scenario="기준 가정(25%)")
    b = sample.dnf_season_value(carry).assign(scenario=f"시뮬레이션({int(carry * 100)}%)")
    fig = px.line(pd.concat([a, b]), x="week", y="value", color="scenario",
                  labels={"week": "주차", "value": "체감 성장 가치 지수(예시)", "scenario": ""},
                  color_discrete_sequence=[C["sky"], C["blue"]])
    for w in (21, 41):
        fig.add_vline(x=w, line_dash="dot", line_color=C["gray"])
    fig.add_annotation(x=21, y=1.02, yref="paper", text="시즌 전환", showarrow=False, font=dict(size=11, color=C["gray"]))
    _plot(style(fig, "시즌별 체감 성장 가치 지수 (예시 모형)"))
    notice("계승 비율을 높이면 '초기화' 낙폭은 줄지만, 신규 시즌 목표의 새로움이 약해질 수 있습니다. → **신규 시즌 콘텐츠 참여율을 가드레일 KPI**로 둡니다.")

    section("랜덤 보상 편차와 천장(보정) 효과", "가설 H2: 획득까지의 시도 횟수 편차가 성취감 저하를 만든다.", sample_badge())
    c1, c2 = st.columns(2)
    p = c1.slider("1회당 목표 아이템 획득 확률 가정 (%)", 0.5, 10.0, 2.0, step=0.5, key="dnf_p") / 100
    pity = c2.slider("천장: N회 시도 시 확정 (0=없음)", 0, 300, 100, step=10, key="dnf_pity")

    base = sample.dnf_attempts_until_drop(p, None)
    capped = sample.dnf_attempts_until_drop(p, pity or None)
    upper = int(np.percentile(base, 99))
    fig2 = go.Figure()
    fig2.add_histogram(x=base[base <= upper], name="천장 없음", marker_color=C["sky"], opacity=0.75, nbinsx=60)
    fig2.add_histogram(x=capped[capped <= upper], name="천장 적용", marker_color=C["blue"], opacity=0.75, nbinsx=60)
    fig2.update_layout(barmode="overlay")
    fig2.update_xaxes(title="획득까지 시도 횟수")
    fig2.update_yaxes(title="이용자 수(시뮬레이션)")
    _plot(style(fig2, "획득까지 시도 횟수 분포 (예시 시뮬레이션)"))

    m1, m2, m3 = st.columns(3)
    m1.metric("평균 시도 횟수", f"{capped.mean():.0f}회", f"{capped.mean() - base.mean():+.0f}회", delta_color="inverse")
    m2.metric("가장 불운한 10% (P90)", f"{np.percentile(capped, 90):.0f}회", f"{np.percentile(capped, 90) - np.percentile(base, 90):+.0f}회", delta_color="inverse")
    m3.metric("편차 지수 P90÷P10", f"{np.percentile(capped, 90) / max(np.percentile(capped, 10), 1):.1f}배")


# ----------------------------------------------------------------------
def lol():
    section("경쟁 피로도 단계별 모드 이용 비중", "가설 H1: 피로도가 높을수록 솔로랭크 비중↓, 칼바람·미접속 비중↑", sample_badge())
    df = sample.lol_mode_share()
    fig = px.bar(df, x="fatigue", y="share", color="mode",
                 labels={"fatigue": "경쟁 피로도 단계(예시 지수)", "share": "다음 2주 이용 비중(%)", "mode": ""},
                 color_discrete_sequence=[C["navy"], C["blue"], C["sky"], "#C9D3E3"])
    fig.update_layout(barmode="stack")
    _plot(style(fig, "피로도 단계별 다음 2주 모드 이용 비중 (예시 데이터)", height=420))
    notice("관점: 칼바람 비중 증가를 '이탈'로만 보지 않고, **이탈(미접속)로 가기 전 머무는 회복 구간**으로 볼 수 있는지가 핵심 검증 포인트입니다 (가설 H2).")

    section("피해 이용자 회복 프로그램 시뮬레이션", "피해 경기 이후 14일간 솔로랭크 재참여율 (North Star)", sample_badge())
    c1, c2, c3 = st.columns(3)
    effects = {}
    if c1.checkbox("신고 결과 피드백", True, key="lol_fb"):
        effects["feedback"] = c1.slider("효과 가정(%p)", 0, 10, 4, key="lol_fb_v")
    if c2.checkbox("휴식 넛지 + 칼바람 회복 루트", True, key="lol_nudge"):
        effects["nudge"] = c2.slider("효과 가정(%p)", 0, 10, 3, key="lol_nudge_v")
    if c3.checkbox("솔로랭크 복귀 미션", False, key="lol_mission"):
        effects["mission"] = c3.slider("효과 가정(%p)", 0, 10, 3, key="lol_mission_v")

    curve = sample.lol_reentry_curve(effects)
    fig2 = px.line(curve, x="day", y="rate", color="group", markers=True,
                   labels={"day": "피해 경기 후 경과일", "rate": "누적 솔로랭크 재참여율(%)", "group": ""},
                   color_discrete_sequence=[C["sky"], C["blue"]])
    _plot(style(fig2, "누적 솔로랭크 재참여율: 대조군 vs 회복 프로그램 (예시 시뮬레이션)"))
    d14 = curve[curve["day"] == 14].set_index("group")["rate"]
    m1, m2 = st.columns(2)
    m1.metric("14일 재참여율(대조군·예시)", f"{d14['현재(대조군)']:.1f}%")
    m2.metric("14일 재참여율(프로그램·시뮬레이션)", f"{d14['회복 프로그램 적용']:.1f}%",
              f"{d14['회복 프로그램 적용'] - d14['현재(대조군)']:+.1f}%p")
    st.caption("실제 효과는 A/B 테스트로 측정해야 하며, 동시에 '전체 게임 이탈률'과 '칼바람 만족도'를 가드레일로 확인합니다.")


DEEP_DIVES = {"overwatch": overwatch, "pubg": pubg, "fconline": fconline, "dnf": dnf, "lol": lol}
