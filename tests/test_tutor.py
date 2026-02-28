import json
import urllib.error

import pytest
from unittest.mock import patch, MagicMock

from drb.tutor import (
    call_openrouter,
    get_hint,
    get_solution,
    HINT_SYSTEM_PROMPT,
    SOLUTION_SYSTEM_PROMPT,
)


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
    """Test HTTP error raises RuntimeError."""
    error = urllib.error.HTTPError(
        url="https://openrouter.ai/api/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=MagicMock(read=lambda: b'{"error":{"message":"Invalid API key"}}'),
    )
    with patch("drb.tutor.urllib.request.urlopen", side_effect=error):
        with pytest.raises(RuntimeError, match="401"):
            call_openrouter(
                messages=[{"role": "user", "content": "help"}],
                config={"tutor_api_key": "bad-key", "tutor_model": "qwen/qwen3.5-27b"},
            )


def test_call_openrouter_timeout():
    """Test timeout raises exception."""
    with patch("drb.tutor.urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        with pytest.raises(TimeoutError):
            call_openrouter(
                messages=[{"role": "user", "content": "help"}],
                config={"tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"},
            )


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
    call_messages = mock_call.call_args[0][0]
    assert call_messages[0]["content"] == SOLUTION_SYSTEM_PROMPT
    assert any("hash maps" in m["content"] for m in call_messages if m["role"] == "user")


def test_get_solution_no_hint_history():
    """Solution works even without any prior hints."""
    problem = {"title": "Two Sum", "description": "Find two numbers."}
    config = {"tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-27b"}

    with patch("drb.tutor.call_openrouter", return_value="def two_sum(nums, target):\n    # solution"):
        solution = get_solution(problem, "pass", [], config)

    assert "two_sum" in solution
