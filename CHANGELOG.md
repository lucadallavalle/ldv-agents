# Changelog

## [0.2.0] - 2025-01-XX

### Added - MCP Support 🔌

- **MCP Integration**: Full Model Context Protocol support via `langchain-mcp-adapters`
- **Configuration System**: `.ldv-agents.toml` for declarative MCP server configuration
- **`init-mcp` Command**: Generate example MCP configuration files
- **Auto-discovery**: Automatically finds `.ldv-agents.toml` in current and parent directories
- **Multi-server Support**: Connect to multiple MCP servers simultaneously
- **Transport Support**: Both stdio and HTTP MCP transports

### Added - Enhanced UI 🎨

- **Token-by-Token Streaming**: Real-time display of LLM output as it generates (matches deepagents-cli behavior)
- **Welcome Banner**: Styled panel showing directory, model, thread, and MCP tool count
- **Rich Tool Panels**: Tool calls displayed in bordered panels with:
  - JSON syntax highlighting for arguments (monokai theme)
  - Color-coded borders (yellow for calls, green for success, red for errors)
  - Automatic truncation of long arguments (500 char limit)
- **Result Formatting**: Tool results shown in panels with smart truncation (10 lines + count)
- **Clean Prompt**: Simple `❯` prompt instead of "You:"
- **Better Spacing**: Clear visual separation between messages, tool calls, and results
- **Error Panels**: Red-bordered panels for clear error visibility

### Changed

- **Dependencies**: Added `langchain-mcp-adapters>=0.1.0` and `tomli>=2.0.1`
- **Chat Command**: Enhanced with `--mcp-config` option for custom config paths
- **Agent Creation**: Now accepts MCP tools automatically

### Documentation

- Added `MCP_GUIDE.md` - Comprehensive MCP setup and usage guide
- Added `EXAMPLE_SESSION.md` - Example chat sessions with visual output
- Added `COMPARISON.md` - Detailed comparison with deepagents-cli
- Added `IMPROVEMENTS.md` - Summary of all improvements
- Added `CHANGELOG.md` - This file
- Updated `README.md` - Added MCP section and updated features table

### Technical

- New module: `src/ldv_agents/mcp_config.py` - MCP configuration loader
- New command: `src/ldv_agents/commands/init_mcp.py` - Config generator
- Enhanced: `src/ldv_agents/commands/chat.py` - UI improvements + MCP integration
- Enhanced: `src/ldv_agents/main.py` - Register init-mcp command

## [0.1.0] - Initial Release

### Added

- **Chat Command**: Interactive REPL-style chat interface
- **Deep Agent Integration**: Uses `deepagents` SDK
- **Built-in Tools**: File operations, shell execution, planning
- **CLI Framework**: typer + rich for beautiful CLI
- **Thread Support**: Conversation history via thread IDs
- **Model Support**: Any model supported by deepagents
- **Working Directory**: Configurable via `--dir` flag
- **Auto-approve**: Optional tool approval bypass via `-y` flag

### Documentation

- Initial `README.md` with usage examples
- Quick start guide
- Basic extensibility examples

---

## Migration Notes

### From 0.1.0 to 0.2.0

No breaking changes! Just add MCP configuration if desired:

```bash
# Optional: Add MCP support
ldv-agents init-mcp
# Edit .ldv-agents.toml
ldv-agents chat  # MCP tools auto-loaded
```

Existing usage works identically:
```bash
ldv-agents chat --model anthropic:claude-sonnet-4-5 --dir /path/to/project
```
