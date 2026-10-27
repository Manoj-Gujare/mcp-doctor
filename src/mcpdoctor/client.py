"""Connect to an MCP server, fetch its tool definitions, and disconnect cleanly."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from typing import IO, Any

import anyio
import httpx2
from mcp import ClientSession, Implementation, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import PaginatedRequestParams

from mcpdoctor import __version__
from mcpdoctor.config import ServerTarget
from mcpdoctor.models import ToolDef

MAX_PAGES = 100  # guard against servers that return the same cursor forever
CLIENT_INFO = Implementation(name="mcpdoctor", version=__version__)


class ScanError(Exception):
    """A one-line, user-facing reason the server could not be scanned."""


@dataclass
class ServerSnapshot:
    name: str
    tools: list[ToolDef] = field(default_factory=list)
    prompt_count: int | None = None
    resource_count: int | None = None


async def fetch(target: ServerTarget, timeout: float) -> ServerSnapshot:
    """Fetch tools (and prompt/resource counts) from `target`, raising ScanError on failure."""
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as errlog:
        try:
            with anyio.fail_after(timeout):
                return await _fetch(target, errlog)
        except TimeoutError as exc:
            raise ScanError(f"Timed out after {timeout:g}s{_stderr_hint(errlog)}") from exc
        except ScanError:
            raise
        except Exception as exc:  # every failure becomes one readable line
            raise ScanError(_describe(_leaf(exc), target) + _stderr_hint(errlog)) from exc


async def _fetch(target: ServerTarget, errlog: IO[str]) -> ServerSnapshot:
    async with _session(target, errlog) as session:
        init = await session.initialize()
        caps = init.capabilities
        name = target.name
        if target.prefer_server_name and init.server_info.name:
            name = init.server_info.name

        tools = await _paginate(session.list_tools, "tools") if caps.tools else []
        prompts = await _paginate(session.list_prompts, "prompts") if caps.prompts else None
        resources = await _paginate(session.list_resources, "resources") if caps.resources else None

        return ServerSnapshot(
            name=name,
            tools=[
                ToolDef(
                    name=t.name,
                    description=t.description,
                    input_schema=dict(t.input_schema or {}),
                )
                for t in tools
            ],
            prompt_count=None if prompts is None else len(prompts),
            resource_count=None if resources is None else len(resources),
        )


@asynccontextmanager
async def _session(target: ServerTarget, errlog: IO[str]) -> AsyncIterator[ClientSession]:
    async with AsyncExitStack() as stack:
        if target.url:
            http_client = None
            if target.headers:
                http_client = await stack.enter_async_context(
                    httpx2.AsyncClient(headers=target.headers)
                )
            read, write = await stack.enter_async_context(
                streamable_http_client(target.url, http_client=http_client)
            )
        else:
            assert target.command is not None
            params = StdioServerParameters(
                command=target.command,
                args=target.args,
                env=target.env or None,
                cwd=target.cwd,
            )
            read, write = await stack.enter_async_context(stdio_client(params, errlog=errlog))
        session = await stack.enter_async_context(
            ClientSession(read, write, client_info=CLIENT_INFO)
        )
        yield session


async def _paginate(call: Callable[..., Awaitable[Any]], attr: str) -> list[Any]:
    items: list[Any] = []
    cursor: str | None = None
    for _ in range(MAX_PAGES):
        params = PaginatedRequestParams(cursor=cursor) if cursor else None
        page = await call(params=params)
        items.extend(getattr(page, attr))
        cursor = page.next_cursor
        if not cursor:
            break
    return items


def _leaf(exc: BaseException) -> BaseException:
    """Unwrap exception groups raised by task groups to the first real error."""
    while isinstance(getattr(exc, "exceptions", None), (list, tuple)) and exc.exceptions:  # type: ignore[attr-defined]
        exc = exc.exceptions[0]  # type: ignore[attr-defined]
    return exc


def _describe(exc: BaseException, target: ServerTarget) -> str:
    if isinstance(exc, FileNotFoundError):
        return f"Command not found: {target.command} (is it installed and on PATH?)"
    if isinstance(exc, httpx2.ConnectError):
        return f"Could not connect: {exc}"
    if isinstance(exc, httpx2.HTTPStatusError):
        return f"Server returned HTTP {exc.response.status_code}"
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def _stderr_hint(errlog: IO[str]) -> str:
    """Last line the server printed to stderr, which often explains a crash."""
    try:
        errlog.seek(0)
        lines = [ln.strip() for ln in errlog.read().splitlines() if ln.strip()]
    except (OSError, ValueError):
        return ""
    return f" (server stderr: {lines[-1][:200]})" if lines else ""
