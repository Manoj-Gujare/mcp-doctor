"""Scan the fixture server and save the terminal output as docs/assets/demo.svg.

Usage: uv run python scripts/render_demo.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import anyio
from rich.console import Console

from mcpgrader.banner import print_banner
from mcpgrader.config import ServerTarget
from mcpgrader.models import Report
from mcpgrader.render import render
from mcpgrader.scanner import scan_target

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "bad_server.py"
OUTPUT = ROOT / "docs" / "assets" / "demo.svg"


def main() -> None:
    target = ServerTarget(
        name="notes-demo", command=sys.executable, args=[str(FIXTURE)], prefer_server_name=True
    )
    report = Report(servers=[anyio.run(scan_target, target, 60.0)])
    console = Console(
        record=True, width=100, file=io.StringIO(), force_terminal=True, color_system="truecolor"
    )
    console.print('[bold green]$[/] mcpgrader scan --stdio "python bad_server.py"\n')
    print_banner(console, force=True)
    render(report, console)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    console.save_svg(str(OUTPUT), title="mcpgrader")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
