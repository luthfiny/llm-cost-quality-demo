from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from lcq.providers import MockProvider, OpenAICompatibleProvider, Provider


@dataclass(frozen=True)
class ModelSpec:
    tier: str
    name: str
    input_per_mtok: float  # USD per 1M input tokens
    output_per_mtok: float  # USD per 1M output tokens

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.input_per_mtok + output_tokens * self.output_per_mtok
        ) / 1_000_000


@dataclass(frozen=True)
class Settings:
    provider: Provider
    models: dict[str, ModelSpec]
    top_k: int
    min_retrieval_score: float


def load_settings(path: Path) -> Settings:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    kind = raw["provider"]["kind"]
    if kind == "mock":
        provider: Provider = MockProvider()
    elif kind == "openai_compatible":
        provider = OpenAICompatibleProvider(
            base_url=raw["provider"]["base_url"],
            api_key_env=raw["provider"]["api_key_env"],
        )
    else:
        raise ValueError(f"Unknown provider kind: {kind}")

    models = {
        tier: ModelSpec(tier, spec["name"], spec["input_per_mtok"], spec["output_per_mtok"])
        for tier, spec in raw["models"].items()
    }
    missing = {"cheap", "strong"} - models.keys()
    if missing:
        raise ValueError(f"Config must define models: {sorted(missing)}")
    unpriced = [t for t, m in models.items() if m.input_per_mtok <= 0 or m.output_per_mtok <= 0]
    if unpriced and kind != "mock":
        raise ValueError(f"Set real per-1M-token prices for: {unpriced} (cost report needs them)")

    retrieval = raw.get("retrieval", {})
    return Settings(
        provider=provider,
        models=models,
        top_k=retrieval.get("top_k", 3),
        min_retrieval_score=retrieval.get("min_score", 3.0),
    )
