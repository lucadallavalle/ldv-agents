import asyncio
import json
from pathlib import Path
from typing import Any

import typer
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner
from rich.tree import Tree
from rich.markdown import Markdown

from ldv_agents.mcp_config import load_mcp_config

app = typer.Typer()
console = Console()


def format_tool_args(args: dict[str, Any]) -> str:
    """Format tool arguments for display."""
    if not args:
        return "[dim](no arguments)[/dim]"

    # Try to format as JSON with syntax highlighting
    try:
        formatted = json.dumps(args, indent=2)
        # Truncate very long arguments
        if len(formatted) > 500:
            formatted = formatted[:500] + "\n  ..."
        return formatted
    except:
        return str(args)


def format_tool_result(result: Any, max_lines: int = 10) -> str:
    """Format tool result for display, truncating if too long."""
    result_str = str(result)
    lines = result_str.split("\n")

    if len(lines) > max_lines:
        preview = "\n".join(lines[:max_lines])
        return f"{preview}\n[dim]... ({len(lines) - max_lines} more lines)[/dim]"

    return result_str


async def run_chat_async(
    working_dir: Path,
    model: str,
    thread_id: str,
    auto_approve: bool,
    mcp_config_path: Path | None = None,
    recursion_limit: int = 1000,
):
    """Async chat loop with streaming support."""
    # Set up persistent checkpointer for thread resumption
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    db_dir = Path.home() / ".ldv-agents"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "sessions.db"

    # Load MCP configuration
    mcp_config = load_mcp_config(mcp_config_path)
    mcp_tools = []
    mcp_client = None

    if mcp_config.has_servers():
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            mcp_client = MultiServerMCPClient(mcp_config.get_servers())
            mcp_tools = await mcp_client.get_tools()

            console.print(
                f"[green]✓[/green] Loaded {len(mcp_tools)} MCP tools from {len(mcp_config.get_servers())} server(s)"
            )
        except ImportError:
            console.print(
                "[yellow]⚠ MCP support requires: pip install langchain-mcp-adapters[/yellow]"
            )
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to load MCP tools: {e}[/yellow]")

    # Welcome banner
    banner_text = (
        f"[bold cyan]LDV Agents[/bold cyan]\n\n"
        f"[dim]Directory:[/dim] {working_dir}\n"
        f"[dim]Model:[/dim] {model}\n"
        f"[dim]Thread:[/dim] {thread_id}"
    )

    if mcp_tools:
        banner_text += f"\n[dim]MCP Tools:[/dim] {len(mcp_tools)} loaded"

    console.print(Panel.fit(banner_text, border_style="cyan"))
    console.print("[dim]Type 'exit' or 'quit' to end the session[/dim]\n")

    # Create backend with filesystem access
    backend = FilesystemBackend(root_dir=str(working_dir))

    # Create checkpointer for persistent threads
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        # Create deep agent with MCP tools
        agent = create_deep_agent(
            model=model,
            backend=backend,
            tools=mcp_tools if mcp_tools else None,
            checkpointer=checkpointer,
        )

        config = {
            "configurable": {
                "thread_id": thread_id,
            },
            "recursion_limit": recursion_limit,
        }

        # Add auto-approve if needed
        if auto_approve:
            config["configurable"]["require_approval"] = False

        while True:
            try:
                # Get user input with styled prompt
                console.print()
                user_input = console.input("[bold blue]❯[/bold blue] ")

                if not user_input.strip():
                    continue

                if user_input.lower() in ["exit", "quit", "/exit", "/quit"]:
                    console.print("\n[cyan]Goodbye![/cyan]")
                    break

                console.print()

                # Track tool calls for better display
                active_tools = {}
                response_started = False

                # Stream the response
                async for event in agent.astream_events(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config,
                    version="v2",
                ):
                    # Handle streaming tokens from the model
                    if event["event"] == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        if hasattr(chunk, "content"):
                            # Start response section if not already started
                            if not response_started:
                                response_started = True

                            # Handle both string content and list of content blocks
                            content = chunk.content
                            if isinstance(content, str) and content:
                                console.print(content, end="", markup=False)
                            elif isinstance(content, list):
                                for block in content:
                                    if (
                                        isinstance(block, dict)
                                        and block.get("type") == "text"
                                    ):
                                        text = block.get("text", "")
                                        if text:
                                            console.print(text, end="", markup=False)

                    # Handle tool calls with rich panels
                    elif event["event"] == "on_tool_start":
                        tool_name = event["name"]
                        tool_input = event["data"].get("input", {})
                        run_id = event.get("run_id", "")

                        # Store tool info for later
                        active_tools[run_id] = {
                            "name": tool_name,
                            "input": tool_input,
                        }

                        # Print tool call with arguments
                        if response_started:
                            console.print("\n")
                            response_started = False

                        args_display = format_tool_args(tool_input)

                        # Create a nice panel for the tool call
                        tool_panel = Panel(
                            Syntax(
                                args_display,
                                "json",
                                theme="monokai",
                                line_numbers=False,
                            ),
                            title=f"[bold yellow]🔧 {tool_name}[/bold yellow]",
                            border_style="yellow",
                            padding=(0, 1),
                        )
                        console.print(tool_panel)

                    elif event["event"] == "on_tool_end":
                        run_id = event.get("run_id", "")
                        output = event["data"].get("output", "")

                        if run_id in active_tools:
                            tool_name = active_tools[run_id]["name"]

                            # Format and display result
                            result_display = format_tool_result(output)

                            result_panel = Panel(
                                f"[dim]{result_display}[/dim]",
                                title=f"[bold green]✓ {tool_name} completed[/bold green]",
                                border_style="green",
                                padding=(0, 1),
                            )
                            console.print(result_panel)
                            console.print()

                            # Clean up
                            del active_tools[run_id]

                if response_started:
                    console.print()  # New line after response

            except KeyboardInterrupt:
                console.print(
                    "\n\n[yellow]⚠ Interrupted. Type 'exit' to quit.[/yellow]"
                )
                continue
            except Exception as e:
                error_msg = str(e)

                # Check for recursion limit error
                if (
                    "recursion" in error_msg.lower()
                    or "GRAPH_RECURSION_LIMIT" in error_msg
                ):
                    console.print(
                        Panel(
                            f"[yellow]Agent hit the step limit ({recursion_limit} steps).[/yellow]\n\n"
                            f"This is unusual - the default limit is very high (1000).\n\n"
                            f"Likely causes:\n"
                            f"• Very long conversation with many tool calls\n"
                            f"• Agent stuck in a loop - check the pattern of tool calls above\n\n"
                            f"Solutions:\n"
                            f"• Start a new thread: [cyan]ldv-agents chat -t new-thread[/cyan]\n"
                            f"• If genuinely needed: [cyan]--recursion-limit 2000[/cyan]\n\n"
                            f"[dim]Full error: {error_msg}[/dim]",
                            title="[bold yellow]⚠ Step Limit Reached[/bold yellow]",
                            border_style="yellow",
                        )
                    )
                else:
                    console.print(
                        Panel(
                            f"[red]{error_msg}[/red]",
                            title="[bold red]Error[/bold red]",
                            border_style="red",
                        )
                    )
                continue


@app.command()
def chat(
    working_dir: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        help="Working directory for the agent",
    ),
    model: str = typer.Option(
        "anthropic:claude-sonnet-4-5",
        "--model",
        "-m",
        help="Model to use (format: provider:model)",
    ),
    thread_id: str = typer.Option(
        "default",
        "--thread",
        "-t",
        help="Thread ID for conversation history",
    ),
    auto_approve: bool = typer.Option(
        False,
        "--auto-approve",
        "-y",
        help="Auto-approve tool calls without prompting",
    ),
    mcp_config: Path | None = typer.Option(
        None,
        "--mcp-config",
        help="Path to MCP configuration file (default: searches for .ldv-agents.toml)",
    ),
    recursion_limit: int = typer.Option(
        1000,
        "--recursion-limit",
        "-r",
        help="Maximum agent steps before stopping (default: 1000)",
    ),
):
    """Start an interactive chat session with a deep agent.

    This provides a simple REPL-style interface similar to Claude Code.

    MCP Support:
    Create a .ldv-agents.toml file in your project with MCP server configurations.
    Run 'ldv-agents init-mcp' to generate an example configuration.
    """
    asyncio.run(
        run_chat_async(
            working_dir, model, thread_id, auto_approve, mcp_config, recursion_limit
        )
    )
