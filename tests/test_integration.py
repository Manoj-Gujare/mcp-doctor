"""End-to-end: launch the fixture server over stdio and scan it."""

from __future__ import annotations

import json
import sys
from collections import Counter

import anyio
import pytest
from conftest import FIXTURE_SERVER
from typer.testing import CliRunner

from mcpdoctor.cli import app
from mcpdoctor.config import ServerTarget
from mcpdoctor.models import ServerReport, Severity
from mcpdoctor.scanner import scan_target

runner = CliRunner()


def as_stdio_arg(command: list[str]) -> str:
    """Quote each part so paths with spaces survive on every OS."""
    return " ".join(f'"{part}"' for part in command)


@pytest.fixture(scope="module")
def report() -> ServerReport:
    target = ServerTarget(
        name="fixture",
        command=sys.executable,
        args=[str(FIXTURE_SERVER)],
        prefer_server_name=True,
    )
    return anyio.run(scan_target, target, 60.0)


def test_scan_reads_server_info_and_tools(report: ServerReport) -> None:
    assert report.error is None
    assert report.server == "notes-demo"
    assert {t.name for t in report.tools} == {
        "get_weather", "run", "helper", "search_notes", "find_notes", "bulk_import",
    }  # fmt: skip


def test_expected_findings(report: ServerReport) -> None:
    got = Counter((f.check, f.severity, f.tool) for f in report.findings)
    lint, cost = "description_lint", "token_cost"
    assert got == Counter(
        {
            (lint, Severity.ERROR, "run"): 1,  # empty description
            (lint, Severity.WARN, "run"): 1,  # undocumented param
            (lint, Severity.WARN, "helper"): 2,  # vague + undocumented param
            (lint, Severity.WARN, "search_notes"): 1,  # duplicate of find_notes
            (lint, Severity.WARN, "bulk_import"): 1,  # undocumented params
            (cost, Severity.WARN, "bulk_import"): 1,  # huge schema
        }
    )
    assert not any(f.tool == "get_weather" for f in report.findings)


def test_expected_score(report: ServerReport) -> None:
    assert report.score == 55
    assert report.grade == "F"


def test_cli_json_output(fixture_command: list[str]) -> None:
    result = runner.invoke(app, ["scan", "--json", "--stdio", as_stdio_arg(fixture_command)])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    server = data["servers"][0]
    assert server["server"] == "notes-demo"
    assert server["score"] == 55
    assert server["finding_count"] == 7
    assert server["results"][0]["metrics"]["approximate"] is True


def test_cli_fail_under(fixture_command: list[str]) -> None:
    args = ["scan", "--stdio", as_stdio_arg(fixture_command), "--fail-under", "80"]
    result = runner.invoke(app, args)
    assert result.exit_code == 1


def test_cli_connection_failure_is_one_line() -> None:
    result = runner.invoke(app, ["scan", "--stdio", "definitely-not-a-real-command-xyz"])
    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert "Scan failed" in result.output


def test_cli_requires_exactly_one_target() -> None:
    result = runner.invoke(app, ["scan"])
    assert result.exit_code == 2


def test_hanging_server_times_out() -> None:
    target = ServerTarget(
        name="hang", command=sys.executable, args=["-c", "import time; time.sleep(30)"]
    )
    result = anyio.run(scan_target, target, 1.0)
    assert result.error is not None
    assert result.error.startswith("Timed out after 1s")
    assert result.score == 0


def test_crashing_server_reports_stderr() -> None:
    code = "import sys; print('boom: missing API key', file=sys.stderr); sys.exit(1)"
    target = ServerTarget(name="crash", command=sys.executable, args=["-c", code])
    result = anyio.run(scan_target, target, 10.0)
    assert result.error is not None
    assert "boom: missing API key" in result.error
