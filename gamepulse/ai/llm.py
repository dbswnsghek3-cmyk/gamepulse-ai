"""생성형 AI 연결용 자리(stub).

⚠ 현재 버전에서는 API 를 호출하지 않습니다. (유료 API 호출 금지 원칙)
다음 단계에서 이 파일의 TODO 부분만 구현하면 됩니다.

연결 절차(예정):
1. requirements.txt 에 사용할 SDK 추가 (예: anthropic)
2. API 키는 코드에 쓰지 말고 환경변수 또는 .streamlit/secrets.toml 에 저장
   (secrets.toml 은 Git 에 올리지 않도록 .gitignore 처리되어 있음)
3. 환경변수 GAMEPULSE_AI_PROVIDER=llm 으로 전환
"""

from __future__ import annotations

import json

from gamepulse.ai.base import ChatMessage, ClassificationResult, CommentClassifier, PMChatbot
from gamepulse.ai.prompts import CHATBOT_SYSTEM_PROMPT, build_classification_prompt


class LLMNotConnectedError(RuntimeError):
    pass


class LLMCommentClassifier(CommentClassifier):
    name = "llm"

    def __init__(self, model: str | None = None):
        self.model = model

    def classify(self, text: str, game_id: str) -> ClassificationResult:
        prompt = build_classification_prompt(text, game_id)
        raw = self._call_model(prompt)  # TODO: 다음 단계에서 구현
        data = json.loads(raw)
        return ClassificationResult(
            category=data.get("category", "기타·미분류"),
            sentiment=data.get("sentiment", "중립"),
            confidence=float(data.get("confidence", 0.0)),
            method=self.name,
            matched_keywords=data.get("evidence", []),
        )

    def _call_model(self, prompt: str) -> str:
        raise LLMNotConnectedError("생성형 AI API 는 아직 연결되지 않았습니다. (다음 단계 예정)")


class LLMChatbot(PMChatbot):
    name = "llm"

    def __init__(self, model: str | None = None):
        self.model = model
        self.system_prompt = CHATBOT_SYSTEM_PROMPT

    def reply(self, messages: list[ChatMessage], game_id: str | None = None) -> str:
        raise LLMNotConnectedError("생성형 AI API 는 아직 연결되지 않았습니다. (다음 단계 예정)")
