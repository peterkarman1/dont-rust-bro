# AI Tutor Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an optional AI tutor mode that provides progressive hints and commented solutions via OpenRouter LLM integration.

**Architecture:** A new `drb/tutor.py` module handles HTTP calls to OpenRouter and manages hint conversation history. The `Api` class in `gui.py` exposes `get_hint()` and `get_solution()` to JavaScript. A slide-out panel in `index.html` displays tutor responses. Configuration (API key, model, enabled flag) is stored in the existing `config.json` and toggled via `drb tutor on/off`.

**Tech Stack:** Python 3.9+, stdlib `urllib.request` + `json` for HTTP, OpenRouter API (OpenAI-compatible), pywebview JS API bridge, HTML/CSS/JS

**Design doc:** `docs/plans/2026-02-28-ai-tutor-mode-design.md`

---

### Task 1: Tutor module — HTTP call to OpenRouter

**Files:**
- Create: `drb/tutor.py`
- Create: `tests/test_tutor.py`

**Step 1: Write the failing test**

Create `tests/test_tutor.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from drb.tutor import call_openrouter


def test_call_openrouter_success():
    """Test successful API call returns content."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Think about hash maps."}}]
    }).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("drb.tutor.urllib.request.urlopen", return_value=mock_response):
        result = call_openrouter(
            messages=[{"role": "user", "content": "help"}],
            config={"tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"},
        )
    assert result == "Think about hash maps."


def test_call_openrouter_http_error():
    """Test HTTP error returns error string."""
    import urllib.error
    error = urllib.error.HTTPError(
        url="https://openrouter.ai/api/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=MagicMock(read=lambda: b'{"error":{"message":"Invalid API key"}}'),
    )
    with patch("drb.tutor.urllib.request.urlopen", side_effect=error):
        with pytest.raises(Exception, match="401"):
            call_openrouter(
                messages=[{"role": "user", "content": "help"}],
                config={"tutor_api_key": "bad-key", "tutor_model": "qwen/qwen3.5-27b"},
            )


def test_call_openrouter_timeout():
    """Test timeout raises exception."""
    import urllib.error
    with patch("drb.tutor.urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        with pytest.raises(TimeoutError):
            call_openrouter(
                messages=[{"role": "user", "content": "help"}],
                config={"tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"},
            )
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_tutor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'drb.tutor'`

**Step 3: Write minimal implementation**

Create `drb/tutor.py`:

```python
import json
import urllib.request
import urllib.error

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3.5-27b"


def call_openrouter(messages: list, config: dict) -> str:
    """Make a chat completion request to OpenRouter.

    Returns the assistant message content.
    Raises on HTTP errors or timeouts.
    """
    body = json.dumps({
        "model": config.get("tutor_model", DEFAULT_MODEL),
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }).encode()

    headers = {
        "Authorization": f"Bearer {config['tutor_api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://dont-rust-bro.com",
        "X-OpenRouter-Title": "dont-rust-bro",
    }

    req = urllib.request.Request(OPENROUTER_URL, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            err_body = json.loads(e.fp.read().decode())
            msg = err_body.get("error", {}).get("message", e.msg)
        except Exception:
            msg = e.msg
        raise RuntimeError(f"OpenRouter API error ({status}): {msg}")
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_tutor.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add drb/tutor.py tests/test_tutor.py
git commit -m "feat: add OpenRouter HTTP call layer for tutor"
```

---

### Task 2: Tutor module — get_hint with history management

**Files:**
- Modify: `drb/tutor.py`
- Modify: `tests/test_tutor.py`

**Step 1: Write the failing tests**

Append to `tests/test_tutor.py`:

```python
from drb.tutor import get_hint, HINT_SYSTEM_PROMPT


def test_get_hint_first_call():
    """First hint builds initial messages with problem + code."""
    problem = {"title": "Two Sum", "description": "Find two numbers that add up to target."}
    config = {"tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}

    with patch("drb.tutor.call_openrouter", return_value="Think about hash maps.") as mock_call:
        hint, history = get_hint(problem, "def two_sum():\n    pass", "", [], config)

    assert hint == "Think about hash maps."
    assert len(history) == 3  # system + user + assistant
    assert history[0]["role"] == "system"
    assert history[0]["content"] == HINT_SYSTEM_PROMPT
    assert "Two Sum" in history[1]["content"]
    assert "def two_sum" in history[1]["content"]
    assert history[2]["role"] == "assistant"

    # Verify call_openrouter received the right messages
    call_messages = mock_call.call_args[0][0]
    assert len(call_messages) == 2  # system + user (no assistant yet when calling)


def test_get_hint_subsequent_with_code_change():
    """Subsequent hint with changed code appends new user message."""
    problem = {"title": "Two Sum", "description": "Find two numbers."}
    config = {"tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}
    existing_history = [
        {"role": "system", "content": HINT_SYSTEM_PROMPT},
        {"role": "user", "content": "Problem: Two Sum\n\nMy code:\n```\npass\n```\n\nTest output: (not run yet)"},
        {"role": "assistant", "content": "Think about hash maps."},
    ]

    with patch("drb.tutor.call_openrouter", return_value="Good! Now store indices."):
        hint, history = get_hint(problem, "seen = {}", "FAILED", existing_history, config)

    assert hint == "Good! Now store indices."
    assert len(history) == 5  # original 3 + new user + new assistant
    assert "I updated my code" in history[3]["content"]
    assert "seen = {}" in history[3]["content"]
    assert "FAILED" in history[3]["content"]


def test_get_hint_no_changes():
    """Hint with no code/output changes sends 'no changes' message."""
    problem = {"title": "Two Sum", "description": "Find two numbers."}
    config = {"tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}
    existing_history = [
        {"role": "system", "content": HINT_SYSTEM_PROMPT},
        {"role": "user", "content": "Problem: Two Sum\n\nMy code:\n```\npass\n```\n\nTest output: (not run yet)"},
        {"role": "assistant", "content": "Think about hash maps."},
    ]

    with patch("drb.tutor.call_openrouter", return_value="Consider what O(1) lookup means."):
        hint, history = get_hint(problem, "pass", "", existing_history, config)

    assert len(history) == 5
    assert "No changes since last hint" in history[3]["content"]
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_tutor.py::test_get_hint_first_call -v`
Expected: FAIL — `ImportError: cannot import name 'get_hint'`

**Step 3: Write implementation**

Append to `drb/tutor.py`:

```python
HINT_SYSTEM_PROMPT = (
    "You are a coding tutor helping a student practice algorithm problems. "
    "Give a short hint toward the next step. Do NOT provide code or the full solution. "
    "Be Socratic — guide the student to discover the answer themselves. "
    "Keep hints to 1-3 sentences."
)


def _extract_last_code_and_output(history: list) -> tuple:
    """Extract code and output from the last user message in history."""
    for msg in reversed(history):
        if msg["role"] == "user":
            content = msg["content"]
            # Extract code between ``` markers
            code = ""
            if "```" in content:
                parts = content.split("```")
                if len(parts) >= 3:
                    code = parts[1].strip()
            # Extract output
            output = ""
            if "Test output:" in content:
                output_part = content.split("Test output:")[-1].strip()
                if "```" in output_part:
                    output_parts = output_part.split("```")
                    if len(output_parts) >= 2:
                        output = output_parts[1].strip()
                elif output_part.startswith("(not run yet)"):
                    output = ""
                else:
                    output = output_part
            return code, output
    return "", ""


def _build_user_message(problem: dict, user_code: str, test_output: str,
                        is_first: bool) -> str:
    """Build a user message with code and output snapshot."""
    output_str = f"```\n{test_output}\n```" if test_output else "(not run yet)"
    if is_first:
        return (
            f"Problem: {problem['title']}\n{problem['description']}\n\n"
            f"My code:\n```\n{user_code}\n```\n\n"
            f"Test output: {output_str}"
        )
    else:
        return (
            f"I updated my code:\n```\n{user_code}\n```\n\n"
            f"Test output: {output_str}"
        )


def get_hint(problem: dict, user_code: str, test_output: str,
             hint_history: list, config: dict) -> tuple:
    """Get a progressive hint from the LLM.

    Returns (hint_text, updated_history).
    hint_history is a list of OpenAI-format messages.
    """
    if not hint_history:
        # First hint: build initial messages
        history = [{"role": "system", "content": HINT_SYSTEM_PROMPT}]
        user_msg = _build_user_message(problem, user_code, test_output, is_first=True)
        history.append({"role": "user", "content": user_msg})
    else:
        history = list(hint_history)
        # Check for code/output changes
        last_code, last_output = _extract_last_code_and_output(history)
        if user_code.strip() == last_code.strip() and test_output.strip() == last_output.strip():
            history.append({"role": "user", "content": "No changes since last hint."})
        else:
            user_msg = _build_user_message(problem, user_code, test_output, is_first=False)
            history.append({"role": "user", "content": user_msg})

    # Call LLM (send all messages except we don't include the last assistant yet)
    hint_text = call_openrouter(history, config)
    history.append({"role": "assistant", "content": hint_text})

    return hint_text, history
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_tutor.py -v`
Expected: 6 passed

**Step 5: Commit**

```bash
git add drb/tutor.py tests/test_tutor.py
git commit -m "feat: add get_hint with progressive history management"
```

---

### Task 3: Tutor module — get_solution

**Files:**
- Modify: `drb/tutor.py`
- Modify: `tests/test_tutor.py`

**Step 1: Write the failing test**

Append to `tests/test_tutor.py`:

```python
from drb.tutor import get_solution, SOLUTION_SYSTEM_PROMPT


def test_get_solution():
    """Solution call sends problem + code + hint context."""
    problem = {"title": "Two Sum", "description": "Find two numbers."}
    config = {"tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}
    hint_history = [
        {"role": "system", "content": HINT_SYSTEM_PROMPT},
        {"role": "user", "content": "Problem: Two Sum..."},
        {"role": "assistant", "content": "Think about hash maps."},
    ]

    with patch("drb.tutor.call_openrouter", return_value="def two_sum(nums, target):\n    # Use hash map...") as mock_call:
        solution = get_solution(problem, "def two_sum():\n    pass", hint_history, config)

    assert "two_sum" in solution
    # Verify it's a separate call with solution system prompt
    call_messages = mock_call.call_args[0][0]
    assert call_messages[0]["content"] == SOLUTION_SYSTEM_PROMPT
    # Verify hint history is included as context
    assert any("hash maps" in m["content"] for m in call_messages if m["role"] == "user")


def test_get_solution_no_hint_history():
    """Solution works even without any prior hints."""
    problem = {"title": "Two Sum", "description": "Find two numbers."}
    config = {"tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}

    with patch("drb.tutor.call_openrouter", return_value="def two_sum(nums, target):\n    # solution"):
        solution = get_solution(problem, "pass", [], config)

    assert "two_sum" in solution
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_tutor.py::test_get_solution -v`
Expected: FAIL — `ImportError: cannot import name 'get_solution'`

**Step 3: Write implementation**

Append to `drb/tutor.py`:

```python
SOLUTION_SYSTEM_PROMPT = (
    "You are a coding tutor. The student has asked for the full solution. "
    "Provide a complete, working solution to the problem. "
    "Add a comment on every significant line explaining the reasoning and approach. "
    "Make sure the solution is correct and handles edge cases."
)


def get_solution(problem: dict, user_code: str,
                 hint_history: list, config: dict) -> str:
    """Get a fully commented solution from the LLM.

    Separate call from hint history. Returns solution text.
    """
    messages = [{"role": "system", "content": SOLUTION_SYSTEM_PROMPT}]

    # Build context including hint history summary
    context_parts = [
        f"Problem: {problem['title']}\n{problem['description']}",
        f"\nStudent's current code:\n```\n{user_code}\n```",
    ]

    if hint_history:
        hint_summary = "\n".join(
            f"- Hint: {m['content']}" for m in hint_history if m["role"] == "assistant"
        )
        context_parts.append(f"\nPrevious hints given:\n{hint_summary}")

    context_parts.append("\nProvide the complete solution with line-by-line comments.")
    messages.append({"role": "user", "content": "\n".join(context_parts)})

    return call_openrouter(messages, config)
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_tutor.py -v`
Expected: 8 passed

**Step 5: Commit**

```bash
git add drb/tutor.py tests/test_tutor.py
git commit -m "feat: add get_solution for full commented solutions"
```

---

### Task 4: CLI — `drb tutor` subcommand

**Files:**
- Modify: `drb/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: Write the failing tests**

Append to `tests/test_cli.py`:

```python
def test_tutor_on_saves_config(tmp_path):
    """Test that tutor on saves key and model to config."""
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir):
        main(["tutor", "on", "--key", "sk-or-test-123"])

    config_path = os.path.join(state_dir, "config.json")
    with open(config_path) as f:
        config = json.load(f)
    assert config["tutor_enabled"] is True
    assert config["tutor_api_key"] == "sk-or-test-123"
    assert config["tutor_model"] == "qwen/qwen3.5-27b"


def test_tutor_on_custom_model(tmp_path):
    """Test that tutor on accepts custom model."""
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir):
        main(["tutor", "on", "--key", "sk-test", "--model", "anthropic/claude-sonnet-4"])

    config_path = os.path.join(state_dir, "config.json")
    with open(config_path) as f:
        config = json.load(f)
    assert config["tutor_model"] == "anthropic/claude-sonnet-4"


def test_tutor_off(tmp_path):
    """Test that tutor off disables but preserves key/model."""
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    # First enable
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}, f)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir):
        main(["tutor", "off"])

    with open(config_path) as f:
        config = json.load(f)
    assert config["tutor_enabled"] is False
    assert config["tutor_api_key"] == "sk-test"  # preserved


def test_tutor_on_requires_key(tmp_path):
    """Test that tutor on without key and no existing key fails."""
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir):
        with pytest.raises(SystemExit):
            main(["tutor", "on"])
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli.py::test_tutor_on_saves_config -v`
Expected: FAIL — `SystemExit: 1` (unknown command "tutor")

**Step 3: Write implementation**

In `drb/cli.py`, add the `tutor` command block. Add this `elif` before the final `else` block at line 181:

```python
    elif command == "tutor":
        from drb.container import load_config, save_config
        config_path = os.path.join(state_dir, "config.json")
        config = load_config(config_path)

        sub = args[1] if len(args) > 1 else "status"

        if sub == "on":
            # Parse --key and --model flags
            key = None
            model = "qwen/qwen3.5-27b"
            i = 2
            while i < len(args):
                if args[i] == "--key" and i + 1 < len(args):
                    key = args[i + 1]
                    i += 2
                elif args[i] == "--model" and i + 1 < len(args):
                    model = args[i + 1]
                    i += 2
                else:
                    i += 1

            if not key:
                key = config.get("tutor_api_key")
            if not key:
                print("Error: --key is required (no existing key found).", file=sys.stderr)
                sys.exit(1)

            config["tutor_enabled"] = True
            config["tutor_api_key"] = key
            config["tutor_model"] = model
            save_config(config_path, config)
            print(f"Tutor enabled. Model: {model}")

        elif sub == "off":
            config["tutor_enabled"] = False
            save_config(config_path, config)
            print("Tutor disabled.")

        elif sub == "status":
            enabled = config.get("tutor_enabled", False)
            model = config.get("tutor_model", "qwen/qwen3.5-27b")
            has_key = bool(config.get("tutor_api_key"))
            key_display = "configured" if has_key else "not set"
            print(f"Tutor: {'enabled' if enabled else 'disabled'}")
            print(f"Model: {model}")
            print(f"API key: {key_display}")

        else:
            print("Usage: drb tutor [on|off|status] [--key KEY] [--model MODEL]")
```

Also update the usage line at line 68:

```python
        print("Commands: show, hide, stop, status, update, packs, tutor, uninstall")
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: All pass (existing + 4 new)

**Step 5: Commit**

```bash
git add drb/cli.py tests/test_cli.py
git commit -m "feat: add drb tutor CLI subcommand"
```

---

### Task 5: GUI — tutor API methods

**Files:**
- Modify: `drb/gui.py`
- Modify: `tests/test_gui.py`

**Step 1: Write the failing tests**

Append to `tests/test_gui.py`:

```python
def test_api_is_tutor_enabled_default(setup_env):
    """Tutor disabled by default when no config."""
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert pw.api.is_tutor_enabled() is False


def test_api_is_tutor_enabled_when_configured(setup_env):
    """Tutor enabled when config has tutor_enabled=True and a key."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert pw.api.is_tutor_enabled() is True


def test_api_get_hint(setup_env):
    """get_hint returns hint dict and updates history."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)

    with patch("drb.tutor.call_openrouter", return_value="Try a hash map."):
        result = pw.api.get_hint("def add(a, b):\n    pass", "")

    assert result["hint"] == "Try a hash map."
    assert result["error"] is None
    assert len(pw._hint_history) == 3  # system + user + assistant


def test_api_get_hint_error(setup_env):
    """get_hint returns error on failure."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)

    with patch("drb.tutor.call_openrouter", side_effect=RuntimeError("API error (401): Invalid key")):
        result = pw.api.get_hint("code", "")

    assert result["hint"] is None
    assert "401" in result["error"]
    assert len(pw._hint_history) == 0  # history not corrupted


def test_api_get_solution(setup_env):
    """get_solution returns solution dict."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)

    with patch("drb.tutor.call_openrouter", return_value="def add(a, b):\n    # Add two numbers\n    return a + b"):
        result = pw.api.get_solution("def add(a, b):\n    pass")

    assert result["solution"] is not None
    assert result["error"] is None


def test_hint_history_resets_on_navigation(setup_env):
    """Hint history clears when navigating to new problem."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    pw._hint_history = [{"role": "system", "content": "test"}]

    pw.next_problem()
    assert pw._hint_history == []
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_gui.py::test_api_is_tutor_enabled_default -v`
Expected: FAIL — `AttributeError: 'Api' object has no attribute 'is_tutor_enabled'`

**Step 3: Write implementation**

Modify `drb/gui.py`:

Add import at top (line 1-2):

```python
import os

from drb.container import load_config
from drb.problems import load_pack, load_problem
from drb.state import StateManager
```

Add `_hint_history` and `_tutor_config` to `PracticeWindow.__init__` after `self._window = None` (around line 73):

```python
        self._hint_history = []
        config_path = os.path.join(state_dir, "config.json")
        self._tutor_config = load_config(config_path)
```

Add hint history reset to `next_problem` and `prev_problem` methods (after `self._load_current_problem()` in each):

```python
        self._hint_history = []
```

Add three new methods to the `Api` class:

```python
    def is_tutor_enabled(self) -> bool:
        config = self._pw._tutor_config
        return bool(
            config.get("tutor_enabled")
            and config.get("tutor_api_key")
        )

    def get_hint(self, code: str, test_output: str) -> dict:
        from drb.tutor import get_hint

        config = self._pw._tutor_config
        problem = self._pw.current_problem
        try:
            hint, history = get_hint(
                problem, code, test_output,
                self._pw._hint_history, config,
            )
            self._pw._hint_history = history
            return {"hint": hint, "error": None}
        except Exception as e:
            return {"hint": None, "error": str(e)}

    def get_solution(self, code: str) -> dict:
        from drb.tutor import get_solution

        config = self._pw._tutor_config
        problem = self._pw.current_problem
        try:
            solution = get_solution(
                problem, code, self._pw._hint_history, config,
            )
            return {"solution": solution, "error": None}
        except Exception as e:
            return {"solution": None, "error": str(e)}
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_gui.py -v`
Expected: All pass (existing 5 + 6 new)

**Step 5: Commit**

```bash
git add drb/gui.py tests/test_gui.py
git commit -m "feat: add tutor API methods to GUI"
```

---

### Task 6: UI — Hint and Solution buttons + slide-out panel

**Files:**
- Modify: `drb/ui/index.html`

This task is UI-only (HTML/CSS/JS). No Python tests needed — the pywebview API is already tested in Task 5.

**Step 1: Add CSS for tutor panel and buttons**

In `drb/ui/index.html`, add these styles inside the `<style>` block (before `</style>`):

```css
  .btn-hint { background: #1a4a6e; color: #a8d8ff; }
  .btn-hint:disabled { background: #1a2a3e; color: #556; }
  .btn-solution { background: #6e4a1a; color: #ffe0a8; }
  .btn-solution:disabled { background: #3e2a1a; color: #556; }

  .tutor-panel {
    position: fixed; top: 0; right: -40%; width: 40%; height: 100vh;
    background: #1a1a2e; border-left: 1px solid #333;
    transition: right 0.3s ease; z-index: 50;
    display: flex; flex-direction: column;
  }
  .tutor-panel.open { right: 0; }
  .tutor-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px; border-bottom: 1px solid #333;
    font-size: 14px; font-weight: 600;
  }
  .tutor-close {
    background: none; border: none; color: #999; font-size: 18px;
    cursor: pointer; padding: 0 4px;
  }
  .tutor-close:hover { color: #fff; }
  .tutor-body {
    flex: 1; overflow-y: auto; padding: 12px 16px;
  }
  .hint-block {
    margin-bottom: 12px; padding: 10px; border-radius: 6px;
    background: #252545; font-size: 13px; line-height: 1.5; color: #ccc;
  }
  .hint-block .hint-label {
    font-size: 11px; font-weight: 600; color: #a8d8ff;
    margin-bottom: 4px; text-transform: uppercase;
  }
  .solution-block {
    margin-bottom: 12px; padding: 10px; border-radius: 6px;
    background: #1e1e1e; font-family: "Menlo", "Consolas", monospace;
    font-size: 12px; line-height: 1.5; color: #d4d4d4;
    white-space: pre-wrap; word-wrap: break-word;
  }
  .solution-block .solution-label {
    font-size: 11px; font-weight: 600; color: #ffe0a8;
    margin-bottom: 4px; text-transform: uppercase;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  .tutor-thinking {
    color: #999; font-size: 13px; font-style: italic;
  }

  body.tutor-open {
    margin-right: 40%;
  }
```

**Step 2: Add tutor panel HTML**

After the closing `</div>` of `<div class="buttons">` and before `<script>`, add:

```html
  <div class="tutor-panel" id="tutorPanel">
    <div class="tutor-header">
      <span>Tutor</span>
      <button class="tutor-close" onclick="closeTutor()">✕</button>
    </div>
    <div class="tutor-body" id="tutorBody"></div>
  </div>
```

**Step 3: Add buttons to button bar**

Replace the buttons div content to include Hint and Solution:

```html
  <div class="buttons">
    <button class="btn-nav" id="prevBtn" onclick="onPrev()">Prev</button>
    <button class="btn-run" id="runBtn" onclick="onRun()">Run</button>
    <button class="btn-hint" id="hintBtn" onclick="onHint()" disabled title="Enable with: drb tutor on --key YOUR_KEY">Hint</button>
    <button class="btn-solution" id="solutionBtn" onclick="onSolution()" disabled title="Enable with: drb tutor on --key YOUR_KEY">Solution</button>
    <button class="btn-nav" id="nextBtn" onclick="onNext()">Next</button>
  </div>
```

**Step 4: Add JavaScript tutor logic**

Add these functions inside the `<script>` tag, before the `pywebviewready` event listener:

```javascript
  function openTutor() {
    document.getElementById("tutorPanel").classList.add("open");
    document.body.classList.add("tutor-open");
  }

  function closeTutor() {
    document.getElementById("tutorPanel").classList.remove("open");
    document.body.classList.remove("tutor-open");
  }

  function clearTutor() {
    document.getElementById("tutorBody").innerHTML = "";
    closeTutor();
  }

  function addHintBlock(text) {
    const body = document.getElementById("tutorBody");
    const block = document.createElement("div");
    block.className = "hint-block";
    const label = document.createElement("div");
    label.className = "hint-label";
    const hintCount = body.querySelectorAll(".hint-block").length + 1;
    label.textContent = "Hint " + hintCount;
    block.appendChild(label);
    const content = document.createElement("div");
    content.textContent = text;
    block.appendChild(content);
    body.appendChild(block);
    body.scrollTop = body.scrollHeight;
  }

  function addSolutionBlock(text) {
    const body = document.getElementById("tutorBody");
    const block = document.createElement("div");
    block.className = "solution-block";
    const label = document.createElement("div");
    label.className = "solution-label";
    label.textContent = "Solution";
    block.appendChild(label);
    const content = document.createElement("div");
    content.textContent = text;
    block.appendChild(content);
    body.appendChild(block);
    body.scrollTop = body.scrollHeight;
  }

  function showThinking() {
    const body = document.getElementById("tutorBody");
    const el = document.createElement("div");
    el.className = "tutor-thinking";
    el.id = "tutorThinking";
    el.textContent = "Thinking...";
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
  }

  function hideThinking() {
    const el = document.getElementById("tutorThinking");
    if (el) el.remove();
  }

  function addErrorBlock(text) {
    const body = document.getElementById("tutorBody");
    const block = document.createElement("div");
    block.className = "hint-block";
    block.style.borderLeft = "3px solid #9b2226";
    block.textContent = text;
    body.appendChild(block);
    body.scrollTop = body.scrollHeight;
  }

  async function onHint() {
    const btn = document.getElementById("hintBtn");
    btn.disabled = true;
    openTutor();
    showThinking();
    const code = document.getElementById("code").value;
    const output = document.getElementById("output").textContent;
    try {
      const result = await window.pywebview.api.get_hint(code, output);
      hideThinking();
      if (result.error) {
        addErrorBlock(result.error);
      } else {
        addHintBlock(result.hint);
      }
    } catch (e) {
      hideThinking();
      addErrorBlock("Error: " + e);
    }
    btn.disabled = false;
  }

  async function onSolution() {
    const btn = document.getElementById("solutionBtn");
    btn.disabled = true;
    openTutor();
    showThinking();
    const code = document.getElementById("code").value;
    try {
      const result = await window.pywebview.api.get_solution(code);
      hideThinking();
      if (result.error) {
        addErrorBlock(result.error);
      } else {
        addSolutionBlock(result.solution);
      }
    } catch (e) {
      hideThinking();
      addErrorBlock("Error: " + e);
    }
    btn.disabled = false;
  }
```

**Step 5: Update problem navigation to clear tutor**

In the `onPrev()` and `onNext()` functions, add `clearTutor();` after the `populate(data)` call:

```javascript
  async function onPrev() {
    if (!confirm("Switching problems will erase your progress on the current one. Continue?")) return;
    const data = await window.pywebview.api.prev_problem();
    populate(data);
    clearTutor();
  }

  async function onNext() {
    if (!confirm("Switching problems will erase your progress on the current one. Continue?")) return;
    const data = await window.pywebview.api.next_problem();
    populate(data);
    clearTutor();
  }
```

**Step 6: Update pywebviewready to check tutor status**

Update the `pywebviewready` event listener to enable/disable tutor buttons:

```javascript
  window.addEventListener("pywebviewready", async () => {
    const data = await window.pywebview.api.get_problem();
    populate(data);
    const tutorEnabled = await window.pywebview.api.is_tutor_enabled();
    if (tutorEnabled) {
      document.getElementById("hintBtn").disabled = false;
      document.getElementById("hintBtn").title = "";
      document.getElementById("solutionBtn").disabled = false;
      document.getElementById("solutionBtn").title = "";
    }
  });
```

**Step 7: Commit**

```bash
git add drb/ui/index.html
git commit -m "feat: add tutor slide-out panel with hint and solution buttons"
```

---

### Task 7: Run full test suite and update docs

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass

**Step 2: Update CLAUDE.md**

Add tutor module to the key modules table:

```markdown
| `drb/tutor.py` | `get_hint()`, `get_solution()` — OpenRouter LLM integration for progressive hints |
```

Add tutor to the data flow section:

```markdown
- **Tutor config** persists to `~/.dont-rust-bro/config.json` (tutor_enabled, tutor_api_key, tutor_model)
- **Hint history** held in memory (resets on problem navigation)
```

Add to the CLI commands in the README-style usage section:

```markdown
| `drb tutor on --key KEY` | Enable AI tutor with OpenRouter API key |
| `drb tutor off` | Disable AI tutor |
| `drb tutor status` | Check tutor configuration |
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with AI tutor module"
```

---

### Task 8: Final verification

**Step 1: Run full test suite one more time**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass

**Step 2: Verify no import errors**

Run: `python3 -c "from drb.tutor import get_hint, get_solution, call_openrouter; print('OK')"`
Expected: `OK`

**Step 3: Verify CLI works**

Run: `python3 -m drb.cli tutor status`
Expected: Prints tutor status (disabled by default)

**Step 4: Push**

```bash
git push
```
