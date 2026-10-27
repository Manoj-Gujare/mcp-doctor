from __future__ import annotations

import io

from rich.console import Console
from typer.testing import CliRunner

from mcpgrader.banner import banner_lines, banner_text, should_show
from mcpgrader.cli import app


def test_banner_rows_are_aligned_and_fit_80_columns() -> None:
    lines = banner_lines()
    assert len(lines) == 6
    assert len({len(line) for line in lines}) == 1
    assert len(lines[0]) <= 80


def test_banner_text_has_tagline_and_version() -> None:
    plain = banner_text().plain
    assert "lint & score any MCP server" in plain
    assert "v0.1.0" in plain


def test_banner_hidden_when_not_a_terminal() -> None:
    console = Console(file=io.StringIO(), width=120)
    assert not should_show(console)


def test_banner_hidden_on_narrow_or_non_unicode_terminal() -> None:
    narrow = Console(file=io.StringIO(), width=60, force_terminal=True)
    assert not should_show(narrow)
    ascii_only = Console(
        file=io.TextIOWrapper(io.BytesIO(), encoding="cp1252"), width=120, force_terminal=True
    )
    assert not should_show(ascii_only)


def test_bare_command_prints_help() -> None:
    result = CliRunner().invoke(app, [])
    assert result.exit_code == 0
    assert "scan" in result.output
