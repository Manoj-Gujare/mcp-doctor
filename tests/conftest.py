from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mcpdoctor.models import ToolDef

FIXTURE_SERVER = Path(__file__).parent / "fixtures" / "bad_server.py"


def tool(name: str, description: str | None = "", **props: dict) -> ToolDef:
    schema = {"type": "object", "properties": props} if props else {"type": "object"}
    return ToolDef(name=name, description=description, input_schema=schema)


@pytest.fixture
def fixture_command() -> list[str]:
    return [sys.executable, str(FIXTURE_SERVER)]
