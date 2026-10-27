# Security policy

## Supported versions

Security fixes are made for the latest released version.

## Reporting a vulnerability

Please do not open a public issue for security problems. Report them privately through
[GitHub security advisories](https://github.com/Manoj-Gujare/mcp-doctor/security/advisories/new).

Include what you found, how to reproduce it, and the impact you expect. You should get a reply
within a few days. Once a fix is released, the advisory is published with credit to you unless
you prefer otherwise.

## Scope notes

`mcpdoctor` starts the server command you give it (`--stdio` or `command` in a config file) with
your user's permissions, just like an MCP client does. Only scan servers you trust to run on your
machine. It never calls tools on the server; it only lists them.
