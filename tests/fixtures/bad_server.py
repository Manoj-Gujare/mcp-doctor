"""A deliberately flawed MCP server used by the integration tests and README demo.

Run it directly with: python tests/fixtures/bad_server.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

server = MCPServer("notes-demo")

Region = Literal[
    "us-east-1", "us-east-2", "us-west-1", "us-west-2", "eu-west-1", "eu-west-2",
    "eu-west-3", "eu-central-1", "eu-north-1", "ap-south-1", "ap-southeast-1",
    "ap-southeast-2", "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "sa-east-1", "ca-central-1", "me-south-1", "af-south-1",
]  # fmt: skip


# Good: specific description, every parameter documented.
@server.tool(
    description=(
        "Get the current weather for a city. Returns temperature, conditions, and "
        "wind speed. Use this for present conditions, not forecasts."
    )
)
def get_weather(
    city: Annotated[str, Field(description="City name, e.g. 'Lisbon' or 'Austin, TX'.")],
    units: Annotated[
        Literal["metric", "imperial"], Field(description="Unit system for the result.")
    ] = "metric",
) -> str:
    return f"Sunny in {city}"


# Bad: empty description, undocumented parameter.
@server.tool(description="")
def run(cmd: str) -> str:
    return cmd


# Bad: vague description.
@server.tool(description="Helper utility.")
def helper(x: str) -> str:
    return x


# Bad: near-duplicate pair.
@server.tool(description="Search the user's notes by keyword and return matching note titles.")
def search_notes(query: Annotated[str, Field(description="Keyword to search for.")]) -> list[str]:
    return []


@server.tool(description="Find the user's notes by keyword and return the matching note titles.")
def find_notes(query: Annotated[str, Field(description="Keyword to look for.")]) -> list[str]:
    return []


# Bad: huge schema with no parameter descriptions.
@server.tool(description="Import many records from a cloud bucket into the notes database.")
def bulk_import(
    source_region: Region,
    target_region: Region,
    backup_region: Region,
    bucket: str,
    prefix: str = "",
    file_format: Literal["csv", "json", "jsonl", "parquet", "avro", "orc", "xml", "yaml"] = "csv",
    compression: Literal["none", "gzip", "bzip2", "zstd", "lz4", "snappy", "brotli"] = "none",
    on_conflict: Literal["skip", "overwrite", "merge", "fail", "rename"] = "skip",
    batch_size: int = 500,
    max_retries: int = 3,
    dry_run: bool = False,
    notify_email: str | None = None,
) -> str:
    return "ok"


if __name__ == "__main__":
    server.run()
