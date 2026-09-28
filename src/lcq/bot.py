from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lcq.config import Settings
from lcq.kb import BM25Index, Hit, load_kb
from lcq.providers import ESCALATION
from lcq.router import Route, route
from lcq.tracing import Tracer

SYSTEM_PROMPT = f"""You are the customer support assistant for Kopi Kilat, a coffee subscription \
service in Indonesia.
Answer ONLY from the CONTEXT passages. Be concise (1-3 sentences).
After each fact, cite the passage id in square brackets, e.g. [plans#plan-prices].
If the context does not contain the answer, reply exactly: "{ESCALATION}"
Never invent prices, dates, or policies."""

_CITATION = re.compile(r"\[([a-z0-9_]+#[a-z0-9-]+)\]")


@dataclass
class Answer:
    question: str
    text: str
    route: Route
    model: str | None
    citations: list[str]
    retrieved: list[str]
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    simulated: bool = False
    extra: dict = field(default_factory=dict)


def build_prompt(question: str, hits: list[Hit]) -> list[dict]:
    context = "\n\n".join(f"[{h.chunk.id}]\n{h.chunk.text}" for h in hits)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
    ]


class SupportBot:
    def __init__(self, settings: Settings, kb_dir: Path, tracer: Tracer | None = None):
        self.settings = settings
        self.index = BM25Index(load_kb(kb_dir))
        self.tracer = tracer or Tracer()

    def answer(self, question: str, force_tier: str | None = None) -> Answer:
        """Answer a question. `force_tier` ("cheap"/"strong") bypasses the router for baselines."""
        s = self.settings
        with self.tracer.trace("support-answer", input=question) as out:
            hits = self.index.search(question, k=s.top_k)
            decided = route(question, hits, s.min_retrieval_score)
            if force_tier:
                # Baselines have no router, so they also lose the $0 escalation shortcut.
                decided = Route(force_tier, f"forced (router said {decided.tier})")

            retrieved = [h.chunk.id for h in hits]
            if decided.tier == "none":
                ans = Answer(question, ESCALATION, decided, None, [], retrieved)
            else:
                spec = s.models[decided.tier]
                messages = build_prompt(question, hits)
                c = s.provider.complete(spec.name, decided.tier, messages)
                cost = spec.cost(c.input_tokens, c.output_tokens)
                ans = Answer(
                    question=question,
                    text=c.text,
                    route=decided,
                    model=spec.name,
                    citations=_CITATION.findall(c.text),
                    retrieved=retrieved,
                    input_tokens=c.input_tokens,
                    output_tokens=c.output_tokens,
                    cost_usd=cost,
                    latency_ms=c.latency_ms,
                    simulated=c.simulated,
                )
                self.tracer.generation(
                    model=spec.name,
                    input=messages,
                    output=c.text,
                    input_tokens=c.input_tokens,
                    output_tokens=c.output_tokens,
                    cost_usd=cost,
                    metadata={"route": decided.tier, "route_reason": decided.reason},
                )
            out.update(answer=ans.text, route=ans.route.tier, cost_usd=ans.cost_usd)
        return ans
