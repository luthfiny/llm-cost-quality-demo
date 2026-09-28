"""Model providers.

`MockProvider` lets the whole pipeline (routing, tracing, evals, cost report) run
offline and in CI. Its two tiers imitate the failure mode that makes routing
worth doing: the small model only reads the top retrieved passage, so it misses
answers that need two passages and it answers questions it should escalate.
Its numbers are simulated. Run with a real provider for real numbers.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from lcq.kb import tokenize

ESCALATION = "I'll connect you with our support team."


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    simulated: bool = False


class Provider(Protocol):
    def complete(self, model: str, tier: str, messages: list[dict]) -> Completion: ...


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


_BLOCK = re.compile(r"^\[([^\]]+)\]\n(.*?)(?=^\[[^\]]+\]\n|^QUESTION:)", re.S | re.M)
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


class MockProvider:
    """Deterministic extractive 'models' that answer from the prompt's context."""

    # Simulated latency so the report has a latency column in offline mode.
    LATENCY_MS = {"cheap": 450.0, "strong": 1600.0}

    def complete(self, model: str, tier: str, messages: list[dict]) -> Completion:
        prompt = messages[-1]["content"]
        question = prompt.split("QUESTION:", 1)[1].strip()
        blocks = [(cid, body.strip()) for cid, body in _BLOCK.findall(prompt)]
        q_terms = set(tokenize(question))

        candidates = []  # (overlap, position, chunk_id, sentence)
        usable = blocks[:1] if tier == "cheap" else blocks
        for cid, body in usable:
            for sentence in _SENTENCE.split(body.replace("\n", " ")):
                overlap = len(q_terms & set(tokenize(sentence)))
                if overlap:
                    candidates.append((overlap, len(candidates), cid, sentence.strip()))
        # Highest overlap first; ties keep retrieval order.
        candidates.sort(key=lambda c: (-c[0], c[1]))

        # The small model is overconfident (any overlap will do) and quotes one sentence.
        # The large model needs real evidence and combines up to 4 sentences.
        min_overlap, max_sentences = (1, 1) if tier == "cheap" else (2, 4)
        picked = [c for c in candidates if c[0] >= min_overlap][:max_sentences]
        if not picked:
            text = ESCALATION
        else:
            picked.sort(key=lambda c: c[1])  # read back in document order
            text = " ".join(f"{sentence} [{cid}]" for _, _, cid, sentence in picked)

        return Completion(
            text=text,
            input_tokens=sum(estimate_tokens(m["content"]) for m in messages),
            output_tokens=estimate_tokens(text),
            latency_ms=self.LATENCY_MS[tier],
            simulated=True,
        )


class OpenAICompatibleProvider:
    """Any `/chat/completions` endpoint: OpenAI, OpenRouter, Gemini's OpenAI API, vLLM, Ollama."""

    def __init__(self, base_url: str, api_key_env: str, timeout: float = 60.0):
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(f"Set {api_key_env} to use the openai_compatible provider.")
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def complete(self, model: str, tier: str, messages: list[dict]) -> Completion:
        start = time.perf_counter()
        resp = self.client.post(
            "/chat/completions",
            json={"model": model, "messages": messages, "temperature": 0},
        )
        resp.raise_for_status()
        latency_ms = (time.perf_counter() - start) * 1000
        body = resp.json()
        text = body["choices"][0]["message"]["content"] or ""
        usage = body.get("usage") or {}
        return Completion(
            text=text.strip(),
            input_tokens=usage.get("prompt_tokens")
            or sum(estimate_tokens(m["content"]) for m in messages),
            output_tokens=usage.get("completion_tokens") or estimate_tokens(text),
            latency_ms=latency_ms,
        )
