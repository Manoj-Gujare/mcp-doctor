from __future__ import annotations

import io
import json

from conftest import tool
from rich.console import Console

from mcpgrader.client import ServerSnapshot
from mcpgrader.models import Report, ServerReport
from mcpgrader.render import render, to_json
from mcpgrader.scanner import analyze


def sample_report() -> Report:
    snapshot = ServerSnapshot(
        name="demo",
        tools=[tool("run", ""), tool("get_weather", "Get the current weather for a given city.")],
        prompt_count=0,
    )
    failed = ServerReport(server="broken", score=0, grade="F", error="Command not found: nope")
    return Report(servers=[analyze(snapshot), failed], tool_version="0.0.0")


def rendered(encoding: str) -> str:
    buffer = io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors="strict")
    console = Console(file=buffer, width=100, color_system=None, legacy_windows=False)
    render(sample_report(), console)
    buffer.flush()
    buffer.seek(0)
    return buffer.read()


def test_terminal_output_contains_key_sections() -> None:
    out = rendered("utf-8")
    for text in ("demo", "get_weather", "Errors (1)", "fix:", "Score", "Summary", "broken"):
        assert text in out
    assert "Command not found: nope" in out


def test_terminal_output_survives_non_unicode_encoding() -> None:
    out = rendered("cp1252")  # would raise UnicodeEncodeError on a Unicode glyph
    assert "Score" in out


def test_json_is_complete_and_serializable() -> None:
    data = json.loads(to_json(sample_report()))
    demo, broken = data["servers"]
    assert demo["server"] == "demo"
    assert demo["finding_count"] == 1
    assert demo["results"][1]["findings"][0]["severity"] == "error"
    assert broken["error"] == "Command not found: nope"
