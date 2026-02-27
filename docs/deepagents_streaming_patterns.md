# DeepAgents-CLI Streaming Implementation Patterns

## Overview

This document outlines the key patterns for implementing streaming in deepagents-cli, based on the analysis of the ldv-agents implementation and LangGraph documentation.

## Key Concepts

### Stream Modes

LangGraph supports multiple streaming modes that can be used together:

1. **`messages`** - Token-by-token streaming from LLM
2. **`updates`** - Complete node updates and state changes
3. **`custom`** - Custom data from within nodes
4. **`values`** - Full state after each super-step
5. **`debug`** - Detailed execution traces

### Why Use Both `messages` and `updates`?

- **`messages`**: Provides real-time token streaming for responsive UX
- **`updates`**: Provides completed node data AND handles interrupts (HITL)

---

## Pattern 1: Token-by-Token Streaming (Basic)

### Using `stream_mode=["messages"]` for Real-Time Output

```python
# Basic token streaming
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Hello!"}]},
    config=config,
    stream_mode=["messages"],
):
    token, metadata = chunk
    if token.content:
        print(token.content, end="", flush=True)
```

**Key Points:**
- Chunk format: `(token, metadata)` tuple
- `token.content` contains the text token
- Use `end=""` and `flush=True` for incremental output
- Works with both sync `stream()` and async `astream()`

### Async Version

```python
async for mode, chunk in agent.astream(
    {"messages": [{"role": "user", "content": "Hello!"}]},
    config=config,
    stream_mode=["messages"],
):
    token, metadata = chunk
    if token.content:
        print(token.content, end="", flush=True)
```

---

## Pattern 2: Combined Streaming with HITL Support

### Using `stream_mode=["messages", "updates"]` (RECOMMENDED)

This is the **canonical pattern** for deepagents-cli implementations:

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "some_id"}}

# Stream with both modes
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Delete old records"}]},
    config=config,
    stream_mode=["updates", "messages"],  # Both modes!
):
    if mode == "messages":
        # Handle token-by-token streaming
        token, metadata = chunk
        if token.content:
            print(token.content, end="", flush=True)
    
    elif mode == "updates":
        # Check for interrupts (HITL)
        if "__interrupt__" in chunk:
            print(f"\n\nInterrupt: {chunk['__interrupt__']}")
            # Handle approval logic here
        
        # Handle completed node updates
        for source, update in chunk.items():
            if source == "model":
                # Model completed - may have tool calls
                pass
            elif source == "tools":
                # Tools completed - has results
                pass
```

**Key Points:**
- Returns tuples: `(mode, chunk)` where mode is `"messages"` or `"updates"`
- `messages` mode: chunk is `(token, metadata)`
- `updates` mode: chunk is dict with node updates or `__interrupt__`
- **CRITICAL**: Only `updates` mode surfaces `__interrupt__` for HITL

---

## Pattern 3: LDV-Agents Current Implementation

### Updates-Only Approach (NO Token Streaming)

The current ldv-agents implementation uses **only** `stream_mode=["updates"]`:

```python
async for stream_mode, chunk in agent.astream(
    current_input,
    config=config,
    stream_mode=["updates"],  # Only updates - no token streaming
):
    if stream_mode == "updates":
        # Check for interrupts (HITL)
        if "__interrupt__" in chunk:
            interrupts_occurred.extend(chunk["__interrupt__"])
            continue
        
        # Process completed node updates
        for source, update in chunk.items():
            if source == "model":
                # Model node completed - display FULL response
                if "messages" in update:
                    last_message = update["messages"][-1]
                    
                    # Display complete text content
                    if hasattr(last_message, "content") and last_message.content:
                        if isinstance(last_message.content, str):
                            console.print(last_message.content, markup=False)
                    
                    # Display tool calls
                    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        for tool_call in last_message.tool_calls:
                            # Show tool call in panel
                            display_tool_call(tool_call)
            
            elif source == "tools":
                # Tools node completed - display results
                if "messages" in update:
                    for message in update["messages"]:
                        display_tool_result(message)
```

**Characteristics:**
- ✅ **Pros**: 
  - Cleaner output (no partial tokens)
  - Simpler code
  - Still supports HITL via `__interrupt__`
- ❌ **Cons**:
  - No real-time feedback during LLM generation
  - User sees nothing until model completes
  - Less responsive UX for long responses

---

## Pattern 4: Full Implementation with Token Streaming + HITL

### Complete Example with Rich UI

```python
import asyncio
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from langgraph.types import Command

console = Console()

async def chat_with_agent(agent, user_input, config):
    """Full streaming implementation with token streaming and HITL."""
    
    current_input = {"messages": [{"role": "user", "content": user_input}]}
    
    # Main execution loop - handles interrupts
    while True:
        interrupts_occurred = []
        token_buffer = []  # Buffer for token accumulation
        spinner = Spinner("dots", text="[cyan]Thinking...[/cyan]")
        live = Live(spinner, console=console, refresh_per_second=10)
        live.start()
        
        first_token = False
        
        async for mode, chunk in agent.astream(
            current_input,
            config=config,
            stream_mode=["messages", "updates"],
        ):
            if mode == "messages":
                # TOKEN STREAMING
                token, metadata = chunk
                
                # Stop spinner on first token
                if not first_token and token.content:
                    live.stop()
                    first_token = True
                
                # Stream token immediately
                if token.content:
                    console.print(token.content, end="", markup=False)
                    token_buffer.append(token.content)
                
                # Handle tool call chunks (progressive tool calls)
                if hasattr(token, "tool_call_chunks") and token.tool_call_chunks:
                    # Tool calls are being streamed
                    # Can accumulate and display progressively
                    pass
            
            elif mode == "updates":
                # NODE UPDATES + INTERRUPTS
                
                # Check for interrupts (HITL)
                if "__interrupt__" in chunk:
                    interrupts_occurred.extend(chunk["__interrupt__"])
                    continue
                
                # Process completed nodes
                for source, update in chunk.items():
                    if source == "model":
                        # Model completed
                        if "messages" in update:
                            last_message = update["messages"][-1]
                            
                            # If we have tool calls, display them
                            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                                console.print()  # New line after tokens
                                for tool_call in last_message.tool_calls:
                                    display_tool_call_panel(tool_call)
                    
                    elif source == "tools":
                        # Tools completed
                        if "messages" in update:
                            for message in update["messages"]:
                                display_tool_result_panel(message)
        
        # Ensure spinner is stopped
        live.stop()
        
        # If no interrupts, we're done
        if not interrupts_occurred:
            break
        
        # Handle interrupts - get user decisions
        console.print("\n")
        decisions = await prompt_for_approval(interrupts_occurred)
        
        # Resume with decisions
        current_input = Command(resume={"decisions": decisions})

def display_tool_call_panel(tool_call):
    """Display tool call in a Rich panel."""
    from rich.panel import Panel
    from rich.syntax import Syntax
    import json
    
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    
    args_json = json.dumps(tool_args, indent=2)
    console.print(Panel(
        Syntax(args_json, "json", theme="monokai", line_numbers=False),
        title=f"[bold yellow]🔧 {tool_name}[/bold yellow]",
        border_style="yellow",
    ))

def display_tool_result_panel(message):
    """Display tool result."""
    console.print(f"[green]✓ {message.name} completed[/green]")
```

---

## Pattern 5: Token Streaming with Metadata Tracking

### Using Metadata to Track Source

```python
current_source = ""

for namespace, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Research quantum computing"}]},
    stream_mode="messages",
    subgraphs=True,  # Include subgraph tokens
):
    token, metadata = chunk
    
    # Check if token came from subagent
    is_subagent = any(s.startswith("tools:") for s in namespace)
    source = "subagent" if is_subagent else "main"
    
    # Print header when source changes
    if source != current_source:
        print(f"\n\n--- [{source}] ---")
        current_source = source
    
    # Stream token
    if token.content:
        print(token.content, end="", flush=True)
```

**Use Cases:**
- Multi-agent systems with subagents
- Tracking which agent/node produced which tokens
- Debugging token sources

---

## Pattern 6: Multiple Stream Modes Combined

### Full Observability

```python
INTERESTING_NODES = {"model_request", "tools"}
last_source = ""
mid_line = False  # Track if we're mid-token-stream

for namespace, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Analyze remote work"}]},
    stream_mode=["updates", "messages", "custom"],
    subgraphs=True,
):
    mode, data = chunk[0], chunk[1]
    is_subagent = any(s.startswith("tools:") for s in namespace)
    source = "subagent" if is_subagent else "main"
    
    if mode == "updates":
        # Node completed
        for node_name in data:
            if node_name not in INTERESTING_NODES:
                continue
            if mid_line:
                print()
                mid_line = False
            print(f"[{source}] step: {node_name}")
    
    elif mode == "messages":
        # Token streaming
        token, metadata = data
        if token.content:
            if source != last_source:
                if mid_line:
                    print()
                    mid_line = False
                print(f"\n[{source}] ", end="")
                last_source = source
            print(token.content, end="", flush=True)
            mid_line = True
    
    elif mode == "custom":
        # Custom events from nodes
        if mid_line:
            print()
            mid_line = False
        print(f"[{source}] custom event:", data)
```

---

## Critical: HITL Interrupt Handling

### ⚠️ Common Pitfall: Wrong API

**WRONG - Do NOT use `astream_events()`:**

```python
# ❌ This does NOT properly surface interrupts!
async for event in agent.astream_events(input, config, version="v2"):
    if event["event"] == "on_chain_end":
        # Unreliable - interrupts may not appear here
        if "__interrupt__" in event.get("data", {}).get("output", {}):
            ...
```

**CORRECT - Use `astream()` with `updates` mode:**

```python
# ✅ This DOES properly surface interrupts
async for mode, chunk in agent.astream(input, config, stream_mode=["updates", "messages"]):
    if mode == "updates" and "__interrupt__" in chunk:
        # Reliable interrupt detection
        interrupts.extend(chunk["__interrupt__"])
```

### Interrupt + Resume Pattern

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "thread_123"}}

while True:
    interrupts_occurred = []
    
    # Stream until completion or interrupt
    async for mode, chunk in agent.astream(
        current_input,
        config=config,
        stream_mode=["updates", "messages"],
    ):
        if mode == "messages":
            # Stream tokens
            token, metadata = chunk
            if token.content:
                print(token.content, end="", flush=True)
        
        elif mode == "updates":
            if "__interrupt__" in chunk:
                interrupts_occurred.extend(chunk["__interrupt__"])
    
    # No interrupts? Done!
    if not interrupts_occurred:
        break
    
    # Get user decisions for each interrupt
    decisions = []
    for interrupt in interrupts_occurred:
        hitl_request = interrupt.value
        for action_request in hitl_request["action_requests"]:
            # Prompt user
            choice = input(f"Approve {action_request['name']}? [y/n]: ")
            if choice.lower() == 'y':
                decisions.append({"type": "approve"})
            else:
                decisions.append({"type": "reject", "message": "User rejected"})
    
    # Resume with decisions
    current_input = Command(resume={"decisions": decisions})
```

---

## Comparison Summary

### Token Streaming vs. Complete Messages

| Aspect | Token Streaming (`messages`) | Complete Messages (`updates` only) |
|--------|------------------------------|-------------------------------------|
| **Responsiveness** | ✅ Immediate feedback | ❌ Wait for completion |
| **UX** | ✅ Better for long responses | ⚠️ Acceptable for short responses |
| **Code Complexity** | ⚠️ More complex | ✅ Simpler |
| **Output Quality** | ⚠️ Can be noisy | ✅ Clean, complete |
| **HITL Support** | ✅ (with `updates`) | ✅ (native) |
| **Progress Indication** | ✅ Tokens show progress | ⚠️ Needs spinner |

### Recommended Patterns by Use Case

1. **Chat Applications (Interactive)**: Use `["messages", "updates"]` for best UX
2. **Automation/Scripting**: Use `["updates"]` only for cleaner logs
3. **Multi-Agent Systems**: Use `["messages", "updates", "custom"]` for full observability
4. **HITL Required**: MUST use `["updates"]` at minimum (can add `["messages"]`)

---

## Implementation Checklist

When implementing streaming in deepagents-cli:

- [ ] Use `agent.astream()` (or `agent.stream()` for sync)
- [ ] Specify `stream_mode=["messages", "updates"]` for token streaming + HITL
- [ ] Handle `mode == "messages"` for token chunks: `(token, metadata)`
- [ ] Handle `mode == "updates"` for node completions and interrupts
- [ ] Check for `"__interrupt__"` in updates chunks
- [ ] Use `print(token.content, end="", flush=True)` for tokens
- [ ] Use `Command(resume={"decisions": [...]})` to resume after interrupts
- [ ] Maintain same `thread_id` in config when resuming
- [ ] Stop any UI spinners when first token arrives
- [ ] Add newlines appropriately between tokens and panels

---

## References

- **LangGraph Streaming Docs**: https://docs.langchain.com/oss/python/langgraph/streaming
- **HITL with Streaming**: https://docs.langchain.com/oss/python/langchain/human-in-the-loop
- **LDV-Agents Implementation**: `/src/ldv_agents/commands/chat.py`
- **LangGraph Interrupts**: https://docs.langchain.com/oss/python/langgraph/interrupts

---

## Code Snippets for Quick Reference

### Minimal Token Streaming
```python
for mode, chunk in agent.stream(input, config, stream_mode="messages"):
    token, metadata = chunk
    if token.content:
        print(token.content, end="", flush=True)
```

### Minimal HITL Detection
```python
for mode, chunk in agent.stream(input, config, stream_mode="updates"):
    if "__interrupt__" in chunk:
        handle_interrupt(chunk["__interrupt__"])
```

### Combined (Most Common)
```python
for mode, chunk in agent.stream(input, config, stream_mode=["messages", "updates"]):
    if mode == "messages":
        token, metadata = chunk
        print(token.content, end="", flush=True)
    elif mode == "updates" and "__interrupt__" in chunk:
        handle_interrupt(chunk["__interrupt__"])
```
