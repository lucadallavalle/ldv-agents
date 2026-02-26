"""Initialize MCP configuration."""

from pathlib import Path

import typer
from rich.console import Console

from ldv_agents.mcp_config import MCPConfig

app = typer.Typer()
console = Console()


@app.command()
def init_mcp(
    output: Path = typer.Option(
        Path(".ldv-agents.toml"),
        "--output",
        "-o",
        help="Output path for config file",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing file",
    ),
):
    """Generate an example MCP configuration file.

    Creates a .ldv-agents.toml file with example MCP server configurations.
    """
    if output.exists() and not force:
        console.print(f"[yellow]File already exists:[/yellow] {output}")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    MCPConfig.create_example_config(output)

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Edit the config file and add your MCP server settings")
    console.print("2. Run: [cyan]ldv-agents chat[/cyan]")
    console.print("\n[dim]Learn more about MCP:[/dim] https://modelcontextprotocol.io")
