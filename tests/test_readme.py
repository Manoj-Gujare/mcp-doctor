"""The README is also the PyPI page, where repo-relative links and images break."""

from __future__ import annotations

import re
from pathlib import Path

README = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")


def test_readme_links_and_images_are_absolute() -> None:
    targets = re.findall(r"\]\(([^)]+)\)", README) + re.findall(r'(?:src|href)="([^"]+)"', README)
    relative = [t for t in targets if not t.startswith(("http://", "https://", "#", "mailto:"))]
    assert relative == []
