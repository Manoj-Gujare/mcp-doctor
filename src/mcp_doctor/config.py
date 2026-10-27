"""Scan targets, and parsing of Claude Desktop / Cursor / VS Code style config files."""

from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a config file or target spec cannot be used."""


@dataclass(frozen=True)
class ServerTarget:
    """One MCP server to scan: either a local command (stdio) or a URL (streamable HTTP)."""

    name: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    # True when `name` is only a placeholder and the server's own reported name is better.
    prefer_server_name: bool = False

    @property
    def transport(self) -> str:
        return "http" if self.url else "stdio"

    @classmethod
    def from_command_line(cls, command_line: str) -> ServerTarget:
        parts = split_command(command_line)
        if not parts:
            raise ConfigError('--stdio needs a command, e.g. --stdio "npx -y some-server"')
        return cls(
            name=Path(parts[0]).name, command=parts[0], args=parts[1:], prefer_server_name=True
        )

    @classmethod
    def from_url(cls, url: str) -> ServerTarget:
        if not url.startswith(("http://", "https://")):
            raise ConfigError(f"--url must start with http:// or https:// (got {url!r})")
        return cls(name=url, url=url, prefer_server_name=True)


def split_command(command_line: str) -> list[str]:
    """Split a shell-style command line.

    On Windows, backslashes are kept literally (they are path separators there) and
    surrounding quotes are stripped from each argument.
    """
    try:
        if os.name != "nt":
            return shlex.split(command_line, posix=True)
        return [_unquote(part) for part in shlex.split(command_line, posix=False)]
    except ValueError as exc:
        raise ConfigError(f"Could not parse command {command_line!r}: {exc}") from exc


def load_config(path: Path) -> list[ServerTarget]:
    """Read every server from a JSON config with an `mcpServers` (or VS Code `servers`) block."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Config file is not valid JSON: {path} ({exc.msg}, line {exc.lineno})"
        ) from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"Config file must contain a JSON object: {path}")
    servers = raw.get("mcpServers", raw.get("servers"))
    if not isinstance(servers, dict):
        raise ConfigError(f'No "mcpServers" block found in {path}')

    targets = [_parse_entry(name, entry) for name, entry in servers.items()]
    return [t for t in targets if t is not None]


def _parse_entry(name: str, entry: Any) -> ServerTarget | None:
    if not isinstance(entry, dict):
        raise ConfigError(f'Server "{name}" must be a JSON object')
    if entry.get("disabled") is True:
        return None

    url = entry.get("url") or entry.get("serverUrl")
    if url:
        headers = {k: os.path.expandvars(v) for k, v in _str_dict(entry.get("headers")).items()}
        return ServerTarget(name=name, url=str(url), headers=headers)

    command = entry.get("command")
    if not command:
        raise ConfigError(f'Server "{name}" needs either "command" or "url"')
    args = entry.get("args") or []
    if not isinstance(args, list):
        raise ConfigError(f'Server "{name}": "args" must be a list')
    return ServerTarget(
        name=name,
        command=str(command),
        args=[str(a) for a in args],
        env={k: os.path.expandvars(v) for k, v in _str_dict(entry.get("env")).items()},
        cwd=entry.get("cwd"),
    )


def _unquote(part: str) -> str:
    if len(part) >= 2 and part[0] == part[-1] and part[0] in "\"'":
        return part[1:-1]
    return part


def _str_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items()}
