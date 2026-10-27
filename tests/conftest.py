from __future__ import annotations

from mcp_doctor.models import ToolDef


def tool(name: str, description: str | None = "", **props: dict) -> ToolDef:
    schema = {"type": "object", "properties": props} if props else {"type": "object"}
    return ToolDef(name=name, description=description, input_schema=schema)
