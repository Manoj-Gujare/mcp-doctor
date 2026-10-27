from __future__ import annotations

import pytest

from mcpgrader.models import Finding, Severity
from mcpgrader.scoring import DEDUCTIONS, grade, score


def finding(severity: Severity) -> Finding:
    return Finding(check="test", severity=severity, message="m", fix="f")


def test_perfect_score_without_findings() -> None:
    assert score([]) == 100


def test_deductions_by_severity() -> None:
    findings = [finding(Severity.ERROR), finding(Severity.WARN), finding(Severity.INFO)]
    expected = 100 - DEDUCTIONS[Severity.ERROR] - DEDUCTIONS[Severity.WARN]
    assert score(findings) == expected


def test_score_floors_at_zero() -> None:
    assert score([finding(Severity.ERROR)] * 50) == 0


@pytest.mark.parametrize(
    ("value", "letter"),
    [(100, "A"), (90, "A"), (89, "B"), (80, "B"), (79, "C"), (70, "C"), (65, "D"), (59, "F"),
     (0, "F")],
)  # fmt: skip
def test_grades(value: int, letter: str) -> None:
    assert grade(value) == letter
