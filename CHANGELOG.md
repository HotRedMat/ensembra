# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Rename skill directories to drop redundant `ensembra-` prefix so commands resolve to `/ensembra:run`, `/ensembra:config`, `/ensembra:transfer`, `/ensembra:report` instead of the doubled `/ensembra:ensembra-run` form. Validated with `claude plugin validate` and live planner agent invocation.

## [0.1.0] — 2026-04-15

### Added
- Plugin manifest at `.claude-plugin/plugin.json`
- 7 agents at `agents/`:
  - `orchestrator` (conductor)
  - `planner`, `architect`, `developer`, `security`, `qa`, `devils-advocate` (6 deliberators)
  - `scribe` (Phase 4 documentation)
- 4 skills at `skills/`:
  - `ensembra-run` — main pipeline entry
  - `ensembra-config` — unified interactive settings picker
  - `ensembra-transfer` — handover document generator
  - `ensembra-report` — daily/weekly roll-up
- 6 presets at `presets/`:
  - `feature.yaml`, `bugfix.yaml`, `refactor.yaml`
  - `security-audit.yaml`, `source-analysis.yaml`, `transfer.yaml`
- 3 JSON schemas at `schemas/`:
  - `agent-input.json`, `agent-output.json`, `config.json`
- Gate1 design documents: `CONTRACT.md`, `INTERVIEW.md`, `SECURITY.md`
- Reuse-First cross-cutting policy with 4 toggleable devices (default: Maximum)
- 5-phase pipeline (Gather → Deliberate → Execute → Audit → Document)
- Consensus threshold 70/40 (configurable)
- Deep Scan 10-item checklist (6 forced + 4 optional)

### Architecture decisions
- External LLMs (Ollama, Gemini) are deliberators only; execution stays with Claude Code
- scribe is Phase 4-only and not a deliberator (no Peer Signature, no debate participation)
- Session handoff notes are out of scope (delegated to external plugins)
- ChatGPT is excluded from performers (ToS and stability)

### Known limitations
- Gate2 runtime is not yet validated with `claude plugin validate`
- Ensembra itself needs installation on a real project to test the full pipeline
- Ollama and Gemini API key setup must be done manually before first use

[Unreleased]: https://github.com/HotRedMat/ensembra/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.1.0
