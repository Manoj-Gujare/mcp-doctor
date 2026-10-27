"""The interface every check implements."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from mcpdoctor.models import CheckResult, ToolDef


class Check(Protocol):
    """A check inspects tool definitions and returns findings.

    Checks must be pure: no network, no LLM calls, no global state.
    """

    name: str
    description: str

    def run(self, tools: Sequence[ToolDef]) -> CheckResult: ...
