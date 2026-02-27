"""Deepagents wrapper with MCP support."""

import argparse
import asyncio
import subprocess
from pathlib import Path

from deepagents_cli.agent import create_cli_agent
from deepagents_cli.app import run_textual_app
from deepagents_cli.config import settings, create_model
from deepagents_cli.sessions import get_checkpointer
from deepagents_cli.tools import fetch_url, http_request, web_search
from rich.console import Console

from ldv_agents.mcp_config import load_mcp_config

console = Console()


def run_deepagents_with_mcp(args: list[str]) -> int:
    """Run deepagents with MCP support.
    
    Extracts --mcp-config if present, loads MCP tools, and runs deepagents with all args.
    """
    # Parse only the --mcp-config argument, leave everything else
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mcp-config", type=Path, default=None)
    
    # Parse known args, keep unknown for deepagents-cli
    known_args, unknown_args = parser.parse_known_args(args)
    
    # If there's an mcp-config, load it and run with MCP tools
    if known_args.mcp_config:
        # Run the async chat with MCP
        return asyncio.run(run_with_mcp(unknown_args, known_args.mcp_config))
    else:
        # Just forward to deepagents-cli as-is
        try:
            result = subprocess.run(["deepagents"] + args, check=False)
            return result.returncode
        except FileNotFoundError:
            console.print("[red]Error: deepagents-cli not found. Is it installed?[/red]")
            return 1


async def run_with_mcp(args: list[str], mcp_config_path: Path) -> int:
    """Run deepagents with MCP tools loaded."""
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
    
    # Handle --resume flag
    thread_id = parsed_args.thread
    if parsed_args.resume is not None:
        checkpointer = get_checkpointer(parsed_args.agent)
        if parsed_args.resume == "":  # -r without ID = most recent
            configs = list(checkpointer.list(None, limit=1))
            if configs:
                thread_id = configs[0]["configurable"]["thread_id"]
                console.print(f"[dim]Resuming most recent thread: {thread_id}[/dim]")
            else:
                console.print("[yellow]No threads found, starting new conversation[/yellow]")
        else:  # -r ID = specific thread
            thread_id = parsed_args.resume
    
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
    # Create model
    model = create_model(model_name)
    
    # Create sandbox backend if needed
    sandbox_backend = None
    if sandbox_type != "none":
        from deepagents_cli.sandboxes import create_sandbox
        sandbox_backend = await create_sandbox(
            sandbox_type=sandbox_type,
            sandbox_id=sandbox_id,
            setup_script=sandbox_setup,
        )
    
    # Combine tools: web tools + MCP tools
    tools = [web_search, fetch_url, http_request] + mcp_tools
    
    # Create agent
    agent, backend = create_cli_agent(
        name=agent_name,
        working_directory=working_dir,
        model=model,
        tools=tools,
        auto_approve_tools=auto_approve,
        sandbox_backend=sandbox_backend,
    )
    
    # Run Textual app
    await run_textual_app(
        agent=agent,
        backend=backend,
        agent_name=agent_name,
        thread_id=thread_id,
        initial_message=initial_message,
    )
