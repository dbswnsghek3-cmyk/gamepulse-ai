# GamePulse AI

> 게임 이용자 문제를 데이터로 정의하고, 사업PM 관점의 개선 전략과 KPI를 설계하는 분석 대시보드
> (게임회사 신입 사업PM 포트폴리오 · v0.1 기본 웹사이트)

⚠️ **이 사이트의 모든 수치·그래프·시뮬레이션은 예시 데이터입니다.** 실제 이용자 수, 매출, 이탈률, 운영 정책을 나타내지 않으며,
이용자 불만과 원인의 관계는 실제 데이터로 검증하기 전까지 **가설**입니다. 본 프로젝트는 각 게임사와 관련 없는 개인 분석물입니다.

---

## 1. 분석 대상과 주제

| 게임 | 핵심 분석 주제 | North Star KPI (예시) |
|---|---|---|
| 오버워치 | 1→2 전환 이후 경험 변화, 신규 진입장벽, 장기 잔존 | 신규 이용자 D30 잔존율 |
| PUBG: 배틀그라운드 → **NEW START** (아래 별도 설명) | A 신규 정착 50% · B 휴면 유저 복귀 40% · C BM 신뢰·수익성 10% | A 신규 D7 잔존율 · B 복귀 로그인 전환율·D30 (가정 설계) |
| FC 온라인 | 이적시장 가격 변동, 구단 가치 하락·강화 실패 박탈감 | 손실 경험 이용자 14일 잔존율 |
| 던전앤파이터 | 시즌제 성장 가치 변화, 랜덤 보상과 성취감 | 시즌 전환 후 8주 기존 이용자 잔존율 |
| 리그 오브 레전드 | 솔로랭크 피로 → 칼바람 전환·이탈, 피해 이용자 회복 | 피해 이용자 14일 내 솔로랭크 재참여율 |

각 게임 페이지는 같은 6개 탭으로 구성됩니다.
**① 문제 정의 → ② 불만 유형 → ③ 원인 가설 → ④ 개선 전략 → ⑤ KPI → ⑥ 심층 분석(시뮬레이션)**

### PUBG: NEW START (실제 자료 기반 프로젝트)

> 첫 치킨을 맛보기도 전에 떠나는 유저들. 그리고 돌아오지 않는 전우들. — 신규 유저 정착과 휴면 유저 재활성화 전략

| 트랙 | 비중 | 핵심 질문 | 해결책 (기획 시안) |
|---|---|---|---|
| A 신규 유저 정착 | 50% | 첫 치킨을 맛보기도 전에, 왜 떠나는가? | A1 NEXT MATCH COACH · A2 FIRST 10 MATCHES · A3 MATCH QUALITY (운영 실험) |
| B 휴면 유저 복귀 | 40% | 한때 배그를 즐기던 유저는 왜 돌아오지 않을까? | B1 «PUBG: 다시 낙하할 시간» 복귀 광고 캠페인 (광고 3종 · 랜딩페이지 · 광고 A/B) · B2 복귀 첫 플레이·D7·D30 |
| C BM 신뢰·수익성 | 10% | 과금 불만을 줄이면서 매출을 지킬 수 있을까? | 유저 화면 변경 없는 내부 분석 (구조 정리 · 정책 시나리오 · 계산기) |

- 탭: 01 문제·결론 · 02 실제 유저 근거 · 03 원인 가설 · 04 해결책 데모 · 05 KPI·A/B 테스트 · 06 실행·사업 판단
- 근거: Steam 리뷰 신규·BM 45건(`data/pubg/opinions.csv`) · 복귀 21건(`data/pubg/opinions_return.csv`, 별도 표본) · 공식 패치노트·개발자 노트(`data/pubg/newstart.json`, 자료마다 '과거 자료/현재 운영 정책' 구분)
- 수치: 실험 기준값·효과·비용·매출 시나리오는 모두 **가정값**이며 실제 운영 데이터가 아닙니다. 데모는 실제 게임 서버와 연결되지 않은 시안입니다.
- 이미지: 게임 분석은 작성자 직접 캡처(다른 플레이어 닉네임 가림) · 광고 1·3은 AI 제작 가상 광고 시안 · 광고 2는 실제 로비 캡처 활용 시안 · 과거 PUBG 아트·WINNER 이미지는 사용자 제공 참고 이미지 · © KRAFTON
- 정적 버전: `scripts/export_static.py` → `docs/pubg.html` (04 탭 A1·A2·B2·C 데모는 JavaScript로 조작 가능) + `docs/pubg-return.html` (B1 복귀 랜딩페이지 데모, 광고별 `?src=` 유입 구분)

### FC 온라인 · 축구 게임인가, 주식 게임인가? (실제 자료 기반 프로젝트)

> 구단 가치는 떨어지고, 경기는 멈췄다.

| 트랙 | 기획 비중 | 핵심 질문 | 해결책 (기획 시안) |
|---|---|---|---|
| A 구단 가치 하락 | 40% | 열심히 키운 구단, 왜 내 노력의 가치는 떨어질까? | A1 하락 원인 분석 · A2 구단 재건 플랜 (시세 보장 대신 성장 경로) |
| B 강화·훈련코치 진입장벽 | 25% | 신규·복귀 유저는 왜 경쟁에 적응하기 전에 떠날까? | 초기 경쟁력 세팅 가이드 (보상 일괄 확대 없이 기존 지원을 순서대로 안내) |
| C 키보드 vs 패드 | 35% | 키보드 vs 패드, 같은 경기인데 공정한가? | 정책 3안 비교 → 3안 권고: 통합 매칭 유지 + 키보드 조작 환경 개선 (5단계 실행) |

- 근거: 공식 강화 확률 공지(26.4 기준) · BP 화폐 단위 조정(2026-08-20) · 작성자 캡처(이적시장 시세 그래프 · 계정 식별정보 블러) · 인벤 게시글 제목 · 유튜브 영상 2편 댓글 캡처 10장 → 유저 의견 요약 카드 8개(출처 링크 · 원문 인용·닉네임·댓글 수·비율 없음 · C 근거로만 사용) (`data/fconline/fc.json`)
- 기획 비중은 포트폴리오 비중이며 유저 불만 비율이 아니다 · 시세는 조정 이후 BP · 매칭 모델은 단순 모델(대기시간은 상대 배수)
- 계산: `gamepulse/sim/fc_sim.py` · 정적 버전 데모(A1 구단 가치 분석기 · C 매칭 정책 비교): `scripts/fc_static_demos.py` → `docs/fconline.html`

---

## 2. 설치 및 실행 방법 (Windows 기준, 처음 하는 분용)

### 2-1. Python 설치 (최초 1회)
1. https://www.python.org/downloads/ 에서 **Python 3.11 또는 3.12** 를 내려받습니다.
2. 설치 첫 화면에서 **`Add python.exe to PATH` 체크박스를 꼭 체크**하고 `Install Now` 를 누릅니다.
3. 설치가 끝나면 VS Code 를 **완전히 껐다가 다시 켭니다.** (PATH 반영)
4. VS Code 메뉴 `터미널 → 새 터미널` 을 열고 아래를 입력해 버전이 나오면 성공입니다.
   ```powershell
   python --version
   ```
   > `Python` 이라고만 나오거나 Microsoft Store 가 열리면: Windows 검색에서 **"앱 실행 별칭"** →
   > `python.exe`, `python3.exe` 의 **앱 설치 관리자** 항목을 **끔**으로 바꾼 뒤 터미널을 다시 여세요.

### 2-2. 가상환경 만들기 (최초 1회, 권장)
gamepulse-ai 폴더가 열린 터미널에서:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
> 빨간 오류("스크립트를 실행할 수 없으므로…")가 나면 아래 한 줄을 실행한 뒤 다시 시도하세요.
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
성공하면 줄 앞에 `(.venv)` 가 붙습니다.

### 2-3. 패키지 설치 (최초 1회)
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2-3-1. 자동 번역 방지 패치 (권장)
Streamlit 기본 HTML이 `lang="en"`이라 Chrome이 한국어 화면을 번역하면서 화면 오류(`removeChild` NotFoundError)나 수치 미갱신이 생길 수 있습니다.
패키지를 설치하거나 다시 설치한 뒤 한 번 실행하세요. (프로젝트 `.venv` 안의 파일 하나만 수정, `--revert`로 복구 가능)
```powershell
python scripts/patch_streamlit_html.py
```

### 2-4. 실행
```powershell
streamlit run app.py
```
브라우저에서 `http://localhost:8501` 이 자동으로 열립니다. 종료는 터미널에서 `Ctrl + C`.

> 다음부터는 `.\.venv\Scripts\Activate.ps1` → `streamlit run app.py` 두 줄만 실행하면 됩니다.

### 2-5. 휴대폰에서 보기 (같은 와이파이)
실행 시 터미널에 표시되는 `Network URL` (예: `http://192.168.0.5:8501`) 을 휴대폰 브라우저에 입력하면 됩니다.
모바일에서는 좌측 상단 `›` 버튼으로 메뉴를 열 수 있습니다.

---

## 3. 폴더 구조

```
gamepulse-ai/
├─ app.py                     # 진입점: 사이드바 메뉴 + 페이지 라우팅
├─ requirements.txt
├─ .streamlit/config.toml     # 화이트·네이비·블루 테마
├─ data/
│  └─ sample_comments_example.csv   # 데이터 랩 연습용 예시 CSV (가상 문장)
└─ gamepulse/
   ├─ config.py               # 색상·공지 문구
   ├─ content/games.py        # ★ 게임별 문제정의·불만유형·가설·전략·KPI (내용 수정은 여기서)
   ├─ data/
   │  ├─ schema.py            # 댓글 CSV 표준 스키마
   │  ├─ loader.py            # CSV 읽기(UTF-8/CP949) · 검증 · 정규화
   │  └─ sample.py            # 예시 데이터·시뮬레이션 생성기
   ├─ ai/
   │  ├─ base.py              # 분류기·챗봇 공통 인터페이스
   │  ├─ rule_based.py        # 현재 사용: 키워드 규칙 기반 분류기·챗봇 (API 없음)
   │  ├─ llm.py               # 다음 단계: 생성형 AI 연결 자리 (현재 호출 안 함)
   │  ├─ prompts.py           # LLM 프롬프트 템플릿
   │  └─ factory.py           # 어떤 구현체를 쓸지 선택
   ├─ analysis.py             # 분류 → 유형/감성/추이 집계 파이프라인
   ├─ ui/                     # CSS, HTML 카드 컴포넌트, Plotly 차트 스타일
   └─ views/                  # 홈, 게임 페이지, 심층 분석, 데이터 랩, 어시스턴트
```

---

## 4. 실제 댓글 CSV 분석하기

사이드바 **데이터 랩 (CSV 분석)** 에서 업로드합니다. 템플릿은 화면에서 내려받을 수 있습니다.

| 컬럼 | 필수 | 설명 |
|---|---|---|
| comment_id | ✅ | 댓글 고유 ID |
| game_id | ✅ | `overwatch` / `pubg` / `fconline` / `dnf` / `lol` (또는 `오버워치`, `배그`, `롤` 등 한글명) |
| source | ✅ | 수집 출처 |
| posted_at | ✅ | 작성일 `YYYY-MM-DD` |
| text | ✅ | 댓글 본문 |
| rating, user_segment, category, sentiment, url | 선택 | `category` 를 직접 라벨링해 두면 분류기 일치율을 계산합니다 |

- 엑셀에서 저장할 때는 **CSV UTF-8** 형식을 권장합니다. (CP949 도 자동 인식)
- 닉네임·계정 ID 등 **개인정보는 넣지 마세요.**
- 댓글을 수집할 때는 각 사이트의 이용약관과 robots 정책을 확인하세요.

---

## 5. 다음 단계: 생성형 AI 연결 계획

1. `requirements.txt` 에 사용할 AI SDK 추가
2. `gamepulse/ai/llm.py` 의 `_call_model()` / `LLMChatbot.reply()` 구현
3. API 키는 `.streamlit/secrets.toml` 또는 환경변수에 저장 (Git 업로드 금지, `.gitignore` 처리됨)
4. `gamepulse/ai/factory.py` 의 `LLM_READY = True`, 환경변수 `GAMEPULSE_AI_PROVIDER=llm`
5. 데이터 랩에서 규칙 기반 vs LLM 분류 결과를 사람 라벨과 비교해 성능 검증

화면(views) 코드는 공통 인터페이스(`CommentClassifier`, `PMChatbot`)만 사용하므로 수정할 필요가 없습니다.

---

## 6. 내용 수정 방법

- 문구·가설·전략·KPI 수정 → `gamepulse/content/games.py`
- 예시 그래프 수치 수정 → `gamepulse/data/sample.py`
- 색상·디자인 → `gamepulse/config.py`, `gamepulse/ui/styles.py`

파일 저장 후 브라우저 오른쪽 위 **Rerun** 을 누르면 반영됩니다.
