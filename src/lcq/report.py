from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from lcq.evals import CaseResult


@dataclass(frozen=True)
class ModeSummary:
    mode: str
    passed: int
    total: int
    cost_usd: float
    mean_latency_ms: float
    p95_latency_ms: float
    routes: Counter
    by_category: dict[str, tuple[int, int]]
    simulated: bool

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def cost_per_1k(self) -> float:
        return self.cost_usd / self.total * 1000 if self.total else 0.0


def summarize(mode: str, results: list[CaseResult]) -> ModeSummary:
    latencies = sorted(r.answer.latency_ms for r in results)
    by_cat: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in results:
        by_cat[r.case.category][0] += r.passed
        by_cat[r.case.category][1] += 1
    p95_index = max(0, round(0.95 * len(latencies)) - 1)
    return ModeSummary(
        mode=mode,
        passed=sum(r.passed for r in results),
        total=len(results),
        cost_usd=sum(r.answer.cost_usd for r in results),
        mean_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
        p95_latency_ms=latencies[p95_index] if latencies else 0.0,
        routes=Counter(r.answer.route.tier for r in results),
        by_category={k: (v[0], v[1]) for k, v in sorted(by_cat.items())},
        simulated=any(r.answer.simulated for r in results),
    )


def render_markdown(
    summaries: list[ModeSummary],
    failures: dict[str, list[CaseResult]],
    models: dict[str, str],
    pricing_note: str | None = None,
) -> str:
    lines = ["# Cost vs quality report", ""]
    if pricing_note:
        lines += [f"> **Pricing:** {pricing_note}", ""]
    if any(s.simulated for s in summaries):
        lines += [
            "> **Simulated run.** These numbers come from the offline mock provider and only",
            "> demonstrate the pipeline. Run with a real provider for real cost and quality.",
            "",
        ]
    lines += [
        f"Models: cheap = `{models['cheap']}`, strong = `{models['strong']}`",
        "",
        "| Mode | Pass | Pass rate | Cost / 1k questions | Mean latency | p95 latency "
        "| Route mix |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        mix = ", ".join(f"{k} {v}" for k, v in sorted(s.routes.items()))
        lines.append(
            f"| {s.mode} | {s.passed}/{s.total} | {s.pass_rate:.0%} | ${s.cost_per_1k:.4f} | "
            f"{s.mean_latency_ms:.0f} ms | {s.p95_latency_ms:.0f} ms | {mix} |"
        )

    base = next((s for s in summaries if s.mode == "strong-only"), None)
    routed = next((s for s in summaries if s.mode == "routed"), None)
    if base and routed and base.cost_usd > 0:
        saving = 1 - routed.cost_usd / base.cost_usd
        delta = routed.passed - base.passed
        lines += [
            "",
            f"**Routed vs strong-only: {saving:.1%} lower cost, "
            f"{delta:+d} eval passes "
            f"({routed.passed}/{routed.total} vs {base.passed}/{base.total}).**",
        ]

    cats = sorted({c for s in summaries for c in s.by_category})
    lines += [
        "",
        "## Pass rate by category",
        "",
        "| Category | " + " | ".join(s.mode for s in summaries) + " |",
        "|---|" + "---|" * len(summaries),
    ]
    for cat in cats:
        cells = []
        for s in summaries:
            p, t = s.by_category.get(cat, (0, 0))
            cells.append(f"{p}/{t}")
        lines.append(f"| {cat} | " + " | ".join(cells) + " |")

    for mode, failed in failures.items():
        if not failed:
            continue
        lines += ["", f"## Failures: {mode}", ""]
        for r in failed:
            lines.append(
                f"- **{r.case.id}** ({r.case.category}, route `{r.answer.route.tier}`): "
                f"{'; '.join(r.failures)}"
            )
            lines.append(f"  - Q: {r.case.question}")
            lines.append(f"  - A: {r.answer.text[:300]}")
    return "\n".join(lines) + "\n"
