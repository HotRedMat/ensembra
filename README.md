# Ensembra

> Where agents perform in concert — a multi-agent orchestrator plugin for Claude Code.

**Status**: Gate2 in progress — v0.1.0 plugin structure complete, runtime validation pending.

## Overview
Ensembra orchestrates multiple sub-agents through a **5-phase pipeline** with a **Reuse-First cross-cutting policy**. Designed for solo developers who want structured deliberation, mutual supervision, and automatic documentation.

## Pipeline
1. **Gather** — Deep Scan of repo (6 forced + 4 optional items)
2. **Deliberate** — R1 → R2 → Synthesis with 70/40 consensus threshold
3. **Execute** — Claude Code performs the agreed Plan
4. **Audit** — designated performers verify the diff
5. **Document** — scribe records Task Report / Design / Request / Daily / Weekly

## Performers (6 deliberators + 1 scribe)
- 🧭 **planner** — requirements interpretation
- 🏛 **architect** — module boundaries and patterns
- 🛠 **developer** — implementation strategy
- 🛡 **security** — threats and secrets
- 🧪 **qa** — edge cases and regression
- 😈 **devils-advocate** — counter-arguments
- ✍️ **scribe** — Phase 4 documentation (not a deliberator)

## Transports
- **Ollama** (local, free) — `qwen2.5:14b`, `llama3.1:8b`
- **Gemini** (official free API) — `gemini-2.0-flash`
- **Claude sub-agents** — `opus`, `sonnet`, `haiku`
- Automatic fallback to Claude when external transports are unavailable

## Skills
- `/ensembra:run <preset> <request>` — main pipeline
- `/ensembra:config` — unified settings picker (all options)
- `/ensembra:transfer [scope]` — handover document
- `/ensembra:report daily|weekly` — roll-up reports

## Presets
`feature`, `bugfix`, `refactor`, `security-audit`, `source-analysis`, `transfer`

## Out of scope
Session handoff notes (mid-work pause/resume) are handled by external plugins such as `d2-ops-handoff`, not Ensembra.

## Documentation
- `CONTRACT.md` — pipeline contract, schemas, Reuse-First policy (Korean)
- `INTERVIEW.md` — design decision log (Korean)
- `SECURITY.md` — threat model and secret handling (Korean)

## License
MIT © 2026 Seungho Lee
