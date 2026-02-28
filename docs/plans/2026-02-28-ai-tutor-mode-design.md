# AI Tutor Mode Design

**Date:** 2026-02-28
**Status:** Approved

## Problem

Users practicing coding problems may get stuck with no guidance. The practice window currently only shows pass/fail test results, offering no pedagogical support. Users must leave the app to look up hints or solutions.

## Solution

Add an optional AI tutor mode that uses OpenRouter to provide progressive hints and commented solutions. The feature is toggled via CLI, stores config in the existing `config.json`, and surfaces as a slide-out panel in the UI with Hint and Solution buttons.

## Architecture

```
User clicks "Hint" --> JS calls pywebview API --> gui.py get_hint()
                                                      |
                                                tutor.py get_hint()
                                                      |
                                              Build message history
                                              (system + code snapshots + prior hints)
                                                      |
                                              POST to OpenRouter
                                              /api/v1/chat/completions
                                                      |
                                              Return hint text
                                                      |
                                              Display in slide-out panel
```

## Component Details

### 1. CLI — `drb tutor`

New subcommand in `drb/cli.py`:

```
drb tutor on --key sk-or-... [--model qwen/qwen3.5-27b]
drb tutor off
drb tutor status
```

- `on` requires `--key` (or reuses existing key from config). `--model` is optional, defaults to `qwen/qwen3.5-27b`.
- `off` sets `tutor_enabled: false`. Key and model are preserved for next `on`.
- `status` prints enabled state, model, and whether a key is configured (masked).

### 2. Configuration

Stored in `~/.dont-rust-bro/config.json` alongside existing container config:

```json
{
  "engine": "podman",
  "tutor_enabled": true,
  "tutor_api_key": "sk-or-v1-...",
  "tutor_model": "qwen/qwen3.5-27b"
}
```

### 3. Tutor Module (`drb/tutor.py`)

New module. Two main functions:

**`get_hint(problem, user_code, test_output, hint_history, config) -> (hint_text, updated_history)`**

- Builds an OpenAI-compatible message list from hint history
- System prompt: "You are a coding tutor. Give a short hint toward the next step. Do NOT provide code or the full solution. Be Socratic — guide the student to discover the answer."
- Compares current code+output against last user message in history:
  - If different: appends a new user message with updated code/output snapshot
  - If identical: appends "No changes since last hint."
- POSTs to `https://openrouter.ai/api/v1/chat/completions`
- Appends assistant response to history
- Returns (hint_text, updated_history)

**`get_solution(problem, user_code, hint_history, config) -> solution_text`**

- Separate LLM call (not appended to hint history)
- System prompt: "Provide a complete, working solution with comments explaining every step."
- Sends problem + user's current code + hint history as context
- Returns the commented solution

**HTTP layer:** stdlib `urllib.request` + `json`. No external dependencies.

**Request format:**

```python
{
    "model": config["tutor_model"],
    "messages": messages,
    "max_tokens": 1024,  # hints are short
    "temperature": 0.7,
}
```

Headers:
```python
{
    "Authorization": f"Bearer {config['tutor_api_key']}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://dont-rust-bro.com",
    "X-OpenRouter-Title": "dont-rust-bro",
}
```

### 4. Hint History Model

The history is a list of OpenAI-format messages tracking code snapshots at each step:

```
1. System: "You are a coding tutor..."
2. User: "Problem: {description}\n\nMy code:\n```\n{code_v1}\n```\n\nTest output: (not run yet)"
3. Assistant: "Think about what data structure lets you look up values in O(1)..."
4. User: "I updated my code:\n```\n{code_v2}\n```\n\nTest output:\n```\nFAILED...\n```"
5. Assistant: "Good! Now check what you're storing..."
6. User: "No changes since last hint."
7. Assistant: "Consider: are you storing the index or the value?"
```

- History is held in memory in `PracticeWindow` (not persisted to disk)
- Resets to empty on problem navigation
- Each hint click snapshots the current code and test output

### 5. GUI Changes (`drb/gui.py`)

New `Api` methods:

- `is_tutor_enabled() -> bool` — JS calls this on load to enable/disable UI buttons
- `get_hint(code, test_output) -> dict` — returns `{"hint": "...", "error": null}` or `{"hint": null, "error": "..."}`
- `get_solution(code) -> dict` — returns `{"solution": "...", "error": null}` or `{"solution": null, "error": "..."}`

`PracticeWindow` gains:
- `_hint_history: list[dict]` — the message history, reset on problem navigation
- `_tutor_config: dict` — loaded from config.json on init

### 6. UI — Slide-out Tutor Panel (`drb/ui/index.html`)

**Buttons:** Hint and Solution buttons appear in the button bar alongside Prev/Run/Next. They are always visible but **disabled** when tutor mode is off (tooltip: "Enable with: drb tutor on --key YOUR_KEY").

**Panel:**
- Slides in from the right on first hint/solution request
- Takes ~40% of window width; code editor remains visible
- Close button (X) at top-right to collapse
- Scrollable content area showing all hints in sequence (chat-log style)
- Each hint is a styled block with subtle visual separation
- Solution appears in a code block with monospace styling
- "Thinking..." loading state with animation while waiting for LLM

**Layout when panel is open:**

```
+----------------------------+------------------+
|  Problem: Two Sum   [Easy] |   Tutor     [X]  |
|----------------------------|------------------|
|  Description...            |  Hint 1:         |
|----------------------------|  Think about O(1)|
|  Solution:                 |  lookups...      |
|  def two_sum(...):         |                  |
|      _                     |  Hint 2:         |
|                            |  Good! Now check |
|----------------------------|  what you store..|
|  Output:                   |                  |
|  (test results)            |                  |
|----------------------------|                  |
|  [Prev] [Run] [Hint] [Solution] [Next]       |
+-----------------------------------------------+
```

**Behavior:**
- Panel opens automatically when first hint arrives
- Stays open across hint requests
- Closes on X click or problem navigation
- Solution replaces hint content with a clear "Solution" header

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No API key configured | Hint/Solution buttons disabled, tooltip shows setup instructions |
| Network error | Show "Hint unavailable: {error}" in tutor panel |
| Invalid API key (401) | Show "Invalid API key. Run: drb tutor on --key NEW_KEY" |
| Rate limited (429) | Show "Rate limited. Try again in a moment." |
| Timeout (30s) | Show "Request timed out. Try again." |
| Other API errors | Show "Error: {message}" in panel |

Errors do not corrupt hint history — user can retry after an error.

## Files Changed

| File | Change |
|------|--------|
| `drb/tutor.py` | **New** — LLM calls, hint history management, HTTP layer |
| `drb/cli.py` | Add `tutor` subcommand (on/off/status) |
| `drb/gui.py` | Add `get_hint()`, `get_solution()`, `is_tutor_enabled()` to Api; hint history in PracticeWindow |
| `drb/ui/index.html` | Slide-out panel, Hint/Solution buttons, tutor UI logic |
| `drb/container.py` | No structural change (config already supports arbitrary keys) |
| `tests/test_tutor.py` | **New** — unit tests for hint/solution with mocked HTTP |
| `tests/test_cli.py` | Add tutor CLI tests |
| `tests/test_gui.py` | Add tutor API tests |

## What Stays the Same

- Daemon architecture (daemon.py + Unix socket IPC)
- Container execution (runner.py + container.py)
- State management (state.py) — hint history is in-memory only
- Problem loading (problems.py)
- Hook system (UserPromptSubmit/Stop)
- All existing problem packs
- Install flow (tutor is opt-in, not required)
