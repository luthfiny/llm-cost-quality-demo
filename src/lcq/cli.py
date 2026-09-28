from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lcq.bot import SupportBot
from lcq.config import load_settings
from lcq.evals import load_cases, run_suite
from lcq.report import render_markdown, summarize
from lcq.tracing import Tracer

ROOT = Path(__file__).resolve().parents[2]
MODES = {"strong-only": "strong", "cheap-only": "cheap", "routed": None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lcq", description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "mock.yaml")
    parser.add_argument("--kb", type=Path, default=ROOT / "data" / "kb")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ask = sub.add_parser("ask", help="Answer one question and show the routing decision")
    ask.add_argument("question")

    ev = sub.add_parser("eval", help="Run the eval suite in one or more modes")
    ev.add_argument("--cases", type=Path, default=ROOT / "data" / "evals" / "cases.yaml")
    ev.add_argument("--modes", default="strong-only,cheap-only,routed")
    ev.add_argument("--out", type=Path, default=ROOT / "reports" / "latest.md")
    ev.add_argument("--traces", type=Path, default=ROOT / "traces")
    ev.add_argument(
        "--min-pass-rate",
        type=float,
        default=None,
        help="Exit non-zero if the routed pass rate is below this (CI gate)",
    )

    args = parser.parse_args(argv)
    settings = load_settings(args.config)

    if args.cmd == "ask":
        tracer = Tracer()
        bot = SupportBot(settings, args.kb, tracer)
        a = bot.answer(args.question)
        tracer.close()
        print(a.text)
        print(
            f"\nroute={a.route.tier} ({a.route.reason}) model={a.model} "
            f"tokens={a.input_tokens}+{a.output_tokens} cost=${a.cost_usd:.6f}"
            f"{' [simulated]' if a.simulated else ''}"
        )
        return 0

    cases = load_cases(args.cases)
    modes = [m.strip() for m in args.modes.split(",")]
    unknown = set(modes) - MODES.keys()
    if unknown:
        parser.error(f"unknown modes: {sorted(unknown)}")

    tracer = Tracer(args.traces, run_name="eval")
    bot = SupportBot(settings, args.kb, tracer)
    summaries, failures = [], {}
    for mode in modes:
        results = run_suite(bot, cases, force_tier=MODES[mode])
        summaries.append(summarize(mode, results))
        failures[mode] = [r for r in results if not r.passed]
    tracer.close()

    report = render_markdown(summaries, failures, {t: m.name for t, m in settings.models.items()})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report: {args.out}\nTraces: {tracer.path}", file=sys.stderr)

    if args.min_pass_rate is not None:
        routed = next((s for s in summaries if s.mode == "routed"), None)
        if routed and routed.pass_rate < args.min_pass_rate:
            print(
                f"FAIL: routed pass rate {routed.pass_rate:.0%} < {args.min_pass_rate:.0%}",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
