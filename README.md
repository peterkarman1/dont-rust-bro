# dont-rust-bro

> **Alpha software.** This is very early, very buggy, and very much a work in progress. If something breaks, [open an issue on GitHub](https://github.com/peterkarman1/dont-rust-bro/issues).

> Don't let your skills get rusty. Practice coding while your agent does the real work.

Your AI agent writes the code that ships to production. But companies still want you to reverse a linked list on a whiteboard in 8 minutes. Make it make sense.

**dont-rust-bro** pops up leetcode-style coding challenges while your AI agent is busy thinking, so you can grind algorithms during the downtime. Your agent handles the real work. You handle the interview prep. Everybody wins — except maybe the interviewers who think this is how they find good engineers.

## Requirements

- **Python 3.9+** (system python on macOS works)
- **Docker** or **Podman** (for running tests in containers)

## Why?

- AI agents do the actual engineering now
- Companies still interview like it's 2015
- You have dead time while your agent thinks
- Might as well get good at the game they make you play

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/peterkarman1/dont-rust-bro/main/install.sh | bash
```

## Demo

[![dont-rust-bro demo](https://img.youtube.com/vi/71oPOum87IU/maxresdefault.jpg)](https://www.youtube.com/watch?v=71oPOum87IU)

## How it works

When you send Claude a prompt, a practice window pops up with a coding problem. Write your solution, click Run, see if you pass. The window automatically hides when Claude finishes — because the real work comes first.

State is saved, so if the window disappears mid-problem, your code is still there when it comes back.

## AI Tutor Mode

Stuck on a problem? Enable the optional AI tutor for progressive hints and full solutions powered by [OpenRouter](https://openrouter.ai/).

```bash
drb tutor on --key YOUR_OPENROUTER_KEY
```

Click **Hint** for a Socratic nudge toward the next step. Click **Solution** for a fully commented answer. The tutor remembers your conversation — each hint builds on the last, and it notices when you update your code.

```bash
drb tutor off          # disable (keeps your key)
drb tutor status       # check configuration
drb tutor on --model anthropic/claude-sonnet-4  # use a different model
```

Default model: `qwen/qwen3.5-27b` (free tier on OpenRouter). Works with any OpenRouter-supported model.

## Commands

| Command | Description |
|---------|-------------|
| `drb status` | Check daemon status |
| `drb packs list` | List installed problem packs |
| `drb packs use <name>` | Switch active pack |
| `drb tutor on --key KEY` | Enable AI tutor with OpenRouter API key |
| `drb tutor off` | Disable AI tutor |
| `drb tutor status` | Check tutor configuration |
| `drb update` | Pull latest problems |
| `drb stop` | Stop the daemon |
| `drb uninstall` | Remove dont-rust-bro completely |

## Problem Packs

- **python** — Python fundamentals and algorithms (default)
- **javascript** — JavaScript fundamentals and algorithms
- **ruby** — Ruby fundamentals and algorithms
- More coming soon (Rust, Go...)

## Philosophy

Your agent is better at writing production code than you are. That's fine. But until the industry catches up, you still need to prove you can implement Two Sum in under 5 minutes. So let your agent do the work that matters, and use the spare cycles to stay sharp on the stuff that gets you hired.

Don't rust, bro.
