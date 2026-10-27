from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcpgrader.config import ConfigError, ServerTarget, load_config, split_command


def write(tmp_path: Path, data: object) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_loads_stdio_and_http_servers(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        {
            "mcpServers": {
                "fs": {"command": "npx", "args": ["-y", "server-fs", "/tmp"], "env": {"A": "1"}},
                "remote": {"url": "https://example.com/mcp", "headers": {"X-Key": "k"}},
                "off": {"command": "nope", "disabled": True},
            }
        },
    )
    fs, remote = load_config(path)

    assert fs == ServerTarget(name="fs", command="npx", args=["-y", "server-fs", "/tmp"],
                              env={"A": "1"})  # fmt: skip
    assert fs.transport == "stdio"
    assert remote.url == "https://example.com/mcp"
    assert remote.headers == {"X-Key": "k"}
    assert remote.transport == "http"


def test_vscode_servers_key(tmp_path: Path) -> None:
    targets = load_config(write(tmp_path, {"servers": {"a": {"command": "x"}}}))
    assert [t.name for t in targets] == ["a"]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({}, "mcpServers"),
        ([], "JSON object"),
        ({"mcpServers": {"a": {}}}, "command"),
        ({"mcpServers": {"a": {"command": "x", "args": "nope"}}}, "args"),
    ],
)
def test_invalid_configs(tmp_path: Path, data: object, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, data))


def test_missing_and_malformed_files(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config(bad)


def test_command_line_target() -> None:
    target = ServerTarget.from_command_line('npx -y "@scope/server" /tmp')
    assert target.command == "npx"
    assert target.args == ["-y", "@scope/server", "/tmp"]
    assert target.prefer_server_name


def test_url_target_requires_http_scheme() -> None:
    with pytest.raises(ConfigError):
        ServerTarget.from_url("example.com/mcp")
    assert ServerTarget.from_url("http://localhost:8000/mcp").transport == "http"


def test_empty_command_rejected() -> None:
    with pytest.raises(ConfigError):
        ServerTarget.from_command_line("   ")


def test_split_command_keeps_quoted_args() -> None:
    assert split_command('python "my server.py" --flag') == ["python", "my server.py", "--flag"]


def test_env_vars_expand_in_env_and_headers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCPD_TOKEN", "secret")
    path = write(
        tmp_path,
        {
            "mcpServers": {
                "a": {"command": "x", "env": {"T": "${MCPD_TOKEN}"}},
                "b": {"url": "https://x/mcp", "headers": {"Authorization": "Bearer ${MCPD_TOKEN}"}},
            }
        },
    )
    a, b = load_config(path)
    assert a.env == {"T": "secret"}
    assert b.headers == {"Authorization": "Bearer secret"}


def test_example_config_parses() -> None:
    example = Path(__file__).parent.parent / "examples" / "mcp.json"
    assert [t.name for t in load_config(example)] == ["filesystem", "memory"]
