"""Big gradient "MCPGRADER" banner for interactive terminals."""

from __future__ import annotations

from rich.color import Color
from rich.console import Console
from rich.style import Style
from rich.text import Text

from mcpgrader import __version__

TAGLINE = "lint & score any MCP server"

# "ANSI Shadow" style letters, 6 rows each.
LETTERS: dict[str, list[str]] = {
    "M": [
        "███╗   ███╗",
        "████╗ ████║",
        "██╔████╔██║",
        "██║╚██╔╝██║",
        "██║ ╚═╝ ██║",
        "╚═╝     ╚═╝",
    ],
    "C": [
        " ██████╗",
        "██╔════╝",
        "██║     ",
        "██║     ",
        "╚██████╗",
        " ╚═════╝",
    ],
    "P": [
        "██████╗ ",
        "██╔══██╗",
        "██████╔╝",
        "██╔═══╝ ",
        "██║     ",
        "╚═╝     ",
    ],
    "D": [
        "██████╗ ",
        "██╔══██╗",
        "██║  ██║",
        "██║  ██║",
        "██████╔╝",
        "╚═════╝ ",
    ],
    "G": [
        " ██████╗ ",
        "██╔════╝ ",
        "██║  ███╗",
        "██║   ██║",
        "╚██████╔╝",
        " ╚═════╝ ",
    ],
    "A": [
        " █████╗ ",
        "██╔══██╗",
        "███████║",
        "██╔══██║",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
    "E": [
        "███████╗",
        "██╔════╝",
        "█████╗  ",
        "██╔══╝  ",
        "███████╗",
        "╚══════╝",
    ],
    "R": [
        "██████╗ ",
        "██╔══██╗",
        "██████╔╝",
        "██╔══██╗",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
}

GRADIENT_START = (0, 200, 255)  # cyan
GRADIENT_END = (200, 80, 255)  # violet


def banner_lines(word: str = "MCPGRADER") -> list[str]:
    return ["".join(LETTERS[ch][row] for ch in word) for row in range(6)]


def banner_text() -> Text:
    lines = banner_lines()
    width = max(len(line) for line in lines)
    text = Text()
    for line in lines:
        for col, char in enumerate(line):
            text.append(char, style=_gradient(col / max(width - 1, 1)))
        text.append("\n")
    gap = max(1, width - len(TAGLINE) - len(__version__) - 3)
    text.append(f"  {TAGLINE}", style="bold")
    text.append(" " * gap + f"v{__version__}", style="dim")
    return text


def should_show(console: Console) -> bool:
    """Only for a real, wide-enough, Unicode-capable terminal."""
    encoding = (console.encoding or "").lower().replace("-", "")
    width = max(len(line) for line in banner_lines())
    return console.is_terminal and encoding.startswith("utf") and console.width >= width


def print_banner(console: Console, force: bool = False) -> None:
    if force or should_show(console):
        console.print(banner_text())
        console.print()


def _gradient(t: float) -> Style:
    r, g, b = (round(a + (z - a) * t) for a, z in zip(GRADIENT_START, GRADIENT_END, strict=True))
    return Style(color=Color.from_rgb(r, g, b), bold=True)
