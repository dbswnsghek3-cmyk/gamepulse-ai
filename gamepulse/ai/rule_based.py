"""API 없이 동작하는 규칙 기반 분류기 · 챗봇 (현재 기본값).

- 분류기: content/games.py 의 불만 유형별 keywords 로 매칭합니다.
- 챗봇: 게임별 분석 콘텐츠에서 질문과 관련된 항목을 찾아 요약해 보여 줍니다.
정확도가 높지 않으므로 '예비 분류'로만 사용하고, 다음 단계에서 LLM 으로 교체합니다.
"""

from __future__ import annotations

from gamepulse.ai.base import ChatMessage, ClassificationResult, CommentClassifier, PMChatbot
from gamepulse.content.games import GAMES, resolve_game_id

NEGATIVE_WORDS = ["싫", "짜증", "스트레스", "접", "최악", "못", "안 ", "어렵", "부담", "억울", "날렸", "폭락", "떡락",
                  "실패", "욕", "트롤", "피로", "지겹", "불안", "무서", "ㅠ", "망", "탈주", "의미 없"]
POSITIVE_WORDS = ["재밌", "좋", "괜찮", "만족", "감사", "최고", "즐겁"]

OTHER_CATEGORY = "기타·미분류"


class RuleBasedClassifier(CommentClassifier):
    name = "rule"

    def classify(self, text: str, game_id: str) -> ClassificationResult:
        t = str(text)
        best_cat, best_hits = OTHER_CATEGORY, []
        for c in GAMES[game_id]["complaints"]:
            hits = [k for k in c["keywords"] if k in t]
            if len(hits) > len(best_hits):
                best_cat, best_hits = c["category"], hits

        neg = sum(w in t for w in NEGATIVE_WORDS)
        pos = sum(w in t for w in POSITIVE_WORDS)
        if neg > pos:
            sentiment = "부정"
        elif pos > neg:
            sentiment = "긍정"
        else:
            sentiment = "부정" if best_hits else "중립"

        confidence = 0.3 if not best_hits else min(0.5 + 0.15 * len(best_hits), 0.9)
        return ClassificationResult(best_cat, sentiment, round(confidence, 2), self.name, best_hits)


class RuleBasedChatbot(PMChatbot):
    """AI 미연결 상태에서 분석 콘텐츠를 검색해 답하는 안내형 챗봇."""

    name = "rule"

    INTENTS = {
        "kpi": ["kpi", "지표", "측정", "목표"],
        "strategy": ["전략", "개선", "해결", "방안", "아이디어"],
        "hypothesis": ["원인", "가설", "왜", "이유"],
        "complaint": ["불만", "문제", "댓글", "유형"],
        "problem": ["정의", "배경", "목적", "핵심"],
    }

    def reply(self, messages: list[ChatMessage], game_id: str | None = None) -> str:
        q = messages[-1].content.lower() if messages else ""
        gid = game_id or self._detect_game(q)
        if not gid:
            names = ", ".join(g["name"] for g in GAMES.values())
            return f"어떤 게임에 대한 질문인지 알려 주세요. (분석 대상: {names})"

        g = GAMES[gid]
        intent = next((k for k, words in self.INTENTS.items() if any(w in q for w in words)), "problem")
        header = f"**[{g['name']}] 규칙 기반 응답 · AI 미연결**\n\n"

        if intent == "kpi":
            lines = [f"- **{k['name']}** ({k['tier']}): {k['definition']}" for k in g["kpis"]]
            return header + "이 게임의 KPI 구성입니다. (수치는 예시)\n\n" + "\n".join(lines)
        if intent == "strategy":
            lines = [f"- **{s['title']}** ({s['phase']}, 대상 가설 {', '.join(s['targets'])}): {' / '.join(s['actions'])}" for s in g["strategies"]]
            return header + "사업PM 개선 전략 후보입니다.\n\n" + "\n".join(lines)
        if intent == "hypothesis":
            lines = [f"- **{h['id']}** {h['statement']}  \n  ↳ 검증: {h['validation']}" for h in g["hypotheses"]]
            return header + "원인 가설입니다. 모두 **검증 전 가설**입니다.\n\n" + "\n".join(lines)
        if intent == "complaint":
            lines = [f"- **{c['category']}**: {c['description']}" for c in g["complaints"]]
            return header + "주요 이용자 불만 유형입니다.\n\n" + "\n".join(lines)
        return header + f"**핵심 문제 정의**\n\n{g['problem']['statement']}\n\n**분석 주제**: {g['theme']}"

    @staticmethod
    def _detect_game(q: str) -> str | None:
        for gid, g in GAMES.items():
            for alias in g["aliases"] + [g["name"]]:
                if alias.lower() in q:
                    return gid
        return resolve_game_id(q)
