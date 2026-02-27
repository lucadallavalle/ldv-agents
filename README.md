# LDV Agents

REPL-style wrapper around `deepagents` SDK with rich UI, built-in MCP support, long-term memory, and skills.

## Quick Start

```bash
uv sync
export ANTHROPIC_API_KEY="sk-..."
ldv-agents init-mcp  # Optional: enables LangChain docs search
ldv-agents chat
```

## Usage

```bash
ldv-agents chat [OPTIONS]

Options:
  -a, --agent TEXT        Agent name (separate memory/skills per agent, default: default)
  -d, --dir PATH          Working directory (default: current)
  -m, --model TEXT        Model (default: anthropic:claude-sonnet-4-5)
  -t, --thread TEXT       Thread ID for conversation history (default: default)
  -y, --auto-approve      Auto-approve tools (disables human-in-the-loop)
  -r, --recursion-limit   Maximum steps (default: 1000)
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

- **File Operations**: `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`
- **Shell Execution**: `execute` command
- **Planning**: `write_todos`, `task` (subagents)
- **MCP Integration**: Connect to any [Model Context Protocol](https://modelcontextprotocol.io) server
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
