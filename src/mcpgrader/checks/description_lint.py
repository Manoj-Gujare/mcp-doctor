"""Rule-based lint for tool descriptions and parameter docs. No LLM calls."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from itertools import combinations
from typing import Any

from mcpgrader.models import CheckResult, Finding, Severity, ToolDef

LIMITS: dict[str, float] = {
    "min_chars": 20,
    "max_chars": 1_000,
    "duplicate_jaccard": 0.7,  # word-set similarity at or above this flags a pair
    "duplicate_min_words": 3,  # ignore pairs where either side has fewer content words
}

STOPWORDS = frozenset(
    "a an the and or of to for in on with by from this that it its is are be as at "
    "into using use uses used via can will should may".split()
)

# Words that carry no information about what a tool does.
VAGUE_WORDS = frozenset(
    "does do doing stuff things thing helper helpers helps help utility utilities util utils "
    "misc miscellaneous various general generic tool tools function functions handler handles "
    "handle manager manages manage processor process processes operation operations action "
    "actions something some etc todo tbd placeholder data info item items".split()
)

VAGUE_PHRASES = (
    "does stuff",
    "does things",
    "does something",
    "helper function",
    "utility function",
    "todo",
    "tbd",
    "fill this in",
    "no description",
)

_WORD_RE = re.compile(r"[a-z0-9]+")
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def words(text: str) -> list[str]:
    return _WORD_RE.findall(_CAMEL_RE.sub(" ", text).lower())


def content_words(text: str) -> set[str]:
    return {w for w in words(text) if w not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_vague(name: str, description: str) -> str | None:
    """Return the reason a description is vague, or None if it is fine."""
    lowered = description.lower().strip()
    for phrase in VAGUE_PHRASES:
        if phrase in lowered:
            return f'contains the vague phrase "{phrase}"'
    desc_words = content_words(description)
    if not desc_words:
        return "has no meaningful words"
    name_words = content_words(name)
    if desc_words <= VAGUE_WORDS | name_words:
        if desc_words & name_words:
            return "only restates the tool name"
        return "uses only generic words"
    return None


def _undocumented_params(schema: dict[str, Any], prefix: str = "") -> Iterable[str]:
    props = schema.get("properties")
    if not isinstance(props, dict):
        return
    for pname, pschema in props.items():
        if not isinstance(pschema, dict):
            continue
        path = f"{prefix}{pname}"
        desc = pschema.get("description")
        if not (isinstance(desc, str) and desc.strip()):
            yield path
        if pschema.get("type") == "object":
            yield from _undocumented_params(pschema, prefix=f"{path}.")


class DescriptionLintCheck:
    name = "description_lint"
    description = "Tool and parameter descriptions are present, specific, and distinct"

    def __init__(self, limits: dict[str, float] | None = None) -> None:
        self.limits = {**LIMITS, **(limits or {})}

    def run(self, tools: Sequence[ToolDef]) -> CheckResult:
        findings: list[Finding] = []
        for tool in tools:
            findings.extend(self._lint_tool(tool))
        findings.extend(self._duplicates(tools))
        return CheckResult(check=self.name, findings=findings)

    def _finding(self, severity: Severity, tool: str, message: str, fix: str) -> Finding:
        return Finding(check=self.name, severity=severity, tool=tool, message=message, fix=fix)

    def _lint_tool(self, tool: ToolDef) -> Iterable[Finding]:
        desc = (tool.description or "").strip()
        lim = self.limits

        if not desc:
            yield self._finding(
                Severity.ERROR,
                tool.name,
                "Missing tool description.",
                "Add a description saying what the tool does, when to use it, and what it returns.",
            )
        else:
            reason = is_vague(tool.name, desc)
            if reason:
                yield self._finding(
                    Severity.WARN,
                    tool.name,
                    f'Vague description ("{_clip(desc)}") {reason}.',
                    "Say concretely what the tool acts on, what it returns, "
                    "and when a model should pick it over similar tools.",
                )
            elif len(desc) < lim["min_chars"]:
                yield self._finding(
                    Severity.WARN,
                    tool.name,
                    f"Description is only {len(desc)} chars (min {int(lim['min_chars'])}).",
                    "Expand it to one or two sentences covering purpose, inputs, and output.",
                )
            if len(desc) > lim["max_chars"]:
                yield self._finding(
                    Severity.WARN,
                    tool.name,
                    f"Description is {len(desc):,} chars (max {int(lim['max_chars']):,}).",
                    "Cut it to the essentials; move examples and edge cases into "
                    "parameter descriptions or external docs.",
                )

        missing = list(_undocumented_params(tool.input_schema))
        if missing:
            shown = ", ".join(missing[:5]) + (
                f" and {len(missing) - 5} more" if len(missing) > 5 else ""
            )
            yield self._finding(
                Severity.WARN,
                tool.name,
                f"{len(missing)} parameter(s) without a description: {shown}.",
                'Add a "description" to each parameter in inputSchema '
                "(format, units, allowed values).",
            )

    def _duplicates(self, tools: Sequence[ToolDef]) -> Iterable[Finding]:
        bags = {
            t.name: content_words(t.description or "")
            for t in tools
            if len(content_words(t.description or "")) >= self.limits["duplicate_min_words"]
        }
        for (a, wa), (b, wb) in combinations(bags.items(), 2):
            sim = jaccard(wa, wb)
            if sim >= self.limits["duplicate_jaccard"]:
                yield self._finding(
                    Severity.WARN,
                    a,
                    f'Description is {sim:.0%} similar to "{b}"; '
                    "a model may not know which to call.",
                    f'Merge "{a}" and "{b}", or rewrite both descriptions to state '
                    "how they differ.",
                )


def _clip(text: str, n: int = 40) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"
