"""Deepagents wrapper with MCP support."""

import argparse
import asyncio
from pathlib import Path

from rich.console import Console

console = Console()


def run_deepagents_with_mcp(args: list[str]) -> int:
    """Run deepagents with MCP support.
    
    Extracts --mcp-config if present, loads MCP tools, and runs deepagents with all args.
    """
    # Subcommands that should bypass MCP mode and go directly to deepagents-cli
    DEEPAGENTS_SUBCOMMANDS = ['list', 'reset', 'threads', 'skills', 'help']
    
    # Check if first arg is a subcommand
    if args and args[0] in DEEPAGENTS_SUBCOMMANDS:
        # Forward directly to deepagents-cli for subcommands
        try:
            from deepagents_cli.main import cli_main
            import sys
            
            original_argv = sys.argv
            try:
                sys.argv = ["deepagents"] + args
                cli_main()
                return 0
            except SystemExit as e:
                return e.code if e.code is not None else 0
            finally:
                sys.argv = original_argv
        except ImportError as e:
            console.print(f"[red]Error: deepagents-cli not found. {e}[/red]")
            return 1
    
    # Quick check: if non-interactive mode (-n or --non-interactive), skip MCP
    # MCP only makes sense for interactive sessions
    if '-n' in args or '--non-interactive' in args:
        try:
            from deepagents_cli.main import cli_main
            import sys
            
            original_argv = sys.argv
            try:
                sys.argv = ["deepagents"] + args
                cli_main()
                return 0
            except SystemExit as e:
                return e.code if e.code is not None else 0
            finally:
                sys.argv = original_argv
        except ImportError as e:
            console.print(f"[red]Error: deepagents-cli not found. {e}[/red]")
            return 1
    
    # Parse only the --mcp-config argument, leave everything else
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mcp-config", type=Path, default=None)
    
    # Parse known args, keep unknown for deepagents-cli
    known_args, unknown_args = parser.parse_known_args(args)
    
    # Auto-detect .ldv-agents.toml if not specified
    mcp_config = known_args.mcp_config
    if mcp_config is None:
        default_config = Path.cwd() / ".ldv-agents.toml"
        if default_config.exists():
            mcp_config = default_config
    
    # If there's an mcp-config, load it and run with MCP tools
    if mcp_config:
        # Run the async chat with MCP
        return asyncio.run(run_with_mcp(unknown_args, mcp_config))
    else:
        # Forward to deepagents-cli directly using the local installation
        try:
            from deepagents_cli.main import cli_main
            import sys
            
            # Set sys.argv to what deepagents-cli expects
            original_argv = sys.argv
            try:
                sys.argv = ["deepagents"] + args
                cli_main()
                return 0
            except SystemExit as e:
                return e.code if e.code is not None else 0
            finally:
                sys.argv = original_argv
        except ImportError as e:
            console.print(f"[red]Error: deepagents-cli not found. Is it installed in .venv? {e}[/red]")
            return 1


async def run_with_mcp(args: list[str], mcp_config_path: Path) -> int:
    """Run deepagents with MCP tools loaded."""
    from deepagents_cli.agent import create_cli_agent
    from deepagents_cli.app import run_textual_app
    from deepagents_cli.config import settings, create_model
    from deepagents_cli.sessions import get_checkpointer
    from deepagents_cli.tools import fetch_url, http_request, web_search
    
    from ldv_agents.mcp_config import load_mcp_config
    
    # Parse deepagents arguments to extract what we need
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-a", "--agent", default="default")
    parser.add_argument("-d", "--dir", type=Path, default=Path.cwd())
    parser.add_argument("-M", "--model", default="anthropic:claude-sonnet-4-5")
    parser.add_argument("-t", "--thread", default=None)
    parser.add_argument("-r", "--resume", default=None, nargs="?", const="")
    parser.add_argument("-m", "--message", default=None)
    parser.add_argument("--auto-approve", action="store_true")
    parser.add_argument("--sandbox", default="none")
    parser.add_argument("--sandbox-id", default=None)
    parser.add_argument("--sandbox-setup", type=Path, default=None)
    parser.add_argument("--shell-allow-list", default=None)
    
    parsed_args = parser.parse_args(args)
    
    # Load MCP configuration
    mcp_config = load_mcp_config(mcp_config_path)
    mcp_tools = []
    
    if mcp_config.has_servers():
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
            
            # Create MCP client and get tools
            mcp_client = MultiServerMCPClient(mcp_config.get_servers())
            mcp_tools = await mcp_client.get_tools()
            
            console.print(
                f"[green]✓[/green] Loaded {len(mcp_tools)} MCP tools from {len(mcp_config.get_servers())} server(s)"
            )
        except ImportError:
            console.print(
                "[yellow]⚠ MCP support requires: pip install langchain-mcp-adapters[/yellow]"
            )
            return 1
    
    # Configure shell allow list if provided
    if parsed_args.shell_allow_list:
        from deepagents_cli.config import parse_shell_allow_list
        settings.shell_allow_list = parse_shell_allow_list(parsed_args.shell_allow_list)
    
    # Import session utilities
    from deepagents_cli.sessions import get_most_recent, get_thread_agent, thread_exists
    
    # Handle --resume flag
    thread_id = parsed_args.thread
    if parsed_args.resume is not None:
        if parsed_args.resume == "":  # -r without ID = most recent
            thread_id = await get_most_recent(parsed_args.agent if parsed_args.agent != "default" else None)
            if thread_id:
                console.print(f"[dim]Resuming most recent thread: {thread_id}[/dim]")
                # Update agent name if thread has one
                agent_name = await get_thread_agent(thread_id)
                if agent_name:
                    parsed_args.agent = agent_name
            else:
                console.print("[yellow]No threads found, starting new conversation[/yellow]")
        else:  # -r ID = specific thread
            if await thread_exists(parsed_args.resume):
                thread_id = parsed_args.resume
                # Update agent name if thread has one
                if parsed_args.agent == "default":
                    agent_name = await get_thread_agent(thread_id)
                    if agent_name:
                        parsed_args.agent = agent_name
            else:
                console.print(f"[red]Thread '{parsed_args.resume}' not found[/red]")
                return 1
    
    # Run the deepagents textual app with MCP tools
    try:
        await run_deepagents_textual(
            agent_name=parsed_args.agent,
            working_dir=parsed_args.dir,
            model_name=parsed_args.model,
            thread_id=thread_id,
            initial_message=parsed_args.message,
            auto_approve=parsed_args.auto_approve,
            sandbox_type=parsed_args.sandbox,
            sandbox_id=parsed_args.sandbox_id,
            sandbox_setup=parsed_args.sandbox_setup,
            mcp_tools=mcp_tools,
        )
        return 0
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


async def run_deepagents_textual(
    agent_name: str,
    working_dir: Path,
    model_name: str,
    thread_id: str | None,
    initial_message: str | None,
    auto_approve: bool,
    sandbox_type: str,
    sandbox_id: str | None,
    sandbox_setup: Path | None,
    mcp_tools: list,
):
    """Run the deepagents textual app with MCP tools."""
    import os
    from deepagents_cli.agent import create_cli_agent
    from deepagents_cli.app import run_textual_app
    from deepagents_cli.config import create_model, settings
    from deepagents_cli.model_config import ModelConfigError
    from deepagents_cli.sessions import get_checkpointer
    from deepagents_cli.tools import fetch_url, http_request, web_search
    
    # Change to working directory if specified
    if working_dir != Path.cwd():
        os.chdir(working_dir)
    
    # Create model
    try:
        result = create_model(model_name, extra_kwargs=None)
    except ModelConfigError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1
    
    model = result.model
    result.apply_to_settings()
    
    # Use async context manager for checkpointer
    async with get_checkpointer() as checkpointer:
        # Combine tools: web tools + MCP tools
        tools = [http_request, fetch_url]
        if settings.has_tavily:
            tools.append(web_search)
        tools.extend(mcp_tools)
        
        # Create sandbox backend if needed
        sandbox_backend = None
        sandbox_cm = None
        if sandbox_type != "none":
            from deepagents_cli.integrations.sandbox_factory import create_sandbox
            
            try:
                sandbox_cm = create_sandbox(
                    sandbox_type,
                    sandbox_id=sandbox_id,
                    setup_script_path=sandbox_setup,
                )
                sandbox_backend = sandbox_cm.__enter__()
            except (ImportError, ValueError, RuntimeError, NotImplementedError) as e:
                console.print()
                console.print("[red]Sandbox creation failed[/red]")
                console.print(f"[dim]{e}[/dim]")
                return 1
        
        try:
            # Create agent
            agent, backend = create_cli_agent(
                model=model,
                assistant_id=agent_name,
                tools=tools,
                sandbox=sandbox_backend,
                sandbox_type=sandbox_type if sandbox_type != "none" else None,
                auto_approve=auto_approve,
                checkpointer=checkpointer,
            )
        except Exception as e:
            console.print(f"[red]Failed to create agent: {e}[/red]")
            return 1
        
        try:
            # Run Textual app
            await run_textual_app(
                agent=agent,
                assistant_id=agent_name,
                backend=backend,
                auto_approve=auto_approve,
                cwd=working_dir,
                thread_id=thread_id,
                initial_prompt=initial_message,
                checkpointer=checkpointer,
                tools=tools,
                sandbox=sandbox_backend,
                sandbox_type=sandbox_type if sandbox_type != "none" else None,
            )
        finally:
            # Clean up sandbox
            if sandbox_cm is not None:
                try:
                    sandbox_cm.__exit__(None, None, None)
                except Exception:
                    pass
        
        return 0
