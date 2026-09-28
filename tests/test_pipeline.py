from pathlib import Path

import pytest

from lcq.bot import SupportBot
from lcq.cli import main
from lcq.config import load_settings
from lcq.evals import Case, check, load_cases, run_suite
from lcq.kb import BM25Index, load_kb, tokenize
from lcq.providers import ESCALATION
from lcq.report import summarize
from lcq.router import route

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "data" / "kb"


@pytest.fixture(scope="module")
def bot():
    return SupportBot(load_settings(ROOT / "config" / "mock.yaml"), KB)


def test_tokenize_folds_plurals_and_drops_stopwords():
    assert tokenize("How many bags are there?") == ["many", "bag"]


def test_retrieval_finds_the_right_section():
    index = BM25Index(load_kb(KB))
    assert (
        index.search("shipping fee outside Java")[0].chunk.id == "shipping#shipping-zones-and-fees"
    )


def test_router_tiers():
    index = BM25Index(load_kb(KB))
    q_none = "Are you hiring baristas?"
    q_cheap = "What payment terms apply to Office plan invoices?"
    q_strong = "How much would the Basic plan plus shipping to Bandung cost me per month?"
    assert route(q_none, index.search(q_none), 3.0).tier == "none"
    assert route(q_cheap, index.search(q_cheap), 3.0).tier == "cheap"
    assert route(q_strong, index.search(q_strong), 3.0).tier == "strong"


def test_escalation_route_costs_nothing(bot):
    a = bot.answer("Are you hiring baristas?")
    assert a.route.tier == "none" and a.cost_usd == 0 and a.text == ESCALATION


def test_forced_tier_overrides_router(bot):
    a = bot.answer("Are you hiring baristas?", force_tier="strong")
    assert a.route.tier == "strong" and a.cost_usd > 0


def test_check_rules():
    case = Case("c", "lookup", "q", must_match=(r"89[.,]?000",), must_cite=("plans",))
    good = type(
        "A", (), {"text": "It is Rp89.000 [plans#plan-prices]", "citations": ["plans#plan-prices"]}
    )
    bad = type("A", (), {"text": "It is IDR 90,000", "citations": []})
    assert check(case, good) == []
    assert len(check(case, bad)) == 2
    esc = Case("e", "escalation", "q", expect_escalation=True)
    assert check(esc, type("A", (), {"text": ESCALATION, "citations": []})) == []


def test_cases_file_is_valid():
    cases = load_cases(ROOT / "data" / "evals" / "cases.yaml")
    assert len(cases) == 50
    assert {c.category for c in cases} == {"lookup", "multi_hop", "policy", "escalation"}


def test_routing_saves_cost_without_losing_much_quality(bot):
    cases = load_cases(ROOT / "data" / "evals" / "cases.yaml")
    strong = summarize("strong-only", run_suite(bot, cases, force_tier="strong"))
    routed = summarize("routed", run_suite(bot, cases))
    assert routed.cost_usd < 0.8 * strong.cost_usd
    assert routed.passed >= strong.passed - 2


def test_cli_eval_writes_report(tmp_path):
    out = tmp_path / "report.md"
    rc = main(["eval", "--out", str(out), "--traces", str(tmp_path / "traces")])
    assert rc == 0
    assert "Routed vs strong-only" in out.read_text()
    assert list((tmp_path / "traces").glob("*.jsonl"))
