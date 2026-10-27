"""Terminal (Rich) and JSON renderers for a Report."""

from __future__ import annotations

import json

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mcpgrader.checks.token_cost import THRESHOLDS
from mcpgrader.models import Finding, Report, ServerReport, Severity

SEVERITY_STYLE: dict[Severity, str] = {
    Severity.ERROR: "bold red",
    Severity.WARN: "yellow",
    Severity.INFO: "cyan",
}
GRADE_STYLE = {"A": "bold green", "B": "green", "C": "yellow", "D": "dark_orange", "F": "bold red"}

# Glyphs, with ASCII fallbacks for terminals that cannot encode Unicode (e.g. cp1252).
UNICODE_GLYPHS = {
    "error": "✗", "warn": "!", "info": "i", "ok": "✓",
    "dot": "·", "arrow": "›", "none": "—", "more": "…",
}  # fmt: skip
ASCII_GLYPHS = {
    "error": "x", "warn": "!", "info": "i", "ok": "ok",
    "dot": "|", "arrow": ">", "none": "-", "more": "...",
}  # fmt: skip


def to_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def render(report: Report, console: Console) -> None:
    g = _glyphs(console)
    for index, server in enumerate(report.servers):
        if index:
            console.print()
        _render_server(server, console, g)
    if len(report.servers) > 1:
        console.print()
        console.print(_summary(report, g))


def _glyphs(console: Console) -> dict[str, str]:
    encoding = (console.encoding or "").lower().replace("-", "")
    return UNICODE_GLYPHS if encoding.startswith("utf") else ASCII_GLYPHS


def _render_server(server: ServerReport, console: Console, g: dict[str, str]) -> None:
    console.print(_header(server, g))
    if server.error:
        console.print(Text(f"{g['error']} Scan failed: ", style="bold red") + Text(server.error))
        return
    if server.tools:
        console.print(_tools_table(server, g, console.width))
    else:
        console.print("[dim]Server exposes no tools.[/]\n")
    _render_findings(server.findings, console, g)
    console.print(_score_panel(server, g))


def _header(server: ServerReport, g: dict[str, str]) -> Text:
    text = Text()
    text.append("mcpgrader ", style="bold magenta")
    text.append(f"{g['arrow']} ", style="dim")
    text.append(server.server, style="bold")
    if not server.error:
        parts = [f"{len(server.tools)} tools"]
        if server.prompt_count is not None:
            parts.append(f"{server.prompt_count} prompts")
        if server.resource_count is not None:
            parts.append(f"{server.resource_count} resources")
        text.append("  " + f" {g['dot']} ".join(parts), style="dim")
    return text


def _tools_table(server: ServerReport, g: dict[str, str], width: int) -> Table:
    token = server.result("token_cost")
    per_tool: dict[str, int] = token.metrics.get("per_tool", {}) if token else {}
    total: int = token.metrics.get("total_tokens", 0) if token else 0
    issues: dict[str, int] = {}
    for f in server.findings:
        if f.tool:
            issues[f.tool] = issues.get(f.tool, 0) + 1

    table = Table(box=box.SIMPLE_HEAD, show_footer=True, pad_edge=False, expand=False)
    name_width = min(max([len(t.name) for t in server.tools] + [5]), 32)
    table.add_column("Tool", footer="Total", style="bold", no_wrap=True, min_width=name_width)
    table.add_column("~Tokens", footer=f"{total:,}", justify="right", no_wrap=True, min_width=7)
    table.add_column("Issues", justify="right", no_wrap=True, min_width=6)
    # Fixed columns + 3 separators; the description gets whatever is left.
    desc_width = max(12, width - name_width - 7 - 6 - 12)
    table.add_column("Description", style="dim", no_wrap=True, overflow="crop", width=desc_width)

    for tool in sorted(server.tools, key=lambda t: per_tool.get(t.name, 0), reverse=True):
        tokens = per_tool.get(tool.name, 0)
        count = issues.get(tool.name, 0)
        desc = " ".join((tool.description or "").split())
        table.add_row(
            tool.name,
            Text(f"{tokens:,}", style="yellow" if tokens > THRESHOLDS["tool_warn"] else ""),
            Text(str(count), style="yellow") if count else Text(g["ok"], style="green"),
            _clip(desc, desc_width, g) or g["none"],
        )
    return table


def _render_findings(findings: list[Finding], console: Console, g: dict[str, str]) -> None:
    if not findings:
        console.print(Text(f"{g['ok']} No issues found.\n", style="bold green"))
        return
    for severity in Severity:
        group = sorted((f for f in findings if f.severity is severity), key=lambda f: f.tool or "")
        if not group:
            continue
        style = SEVERITY_STYLE[severity]
        label = {"error": "Errors", "warn": "Warnings", "info": "Info"}[severity.value]
        console.print(Text(f"{label} ({len(group)})", style=style))
        grid = Table.grid(padding=(0, 1))
        grid.add_column(width=3, justify="right")
        grid.add_column()
        for f in group:
            body = Text()
            if f.tool:
                body.append(f.tool, style="bold")
                body.append("  ")
            body.append(f.message)
            body.append(f"\nfix: {f.fix}", style="dim")
            grid.add_row(Text(g[severity.value], style=style), body)
        console.print(grid)
        console.print()


def _score_panel(server: ServerReport, g: dict[str, str]) -> Panel:
    style = GRADE_STYLE.get(server.grade, "bold")
    counts = {s: sum(1 for f in server.findings if f.severity is s) for s in Severity}
    dot = f" {g['dot']} "
    body = Group(
        Text.assemble(
            ("Score ", "bold"),
            (f"{server.score}/100", style),
            ("   Grade ", "bold"),
            (server.grade, style),
        ),  # fmt: skip
        Text(
            dot.join(
                [
                    _plural(counts[Severity.ERROR], "error"),
                    _plural(counts[Severity.WARN], "warning"),
                    f"{counts[Severity.INFO]} info",
                ]
            ),
            style="dim",
        ),
    )
    return Panel(body, border_style=style.removeprefix("bold "), expand=False, padding=(0, 2))


def _summary(report: Report, g: dict[str, str]) -> Table:
    table = Table(title="Summary", box=box.SIMPLE_HEAD, title_style="bold", title_justify="left")
    table.add_column("Server", style="bold")
    table.add_column("Tools", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Grade", justify="center")
    for s in report.servers:
        if s.error:
            table.add_row(s.server, g["none"], g["none"], Text("failed", style="bold red"))
        else:
            style = GRADE_STYLE.get(s.grade, "")
            table.add_row(
                s.server, str(len(s.tools)), Text(str(s.score), style=style),
                Text(s.grade, style=style),
            )  # fmt: skip
    return table


def _clip(text: str, n: int, g: dict[str, str]) -> str:
    return text if len(text) <= n else text[: n - len(g["more"])] + g["more"]


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"
