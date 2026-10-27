"""Glue: fetch tool definitions, run every registered check, and score the result."""

from __future__ import annotations

from collections.abc import Sequence

import anyio

from mcpgrader import __version__, scoring
from mcpgrader.checks import Check, run_checks
from mcpgrader.client import ScanError, ServerSnapshot, fetch
from mcpgrader.config import ServerTarget
from mcpgrader.models import Report, ServerReport


def analyze(snapshot: ServerSnapshot, checks: Sequence[Check] | None = None) -> ServerReport:
    """Run checks over an already-fetched server. Pure, so it is easy to test."""
    report = ServerReport(
        server=snapshot.name,
        tools=snapshot.tools,
        prompt_count=snapshot.prompt_count,
        resource_count=snapshot.resource_count,
        results=run_checks(snapshot.tools, checks),
    )
    report.score = scoring.score(report.findings)
    report.grade = scoring.grade(report.score)
    return report


async def scan_target(target: ServerTarget, timeout: float) -> ServerReport:
    try:
        snapshot = await fetch(target, timeout)
    except ScanError as exc:
        return ServerReport(server=target.name, score=0, grade="F", error=str(exc))
    return analyze(snapshot)


def scan(targets: Sequence[ServerTarget], timeout: float) -> Report:
    async def _all() -> list[ServerReport]:
        return [await scan_target(t, timeout) for t in targets]

    return Report(servers=anyio.run(_all), tool_version=__version__)
