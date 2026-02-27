# Human-in-the-Loop (HITL) Implementation

## Overview

This document describes how ldv-agents implements human approval for sensitive tool calls, based on deepagents' HITL architecture.

## Architecture

### Core Components

Human-in-the-loop functionality is implemented via LangGraph's interrupt mechanism and middleware pattern:

1. **LangGraph Interrupt Primitive** (`langgraph.types.interrupt()`)
   - Pauses graph execution by raising `GraphInterrupt` 
   - Returns control to the caller with a value
   - Requires a checkpointer to persist state
   - Resumed via `Command(resume=value)`

2. **DeepAgents Middleware** (`deepagents/graph.py`)
   - Lines 212-213, 296-297: Conditionally adds HITL middleware when `interrupt_on` is configured
   - Integrates with the agent graph via `after_model()` hook

3. **LangChain HITL Middleware** (from langchain's middleware)
   - Intercepts tool calls after model generation
   - Compares tool names against `interrupt_on` config
   - Calls `interrupt()` with structured request
   - Processes user decisions (approve/reject/edit)

### Configuration

```python
agent = create_deep_agent(
    model=model,
    interrupt_on={
        "write_file": True,      # Enable HITL
        "edit_file": True,
        "execute": True,
        "read_file": False,      # Disable (auto-approve)
    },
    checkpointer=checkpointer,   # REQUIRED for interrupts
)
```

### Interrupt Flow

1. **Model generates tool calls** → middleware intercepts
2. **Middleware calls `interrupt()`** → execution pauses
3. **Caller receives interrupt** via `__interrupt__` in result
4. **User makes decision** (approve/reject/edit)
5. **Resume with `Command()`** → execution continues

### Interrupt Payload Structure

When execution is interrupted, the result contains:

```python
{
    "__interrupt__": [
        {
            "value": {
                "action_requests": [
                    {
                        "name": "write_file",
                        "args": {"file_path": "/test.txt", "content": "..."},
                        "description": "Tool: write_file\nArgs: {...}"
                    }
                ],
                "review_configs": [
                    {
                        "action_name": "write_file",
                        "allowed_decisions": ["approve", "edit", "reject"]
                    }
                ]
            }
        }
    ]
}
```

### Decision Types

**Approve** - Execute tool as-is:
```python
{"type": "approve"}
```

**Reject** - Cancel execution with optional message:
```python
{"type": "reject", "message": "User rejected execution"}
```

**Edit** - Modify tool call (not implemented in ldv-agents):
```python
{"type": "edit", "edited_action": {"name": "...", "args": {...}}}
```

### Resuming Execution

```python
from langgraph.types import Command

# Collect decisions (one per action_request, in order)
decisions = [
    {"type": "approve"},
    {"type": "reject", "message": "Not allowed"}
]

# Resume with same thread_id
result = agent.invoke(
    Command(resume={"decisions": decisions}),
    config=config  # MUST use same thread_id
)
```

## LDV-Agents Implementation

### Detection

We detect interrupts during streaming using the `updates` stream mode:

```python
async for stream_mode, chunk in agent.astream(
    current_input,
    config=config,
    stream_mode=["messages", "updates"],
):
    if stream_mode == "messages":
        # Handle streaming tokens
        token, metadata = chunk
        if token.content:
            print(token.content, end="")
    
    elif stream_mode == "updates":
        # Check for interrupts
        if "__interrupt__" in chunk:
            interrupts_occurred.extend(chunk["__interrupt__"])
```

### User Interface

When an interrupt occurs, we show an interactive prompt:

```
┌─ ⚠️  Approval Required: write_file ────┐
│ {                                       │
│   "file_path": "/test.txt",            │
│   "content": "Hello World"             │
│ }                                       │
└────────────────────────────────────────┘

? How would you like to proceed?
❯ ✓ Yes - Approve this action
  ✗ No - Reject this action
  ✓✓ Always - Approve all 'write_file' for this session
```

### Session-Level "Always Approve"

Enhancement over base deepagents pattern:
- When user selects "Always", tool is added to `session_approvals` dict
- Future calls to that tool auto-approve without prompting
- State persists only for current session (resets on exit)

### Resume Loop

```python
# Main execution loop - handles multiple interrupt/resume cycles
while True:
    interrupts_occurred = []
    
    # Stream until completion or interrupt
    async for stream_mode, chunk in agent.astream(
        current_input,
        config=config,
        stream_mode=["messages", "updates"],
    ):
        if stream_mode == "messages":
            # Handle streaming tokens
            token, metadata = chunk
            if token.content:
                print(token.content, end="")
        
        elif stream_mode == "updates":
            # Check for interrupts
            if "__interrupt__" in chunk:
                interrupts_occurred.extend(chunk["__interrupt__"])
    
    # No interrupts? We're done
    if not interrupts_occurred:
        break
    
    # Prompt user for decisions
    decisions = await handle_interrupts(interrupts_occurred, session_approvals)
    
    # Resume with decisions
    current_input = Command(resume={"decisions": decisions})
```

## Key Requirements

1. **Checkpointer is mandatory** - Interrupts require state persistence
2. **Correct streaming API** - Must use `astream()` with `stream_mode=["messages", "updates"]`, NOT `astream_events()`
3. **Thread ID consistency** - Must use same `thread_id` when resuming
4. **Decision order matters** - Decisions must match order of `action_requests`
5. **All decisions required** - Must provide decision for each interrupted tool

## Common Pitfall: Wrong Streaming API

⚠️ **DO NOT use `astream_events()`** for HITL - it does not properly surface interrupts!

**Wrong:**
```python
# This will NOT detect interrupts properly
async for event in agent.astream_events(input, config, version="v2"):
    if event["event"] == "on_chain_end":
        # Unreliable - interrupts may not appear here
        if "__interrupt__" in event.get("data", {}).get("output", {}):
            ...
```

**Correct:**
```python
# This WILL detect interrupts properly
async for mode, chunk in agent.astream(input, config, stream_mode=["messages", "updates"]):
    if mode == "updates" and "__interrupt__" in chunk:
        # Reliable interrupt detection
        interrupts.extend(chunk["__interrupt__"])
```

## References

- DeepAgents integration: `deepagents/graph.py` lines 212-213, 296-297
- LangGraph interrupts: `langgraph.types.interrupt()` and `Command`
- Middleware pattern: LangChain's `HumanInTheLoopMiddleware` (via deepagents dependency)
