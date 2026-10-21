"""Model providers.

`MockProvider` lets the whole pipeline (routing, tracing, evals, cost report) run
offline and in CI. Its two tiers imitate the failure mode that makes routing
worth doing: the small model only reads the top retrieved passage, so it misses
answers that need two passages and it answers questions it should escalate.
Its numbers are simulated. Run with a real provider for real numbers.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
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


class ProviderError(RuntimeError):
    def __init__(self, model: str, status: int, detail: str):
        super().__init__(f"{model}: HTTP {status}: {detail}")
        self.status = status


class OpenAICompatibleProvider:
    """Any `/chat/completions` endpoint: OpenAI, OpenRouter, Gemini's OpenAI API, vLLM, Ollama."""

    def __init__(
        self, base_url: str, api_key_env: str, timeout: float = 120.0, max_retries: int = 4
    ):
        self.max_retries = max_retries
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(f"Set {api_key_env} to use the openai_compatible provider.")
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def complete(self, model: str, tier: str, messages: list[dict]) -> Completion:
        payload = {"model": model, "messages": messages, "temperature": 0}
        for attempt in range(self.max_retries + 1):
            start = time.perf_counter()
            resp = self.client.post("/chat/completions", json=payload)
            latency_ms = (time.perf_counter() - start) * 1000
            body = (
                resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            # Gateways such as OpenRouter can return HTTP 200 with an upstream error in the body.
            error = body.get("error") if isinstance(body, dict) else None
            code = error.get("code") if isinstance(error, dict) else None
            if resp.status_code >= 400:
                status = resp.status_code
            elif error:
                status = code if isinstance(code, int) else 500
            else:
                status = 200
            # A per-day quota will not clear with a short backoff, so fail fast on it.
            daily_quota = status == 429 and "per-day" in resp.text
            if status == 429 and not daily_quota or status >= 500:
                if attempt < self.max_retries:
                    time.sleep(_retry_delay(resp, attempt))
                    continue
            if status >= 400 or error or not body.get("choices"):
                raise ProviderError(model, status, str(error or resp.text[:300]))
            text = body["choices"][0]["message"].get("content") or ""
            usage = body.get("usage") or {}
            return Completion(
                text=text.strip(),
                input_tokens=usage.get("prompt_tokens")
                or sum(estimate_tokens(m["content"]) for m in messages),
                output_tokens=usage.get("completion_tokens") or estimate_tokens(text),
                latency_ms=latency_ms,
            )
        raise AssertionError("unreachable")


def _retry_delay(resp: httpx.Response, attempt: int) -> float:
    retry_after = resp.headers.get("retry-after")
    if retry_after and retry_after.isdigit():
        return min(float(retry_after), 120.0)
    return min(5.0 * 2**attempt, 120.0)


class CachingProvider:
    """Replays identical requests from disk.

    Evals run at temperature 0, so a (model, messages) pair only needs one paid
    call: re-runs and the routed mode reuse the baseline answers. Latency and
    token usage are replayed too, so cost accounting is unchanged.
    """

    def __init__(self, inner: Provider, path: Path):
        self.inner = inner
        self.path = path
        self.entries: dict[str, dict] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                self.entries[entry["key"]] = entry["completion"]
        self.hits = self.misses = 0

    def complete(self, model: str, tier: str, messages: list[dict]) -> Completion:
        key = hashlib.sha256(json.dumps([model, messages], sort_keys=True).encode()).hexdigest()
        if key in self.entries:
            self.hits += 1
            return Completion(**self.entries[key])
        self.misses += 1
        completion = self.inner.complete(model, tier, messages)
        self.entries[key] = asdict(completion)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "completion": asdict(completion)}) + "\n")
        return completion
