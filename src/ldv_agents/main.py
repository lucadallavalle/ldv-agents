import typer

# Import subcommands
from ldv_agents.commands import chat, init_mcp, skills

app = typer.Typer(
    name="ldv-agents",
    help="LDV Agents CLI tool",
    rich_markup_mode="rich",  # Requires rich dependency
)

# Register subcommands
app.command(name="chat")(chat.chat)
app.command(name="init-mcp")(init_mcp.init_mcp)

# Register skills subcommands
app.add_typer(skills.app, name="skills", help="Manage skills")


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """Global CLI options"""
    if verbose:
        typer.echo("Verbose mode enabled")


if __name__ == "__main__":
    app()
