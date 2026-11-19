# 보관함 · 오버워치 v0.1 분석

오버워치 페이지의 핵심 프로젝트는 **PROJECT RE:START** 하나입니다.
초기 버전(v0.1)의 오버워치 분석은 RE:START와 주제·기준값이 달라 공개 페이지와 GitHub Pages 보고서에서 제외했지만, 삭제하지 않고 아래 위치에 그대로 보관합니다.

| 내용 | 보관 위치 |
|---|---|
| 문제 정의 · 불만 유형(가상) · 원인 가설 · 개선 전략 · KPI | `gamepulse/content/games.py` 의 `GAMES["overwatch"]` |
| 심층 분석 (보호 매칭 · 역할별 잔존율 · 그룹 플레이 · 온보딩 퍼널) | `gamepulse/views/deep_dives.py` 의 `overwatch()` |
| 화면 구성 함수 | `gamepulse/views/game_page.py` (`_problem`, `_complaints`, `_hypotheses`, `_strategies`, `_kpis`) |

## 로컬에서 보기

```powershell
$env:GAMEPULSE_SHOW_ARCHIVE = "1"
.venv\Scripts\python.exe -m streamlit run app.py
```

오버워치 페이지 맨 아래에 "보관함 · v0.1 분석 (비공개)" 펼치기가 나타납니다.
Streamlit Cloud와 정적 보고서(`scripts/export_static.py`)는 이 환경변수를 쓰지 않으므로 공개 화면에는 나오지 않습니다.

## 왜 제외했나

- v0.1은 시연용 **예시 데이터**이고, RE:START는 실제 자료 + 하나의 가정값 세트(`data/overwatch/restart.json` 의 `experiment`)로 일관되게 계산합니다.
- v0.1의 잔존율·퍼널·KPI 목표가 RE:START의 D7/D30 기준값과 달라, 한 페이지에 함께 두면 수치가 혼재합니다.
