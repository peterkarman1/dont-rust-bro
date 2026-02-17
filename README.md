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

## Commands

| Command | Description |
|---------|-------------|
| `drb status` | Check daemon status |
| `drb packs list` | List installed problem packs |
| `drb packs use <name>` | Switch active pack |
| `drb update` | Pull latest problems |
| `drb stop` | Stop the daemon |
| `drb uninstall` | Remove dont-rust-bro completely |

## Problem Packs

- **python** — Python fundamentals and algorithms (default)
- **javascript** — JavaScript fundamentals and algorithms
- More coming soon (Rust, Go...)

## Philosophy

Your agent is better at writing production code than you are. That's fine. But until the industry catches up, you still need to prove you can implement Two Sum in under 5 minutes. So let your agent do the work that matters, and use the spare cycles to stay sharp on the stuff that gets you hired.

Don't rust, bro.
