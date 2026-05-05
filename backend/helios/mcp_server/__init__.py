"""Pattern C — MCP server.

Exposes Helios as Model Context Protocol tools that any MCP-aware agent
(Claude Code, Cursor, Cline, etc.) can call. The server delegates to a
running Helios HTTP backend via the agent.HeliosClient.

Run with:
    helios-mcp                  # stdio transport (default)
"""
