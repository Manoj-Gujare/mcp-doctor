from __future__ import annotations

from conftest import tool

from mcpdoctor.checks.token_cost import THRESHOLDS, TokenCostCheck, count_tool_tokens
from mcpdoctor.models import Severity


def test_counts_tokens_per_tool_and_total() -> None:
    tools = [tool("a", "Read a file from disk."), tool("b", "Write a file to disk.")]
    result = TokenCostCheck().run(tools)

    per_tool = result.metrics["per_tool"]
    assert set(per_tool) == {"a", "b"}
    assert all(n > 0 for n in per_tool.values())
    assert result.metrics["total_tokens"] == sum(per_tool.values())
    assert result.metrics["approximate"] is True
    assert result.findings == []


def test_heaviest_is_sorted_and_capped_at_top_n() -> None:
    tools = [tool(f"t{i}", "word " * (i * 10 + 1)) for i in range(8)]
    heaviest = TokenCostCheck().run(tools).metrics["heaviest"]

    assert len(heaviest) == THRESHOLDS["top_n"]
    assert heaviest[0]["tool"] == "t7"
    tokens = [h["tokens"] for h in heaviest]
    assert tokens == sorted(tokens, reverse=True)


def test_single_heavy_tool_warns() -> None:
    heavy = tool("heavy", "x " * 600)
    assert count_tool_tokens(heavy) > THRESHOLDS["tool_warn"]

    findings = TokenCostCheck().run([heavy]).findings
    per_tool = [f for f in findings if f.tool == "heavy"]
    assert len(per_tool) == 1
    assert per_tool[0].severity is Severity.WARN


def test_total_thresholds_warn_then_error() -> None:
    check = TokenCostCheck(thresholds={"total_warn": 10, "total_error": 1_000, "tool_warn": 10**6})
    server_level = [f for f in check.run([tool("a", "word " * 50)]).findings if f.tool is None]
    assert [f.severity for f in server_level] == [Severity.WARN]

    check = TokenCostCheck(thresholds={"total_warn": 10, "total_error": 20, "tool_warn": 10**6})
    server_level = [f for f in check.run([tool("a", "word " * 50)]).findings if f.tool is None]
    assert [f.severity for f in server_level] == [Severity.ERROR]


def test_empty_server_costs_nothing() -> None:
    result = TokenCostCheck().run([])
    assert result.metrics["total_tokens"] == 0
    assert result.findings == []
