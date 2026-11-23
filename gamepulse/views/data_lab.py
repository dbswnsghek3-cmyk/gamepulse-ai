"""데이터 랩: 댓글 CSV 업로드 → 데이터 검증 → 분석 결과 → 시각화 → 다운로드.

- 실제로 업로드한 데이터만 분석한다 (업로드가 없으면 결과를 만들지 않는다). '예시 데이터'는 버튼으로만 불러오고 화면에 예시라고 표시한다.
- 분류는 키워드 규칙 기반 (content/games.py 의 불만 유형 키워드) → 'AI 분류'라고 표시하지 않는다.
- 분석 요약은 st.session_state["datalab_summary"] 에 저장 → PM 어시스턴트가 관련 결과를 함께 보여 준다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from gamepulse.ai.factory import current_provider, get_classifier
from gamepulse.analysis import category_summary, classify_comments, sentiment_summary, weekly_trend
from gamepulse.content.games import GAME_ORDER, GAMES
from gamepulse.data.loader import normalize_comments, read_csv_any_encoding, row_issues, validate_comments
from gamepulse.data.schema import schema_table, template_dataframe
from gamepulse.ui import charts
from gamepulse.ui.components import hero, notice, section

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample_comments_example.csv"


def _issue_summary(result: pd.DataFrame) -> pd.DataFrame:
    """게임별 주요 이슈: 상위 불만 유형 3개 · 부정 비율 · 대표 댓글 1개 (업로드 데이터만)."""
    rows = []
    for gid in [g for g in GAME_ORDER if g in set(result["game_id"])]:
        sub = result[result["game_id"] == gid]
        cats = sub[sub["pred_category"] != "기타·미분류"]["pred_category"].value_counts()
        top = " · ".join(f"{c} {n}건" for c, n in cats.head(3).items()) or "분류된 불만 없음"
        neg = (sub["pred_sentiment"] == "부정").mean() * 100 if len(sub) else 0
        ex = sub[sub["pred_category"] == cats.index[0]]["text"].iloc[0][:60] if len(cats) else "—"
        rows.append({"game_id": gid, "게임": GAMES[gid]["name"], "댓글 수": len(sub), "상위 불만 유형": top, "부정 비율 (%)": round(neg, 1), "대표 댓글 (앞 60자)": ex})
    return pd.DataFrame(rows)


def render() -> None:
    hero("Data Lab", "댓글 CSV 분석", "CSV 업로드 → 데이터 검증 → 분석 결과 → 시각화 → 다운로드")
    notice(f"분류 방식: **키워드 규칙 기반{'' if current_provider() == 'rule' else ' (생성형 AI 설정됨)'}** (AI 분류 아님) · "
           "업로드한 파일은 실행 중인 앱 안에서만 처리되며 외부로 전송되지 않습니다 · "
           "**닉네임·계정 ID 등 개인정보는 업로드 전에 지워 주세요.**")

    # ① 업로드 -----------------------------------------------------------
    section("① CSV 업로드")
    c1, c2 = st.columns([2, 1])
    with c1:
        file = st.file_uploader("댓글 CSV (UTF-8 또는 엑셀 CSV)", type=["csv"])
    with c2:
        use_sample = st.toggle("예시 데이터로 체험하기", key="dl_sample", help="data/sample_comments_example.csv · 실제 수집 데이터가 아닌 예시")
        st.download_button("CSV 템플릿 내려받기", template_dataframe().to_csv(index=False).encode("utf-8-sig"),
                           file_name="gamepulse_comments_template.csv", mime="text/csv")
    with st.expander("CSV 형식 (표준 스키마) · 지원 게임: overwatch · pubg · fconline · dnf"):
        st.dataframe(schema_table(), hide_index=True)

    if file is None and not use_sample:
        st.info("파일을 올리거나 '예시 데이터로 체험하기'를 켜면 아래에 결과가 나옵니다. 업로드가 없으면 결과를 만들지 않습니다.")
        st.session_state.pop("datalab_summary", None)
        return
    is_sample = file is None
    if is_sample:
        st.warning("**예시 데이터**로 분석 중입니다 · 실제 이용자 의견이 아닙니다.")
    try:
        raw = read_csv_any_encoding(file if file is not None else str(SAMPLE))
    except ValueError as e:
        st.error(str(e))
        return

    # ② 검증 -------------------------------------------------------------
    section("② 데이터 검증")
    report = validate_comments(raw)
    issues = row_issues(raw)
    for e in report.errors:
        st.error(e)
    if not report.ok:
        return
    df = normalize_comments(raw)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("전체 행", report.row_count)
    m2.metric("분석 행", len(df))
    m3.metric("제외 행", report.row_count - len(df))
    m4.metric("확인 필요", int((issues["처리"].str.startswith("확인") | issues["처리"].str.startswith("추이")).sum()) if len(issues) else 0)
    for w in report.warnings:
        st.warning(w)
    if len(issues):
        with st.expander(f"오류·확인 필요 행 {len(issues)}건 보기"):
            st.dataframe(issues, hide_index=True)
            st.download_button("오류 행 CSV 내려받기", issues.to_csv(index=False).encode("utf-8-sig"), file_name="gamepulse_row_issues.csv", mime="text/csv")
    else:
        st.success("누락값 · 중복 · 형식 오류 없음")
    if df.empty:
        st.error("분석 가능한 행이 없습니다.")
        return

    with st.spinner("댓글 분류 중..."):
        result = classify_comments(df, get_classifier())

    # ③ 분석 결과 --------------------------------------------------------
    section("③ 분석 결과 · 게임별 주요 이슈")
    summ = _issue_summary(result)
    st.dataframe(summ.drop(columns="game_id"), hide_index=True)
    st.session_state["datalab_summary"] = {"sample": is_sample, "rows": summ.to_dict("records"),
                                           "by_game": {r["game_id"]: r for r in summ.to_dict("records")}}
    st.caption("상위 불만 유형은 키워드 규칙 기반 예비 분류 · 불만과 원인의 관계는 가설이며 로그로 검증이 필요합니다.")

    # ④ 시각화 -----------------------------------------------------------
    section("④ 시각화")
    games_in = [g for g in GAME_ORDER if g in set(result["game_id"])]
    gid = st.selectbox("게임 선택", games_in, format_func=lambda x: GAMES[x]["name"])
    sub = result[result["game_id"] == gid]
    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(charts.complaint_bar(category_summary(sub), f"{GAMES[gid]['name']} 불만 유형 비중 ({'예시' if is_sample else '업로드'} 데이터)"), config=charts.PLOTLY_CONFIG)
    with c2:
        st.plotly_chart(charts.sentiment_donut(sentiment_summary(sub), "감성 분포 (긍정·중립·부정)"), config=charts.PLOTLY_CONFIG)
    trend = weekly_trend(sub)
    if not trend.empty:
        st.plotly_chart(charts.trend_line(trend, "날짜별(주) 불만 언급 추이"), config=charts.PLOTLY_CONFIG)
    else:
        st.caption("날짜가 있는 행이 부족해 추이를 그리지 않습니다.")
    if sub["category"].notna().any():
        labeled = sub[sub["category"].notna()]
        st.metric("사람 라벨 대비 분류 일치율", f"{(labeled['category'] == labeled['pred_category']).mean() * 100:.1f}%",
                  help="CSV 에 category 컬럼을 채워 두면 규칙 분류의 정확도를 비교할 수 있습니다.")
    with st.expander("분류 기준과 한계"):
        st.markdown("- 불만 유형: 게임별 키워드 목록과 일치하는 단어가 가장 많은 유형 · 일치가 없으면 '기타·미분류'\n"
                    "- 감성: 부정어·긍정어 개수 비교 · 반어·맥락은 반영하지 못함\n"
                    "- 신뢰도: 일치한 키워드 수에 따른 규칙 점수 (확률이 아님)\n"
                    "- 소수 표본·특정 커뮤니티 편향은 보정하지 않음")
    st.dataframe(sub[["comment_id", "posted_at", "source", "text", "pred_category", "pred_sentiment", "pred_confidence"]], hide_index=True)

    # ⑤ 다운로드 ---------------------------------------------------------
    section("⑤ 다운로드")
    d1, d2 = st.columns(2)
    d1.download_button("분류 결과 CSV (전체 행)", result.to_csv(index=False).encode("utf-8-sig"), file_name="gamepulse_classified.csv", mime="text/csv")
    d2.download_button("게임별 이슈 요약 CSV", summ.to_csv(index=False).encode("utf-8-sig"), file_name="gamepulse_issue_summary.csv", mime="text/csv")
