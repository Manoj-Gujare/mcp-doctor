"""Scan the fixture server and save the terminal output as docs/assets/demo.svg.

Usage: uv run python scripts/render_demo.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import anyio
from rich.console import Console

from mcp_doctor.config import ServerTarget
from mcp_doctor.models import Report
from mcp_doctor.render import render
from mcp_doctor.scanner import scan_target

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
    console.print('[bold green]$[/] mcpdoctor scan --stdio "python bad_server.py"\n')
    render(report, console)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    console.save_svg(str(OUTPUT), title="mcp-doctor")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
