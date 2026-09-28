"""Tracing: a local JSONL tracer that always works, plus optional Langfuse (SDK v4).

Tracing must never break the request path, so every Langfuse call is wrapped and
failures are downgraded to a warning (the same "non-blocking" rule used in
production chat systems).
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class Tracer:
    def __init__(self, out_dir: Path | None = None, run_name: str = "run"):
        self.run_id = f"{run_name}-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self._file = None
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            self.path = out_dir / f"{self.run_id}.jsonl"
            self._file = self.path.open("w", encoding="utf-8")
        self._langfuse = _maybe_langfuse()

    def record(self, event: dict[str, Any]) -> None:
        if self._file:
            self._file.write(json.dumps({"run_id": self.run_id, **event}) + "\n")

    @contextmanager
    def trace(self, name: str, input: Any, metadata: dict[str, Any] | None = None):
        """Yields a dict; whatever the caller puts in it is sent as the trace output."""
        out: dict[str, Any] = {}
        span_cm = None
        if self._langfuse:
            try:
                span_cm = self._langfuse.start_as_current_observation(
                    name=name,
                    as_type="chain",
                    input=input,
                    metadata={"run_id": self.run_id, **(metadata or {})},
                )
                span = span_cm.__enter__()
            except Exception as exc:  # noqa: BLE001
                _warn(exc)
                span_cm = None
        try:
            yield out
        finally:
            if span_cm:
                try:
                    span.update(output=out)
                    span_cm.__exit__(None, None, None)
                except Exception as exc:  # noqa: BLE001
                    _warn(exc)

    def generation(
        self,
        *,
        model: str,
        input: Any,
        output: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        metadata: dict[str, Any],
    ) -> None:
        if not self._langfuse:
            return
        try:
            with self._langfuse.start_as_current_observation(
                name="llm",
                as_type="generation",
                model=model,
                input=input,
                output=output,
                metadata=metadata,
                usage_details={"input": input_tokens, "output": output_tokens},
                cost_details={"total": cost_usd},
            ):
                pass
        except Exception as exc:  # noqa: BLE001
            _warn(exc)

    def close(self) -> None:
        if self._file:
            self._file.close()
        if self._langfuse:
            try:
                self._langfuse.flush()
            except Exception as exc:  # noqa: BLE001
                _warn(exc)


def _maybe_langfuse():
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        return None
    try:
        from langfuse import get_client

        return get_client()
    except Exception as exc:  # noqa: BLE001
        _warn(exc)
        return None


_warned = False


def _warn(exc: Exception) -> None:
    global _warned
    if not _warned:
        print(f"[tracing] Langfuse error, request continues untraced: {exc!r}", file=sys.stderr)
        _warned = True
