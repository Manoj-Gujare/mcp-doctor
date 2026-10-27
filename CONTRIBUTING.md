# Contributing to mcpdoctor

Thanks for helping make MCP servers better. Bug reports, false-positive reports, and new checks
are all welcome.

## Development setup

You need [uv](https://docs.astral.sh/uv/) and Python 3.10 or newer.

```bash
git clone https://github.com/Manoj-Gujare/mcp-doctor.git
cd mcp-doctor
uv sync                       # creates .venv with runtime + dev dependencies
uv run pytest                 # run the test suite
uv run ruff check .           # lint
uv run ruff format .          # format
uv run mcpdoctor scan --stdio "python tests/fixtures/bad_server.py"
```

Optional: `uvx pre-commit install` runs ruff on every commit.

## Project layout

```
src/mcpdoctor/
  cli.py          Typer CLI: argument parsing, exit codes
  config.py       ServerTarget and parsing of mcpServers JSON configs
  client.py       connect over stdio / streamable HTTP, list tools, disconnect
  scanner.py      fetch, run checks, score
  models.py       ToolDef, Finding, CheckResult, ServerReport, Report
  scoring.py      deductions and grades
  render.py       Rich terminal output and JSON
  checks/
    __init__.py   CHECKS registry
    base.py       Check protocol
    token_cost.py
    description_lint.py
tests/
  fixtures/bad_server.py   deliberately flawed MCP server used by integration tests
```

## Adding a check

A check is a class with a `name`, a `description`, and a `run(tools)` method that returns a
`CheckResult`. It must be pure: no network calls, no LLM calls, no global state.

1. Create `src/mcpdoctor/checks/my_check.py`:

   ```python
   from collections.abc import Sequence

   from mcpdoctor.models import CheckResult, Finding, Severity, ToolDef


   class MyCheck:
       name = "my_check"
       description = "One line describing what this check looks for"

       def run(self, tools: Sequence[ToolDef]) -> CheckResult:
           findings = [
               Finding(
                   check=self.name,
                   severity=Severity.WARN,
                   tool=tool.name,
                   message="What is wrong, specifically.",
                   fix="What to change, concretely.",
               )
               for tool in tools
               if ...
           ]
           return CheckResult(check=self.name, findings=findings)
   ```

2. Register it by adding `MyCheck()` to `CHECKS` in `src/mcpdoctor/checks/__init__.py`.
3. Add `tests/test_my_check.py` with cases that should and should not fire.
4. If it changes what the fixture server reports, update `tests/test_integration.py`.
5. Document it in the README's **Checks** section.

Guidelines for good findings:

- Every finding needs a `fix` a server author can act on without reading the source.
- Put thresholds in a module-level dict so they are easy to find and tune.
- Prefer one finding per problem per tool. Do not report the same root cause twice.
- Use `error` only for problems that clearly break model behavior; most things are `warn`.

## Pull requests

- Branch from `main` and keep each PR focused on one change.
- Use clear commit messages in the imperative mood ("Add schema check", not "added stuff").
- Make sure `ruff check`, `ruff format --check`, and `pytest` pass. CI runs them on Linux,
  macOS, and Windows for Python 3.10 to 3.13.
- Add a line to `CHANGELOG.md` under **Unreleased** for user-facing changes.

## Releasing (maintainers)

1. Bump `version` in `pyproject.toml` and `src/mcpdoctor/__init__.py`.
2. Move **Unreleased** entries in `CHANGELOG.md` under the new version.
3. Tag and push: `git tag v0.2.0 && git push origin v0.2.0`. The release workflow builds and
   publishes to PyPI via trusted publishing and creates a GitHub release.

By contributing you agree that your work is released under the [MIT License](LICENSE) and that
you will follow the [Code of Conduct](CODE_OF_CONDUCT.md).
