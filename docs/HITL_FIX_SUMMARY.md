# Human-in-the-Loop (HITL) Fix Summary

> **Fix History:** This document tracks three attempts to fix HITL.
> - **Fix #1-2:** Addressed UI/prompt issues (questionary → prompt_toolkit)
> - **Fix #3:** Fixed the root cause - wrong streaming API (astream_events → astream)
> 
> **Status:** ✅ RESOLVED - HITL now works correctly

## Problem
The human-in-the-loop approval functionality was not working at all - tools requiring approval were executing automatically without prompting the user.

## Root Causes

### Fix Attempt #1 & #2: UI/Prompt Issues (RESOLVED)
The issue was caused by a conflict between **questionary** and **Rich console** libraries:

1. **Terminal State Conflicts**: questionary and Rich were both trying to control terminal state simultaneously
2. **Silent Failures**: questionary's `ask_async()` was returning `None` when it couldn't acquire proper terminal control
3. **Missing Error Handling**: The code didn't handle `None` returns, causing all prompts to fall through to rejection
4. **Event Loop Issues**: Using `ask_async()` in an async context alongside Rich's Live displays caused unpredictable behavior

**Solution (Fix #1):** Replaced questionary with prompt_toolkit

### Fix Attempt #3: Streaming API Issue (RESOLVED)
**The fundamental problem:** The code was using the **wrong streaming API** that doesn't surface interrupts!

1. **Wrong API**: Used `astream_events()` with `version="v2"` 
2. **Interrupts Not Detected**: Tried to detect interrupts via `on_chain_end` events, which doesn't work for HITL
3. **Documentation Mismatch**: LangGraph docs explicitly state HITL requires `astream()` with `stream_mode=["messages", "updates"]`
4. **Approval Never Triggered**: Since interrupts were never detected, the (now working) approval prompt code was never called

## Solution (Fix #3)
Replaced `astream_events()` with `astream()` using proper stream modes for HITL:

### Previous Fix (Fix #1 - Still Valid)
Replaced questionary with **prompt_toolkit** (which is already a dependency and used elsewhere in the codebase):

### Changes Made

1. **Removed questionary dependency** (`pyproject.toml`)
   - Removed `questionary>=2.0.0` from dependencies
   - Reduces potential conflicts and dependency bloat

2. **Rewrote approval prompt** (`chat.py`)
   - Uses `prompt_toolkit.prompt()` directly with custom validator
   - Simple single-character input: `y` (yes), `n` (no), `a` (always)
   - Runs in thread executor to avoid blocking async loop
   - Better error handling for KeyboardInterrupt and EOFError

3. **Added proper error handling**:
   - TTY availability check before prompting
   - Explicit console flushing before taking terminal control
   - Graceful handling of Ctrl+C (KeyboardInterrupt) and Ctrl+D (EOFError)
   - Debug information when terminal issues occur

4. **Improved user experience**:
   - Clear prompt messages with colored output
   - Input validation with helpful error messages
   - Consistent behavior across different terminal environments

## Technical Details

### The Core Issue: Wrong Streaming API

**Before (BROKEN):**
```python
# Using astream_events() - doesn't properly surface interrupts for HITL
async for event in agent.astream_events(
    current_input,
    config=config,
    version="v2",
):
    if event["event"] == "on_chat_model_stream":
        # Handle tokens...
    elif event["event"] == "on_chain_end":
        # Try to detect interrupts - THIS DOESN'T WORK!
        output = event.get("data", {}).get("output", {})
        if isinstance(output, dict) and "__interrupt__" in output:
            interrupts_occurred.extend(output["__interrupt__"])
```

**After (CORRECT):**
```python
# Using astream() with dual stream mode - proper HITL support
async for stream_mode, chunk in agent.astream(
    current_input,
    config=config,
    stream_mode=["messages", "updates"],  # Key change!
):
    if stream_mode == "messages":
        # Handle streaming tokens and tool_call_chunks
        token, metadata = chunk
        if token.content:
            console.print(token.content, end="")
    
    elif stream_mode == "updates":
        # Check for interrupts - THIS WORKS!
        if "__interrupt__" in chunk:
            interrupts_occurred.extend(chunk["__interrupt__"])
        
        # Also handle completed node updates (model, tools)
        for source, update in chunk.items():
            if source == "model":
                # Display completed tool calls
            elif source == "tools":
                # Display tool results
```

### Previous Fix Details (Fix #1)

**Before (with questionary):**
```python
choice = await select(
    "How would you like to proceed?",
    choices=[...],
    style=custom_style,
).ask_async()

# ask_async() could return None silently, causing rejections
```

**After (with prompt_toolkit):**
```python
choice = await loop.run_in_executor(
    None,
    lambda: prompt(
        HTML('<ansicyan><b>Choice [y/n/a]:</b></ansicyan> '),
        style=prompt_style,
        validator=ChoiceValidator(),
    )
)
# Explicit exception handling and validation
```

## Testing

To test the fix:

```bash
# Update dependencies
uv sync

# Start chat with HITL enabled (default)
ldv-agents chat

# Try an action that requires approval (e.g., write_file, edit_file, execute)
# You should now see:
#   - Yellow panel with tool arguments
#   - Prompt: "Choice [y/n/a]:"
#   - Ability to type y, n, or a and press Enter
```

## Benefits

### From Fix #3 (Streaming API):
1. ✅ **HITL Actually Works**: Interrupts are now properly detected and handled
2. ✅ **Follows LangGraph Best Practices**: Uses documented approach for HITL streaming
3. ✅ **Better Streaming Architecture**: Cleaner separation of messages vs updates
4. ✅ **Reliable Interrupt Detection**: No more guessing from `on_chain_end` events
5. ✅ **Future-proof**: Aligned with LangGraph's intended interrupt mechanism

### From Fix #1 (Prompt Toolkit):
1. ✅ **More Reliable**: prompt_toolkit is already used for main input, no conflicts
2. ✅ **Better Error Handling**: Explicit handling of cancellation and terminal issues
3. ✅ **Simpler UX**: Single-character input is faster than arrow key navigation
4. ✅ **Fewer Dependencies**: Removed questionary entirely
5. ✅ **Consistent**: Uses same library as main prompt session

## Backward Compatibility

- No breaking changes to CLI arguments or behavior
- `--auto-approve` flag still works to bypass all prompts
- HITL config remains the same (write_file, edit_file, execute)
