# dont-rust-bro

Don't let your skills get rusty. Practice coding while your agent does the real work.

## What is this?

A coding practice popup that shows leetcode-style problems while AI coding agents are working. Instead of watching your agent think, sharpen your skills with bite-sized coding challenges.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/peterkarman1/dont-rust-bro/main/install.sh | bash
```

## How it works

When Claude Code spawns subagents, a practice window pops up with a coding problem. Write your solution and click Run to test it. The window automatically hides when Claude is ready for your input.

## Commands

| Command | Description |
|---------|-------------|
| `drb status` | Check daemon status |
| `drb packs list` | List installed problem packs |
| `drb packs use <name>` | Switch active pack |
| `drb update` | Pull latest problems |
| `drb stop` | Stop the daemon |

## Problem Packs

- **python** - Python fundamentals and algorithms (default)
- More coming soon (JavaScript, Rust, Go...)
