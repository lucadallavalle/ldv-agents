# Extensible Architecture

## Overview

`ldv-agents` is designed as a **unified CLI for multiple agent frameworks** with MCP integration.

## Current Structure

```
ldv-agents
├── deepagents [OPTIONS] [SUBCOMMAND]  # deepagents-cli with MCP
├── init-mcp                           # MCP config generator
└── (future tools...)                  # OpenHands, Aider, etc.
```

## Command Structure

### deepagents
```bash
ldv-agents deepagents [DEEPAGENTS_OPTIONS]
ldv-agents deepagents list
ldv-agents deepagents threads list
ldv-agents deepagents --mcp-config config.toml
```

### Future: OpenHands
```bash
ldv-agents openhands [OPENHANDS_OPTIONS]
ldv-agents openhands --mcp-config config.toml
```

### Future: Aider
```bash
ldv-agents aider [AIDER_OPTIONS]
ldv-agents aider --mcp-config config.toml
```

## Adding New Tools

Adding a new tool integration is simple:

### 1. Create Tool Wrapper

```python
# src/ldv_agents/commands/newtool.py
import sys
from ldv_agents.mcp_config import load_mcp_config

def run_newtool_with_mcp(args: list[str]) -> int:
    """Run newtool with MCP support."""
    # Parse --mcp-config from args
    # Load MCP tools
    # Pass tools to newtool
    # Forward remaining args
    ...
```

### 2. Register Command

```python
# src/ldv_agents/main.py
from ldv_agents.commands import newtool

@app.command(
    name="newtool",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def newtool_cmd(ctx: typer.Context):
    """Run newtool with MCP support."""
    args = sys.argv[sys.argv.index('newtool') + 1:]
    exit_code = newtool.run_newtool_with_mcp(args)
    raise typer.Exit(code=exit_code)
```

### 3. Done!

```bash
ldv-agents newtool --mcp-config .ldv-agents.toml
```

## Benefits

1. **Unified Interface** - One CLI for all agent tools
2. **Consistent MCP Integration** - All tools get MCP support the same way
3. **Clean Separation** - Each tool is isolated in its own module
4. **Easy to Extend** - Adding new tools is straightforward
5. **Shared Config** - `.ldv-agents.toml` works across all tools

## Example: Full Workflow

```bash
# Initialize MCP config once
ldv-agents init-mcp

# Use with any tool
ldv-agents deepagents --mcp-config .ldv-agents.toml
ldv-agents openhands --mcp-config .ldv-agents.toml  # (future)
ldv-agents aider --mcp-config .ldv-agents.toml      # (future)
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│           ldv-agents (main CLI)                 │
│  Unified interface with MCP integration         │
└────────────┬────────────────────────────────────┘
             │
       ┌─────┴─────┬──────────┬────────────┐
       │           │          │            │
   ┌───▼────┐  ┌───▼───┐  ┌───▼────┐  ┌───▼────┐
   │deepagts│  │openhds│  │ aider  │  │  ...   │
   │+ MCP   │  │+ MCP  │  │ + MCP  │  │ + MCP  │
   └────────┘  └───────┘  └────────┘  └────────┘
        │          │          │            │
        └──────────┴──────────┴────────────┘
                      │
              ┌───────▼────────┐
              │  MCP Servers   │
              │  (filesystem,  │
              │   database,    │
              │   APIs, etc.)  │
              └────────────────┘
```

## Why This Matters

Instead of:
```bash
deepagents list
openhands-cli run
aider --some-args
```

You get:
```bash
ldv-agents deepagents list
ldv-agents openhands run
ldv-agents aider --some-args
```

All with **consistent MCP integration** via a single config file.
