# LLM Cost & Quality Demo

A small customer-support chatbot built to show the three things most LLM features ship without:

1. **An eval suite** that says, in numbers, how often the bot is right (50 cases, deterministic checks, runs in CI).
2. **Per-request cost accounting and tracing** (local JSONL traces, optional [Langfuse](https://langfuse.com)).
3. **Cost-aware model routing**: cheap model for lookups, strong model for multi-step questions, and a $0 hand-off when retrieval finds nothing.

It exists to answer the question every team with an LLM feature eventually asks: *"Can we cut the model bill without the bot getting worse, and how would we know?"*

```
question ─► BM25 retrieval ─► router ─┬─ none   ─► canned hand-off ($0)
                                      ├─ cheap  ─► small model
                                      └─ strong ─► frontier model
                    every step ─► trace (tokens, cost, route, latency)
                    eval suite  ─► pass rate + cost per 1k questions, per mode
```

## Quickstart (offline, no API key)

```bash
uv sync
uv run lcq ask "How much is the Basic plan?"
uv run lcq eval            # strong-only vs cheap-only vs routed
uv run pytest
```

Offline mode uses a deterministic mock provider so the full pipeline runs in CI. The mock "models"
are keyword extractors: the small one reads only the top passage and never escalates, the large one
combines passages. **Its numbers are simulated** and show the shape of the trade-off, not real
model quality. The simulated report is in [reports/sample-mock-report.md](reports/sample-mock-report.md):

| Mode | Pass | Cost / 1k questions | Route mix |
|---|---|---|---|
| strong-only | 36/50 | $0.81 | strong 50 |
| cheap-only | 25/50 | $0.03 | cheap 50 |
| routed | 35/50 | $0.45 | cheap 23, none 5, strong 22 |

### Real models (OpenRouter, 2026-09-29)

cheap = `nvidia/nemotron-3.5-lightning`, strong = `nvidia/nemotron-3-ultra-550b-a55b`.
Full report: [reports/openrouter-report.md](reports/openrouter-report.md).

| Mode | Pass | Cost / 1k questions | Route mix |
|---|---|---|---|
| strong-only | 49/50 | $0.51 | strong 50 |
| cheap-only | 47/50 | $0.19 | cheap 50 |
| **routed** | **48/50** | **$0.35** | cheap 23, none 5, strong 22 |

**Routing cut cost by 32.1% for one fewer eval pass (48/50 vs 49/50).**

What the evals caught:

- **Per-token price is not per-answer price.** The cheap model lists at 7–12× lower prices, but it
  averaged 843 output tokens per answer against the strong model's 150, so it was only ~2.7× cheaper per
  answer.
- **The cheap model's failures were operational, not factual:** two empty answers (its token budget
  went to reasoning) and one answer that leaked its reasoning ("Here's a thinking process: ...").
  Neither shows up in a manual spot check. Both show up in an eval.
- **Both models handed off all 8 out-of-scope questions.** The strong model's one miss was over-cautious:
  it escalated a Jakarta delivery question because the docs say "Jabodetabek" and never "Jakarta".
  The fix is in the knowledge base, not the model.
- Two checks rejected correct answers on the first run ("you won't be billed", "not charged a
  prorated amount"). They were widened before the final report. Grader bugs are real bugs, too.

> Runs used OpenRouter's free variants. Costs use the list prices of the paid variants of the same
> models. Latency is omitted because free-tier queueing (up to minutes per request) says nothing
> about production latency.

## Run against real models

Any OpenAI-compatible endpoint works (OpenAI, OpenRouter, Gemini's OpenAI API, vLLM, Ollama).

```bash
cp config/openrouter.example.yaml config/openrouter.yaml   # set models + current prices
export OPENROUTER_API_KEY=...
uv run lcq --config config/openrouter.yaml eval
```

Optional Langfuse tracing (self-hosted or cloud):

```bash
uv sync --extra langfuse
export LANGFUSE_PUBLIC_KEY=... LANGFUSE_SECRET_KEY=... LANGFUSE_HOST=https://cloud.langfuse.com
```

Tracing is non-blocking: if Langfuse is down, answers still go out and a single warning is printed.

## What is in here

| Path | What it shows |
|---|---|
| [src/lcq/router.py](src/lcq/router.py) | Readable routing rules with a reason string on every decision |
| [src/lcq/evals.py](src/lcq/evals.py) | Regex / citation / escalation checks; no LLM judge needed for most cases |
| [data/evals/cases.yaml](data/evals/cases.yaml) | 50 cases: lookup, multi-hop, policy (date rules), escalation |
| [src/lcq/tracing.py](src/lcq/tracing.py) | JSONL traces + Langfuse v4 spans/generations with usage and cost |
| [src/lcq/report.py](src/lcq/report.py) | Pass rate, cost per 1k questions, latency, route mix, failure list |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | Eval gate: the build fails if routed pass rate drops |

## Design choices

- **Deterministic checks first.** Regex, citation and hand-off checks are cheap, reproducible and
  easy to explain. An LLM judge is worth adding only for cases these cannot express.
- **Escalation is a feature.** Out-of-scope questions are a separate category because a bot that
  confidently answers them is worse than one that hands off.
- **Every routing change is gated by the same eval suite.** Cost savings only count if the pass
  rate holds.
- **Plain rules before a classifier.** Start with rules a client can read; replace them with a small
  classifier trained on traced traffic once there is enough of it.

## About

Built by Luthfi Naufan Yamin, AI engineer ([portfolio](https://luthfiny-portfolio.netlify.app)).
I set up evals, tracing and cost controls for teams running LLM chatbots and agents. If your team
has an LLM feature in production and no clear answer to "how often is it wrong, and what does each
conversation cost?", get in touch through the portfolio.

The company in the knowledge base (Kopi Kilat) is fictional.

MIT licensed.
