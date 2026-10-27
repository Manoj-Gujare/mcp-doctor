# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

### Added

- `mcp-doctor scan` with `--stdio`, `--url` (streamable HTTP), and `--config`
  (Claude Desktop / Cursor / VS Code `mcpServers` JSON).
- `token_cost` check: approximate per-tool and total token cost (tiktoken `cl100k_base`),
  top five heaviest tools.
- `description_lint` check: missing, short, long, and vague descriptions, undocumented
  parameters, and near-duplicate tools.
- Score from 0 to 100 with an A to F grade.
- Rich terminal output and `--json` output.
- `--fail-under` and `--timeout` for CI use.

[Unreleased]: https://github.com/Manoj-Gujare/mcp-doctor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Manoj-Gujare/mcp-doctor/releases/tag/v0.1.0
