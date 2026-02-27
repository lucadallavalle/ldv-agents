import asyncio
import json
from pathlib import Path
from typing import Any

import typer
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend, CompositeBackend, StoreBackend
from langchain_core.messages import HumanMessage
from langgraph.store.base import BaseStore
from langgraph.types import Command
from prompt_toolkit import PromptSession, prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.styles import Style as PromptStyle
from rich import pretty
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner
from rich.tree import Tree
from rich.markdown import Markdown

from ldv_agents.mcp_config import load_mcp_config

# Install pretty printing globally
pretty.install()

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


async def prompt_for_approval(action_request: dict[str, Any], session_approvals: dict[str, bool]) -> dict[str, Any]:
    """Prompt user to approve/reject a tool call with yes/no/always options.
    
    Args:
        action_request: The action request from the interrupt
        session_approvals: Dict tracking "always approve" for this session
        
    Returns:
        Decision dict with type "approve" or "reject"
    """
    import sys
    
    tool_name = action_request["name"]
    tool_args = action_request["args"]
    
    # Check if user has already approved this tool for the session
    if session_approvals.get(tool_name, False):
        console.print(f"[dim]✓ Auto-approved {tool_name} (always for session)[/dim]")
        return {"type": "approve"}
    
    # Format tool info for display
    console.print()
    console.print(Panel(
        Syntax(
            json.dumps(tool_args, indent=2),
            "json",
            theme="monokai",
            line_numbers=False,
        ),
        title=f"[bold yellow]⚠️  Approval Required: {tool_name}[/bold yellow]",
        border_style="yellow",
        padding=(0, 1),
    ))
    
    # Check TTY availability
    if not sys.stdin.isatty():
        console.print("[red]Error: Interactive approval requires a TTY. Use --auto-approve for non-interactive mode.[/red]")
        return {"type": "reject", "message": "No TTY available for interactive approval"}
    
    # Flush any pending output from Rich console
    console.file.flush()
    if hasattr(sys.stderr, 'flush'):
        sys.stderr.flush()
    
    # Custom validator for single-character input
    class ChoiceValidator(Validator):
        def validate(self, document):
            text = document.text.strip().lower()
            if text not in ['y', 'n', 'a']:
                raise ValidationError(
                    message="Please enter 'y' (yes), 'n' (no), or 'a' (always)",
                    cursor_position=len(document.text)
                )
    
    # Prompt style
    prompt_style = PromptStyle.from_dict({
        'prompt': 'cyan bold',
        'answer': 'green bold',
    })
    
    # Prompt for decision using prompt_toolkit
    try:
        console.print("[cyan bold]How would you like to proceed?[/cyan bold]")
        console.print("  [cyan]y[/cyan] - Yes, approve this action")
        console.print("  [cyan]n[/cyan] - No, reject this action")
        console.print(f"  [cyan]a[/cyan] - Always approve '{tool_name}' for this session")
        console.print()
        
        # Run prompt in executor to avoid blocking async loop
        loop = asyncio.get_event_loop()
        choice = await loop.run_in_executor(
            None,
            lambda: prompt(
                HTML('<ansicyan><b>Choice [y/n/a]:</b></ansicyan> '),
                style=prompt_style,
                validator=ChoiceValidator(),
            )
        )
        
        choice = choice.strip().lower()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Cancelled by user (Ctrl+C) - rejecting action[/yellow]")
        return {"type": "reject", "message": f"User cancelled (Ctrl+C) approval for {tool_name}"}
    except EOFError:
        console.print("\n[yellow]⚠ Input closed (Ctrl+D) - rejecting action[/yellow]")
        return {"type": "reject", "message": f"User closed input (Ctrl+D) for {tool_name}"}
    except Exception as e:
        console.print(f"\n[red]Error during approval prompt: {e}[/red]")
        console.print(f"[dim]Debug: TTY status - stdin:{sys.stdin.isatty()}, stdout:{sys.stdout.isatty()}[/dim]")
        return {"type": "reject", "message": f"Approval prompt failed: {str(e)}"}
    
    # Process choice
    if choice == 'a':
        session_approvals[tool_name] = True
        console.print(f"[green]✓ Will auto-approve all '{tool_name}' calls this session[/green]")
        return {"type": "approve"}
    elif choice == 'y':
        console.print(f"[green]✓ Approved[/green]")
        return {"type": "approve"}
    else:  # choice == 'n'
        console.print(f"[yellow]✗ Rejected[/yellow]")
        return {"type": "reject", "message": f"User rejected {tool_name} execution"}


async def handle_interrupts(interrupts: list, session_approvals: dict[str, bool]) -> list[dict[str, Any]]:
    """Handle all interrupts and collect user decisions.
    
    Args:
        interrupts: List of interrupt objects from the graph
        session_approvals: Dict tracking "always approve" for this session
        
    Returns:
        List of decisions matching the order of action_requests
    """
    decisions = []
    
    for interrupt_obj in interrupts:
        hitl_request = interrupt_obj.value
        action_requests = hitl_request.get("action_requests", [])
        
        # Collect decisions for each action request
        for action_request in action_requests:
            decision = await prompt_for_approval(action_request, session_approvals)
            decisions.append(decision)
    
    return decisions


async def run_chat_async(
    working_dir: Path,
    model: str,
    agent_name: str,
    thread_id: str,
    auto_approve: bool,
    mcp_config_path: Path | None = None,
    recursion_limit: int = 1000,
    verbose: bool = False,
):
    """Async chat loop with streaming support."""
    # Set up agent directory structure: ~/.ldv-agents/<agent_name>/
    # This matches deepagents-cli's ~/.deepagents/<agent_name>/ structure
    agent_dir = Path.home() / ".ldv-agents" / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    # Per-agent databases
    sessions_db = agent_dir / "sessions.db"
    memory_db = agent_dir / "memory.db"
    
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.store.sqlite import AsyncSqliteStore

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

    # Scan for skills directories
    skills_paths = []
    
    # 1. Agent-specific skills: ~/.ldv-agents/<agent_name>/skills/
    agent_skills = agent_dir / "skills"
    if agent_skills.exists() and agent_skills.is_dir():
        skills_paths.append(str(agent_skills))
    
    # 2. Project-local skills: .ldv-agents/skills/ (if in a project)
    project_skills = working_dir / ".ldv-agents" / "skills"
    if project_skills.exists() and project_skills.is_dir():
        skills_paths.append(str(project_skills))
    
    # Scan for AGENTS.md files (memory)
    memory_paths = []
    
    # 1. Agent-specific memory: ~/.ldv-agents/<agent_name>/AGENTS.md
    agent_memory = agent_dir / "AGENTS.md"
    if agent_memory.exists() and agent_memory.is_file():
        memory_paths.append(str(agent_memory))
    
    # 2. Project-local memory: <working_dir>/AGENTS.md
    project_memory = working_dir / "AGENTS.md"
    if project_memory.exists() and project_memory.is_file():
        memory_paths.append(str(project_memory))

    # Welcome banner
    banner_text = (
        f"[bold cyan]LDV Agents[/bold cyan]\n\n"
        f"[dim]Directory:[/dim] {working_dir}\n"
        f"[dim]Model:[/dim] {model}\n"
        f"[dim]Agent:[/dim] {agent_name}\n"
        f"[dim]Thread:[/dim] {thread_id}"
    )

    if mcp_tools:
        banner_text += f"\n[dim]MCP Tools:[/dim] {len(mcp_tools)} loaded"
    
    if skills_paths:
        banner_text += f"\n[dim]Skills:[/dim] {len(skills_paths)} location(s)"
    
    if memory_paths:
        banner_text += f"\n[dim]Memory:[/dim] {len(memory_paths)} AGENTS.md file(s)"
    
    if not auto_approve:
        banner_text += f"\n[dim]HITL:[/dim] Enabled (write_file, edit_file, execute)"

    console.print(Panel.fit(banner_text, border_style="cyan"))
    console.print("[dim]Type 'exit' or 'quit' to end the session[/dim]")
    console.print("[dim]Press Esc+Enter or Ctrl+D to submit multiline input[/dim]\n")

    # Create prompt session with history and multiline support (global)
    history_file = Path.home() / ".ldv-agents" / "input_history.txt"
    
    # Set up key bindings for multiline input
    bindings = KeyBindings()
    
    @bindings.add("escape", "enter")  # Esc+Enter submits
    @bindings.add("c-d")  # Ctrl+D also submits (common convention)
    def _(event):
        event.current_buffer.validate_and_handle()
    
    session = PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
        multiline=True,  # Always allow multiline
        enable_history_search=True,
        key_bindings=bindings,
        prompt_continuation="... ",  # Continuation prompt for multiline
    )

    # Create checkpointer and store for persistent threads and memory
    async with AsyncSqliteSaver.from_conn_string(str(sessions_db)) as checkpointer, \
               AsyncSqliteStore.from_conn_string(str(memory_db)) as store:
        
        await store.setup()  # Initialize store schema
        
        # Create composite backend: /memories/* goes to store, everything else to filesystem
        def make_backend(runtime):
            return CompositeBackend(
                default=FilesystemBackend(root_dir=str(working_dir)),
                routes={"/memories/": StoreBackend(runtime)}
            )
        
        # Configure human-in-the-loop for sensitive operations
        interrupt_config = None
        if not auto_approve:
            interrupt_config = {
                "write_file": True,
                "edit_file": True,
                "execute": True,
            }
        
        # Build system prompt with working directory information
        system_prompt_additions = (
            f"\n\n### Current Working Directory\n\n"
            f"The filesystem backend is currently operating in: `{working_dir}`\n\n"
            f"### File System and Paths\n\n"
            f"**IMPORTANT - Path Handling:**\n"
            f"- All file paths must be absolute paths (e.g., `{working_dir}/file.txt`)\n"
            f"- Use the working directory to construct absolute paths\n"
            f"- Example: To create a file in your working directory, use `{working_dir}/project/file.md`\n"
            f"- Never use relative paths - always construct full absolute paths\n"
        )
        
        # Create deep agent with MCP tools, memory, and skills
        agent = create_deep_agent(
            model=model,
            backend=make_backend,
            store=store,
            tools=mcp_tools if mcp_tools else None,
            skills=skills_paths if skills_paths else None,
            memory=memory_paths if memory_paths else None,
            interrupt_on=interrupt_config,
            checkpointer=checkpointer,
            system_prompt=system_prompt_additions,
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
        
        # Track "always approve" decisions for this session
        session_approvals = {}

        while True:
            try:
                # Get user input with prompt_toolkit (supports history, multiline, autocomplete)
                console.print()
                user_input = await session.prompt_async(
                    HTML("<ansicyan><b>❯</b></ansicyan> "),
                    enable_history_search=True,
                )

                if not user_input.strip():
                    continue

                if user_input.lower() in ["exit", "quit", "/exit", "/quit"]:
                    console.print("\n[cyan]Goodbye![/cyan]")
                    break

                console.print()

                # Track tool calls for better display
                active_tools = {}
                response_started = False
                agent_output_started = False  # Track if we've seen any output
                current_input = {"messages": [HumanMessage(content=user_input)]}
                
                # Create a spinner for "thinking" state
                spinner = Spinner("dots", text="[cyan]Thinking...[/cyan]", style="cyan")
                live = Live(spinner, console=console, refresh_per_second=10)

                # Main execution loop - may need to resume after interrupts
                while True:
                    interrupts_occurred = []
                    # Track tool calls as they're being built (for streaming display)
                    streaming_tool_calls = {}
                    
                    # Start spinner before streaming
                    if not agent_output_started:
                        live.start()
                    
                    # Stream the response using updates mode only (no token-by-token streaming)
                    # This prevents partial output spam and shows complete messages
                    async for stream_mode, chunk in agent.astream(
                        current_input,
                        config=config,
                        stream_mode=["updates"],
                    ):
                        if stream_mode == "updates":
                            # Stream mode: updates - handles node completions and interrupts
                            
                            # Check for interrupts (HITL)
                            if "__interrupt__" in chunk:
                                interrupts_occurred.extend(chunk["__interrupt__"])
                                continue
                            
                            # Process completed node updates
                            for source, update in chunk.items():
                                if source == "model":
                                    # Model node completed - display text response and/or tool calls
                                    if "messages" in update:
                                        last_message = update["messages"][-1]
                                        
                                        # Stop spinner on first output
                                        if not agent_output_started:
                                            live.stop()
                                            agent_output_started = True
                                        
                                        # Display text content if present
                                        if hasattr(last_message, "content") and last_message.content:
                                            if isinstance(last_message.content, str) and last_message.content.strip():
                                                console.print(last_message.content, markup=False)
                                                console.print()
                                                response_started = True
                                        
                                        # Display completed tool calls with full args
                                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                                            # Display each tool call
                                            for tool_call in last_message.tool_calls:
                                                tool_name = tool_call["name"]
                                                tool_args = tool_call["args"]
                                                tool_id = tool_call["id"]
                                                
                                                # Track for result matching
                                                active_tools[tool_id] = {
                                                    "name": tool_name,
                                                    "input": tool_args,
                                                }
                                                
                                                # Display tool call panel
                                                args_display = format_tool_args(tool_args)
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
                                
                                elif source == "tools":
                                    # Tools node completed - display results
                                    if "messages" in update:
                                        for message in update["messages"]:
                                            if hasattr(message, "tool_call_id"):
                                                tool_id = message.tool_call_id
                                                
                                                if tool_id in active_tools:
                                                    tool_name = active_tools[tool_id]["name"]
                                                    
                                                    # Display result based on verbosity
                                                    if verbose:
                                                        result_display = format_tool_result(message.content)
                                                        result_panel = Panel(
                                                            f"[dim]{result_display}[/dim]",
                                                            title=f"[bold green]✓ {tool_name} completed[/bold green]",
                                                            border_style="green",
                                                            padding=(0, 1),
                                                        )
                                                        console.print(result_panel)
                                                        console.print()
                                                    else:
                                                        console.print(f"[green]✓ {tool_name} completed[/green]")
                                                    
                                                    # Clean up
                                                    del active_tools[tool_id]
                    
                    # If we finished streaming without interrupts, we're done
                    if not interrupts_occurred:
                        break
                    
                    # Stop spinner if still running (edge case)
                    if not agent_output_started:
                        live.stop()
                        agent_output_started = True
                    
                    # Handle interrupts - prompt user for decisions
                    console.print()
                    decisions = await handle_interrupts(interrupts_occurred, session_approvals)
                    
                    # Resume execution with decisions
                    current_input = Command(resume={"decisions": decisions})
                    console.print()

                # Ensure spinner is stopped
                if not agent_output_started:
                    live.stop()
                
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
    agent_name: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help="Agent name (separate memory and config per agent)",
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
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed tool output in panels",
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
            working_dir, model, agent_name, thread_id, auto_approve, mcp_config, recursion_limit, verbose
        )
    )
