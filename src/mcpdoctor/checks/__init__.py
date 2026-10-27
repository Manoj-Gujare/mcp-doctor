"""Check registry. To add a check: write a module in this package, add it to CHECKS."""

from __future__ import annotations

from collections.abc import Sequence

from mcpdoctor.checks.base import Check
from mcpdoctor.checks.description_lint import DescriptionLintCheck
from mcpdoctor.checks.token_cost import TokenCostCheck
from mcpdoctor.models import CheckResult, ToolDef

CHECKS: list[Check] = [
    TokenCostCheck(),
    DescriptionLintCheck(),
]


def run_checks(
    tools: Sequence[ToolDef], checks: Sequence[Check] | None = None
) -> list[CheckResult]:
    return [check.run(tools) for check in (CHECKS if checks is None else checks)]


__all__ = ["CHECKS", "Check", "run_checks"]
