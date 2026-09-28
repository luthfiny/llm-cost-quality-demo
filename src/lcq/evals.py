"""Deterministic eval harness.

Each case declares what a correct answer must (and must not) contain. String and
regex checks are cheap, reproducible and explainable to a client; add an LLM
judge only for the cases these checks cannot express.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lcq.bot import Answer, SupportBot
from lcq.providers import ESCALATION

_ESCALATION_RE = re.compile(re.escape(ESCALATION.rstrip(".")), re.I)


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    question: str
    must_match: tuple[str, ...] = ()  # every regex must match
    must_not_match: tuple[str, ...] = ()
    must_cite: tuple[str, ...] = ()  # doc ids (before '#') that must be cited
    expect_escalation: bool = False


@dataclass
class CaseResult:
    case: Case
    answer: Answer
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


def load_cases(path: Path) -> list[Case]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases = []
    for item in raw["cases"]:
        cases.append(
            Case(
                id=item["id"],
                category=item["category"],
                question=item["question"],
                must_match=tuple(item.get("must_match", [])),
                must_not_match=tuple(item.get("must_not_match", [])),
                must_cite=tuple(item.get("must_cite", [])),
                expect_escalation=item.get("expect_escalation", False),
            )
        )
    ids = [c.id for c in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"Duplicate case ids: {sorted(dupes)}")
    return cases


def check(case: Case, answer: Answer) -> list[str]:
    text = answer.text
    failures = []
    escalated = bool(_ESCALATION_RE.search(text))
    if case.expect_escalation:
        if not escalated:
            failures.append("should have escalated but answered")
        return failures
    if escalated:
        return ["escalated a question the knowledge base answers"]
    for pattern in case.must_match:
        if not re.search(pattern, text, re.I):
            failures.append(f"missing /{pattern}/")
    for pattern in case.must_not_match:
        if re.search(pattern, text, re.I):
            failures.append(f"contains forbidden /{pattern}/")
    cited_docs = {c.split("#", 1)[0] for c in answer.citations}
    for doc in case.must_cite:
        if doc not in cited_docs:
            failures.append(f"no citation to {doc}")
    return failures


def run_suite(
    bot: SupportBot, cases: list[Case], force_tier: str | None = None
) -> list[CaseResult]:
    results = []
    for case in cases:
        answer = bot.answer(case.question, force_tier=force_tier)
        result = CaseResult(case, answer, check(case, answer))
        bot.tracer.record(
            {
                "case_id": case.id,
                "category": case.category,
                "mode": force_tier or "routed",
                "route": answer.route.tier,
                "route_reason": answer.route.reason,
                "model": answer.model,
                "answer": answer.text,
                "retrieved": answer.retrieved,
                "passed": result.passed,
                "failures": result.failures,
                "input_tokens": answer.input_tokens,
                "output_tokens": answer.output_tokens,
                "cost_usd": answer.cost_usd,
                "latency_ms": answer.latency_ms,
            }
        )
        results.append(result)
    return results
