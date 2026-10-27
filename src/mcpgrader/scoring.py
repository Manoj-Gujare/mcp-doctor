"""Score = 100 minus a fixed deduction per finding, floored at 0, mapped to a letter grade."""

from __future__ import annotations

from collections.abc import Iterable

from mcpgrader.models import Finding, Severity

DEDUCTIONS: dict[Severity, int] = {
    Severity.ERROR: 15,
    Severity.WARN: 5,
    Severity.INFO: 0,
}

# (minimum score, grade), checked top to bottom.
GRADES: list[tuple[int, str]] = [
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (0, "F"),
]


def score(findings: Iterable[Finding]) -> int:
    return max(0, 100 - sum(DEDUCTIONS[f.severity] for f in findings))


def grade(value: int) -> str:
    for minimum, letter in GRADES:
        if value >= minimum:
            return letter
    return "F"
