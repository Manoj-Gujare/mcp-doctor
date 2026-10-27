"""Plain dataclasses shared by the client, checks, scoring, and renderers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


@dataclass(frozen=True)
class ToolDef:
    """A tool as advertised by tools/list."""

    name: str
    description: str | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)

    def as_model_payload(self) -> dict[str, Any]:
        """The shape a client typically sends to a model for this tool."""
        return {
            "name": self.name,
            "description": self.description or "",
            "input_schema": self.input_schema,
        }


@dataclass(frozen=True)
class Finding:
    check: str
    severity: Severity
    message: str
    fix: str
    tool: str | None = None  # None means the finding applies to the whole server


@dataclass
class CheckResult:
    check: str
    findings: list[Finding] = field(default_factory=list)
    # Free-form numbers a check wants to surface (e.g. token counts).
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerReport:
    server: str
    tools: list[ToolDef] = field(default_factory=list)
    prompt_count: int | None = None  # None means the server does not support prompts
    resource_count: int | None = None
    results: list[CheckResult] = field(default_factory=list)
    score: int = 100
    grade: str = "A"
    error: str | None = None  # set when the scan failed (connection, timeout, ...)

    @property
    def findings(self) -> list[Finding]:
        return [f for r in self.results for f in r.findings]

    def result(self, check: str) -> CheckResult | None:
        return next((r for r in self.results if r.check == check), None)


@dataclass
class Report:
    servers: list[ServerReport] = field(default_factory=list)
    tool_version: str = ""

    @property
    def min_score(self) -> int:
        scored = [s.score for s in self.servers if s.error is None]
        return min(scored) if scored else 0

    def to_dict(self) -> dict[str, Any]:
        def convert(obj: Any) -> Any:
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj

        return {
            "tool_version": self.tool_version,
            "servers": [
                {**convert(asdict(s)), "finding_count": len(s.findings)} for s in self.servers
            ],
        }
