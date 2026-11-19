"""생성형 AI 연결 시 사용할 프롬프트 템플릿 (현재는 호출하지 않음)."""

from __future__ import annotations

from gamepulse.content.games import GAMES

CHATBOT_SYSTEM_PROMPT = """너는 게임회사 사업PM을 돕는 분석 어시스턴트다.
규칙:
- 확인되지 않은 이용자 수, 매출, 이탈률, 실제 운영 정책을 사실처럼 말하지 않는다.
- 원인에 대한 설명은 '가설'로 표현하고, 검증에 필요한 데이터와 방법을 함께 제시한다.
- 제재 강화 같은 단일 해법보다 이용자 경험 회복, 잔존, KPI 측정 가능성을 함께 고려한다.
- 답변은 한국어로, 핵심 → 근거(가설) → 실행안 → KPI 순서로 간결하게 작성한다.
"""


def build_classification_prompt(text: str, game_id: str) -> str:
    g = GAMES[game_id]
    cats = "\n".join(f"- {c['category']}: {c['description']}" for c in g["complaints"])
    return f"""다음은 '{g['name']}' 이용자 댓글이다. 아래 불만 유형 중 하나로 분류하라.
해당 없으면 '기타·미분류'로 분류한다.

[불만 유형]
{cats}

[댓글]
{text}

JSON 으로만 답하라:
{{"category": "...", "sentiment": "부정|중립|긍정", "confidence": 0.0~1.0, "evidence": ["근거 표현"]}}
"""
