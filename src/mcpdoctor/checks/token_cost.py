"""Approximate how many context tokens a server's tool definitions cost."""

from __future__ import annotations

import json
from collections.abc import Sequence
from functools import lru_cache

import tiktoken

from mcpdoctor.models import CheckResult, Finding, Severity, ToolDef

THRESHOLDS: dict[str, int] = {
    "total_warn": 2_000,
    "total_error": 5_000,
    "tool_warn": 500,
    "top_n": 5,
}

ENCODING = "cl100k_base"


@lru_cache(maxsize=1)
def _encoder() -> tiktoken.Encoding:
    return tiktoken.get_encoding(ENCODING)


def count_tool_tokens(tool: ToolDef) -> int:
    payload = json.dumps(tool.as_model_payload(), separators=(",", ":"), ensure_ascii=False)
    return len(_encoder().encode(payload))


class TokenCostCheck:
    name = "token_cost"
    description = f"Approximate token cost of tool definitions ({ENCODING})"

    def __init__(self, thresholds: dict[str, int] | None = None) -> None:
        self.thresholds = {**THRESHOLDS, **(thresholds or {})}

    def run(self, tools: Sequence[ToolDef]) -> CheckResult:
        t = self.thresholds
        per_tool = {tool.name: count_tool_tokens(tool) for tool in tools}
        total = sum(per_tool.values())
        heaviest = sorted(per_tool.items(), key=lambda kv: kv[1], reverse=True)[: t["top_n"]]

        findings: list[Finding] = []
        if total > t["total_error"]:
            severity: Severity | None = Severity.ERROR
        elif total > t["total_warn"]:
            severity = Severity.WARN
        else:
            severity = None
        if severity is not None:
            top = ", ".join(name for name, _ in heaviest[:3])
            findings.append(
                Finding(
                    check=self.name,
                    severity=severity,
                    message=f"Tool definitions cost ~{total:,} tokens in every request "
                    f"(warn > {t['total_warn']:,}, error > {t['total_error']:,}).",
                    fix=f"Trim the heaviest tools first ({top}), drop rarely used tools, "
                    "or split the server into smaller focused servers.",
                )
            )

        for name, tokens in per_tool.items():
            if tokens > t["tool_warn"]:
                findings.append(
                    Finding(
                        check=self.name,
                        severity=Severity.WARN,
                        tool=name,
                        message=f"Definition costs ~{tokens:,} tokens (limit {t['tool_warn']:,}).",
                        fix="Shorten the description, remove schema fields that are not needed, "
                        "and move long enum lists or examples into documentation.",
                    )
                )

        return CheckResult(
            check=self.name,
            findings=findings,
            metrics={
                "encoding": ENCODING,
                "approximate": True,
                "total_tokens": total,
                "per_tool": per_tool,
                "heaviest": [{"tool": n, "tokens": c} for n, c in heaviest],
            },
        )
