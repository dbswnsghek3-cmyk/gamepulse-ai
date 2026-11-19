"""데이터 랩: 실제 댓글 CSV 업로드 → 검증 → 분류 → 시각화."""

from __future__ import annotations

import streamlit as st

from gamepulse.ai.factory import current_provider, get_classifier
from gamepulse.analysis import category_summary, classify_comments, sentiment_summary, weekly_trend
from gamepulse.content.games import GAMES
from gamepulse.data.loader import normalize_comments, read_csv_any_encoding, validate_comments
from gamepulse.data.schema import schema_table, template_dataframe
from gamepulse.ui import charts
from gamepulse.ui.components import hero, notice, section


def render() -> None:
    hero("Data Lab", "댓글 CSV 분석", "직접 수집한 댓글 CSV 를 올리면 표준 스키마로 검증하고, 불만 유형·감성을 분류해 시각화합니다.")
    notice(
        f"현재 분류 방식: **{'규칙 기반(키워드)' if current_provider() == 'rule' else '생성형 AI'}** · "
        "업로드한 파일은 이 컴퓨터에서 실행 중인 앱 안에서만 처리되며 외부로 전송되지 않습니다. "
        "개인정보(닉네임, 계정 ID 등)는 CSV 에 넣지 않는 것을 권장합니다."
    )

    section("1. CSV 형식 (표준 스키마)")
    st.dataframe(schema_table(), hide_index=True)
    st.download_button(
        "CSV 템플릿 내려받기",
        template_dataframe().to_csv(index=False).encode("utf-8-sig"),
        file_name="gamepulse_comments_template.csv",
        mime="text/csv",
    )

    section("2. 파일 업로드")
    file = st.file_uploader("댓글 CSV 파일 (UTF-8 또는 엑셀 CSV)", type=["csv"])
    if file is None:
        st.info("파일을 올리면 분석 결과가 이 아래에 표시됩니다. 연습용으로 `data/sample_comments_example.csv` 를 올려 보세요.")
        return

    try:
        raw = read_csv_any_encoding(file)
    except ValueError as e:
        st.error(str(e))
        return

    report = validate_comments(raw)
    for w in report.warnings:
        st.warning(w)
    if not report.ok:
        for e in report.errors:
            st.error(e)
        return

    df = normalize_comments(raw)
    if df.empty:
        st.error("분석 가능한 행이 없습니다.")
        return
    st.success(f"검증 통과: 전체 {report.row_count}행 중 {len(df)}행을 분석합니다.")

    with st.spinner("댓글 분류 중..."):
        result = classify_comments(df, get_classifier())

    section("3. 분석 결과")
    games_in = [gid for gid in GAMES if gid in set(result["game_id"])]
    gid = st.selectbox("게임 선택", games_in, format_func=lambda x: GAMES[x]["name"])
    sub = result[result["game_id"] == gid]

    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(charts.complaint_bar(category_summary(sub), f"{GAMES[gid]['name']} 불만 유형 분포 (업로드 데이터)"), config=charts.PLOTLY_CONFIG)
    with c2:
        st.plotly_chart(charts.sentiment_donut(sentiment_summary(sub), "감성 분포 (업로드 데이터)"), config=charts.PLOTLY_CONFIG)

    trend = weekly_trend(sub)
    if not trend.empty:
        st.plotly_chart(charts.trend_line(trend, "주차별 불만 언급 추이 (업로드 데이터)"), config=charts.PLOTLY_CONFIG)

    if sub["category"].notna().any():
        labeled = sub[sub["category"].notna()]
        acc = (labeled["category"] == labeled["pred_category"]).mean() * 100
        st.metric("사람 라벨 대비 분류 일치율", f"{acc:.1f}%", help="CSV 에 category 컬럼을 채워 두면 분류기 성능을 비교할 수 있습니다.")

    st.caption("규칙 기반 분류는 예비 결과입니다. 불만과 원인의 관계는 여전히 가설이며, 로그 데이터로 검증이 필요합니다.")
    st.dataframe(sub[["comment_id", "posted_at", "source", "text", "pred_category", "pred_sentiment", "pred_confidence"]], hide_index=True)
    st.download_button(
        "분류 결과 CSV 내려받기",
        result.to_csv(index=False).encode("utf-8-sig"),
        file_name="gamepulse_classified.csv",
        mime="text/csv",
    )
