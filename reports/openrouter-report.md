# Cost vs quality report

> **Pricing:** Run on OpenRouter's free variants; costs use the list prices of the paid variants of the same models (OpenRouter, 2026-09-29).

Models: cheap = `nvidia/nemotron-3.5-lightning:free`, strong = `nvidia/nemotron-3-ultra-550b-a55b:free`

| Mode | Pass | Pass rate | Cost / 1k questions | Mean latency | p95 latency | Route mix |
|---|---|---|---|---|---|---|
| strong-only | 49/50 | 98% | $0.5143 | 7841 ms | 26888 ms | strong 50 |
| cheap-only | 47/50 | 94% | $0.1891 | 76314 ms | 241478 ms | cheap 50 |
| routed | 48/50 | 96% | $0.3490 | 29804 ms | 107549 ms | cheap 23, none 5, strong 22 |

**Routed vs strong-only: 32.1% lower cost, -1 eval passes (48/50 vs 49/50).**

## Pass rate by category

| Category | strong-only | cheap-only | routed |
|---|---|---|---|
| escalation | 8/8 | 8/8 | 8/8 |
| lookup | 24/24 | 23/24 | 23/24 |
| multi_hop | 13/14 | 12/14 | 13/14 |
| policy | 4/4 | 4/4 | 4/4 |

## Failures: strong-only

- **hop-thursday-cutoff** (multi_hop, route `strong`): escalated a question the knowledge base answers
  - Q: If I confirm my order at 11:00 WIB on a Thursday, does it ship the same day, and how long until it reaches Jakarta?
  - A: I'll connect you with our support team.

## Failures: cheap-only

- **lookup-grinder-loan** (lookup, route `cheap`): missing /grinder loan|loan/; no citation to office
  - Q: Do Office plan customers get a grinder?
  - A: 
- **hop-basic-bandung-total** (multi_hop, route `cheap`): missing /89[.,]?000/; missing /15[.,]?000/; no citation to plans; no citation to shipping
  - Q: How much would the Basic plan plus shipping to Bandung cost me per month?
  - A: 
- **hop-thursday-cutoff** (multi_hop, route `cheap`): escalated a question the knowledge base answers
  - Q: If I confirm my order at 11:00 WIB on a Thursday, does it ship the same day, and how long until it reaches Jakarta?
  - A: Here's a thinking process:

1.  **Analyze User Input:**
   - User asks: "If I confirm my order at 11:00 WIB on a Thursday, does it ship the same day, and how long until it reaches Jakarta?"
   - Constraints: Answer ONLY from the CONTEXT passages. Be concise (1-3 sentences). After each fact, cite the

## Failures: routed

- **lookup-grinder-loan** (lookup, route `cheap`): missing /grinder loan|loan/; no citation to office
  - Q: Do Office plan customers get a grinder?
  - A: 
- **hop-thursday-cutoff** (multi_hop, route `strong`): escalated a question the knowledge base answers
  - Q: If I confirm my order at 11:00 WIB on a Thursday, does it ship the same day, and how long until it reaches Jakarta?
  - A: I'll connect you with our support team.
