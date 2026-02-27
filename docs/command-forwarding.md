# Command Forwarding

## Overview

Instead of reimplementing all deepagents-cli commands, we forward most of them and only intercept where we add value.

## Implementation

```python
def forward_to_deepagents(args: list[str]) -> int:
    """Forward command to deepagents-cli."""
    result = subprocess.run(["deepagents"] + args, check=False)
    return result.returncode
```

## Commands

### 🎯 Handled by ldv-agents (Enhanced)
- **`chat`** - Loads MCP tools and injects them into agent
- **`init-mcp`** - Creates `.ldv-agents.toml` with MCP config

### ⏩ Forwarded to deepagents-cli
- **`list`** - List agents
- **`reset`** - Reset agent prompts  
- **`threads`** - Thread management (list/delete)
- **`skills`** - Skills management
- **`default-model`** - Model configuration
- **`--version`** - Show version info

## Benefits

1. **Feature Parity** - Automatically get all deepagents-cli features
2. **No Duplication** - Don't reimplement what already works
3. **Automatic Updates** - New deepagents-cli features appear automatically
4. **Maintainability** - Less code to maintain
5. **Focus** - Spend time on MCP, not plumbing

## User Experience

From the user's perspective, it's seamless:

```bash
# These all work as expected
ldv-agents list
ldv-agents threads list
ldv-agents reset --agent my-agent

# This one gets MCP support!
ldv-agents chat
```

The only difference is that `chat` loads MCP tools first.

## Version Display

When running `ldv-agents --version`, we show both:

```
ldv-agents v0.1.0 (with MCP support)
deepagents-cli v0.0.25
```

This makes it clear we're an enhancement, not a replacement.
