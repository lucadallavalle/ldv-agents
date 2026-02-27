# Shortcuts and Aliases

## Bash Aliases

To make `ldv-agents` easier to use, you can create shell aliases.

### Quick Setup

Add these to your `~/.bashrc` or `~/.bash_aliases`:

```bash
# Short alias for deepagents
alias agd='ldv-agents deepagents'

# Alias with MCP config auto-loaded
alias agdm='ldv-agents deepagents --mcp-config .ldv-agents.toml'
```

Then reload:
```bash
source ~/.bashrc
```

### Usage

```bash
# Instead of: ldv-agents deepagents list
agd list

# Instead of: ldv-agents deepagents threads list
agd threads list

# Instead of: ldv-agents deepagents --mcp-config .ldv-agents.toml
agdm

# All deepagents options work
agd --sandbox modal
agd -r  # Resume most recent thread
agd skills create my-skill
```

## Zsh Aliases

Add to `~/.zshrc`:

```bash
alias agd='ldv-agents deepagents'
alias agdm='ldv-agents deepagents --mcp-config .ldv-agents.toml'
```

## Fish Shell Abbreviations

Add to `~/.config/fish/config.fish`:

```fish
abbr -a agd ldv-agents deepagents
abbr -a agdm ldv-agents deepagents --mcp-config .ldv-agents.toml
```

## Recommended Aliases

```bash
# Core command
alias agd='ldv-agents deepagents'

# With MCP
alias agdm='ldv-agents deepagents --mcp-config .ldv-agents.toml'

# With auto-approve (for development)
alias agda='ldv-agents deepagents --auto-approve'

# With MCP + sandbox
alias agds='ldv-agents deepagents --mcp-config .ldv-agents.toml --sandbox modal'

# Resume most recent thread
alias agdr='ldv-agents deepagents -r'

# List commands
alias agdl='ldv-agents deepagents list'
alias agdt='ldv-agents deepagents threads list'
```

## Project-Specific Aliases

You can also add project-specific aliases to a `.envrc` file (if using direnv):

```bash
# .envrc in your project root
alias agd='ldv-agents deepagents --mcp-config .ldv-agents.toml --dir $(pwd)'
```

## Shell Functions

For more complex shortcuts, use functions:

```bash
# ~/.bashrc or ~/.zshrc

# Start agent with MCP in current directory
agdh() {
    ldv-agents deepagents --mcp-config .ldv-agents.toml --dir "$(pwd)" "$@"
}

# Quick agent with message
agdq() {
    ldv-agents deepagents --mcp-config .ldv-agents.toml -m "$*"
}
```

Usage:
```bash
agdq "Analyze this codebase"
agdh list
```

## Making `agd` Available Globally

If you want `agd` to work system-wide:

1. Add to `~/.bashrc`:
   ```bash
   alias agd='ldv-agents deepagents'
   ```

2. Add to `~/.bash_profile` or `~/.profile` for login shells:
   ```bash
   [ -f ~/.bashrc ] && source ~/.bashrc
   ```

3. For all users (requires sudo):
   ```bash
   echo "alias agd='ldv-agents deepagents'" | sudo tee -a /etc/bash.bashrc
   ```
