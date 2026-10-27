from __future__ import annotations

import pytest
from conftest import tool

from mcpgrader.checks.description_lint import DescriptionLintCheck, is_vague, jaccard
from mcpgrader.models import Severity

GOOD = "Get the current weather for a city, including temperature and wind speed."
DOC = {"type": "string", "description": "City name."}


def lint(*tools):
    return DescriptionLintCheck().run(list(tools)).findings


def messages(findings) -> str:
    return " | ".join(f.message for f in findings)


def test_good_tool_has_no_findings() -> None:
    assert lint(tool("get_weather", GOOD, city=DOC)) == []


@pytest.mark.parametrize("description", [None, "", "   "])
def test_missing_description_is_error(description: str | None) -> None:
    findings = lint(tool("run", description))
    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "Missing" in findings[0].message


def test_short_description_warns() -> None:
    findings = lint(tool("get_weather", "Weather for city."))
    assert len(findings) == 1
    assert "only 17 chars" in findings[0].message


def test_long_description_warns() -> None:
    findings = lint(tool("get_weather", GOOD + " More detail." * 100))
    assert any("max 1,000" in f.message for f in findings)


@pytest.mark.parametrize(
    ("name", "description"),
    [
        ("helper", "Helper utility."),
        ("thing", "Does stuff."),
        ("misc", "A tool that does various things."),
        ("list_files", "List files."),
        ("x", "TODO"),
    ],
)
def test_vague_descriptions(name: str, description: str) -> None:
    assert is_vague(name, description) is not None
    findings = lint(tool(name, description))
    assert any("Vague" in f.message for f in findings)
    # Vague and too-short describe the same problem, so only one is reported.
    assert not any("chars" in f.message for f in findings)


def test_specific_description_is_not_vague() -> None:
    assert is_vague("get_weather", GOOD) is None


def test_undocumented_parameters_including_nested() -> None:
    nested = {"type": "object", "properties": {"inner": {"type": "string"}}}
    findings = lint(tool("get_weather", GOOD, city=DOC, units={"type": "string"}, opts=nested))
    assert len(findings) == 1
    assert "3 parameter(s)" in findings[0].message
    for name in ("units", "opts", "opts.inner"):
        assert name in findings[0].message


def test_near_duplicate_pair_is_flagged_once() -> None:
    a = tool("search_notes", "Search the user's notes by keyword and return matching titles.")
    b = tool("find_notes", "Find the user's notes by keyword and return the matching titles.")
    findings = lint(a, b, tool("get_weather", GOOD))
    dupes = [f for f in findings if "similar" in f.message]
    assert len(dupes) == 1
    assert dupes[0].tool == "search_notes"
    assert "find_notes" in dupes[0].message


def test_distinct_tools_are_not_duplicates() -> None:
    a = tool("read_file", "Read a text file from disk and return its contents as a string.")
    b = tool("delete_branch", "Delete a git branch locally after checking it has been merged.")
    assert not any("similar" in f.message for f in lint(a, b))


def test_jaccard() -> None:
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard({"a"}, {"b"}) == 0.0
    assert jaccard(set(), set()) == 0.0


def test_every_finding_has_a_fix() -> None:
    findings = lint(tool("run", ""), tool("helper", "Helper.", x={"type": "string"}))
    assert findings
    assert all(f.fix and f.check == "description_lint" for f in findings)
