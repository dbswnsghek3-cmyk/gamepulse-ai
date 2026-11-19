"""AI 기능 공통 인터페이스.

다음 단계에서 생성형 AI API 를 연결할 때, 아래 추상 클래스를 상속한 구현체만 추가하면
화면(views) 코드를 수정하지 않고 분류기·챗봇을 교체할 수 있습니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    category: str                 # 불만 유형 (게임별 complaints.category 또는 '기타')
    sentiment: str                # 부정 / 중립 / 긍정
    confidence: float             # 0~1
    method: str                   # 'rule' / 'llm' 등
    matched_keywords: list[str] = field(default_factory=list)


class CommentClassifier(ABC):
    """댓글 1건을 불만 유형·감성으로 분류하는 인터페이스."""

    name: str = "base"

    @abstractmethod
    def classify(self, text: str, game_id: str) -> ClassificationResult:
        ...

    def classify_many(self, texts: list[str], game_id: str) -> list[ClassificationResult]:
        # LLM 구현체는 배치 호출로 덮어써서 비용·속도를 최적화할 수 있습니다.
        return [self.classify(t, game_id) for t in texts]


@dataclass
class ChatMessage:
    role: str      # 'user' / 'assistant'
    content: str


class PMChatbot(ABC):
    """사업PM 질문에 답하는 챗봇 인터페이스."""

    name: str = "base"

    @abstractmethod
    def reply(self, messages: list[ChatMessage], game_id: str | None = None) -> str:
        ...
