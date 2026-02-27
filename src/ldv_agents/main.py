"""Main CLI entry point for ldv-agents."""

import sys
import subprocess
import typer

from ldv_agents.commands import deepagents, init_mcp

app = typer.Typer(
    name="ldv-agents",
    help="LDV Agents - Unified CLI for deep agents with MCP and tool integration",
    rich_markup_mode="rich",
)


@app.command(
    name="deepagents",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def deepagents_cmd(ctx: typer.Context):
    """Run deepagents-cli with MCP support.
    
    All deepagents-cli options and commands are supported.
    Pass any deepagents arguments after this command.
    
    Examples:
        ldv-agents deepagents --mcp-config .ldv-agents.toml
        ldv-agents deepagents list
        ldv-agents deepagents threads list  
        ldv-agents deepagents --sandbox modal
    """
    # Get all arguments after 'deepagents'
    try:
        deepagents_idx = sys.argv.index('deepagents')
        args = sys.argv[deepagents_idx + 1:]
    except ValueError:
        args = []
    
    exit_code = deepagents.run_deepagents_with_mcp(args)
    raise typer.Exit(code=exit_code)


# Register other commands
app.command(name="init-mcp")(init_mcp.init_mcp)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", help="Show version information"
    ),
):
    """LDV Agents - Unified CLI for deep agents with MCP and tool integration.
    
    Run 'ldv-agents deepagents' to use deepagents-cli with MCP support.
    Run 'ldv-agents init-mcp' to generate MCP configuration.
    
    If no command is provided, defaults to 'deepagents' for backward compatibility.
    """
    if version:
        from ldv_agents import __version__
        typer.echo(f"ldv-agents v{__version__} (with MCP support)")
        try:
            subprocess.run(["deepagents", "--version"], check=False)
        except FileNotFoundError:
            typer.echo("Error: deepagents-cli not found. Is it installed?", err=True)
        raise typer.Exit(0)
    
    # If a command was invoked, let it handle
    if ctx.invoked_subcommand is not None:
        return
    
    # No subcommand - default to 'deepagents' for backward compatibility
    # Forward all args to deepagents
    exit_code = deepagents.run_deepagents_with_mcp(sys.argv[1:])
    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
