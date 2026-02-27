# Token-by-Token Streaming Implementation

## Overview

Updated the chat interface to stream partial LLM outputs token-by-token in real-time, matching the behavior of deepagents-cli.

## Changes Made

### 1. Stream Mode Configuration

**Before:**
```python
stream_mode=["updates"]  # Only complete node updates
```

**After:**
```python
stream_mode=["messages", "updates"]  # Token streaming + node updates
```

### 2. Token Streaming Handler

Added a new handler for the `"messages"` stream mode:

```python
if stream_mode == "messages":
    token, metadata = chunk
    
    if not agent_output_started:
        live.stop()  # Stop spinner on first token
        agent_output_started = True
    
    if hasattr(token, "content") and token.content:
        if isinstance(token.content, str):
            console.print(token.content, end="", markup=False)
            sys.stdout.flush()  # Immediate display
            response_started = True
```

**Key aspects:**
- `end=""` prevents newlines between tokens
- `sys.stdout.flush()` ensures immediate display
- Spinner stops on first token
- `response_started` tracks if text was displayed

### 3. Updates Handler Changes

Modified the `"updates"` handler to work with streamed tokens:

- Removed duplicate text content display (now handled by token streaming)
- Added newline logic after streamed text before tool calls
- Kept tool call display and HITL interrupt handling unchanged

### 4. Interrupt Handling

Added reset of `response_started` flag when resuming after interrupts:

```python
response_started = False  # Reset for next iteration
```

## Behavior

### Before
- Complete messages appeared at once after LLM finished generating
- Noticeable delay for longer responses
- Clean but less responsive UX

### After
- Text appears token-by-token as LLM generates
- Immediate feedback to user
- Matches deepagents-cli streaming behavior
- Still supports HITL interrupts

## Stream Modes Explained

1. **`"messages"`**: Emits partial tokens from LLM as they're generated
   - Format: `(token, metadata)` tuple
   - Use for real-time text streaming

2. **`"updates"`**: Emits complete node updates
   - Format: `{node_name: update_dict}`
   - Required for HITL interrupts (`"__interrupt__"` key)
   - Shows completed tool calls and results

Using both modes provides the best UX while maintaining HITL functionality.
