"""MCP server configuration and management."""

import json
from pathlib import Path
from typing import Any

import tomli
from rich.console import Console

console = Console()


class MCPConfig:
    """Load and manage MCP server configurations."""

    def __init__(self, config_path: Path | None = None):
        """Initialize MCP config.

        Args:
            config_path: Path to config file. If None, searches for .ldv-agents.toml
                        in current directory and parent directories.
        """
        self.config_path = config_path or self._find_config()
        self.servers = self._load_config()

    def _find_config(self) -> Path | None:
        """Search for .ldv-agents.toml in current and parent directories."""
        current = Path.cwd()

        # Search up to 5 levels
        for _ in range(5):
            config_file = current / ".ldv-agents.toml"
            if config_file.exists():
                return config_file

            # Move to parent
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent

        return None

    def _load_config(self) -> dict[str, dict[str, Any]]:
        """Load MCP server configs from TOML file."""
        if not self.config_path or not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, "rb") as f:
                data = tomli.load(f)
                return data.get("mcp", {}).get("servers", {})
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load MCP config: {e}[/yellow]")
            return {}

    def get_servers(self) -> dict[str, dict[str, Any]]:
        """Get all configured MCP servers."""
        return self.servers

    def has_servers(self) -> bool:
        """Check if any MCP servers are configured."""
        return bool(self.servers)

    @staticmethod
    def create_example_config(path: Path) -> None:
        """Create an example .ldv-agents.toml configuration file."""
        example = """# LDV Agents Configuration

# LangChain Docs Search (HTTP-based, no setup needed!)
[mcp.servers.langchain-docs]
transport = "http"
url = "https://docs.langchain.com/mcp"

# More examples below (uncomment to use):

# Filesystem access (requires Node.js)
# [mcp.servers.filesystem]
# transport = "stdio"
# command = "npx"
# args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"]

# GitHub integration (requires Node.js + token)
# [mcp.servers.github]
# transport = "stdio"
# command = "npx"
# args = ["-y", "@modelcontextprotocol/server-github"]
# env = { GITHUB_PERSONAL_ACCESS_TOKEN = "your_token_here" }

# PostgreSQL database (requires Node.js)
# [mcp.servers.postgres]
# transport = "stdio"
# command = "npx"
# args = ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]

# Custom HTTP server
# [mcp.servers.custom]
# transport = "http"
# url = "http://localhost:8000/mcp"
# headers = { Authorization = "Bearer your_token" }
"""
        path.write_text(example)
        console.print(f"[green]✓[/green] Created example config at [cyan]{path}[/cyan]")


def load_mcp_config(config_path: Path | None = None) -> MCPConfig:
    """Load MCP configuration from file.

    Args:
        config_path: Optional path to config file. If None, searches current directory.

    Returns:
        MCPConfig instance with loaded server configurations.
    """
    return MCPConfig(config_path)
