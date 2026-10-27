"""Command-line interface."""

from __future__ import annotations

import errno
import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from mcpdoctor import __version__
from mcpdoctor.config import ConfigError, ServerTarget, load_config
from mcpdoctor.render import render, to_json
from mcpdoctor.scanner import scan as run_scan

# Exit codes
EXIT_OK = 0
EXIT_BELOW_THRESHOLD = 1
EXIT_SCAN_FAILED = 2

app = typer.Typer(
    name="mcpdoctor",
    help="Audit MCP servers for token bloat and tool-description quality.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,  # locals can hold env vars and tokens
)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"mcpdoctor {__version__}")
        raise typer.Exit()


def _ensure_safe_streams() -> None:
    """Never crash on characters the terminal encoding cannot represent."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def _silence_stdout() -> None:
    """Point stdout at devnull so the interpreter's final flush cannot fail again."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", callback=_version, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Audit MCP servers for token bloat and tool-description quality."""


@app.command()
def scan(
    stdio: Annotated[
        str | None,
        typer.Option(
            "--stdio",
            metavar="COMMAND",
            help='Launch a local server, e.g. --stdio "npx -y @modelcontextprotocol/server-memory"',
        ),
    ] = None,
    url: Annotated[
        str | None,
        typer.Option("--url", metavar="URL", help="Connect to a streamable HTTP server."),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            metavar="PATH",
            help="Scan every server in a Claude Desktop / Cursor style JSON config.",
        ),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print the full report as JSON.")
    ] = False,
    fail_under: Annotated[
        int | None,
        typer.Option(
            "--fail-under",
            min=0,
            max=100,
            metavar="SCORE",
            help="Exit with code 1 if any server scores below SCORE.",
        ),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", min=1, metavar="SECONDS", help="Per-server timeout."),
    ] = 30.0,
) -> None:
    """Connect to MCP server(s), audit their tools, and print a score with fixes.

    Exit codes: 0 ok, 1 score below --fail-under, 2 a server could not be scanned or bad input.
    """
    _ensure_safe_streams()
    err = Console(stderr=True)
    chosen = [opt for opt in (stdio, url, config) if opt is not None]
    if len(chosen) != 1:
        err.print("[bold red]error:[/] pass exactly one of --stdio, --url, or --config")
        raise typer.Exit(EXIT_SCAN_FAILED)

    try:
        if stdio is not None:
            targets = [ServerTarget.from_command_line(stdio)]
        elif url is not None:
            targets = [ServerTarget.from_url(url)]
        else:
            assert config is not None
            targets = load_config(config)
    except ConfigError as exc:
        err.print(f"[bold red]error:[/] {exc}")
        raise typer.Exit(EXIT_SCAN_FAILED) from None

    if not targets:
        err.print("[bold red]error:[/] no enabled servers found in config")
        raise typer.Exit(EXIT_SCAN_FAILED)

    if json_output:
        report = run_scan(targets, timeout)
    else:
        console = Console()
        with console.status(f"Scanning {len(targets)} server(s)...", spinner="dots"):
            report = run_scan(targets, timeout)

    try:
        if json_output:
            sys.stdout.write(to_json(report) + "\n")
            sys.stdout.flush()
        else:
            render(report, console)
    except OSError as exc:
        # Reader went away (e.g. `| head`). Windows reports this as EINVAL, not EPIPE.
        if not isinstance(exc, BrokenPipeError) and exc.errno != errno.EINVAL:
            raise
        _silence_stdout()

    if any(s.error for s in report.servers):
        raise typer.Exit(EXIT_SCAN_FAILED)
    if fail_under is not None and report.min_score < fail_under:
        if not json_output:
            err.print(
                f"[bold red]error:[/] score {report.min_score} is below --fail-under {fail_under}"
            )
        raise typer.Exit(EXIT_BELOW_THRESHOLD)
    raise typer.Exit(EXIT_OK)
