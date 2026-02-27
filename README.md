# LDV Agents

**Unified CLI for agent frameworks with Model Context Protocol (MCP) support**

One CLI for all your agent tools with consistent MCP integration:

```bash
ldv-agents deepagents [OPTIONS]    # deepagents-cli + MCP ✅
ldv-agents openhands [OPTIONS]     # (coming soon) OpenHands + MCP
ldv-agents aider [OPTIONS]         # (future) Aider + MCP
```

Built on proven frameworks, enhanced with MCP integration for connecting external tools and data sources.

## Quick Start

```bash
uv sync
export ANTHROPIC_API_KEY="sk-..."
ldv-agents init-mcp  # Optional: generate MCP config
ldv-agents deepagents --mcp-config .ldv-agents.toml
```

## Usage

```bash
# Start interactive chat (with MCP support!)
ldv-agents deepagents [OPTIONS]
ldv-agents deepagents --mcp-config .ldv-agents.toml

# List all agents
ldv-agents deepagents list

# Manage threads
ldv-agents deepagents threads list
ldv-agents deepagents threads delete <ID>

# Reset agent prompt
ldv-agents deepagents reset --agent <NAME>

# Manage default model
ldv-agents deepagents --default-model [MODEL]

# Manage skills
ldv-agents deepagents skills list
ldv-agents deepagents skills create <NAME>
ldv-agents deepagents skills info <NAME>
ldv-agents deepagents skills delete <NAME>

# MCP Configuration
ldv-agents init-mcp  # Generate example config
```

### Chat Options
```
-a, --agent TEXT          Agent name (default: default)
-d, --dir PATH            Working directory (default: current)
-M, --model TEXT          Model (default: anthropic:claude-sonnet-4-5)
-t, --thread TEXT         Thread ID to resume
-r, --resume [ID]         Resume thread: -r for most recent, -r ID for specific
-m, --message TEXT        Initial prompt to auto-submit on start
--auto-approve            Auto-approve tools (disables HITL)
--sandbox TYPE            Remote sandbox (none, modal, runloop, daytona, langsmith)
--sandbox-id ID           Reuse existing sandbox
--sandbox-setup PATH      Setup script for sandbox
--shell-allow-list CMDS   Comma-separated local shell commands to allow
--mcp-config PATH         Path to MCP config file
```

**Examples:**
```bash
# Start new chat with MCP tools
ldv-agents chat

# Resume most recent thread
ldv-agents chat -r

# Resume specific thread
ldv-agents chat -r abc123

# Start with initial message
ldv-agents chat -m "Analyze the codebase"

# Combine: resume + initial message
ldv-agents chat -r -m "Continue where we left off"
```

**Directory Structure:**
```
~/.ldv-agents/                    # Global (like deepagents ~/.deepagents/)
  <agent_name>/
    memory.db                     # Long-term memory (cross-thread)
    sessions.db                   # Thread checkpoints
    skills/                       # Agent-specific skills
  input_history.txt               # Shared command history

<working_dir>/.ldv-agents/        # Project-local (optional)
  skills/                         # Project-specific skills
```

## Features

### What Makes This Different

**🔌 MCP Integration** - The key differentiator from deepagents-cli. Connect to any [Model Context Protocol](https://modelcontextprotocol.io) server and add external tools to your agent.

### All deepagents-cli Features

- **Textual TUI** - Full terminal UI with streaming, message widgets, status bars
- **File Operations**: `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`
- **Shell Execution**: `execute` command  
- **Planning**: `write_todos`, `task` (subagents)
- **Long-term Memory**: `/memories/*` persists across threads
- **Skills System**: Reusable agent capabilities with progressive disclosure
- **Human-in-the-Loop**: Approval workflow for sensitive operations

## MCP Configuration

```bash
ldv-agents init-mcp  # Generates .ldv-agents.toml
```

Default config includes LangChain docs search (zero setup):
```toml
[mcp.servers.langchain-docs]
transport = "http"
url = "https://docs.langchain.com/mcp"
```

Add more servers:
```toml
[mcp.servers.github]
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxx" }
```

Popular servers: `filesystem`, `github`, `postgres`, `sqlite`, `google-drive`  
Browse more: https://github.com/modelcontextprotocol/servers

## Skills

Create reusable agent capabilities:

```bash
# Create a skill
ldv-agents skills create web-research

# List skills
ldv-agents skills list
ldv-agents skills list --project  # Project-wide skills

# Get skill info
ldv-agents skills info web-research

# Delete a skill
ldv-agents skills delete web-research
```

Skills are markdown files with frontmatter that provide specialized instructions to agents. They use progressive disclosure - only loaded when relevant.

## Long-term Memory

Agents can persist information across threads:

```python
# Agent can write to /memories/ for persistent storage
"Save my preference to /memories/user-prefs.txt"
"What did I save in /memories/?"
```

Files in `/memories/*` persist in the agent's memory database, accessible across all threads.

## Extending

**Custom tools:**
```python
from langchain_core.tools import tool

@tool
def my_tool(query: str) -> str:
    """Tool description."""
    return f"Result: {query}"

agent = create_deep_agent(model=model, backend=backend, tools=[my_tool])
```

**System prompt:**
```python
agent = create_deep_agent(model=model, backend=backend, system_prompt="You are X")
```

## Environment

Set API keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.

## Human-in-the-Loop (HITL)

By default, ldv-agents requires approval for sensitive operations:

- `write_file` - Creating/overwriting files
- `edit_file` - Modifying existing files  
- `execute` - Running shell commands

When approval is needed, you'll see:
```
⚠️  Approval Required: write_file
{ file_path: "/path/to/file", content: "..." }

How would you like to proceed?
  y - Yes, approve this action
  n - No, reject this action
  a - Always approve 'write_file' for this session

Choice [y/n/a]:
```

To bypass approvals entirely:
```bash
ldv-agents chat --auto-approve
```

See **[docs/HITL.md](docs/HITL.md)** for technical details.

## Documentation

- **[docs/HITL.md](docs/HITL.md)** - Human-in-the-loop implementation
- **[docs/MCP.md](docs/MCP.md)** - MCP setup and examples
- **[CHANGELOG.md](CHANGELOG.md)** - Version history
