# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Rename skill directories to drop redundant `ensembra-` prefix so commands resolve to `/ensembra:run`, `/ensembra:config`, `/ensembra:transfer`, `/ensembra:report` instead of the doubled `/ensembra:ensembra-run` form. Validated with `claude plugin validate` and live planner agent invocation.

### Verified
- **End-to-end pipeline smoke test passed.** `/ensembra:run feature` executed on a sandbox JS project requesting `add multiply function + test`. Phase 0~3 all ran, 100% consensus, 0 rework, real file edits applied, resulting tests passed (`node tests/calculator.test.js` → `all tests passed`).
- **All 8 agents individually verified** via `claude --plugin-dir` live invocation: planner (requirements), architect (module design), developer (implementation plan), security (OWASP review), qa (edge cases), devils-advocate (YAGNI pushback), scribe (template fill), orchestrator (pipeline explanation). Each agent honored its role definition, Korean output, and output schema.
- **Reuse-First policy actually applies**: Synthesis report confirmed the multiply-function change reused existing `function X(a,b) { ... }` pattern, `module.exports` object literal, and `console.assert` test style with no new files or dependencies.
- **Audit override logic works**: qa verdict `rework` was correctly overridden because the issues were pre-existing structural limitations (not regressions introduced by the change) and only one auditor out of two flagged it, below the majority threshold. Final verdict: Pass.

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
