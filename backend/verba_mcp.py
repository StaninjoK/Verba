"""Launcher for the Verba MCP server (lets Claude use Verba as a tool). See docs/CLAUDE_TOOL.md."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verba.mcp_server import main  # noqa: E402

main()
