"""Plotly 차트 공통 스타일 · 공용 차트."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from gamepulse.config import COLORS as C
from gamepulse.config import SEQ

FONT = "Pretendard, 'Noto Sans KR', 'Malgun Gothic', sans-serif"
PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}


def style(fig: go.Figure, title: str | None = None, height: int = 380, legend_bottom: bool = True) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT, color=C["navy"], size=13),
        margin=dict(l=8, r=8, t=56 if title else 16, b=40),
        height=height,
        colorway=SEQ,
        paper_bgcolor="white",
        plot_bgcolor="white",
        hoverlabel=dict(font_family=FONT, bgcolor="white"),
        # 범례는 x축 제목 아래에 두어 겹치지 않게 함 (Plotly 가 하단 여백을 자동 확장)
        legend=dict(orientation="h", yanchor="top", y=-0.32, x=0, title_text="") if legend_bottom else dict(title_text=""),
    )
    if title:
        fig.update_layout(title=dict(text=title, x=0, xanchor="left", font=dict(size=15, color=C["navy"])))
    fig.update_xaxes(showgrid=False, linecolor=C["line"], title_font=dict(size=12, color=C["gray"]))
    fig.update_yaxes(gridcolor="#EEF2F8", zeroline=False, title_font=dict(size=12, color=C["gray"]))
    return fig


def complaint_bar(summary: pd.DataFrame, title: str) -> go.Figure:
    d = summary.sort_values("count")
    fig = go.Figure(
        go.Bar(
            x=d["count"], y=d["category"], orientation="h",
            marker_color=[C["gray"] if c.startswith("기타") else C["blue"] for c in d["category"]],
            text=[f"{s}%" for s in d["share"]], textposition="outside", cliponaxis=False,
            hovertemplate="%{y}<br>%{x}건<extra></extra>",
        )
    )
    fig.update_xaxes(title="댓글 수(건)")
    return style(fig, title, height=max(300, 60 * len(d) + 80))


def trend_line(trend: pd.DataFrame, title: str) -> go.Figure:
    fig = px.line(trend, x="week", y="count", color="category", markers=True,
                  labels={"week": "주차", "count": "댓글 수(건)", "category": "불만 유형"})
    fig.update_traces(line=dict(width=2.2))
    style(fig, title, height=420)
    fig.update_layout(legend=dict(y=-0.42))  # 날짜 눈금이 기울어져 범례를 더 아래에 둠
    return fig


def sentiment_donut(summary: pd.DataFrame, title: str) -> go.Figure:
    colors = {"부정": C["navy"], "중립": C["sky"], "긍정": C["blue"]}
    fig = go.Figure(
        go.Pie(labels=summary["sentiment"], values=summary["count"], hole=0.6,
               marker_colors=[colors.get(s, C["gray"]) for s in summary["sentiment"]],
               textinfo="label+percent", sort=False)
    )
    fig.update_layout(showlegend=False)
    return style(fig, title, height=320)


def priority_matrix(strategies: list[dict], title: str) -> go.Figure:
    df = pd.DataFrame(strategies)
    fig = go.Figure(
        go.Scatter(
            x=df["effort"], y=df["impact"], mode="markers+text",
            text=df["title"], textposition="top center",
            marker=dict(size=22, color=C["blue"], line=dict(color="white", width=2), opacity=0.9),
            hovertemplate="%{text}<br>예상 효과 %{y} / 실행 난이도 %{x}<extra></extra>",
        )
    )
    fig.add_shape(type="rect", x0=0.5, x1=3, y0=3, y1=5.6, fillcolor=C["ice"], opacity=0.5, line_width=0, layer="below")
    fig.add_annotation(x=0.6, y=5.5, text="Quick Win 영역", showarrow=False, xanchor="left", font=dict(color=C["blue"], size=11))
    fig.update_xaxes(range=[0.5, 5.5], title="실행 난이도 (1 쉬움 → 5 어려움, 가정 평가)", dtick=1)
    fig.update_yaxes(range=[0.5, 5.9], title="예상 효과 (가정 평가)", dtick=1)
    return style(fig, title, height=420)


def kpi_compare(kpis: list[dict], title: str) -> go.Figure:
    df = pd.DataFrame([k for k in kpis if k["unit"] == "%"])
    fig = go.Figure()
    fig.add_bar(y=df["name"], x=df["baseline"], name="현재(예시)", orientation="h", marker_color=C["sky"])
    fig.add_bar(y=df["name"], x=df["target"], name="목표(예시)", orientation="h", marker_color=C["blue"])
    fig.update_layout(barmode="group")
    fig.update_xaxes(title="%", range=[0, 100])
    fig.update_yaxes(autorange="reversed")
    return style(fig, title, height=max(320, 70 * len(df) + 100))
