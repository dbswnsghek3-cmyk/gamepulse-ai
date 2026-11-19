"""분류기·챗봇 선택 지점.

환경변수 GAMEPULSE_AI_PROVIDER 로 구현체를 고릅니다. (기본: rule)
LLM 구현이 완료되기 전까지는 'llm' 을 지정해도 규칙 기반으로 안전하게 대체합니다.
"""

from __future__ import annotations

import os

from gamepulse.ai.base import CommentClassifier, PMChatbot
from gamepulse.ai.rule_based import RuleBasedChatbot, RuleBasedClassifier

LLM_READY = False  # 다음 단계에서 LLM 연결을 마치면 True 로 변경


def current_provider() -> str:
    p = os.getenv("GAMEPULSE_AI_PROVIDER", "rule").lower()
    return p if (p == "llm" and LLM_READY) else "rule"


def get_classifier() -> CommentClassifier:
    if current_provider() == "llm":
        from gamepulse.ai.llm import LLMCommentClassifier
        return LLMCommentClassifier()
    return RuleBasedClassifier()


def get_chatbot() -> PMChatbot:
    if current_provider() == "llm":
        from gamepulse.ai.llm import LLMChatbot
        return LLMChatbot()
    return RuleBasedChatbot()
