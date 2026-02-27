# Architecture

## Design Philosophy

**ldv-agents = deepagents-cli + MCP integration**

We follow a "composition over duplication" approach:
- **Reuse** what works (deepagents-cli's Textual UI)
- **Extend** where we add value (MCP support)
- **Forward** everything else (agent/thread management)

## Command Routing

### Commands We Handle
- ✅ **`chat`** - Enhanced with MCP tool loading
- ✅ **`init-mcp`** - Generate MCP configuration
- ✅ **`skills`** - Our own skills management

### Commands We Forward
Commands forwarded to `deepagents-cli`:
- `list` - List agents
- `reset` - Reset agent prompts
- `threads` - Thread management
- `--version` - Show version (both ours and deepagents-cli)

## Chat Command Flow

```
ldv-agents chat
    ↓
1. Load MCP config (.ldv-agents.toml)
    ↓
2. Initialize MCP tools (MultiServerMCPClient)
    ↓
3. Create model (deepagents_cli.config.create_model)
    ↓
4. Create agent with MCP tools (create_cli_agent)
    ↓
5. Run Textual app (run_textual_app)
    - Streaming ✓
    - HITL ✓
    - Message widgets ✓
    - All deepagents-cli features ✓
    - MCP tools available! ✓
```

## MCP Integration

MCP tools are injected at agent creation:

```python
# Standard tools
tools = [http_request, fetch_url, web_search]

# Add MCP tools
tools.extend(mcp_tools)

# Create agent with all tools
agent, backend = create_cli_agent(
    model=model,
    tools=tools,  # Standard + MCP tools
    ...
)
```

## Benefits of This Approach

1. **Minimal Code** - ~150 lines vs thousands
2. **Automatic Updates** - Get deepagents-cli improvements for free
3. **Proven UI** - Textual implementation already works
4. **Focus** - Spend time on MCP, not UI debugging
5. **Composable** - Easy to add more integrations

## Trade-offs

**Pros:**
- Less code to maintain
- Inherits all deepagents-cli features
- Streaming works perfectly

**Cons:**
- Depends on deepagents-cli internals (could break on updates)
- Less flexibility for radical UI changes
- Additional dependency

**Verdict:** Worth it. The UI is complex, MCP integration is simple.
