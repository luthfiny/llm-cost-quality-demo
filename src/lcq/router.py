"""Cost-aware routing.

Three routes, cheapest first:
  none   - retrieval found nothing relevant, reply with a canned escalation ($0).
  cheap  - one passage is enough; a small model can quote it.
  strong - the answer spans several passages or needs arithmetic / conditions.

The rules are deliberately plain so a client can read and tune them. In production
you would replace `_complex_signals` with a small classifier trained on traced
traffic, and keep the eval suite as the gate for every change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lcq.kb import Hit

REASONING_CUES = re.compile(
    r"\b(if|total|compare|difference|both|and also|after|before|"
    r"instead|cheaper|more expensive|combined|per year|annual|calculate|would)\b",
    re.I,
)


@dataclass(frozen=True)
class Route:
    tier: str  # "none" | "cheap" | "strong"
    reason: str


def _complex_signals(question: str, hits: list[Hit]) -> list[str]:
    signals = []
    if REASONING_CUES.search(question):
        signals.append("reasoning-cue")
    if len(question.split()) > 25:
        signals.append("long-question")
    if hits:
        strong_hits = [h for h in hits if h.score >= 0.6 * hits[0].score]
        if len({h.chunk.doc_id for h in strong_hits}) >= 2:
            signals.append("multi-doc-evidence")
    return signals


def route(question: str, hits: list[Hit], min_retrieval_score: float) -> Route:
    if not hits or hits[0].score < min_retrieval_score:
        top = hits[0].score if hits else 0.0
        return Route("none", f"top retrieval score {top:.2f} < {min_retrieval_score}")
    signals = _complex_signals(question, hits)
    if signals:
        return Route("strong", ",".join(signals))
    return Route("cheap", "single-passage lookup")
