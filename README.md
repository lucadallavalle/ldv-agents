# LDV Agents

REPL-style wrapper around `deepagents` SDK with rich UI and built-in MCP support.

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
  -d, --dir PATH          Working directory (default: current)
  -m, --model TEXT        Model (default: anthropic:claude-sonnet-4-5)
  -t, --thread TEXT       Thread ID for history (default: default)
  -y, --auto-approve      Auto-approve tools
  -r, --recursion-limit   Maximum steps (default: 1000)
```

Conversations persist to `~/.ldv-agents/sessions.db`. Resume with same thread ID.

## Built-in Tools

- **Files**: `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`
- **Shell**: `execute`
- **Planning**: `write_todos`, `task` (subagents)
- **MCP**: Connect to any [Model Context Protocol](https://modelcontextprotocol.io) server

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

## Documentation

- **[docs/MCP.md](docs/MCP.md)** - MCP setup and examples
- **[CHANGELOG.md](CHANGELOG.md)** - Version history
