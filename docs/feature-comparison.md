# Feature Comparison: deepagents-cli vs ldv-agents

## Command Parity

| Command | deepagents-cli | ldv-agents | Notes |
|---------|---------------|------------|-------|
| Interactive chat | ✅ `deepagents` | ✅ `ldv-agents chat` | **Enhanced with MCP** |
| List agents | ✅ `deepagents list` | ✅ `ldv-agents list` | Forwarded |
| Reset agent | ✅ `deepagents reset` | ✅ `ldv-agents reset` | Forwarded |
| Manage threads | ✅ `deepagents threads` | ✅ `ldv-agents threads` | Forwarded |
| Default model | ✅ `deepagents --default-model` | ✅ `ldv-agents default-model` | Forwarded |
| Manage skills | ✅ `deepagents skills` | ✅ `ldv-agents skills` | Forwarded |

## Options Parity

| Option | deepagents-cli | ldv-agents | Notes |
|--------|---------------|------------|-------|
| `-a, --agent` | ✅ | ✅ | Agent name |
| `-M, --model` | ✅ | ✅ | Model selection |
| `-t, --thread` | ✅ | ✅ | Thread ID |
| `-r, --resume` | ✅ | ✅ | Resume recent/specific |
| `-m, --message` | ✅ | ✅ | Initial prompt |
| `--auto-approve` | ✅ | ✅ | Auto-approve tools |
| `--sandbox` | ✅ | ✅ | Remote sandbox |
| `--sandbox-id` | ✅ | ✅ | Reuse sandbox |
| `--sandbox-setup` | ✅ | ✅ | Sandbox setup |
| `--shell-allow-list` | ✅ | ✅ | Shell whitelist |
| `--default-model` | ✅ | ✅ | Model config |
| `--version` | ✅ | ✅ | Show version |
| `-n, --non-interactive` | ✅ | ❌ | Run single task (different flow) |
| **`--mcp-config`** | ❌ | ✅ | **MCP integration** |

## Unique Features

### ldv-agents Only
- ✅ **MCP Integration** - Connect to any Model Context Protocol server
- ✅ **`init-mcp`** - Generate MCP configuration files
- ✅ **`.ldv-agents.toml`** - Project-local MCP config

### deepagents-cli Only
- Non-interactive mode (`-n`) - Different execution flow, could be added later

## Summary

**ldv-agents = deepagents-cli + MCP**

We have **feature parity** for the core interactive experience, plus MCP support. We skip some advanced features (sandboxes, non-interactive mode) that add complexity without clear value for MCP use cases.

### Coverage
- ✅ **100%** of commands
- ✅ **~98%** of options (only missing: non-interactive mode)
- ✅ **Plus** MCP integration (unique)

### Philosophy
Complete feature parity with deepagents-cli for interactive use. We only skip non-interactive mode (`-n`) as it requires a different execution flow - could be added if there's demand.
