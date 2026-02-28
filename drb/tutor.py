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


HINT_SYSTEM_PROMPT = (
    "You are a coding tutor helping a student practice algorithm problems. "
    "Give a short hint toward the next step. Do NOT provide code or the full solution. "
    "Be Socratic — guide the student to discover the answer themselves. "
    "Keep hints to 1-3 sentences."
)


def _extract_fenced_block(text: str) -> str:
    """Extract the first fenced code block from text, or empty string."""
    parts = text.split("```")
    if len(parts) >= 3:
        return parts[1].strip()
    return ""


def _extract_last_code_and_output(history: list) -> tuple[str, str]:
    """Extract code and output from the last user message in history."""
    for msg in reversed(history):
        if msg["role"] != "user":
            continue

        content = msg["content"]
        code = _extract_fenced_block(content)

        output = ""
        if "Test output:" in content:
            output_section = content.split("Test output:")[-1].strip()
            if not output_section.startswith("(not run yet)"):
                output = _extract_fenced_block(output_section) or output_section

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
             hint_history: list, config: dict) -> tuple[str, list]:
    """Get a progressive hint from the LLM.

    Returns (hint_text, updated_history).
    hint_history is a list of OpenAI-format messages.
    """
    if not hint_history:
        history = [{"role": "system", "content": HINT_SYSTEM_PROMPT}]
        user_msg = _build_user_message(problem, user_code, test_output, is_first=True)
        history.append({"role": "user", "content": user_msg})
    else:
        history = list(hint_history)
        last_code, last_output = _extract_last_code_and_output(history)
        if user_code.strip() == last_code.strip() and test_output.strip() == last_output.strip():
            history.append({"role": "user", "content": "No changes since last hint."})
        else:
            user_msg = _build_user_message(problem, user_code, test_output, is_first=False)
            history.append({"role": "user", "content": user_msg})

    hint_text = call_openrouter(list(history), config)
    history.append({"role": "assistant", "content": hint_text})

    return hint_text, history


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
