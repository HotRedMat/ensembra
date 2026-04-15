# Ensembra

> Where agents perform in concert — a multi-agent orchestrator plugin for Claude Code.

**Status**: Gate1 draft — design in progress. Not yet functional.

## Overview
Ensembra is a Claude Code plugin that orchestrates multiple sub-agents through a phase-based pipeline. Think of it as a conductor that coordinates specialist agents to produce a synthesized result from independent analyses and counter-arguments.

## Current Stage
This repository is in **Gate1** (specification and contract). Runtime, language, and build toolchain are intentionally undecided. See `INTERVIEW.md` for the pending decisions and `CONTRACT.md` for the orchestrator-agent interface.

## Roadmap
- **Gate1** — design interview + contract (this stage)
- **Gate2** — runtime implementation (after Gate1 decisions are locked)
- **Gate3** — marketplace submission

## Documents
- `INTERVIEW.md` — open design questions (Korean)
- `CONTRACT.md` — orchestrator ↔ agent contract (Korean)
- `SECURITY.md` — threat model and secret handling (Korean)
- `.claude/agents/orchestrator.md` — orchestrator agent definition

## License
MIT © 2026 Seungho Lee
