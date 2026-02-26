# MCP (Model Context Protocol)

[MCP](https://modelcontextprotocol.io) is an open protocol for connecting AI agents to external tools and data sources.

## Quick Start

```bash
ldv-agents init-mcp  # Creates .ldv-agents.toml
ldv-agents chat      # MCP tools auto-loaded
```

## Configuration

### LangChain Docs Search (Default)

Search official LangChain documentation - zero setup required:

```toml
[mcp.servers.langchain-docs]
transport = "http"
url = "https://docs.langchain.com/mcp"
```

**Try asking:**
- "How do I create a deep agent?"
- "Show me LangGraph checkpointing examples"
- "MCP integration syntax?"

### Filesystem

```toml
[mcp.servers.filesystem]
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/directory"]
```

**Tools**: `read_file`, `write_file`, `list_directory`, `create_directory`, `move_file`, `search_files`

### GitHub

```toml
[mcp.servers.github]
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxx" }
```

**Tools**: Create/update/delete files, create issues/PRs, search repos

### PostgreSQL

```toml
[mcp.servers.postgres]
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost/db"]
```

**Tools**: Query execution, schema inspection

### SQLite

```toml
[mcp.servers.sqlite]
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-sqlite", "/path/to/database.db"]
```

**Tools**: Query execution, table inspection

### Google Drive

```toml
[mcp.servers.gdrive]
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-google-drive"]
env = { GOOGLE_APPLICATION_CREDENTIALS = "/path/to/credentials.json" }
```

**Tools**: Search, read, write files

## HTTP Transport

For custom HTTP MCP servers:

```toml
[mcp.servers.custom]
transport = "http"
url = "http://localhost:8000/mcp"
headers = { Authorization = "Bearer token" }
```

## Multiple Servers

Configure as many servers as needed - all tools are available simultaneously:

```toml
[mcp.servers.langchain-docs]
transport = "http"
url = "https://docs.langchain.com/mcp"

[mcp.servers.github]
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxx" }

[mcp.servers.postgres]
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
```

## Config Discovery

Config files are auto-discovered from:
1. Current directory: `.ldv-agents.toml`
2. Parent directories (searches up)
3. Custom path: `ldv-agents chat --mcp-config /path/to/config.toml`

## More Servers

Browse the ecosystem: https://github.com/modelcontextprotocol/servers
