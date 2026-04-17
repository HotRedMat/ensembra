<p align="center">
  <img src="./assets/icon-256.png" width="160" height="160" alt="Ensembra icon"/>
</p>

<h1 align="center">Ensembra</h1>

<p align="center">
  <em>Where agents perform in concert — a multi-agent orchestrator plugin for Claude Code.</em>
</p>

<p align="center">
  <a href="https://github.com/HotRedMat/ensembra/releases"><img src="https://img.shields.io/badge/version-0.8.1-blue" alt="version"/></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="license"/></a>
  <img src="https://img.shields.io/badge/plugin%20validate-passing-brightgreen" alt="plugin validate"/>
  <img src="https://img.shields.io/badge/verification-end--to--end-brightgreen" alt="verification"/>
</p>

## Screenshots

<table>
  <tr>
    <td align="center">
      <img src="./assets/screenshot-run.png" width="360" alt="/ensembra:run feature output"/><br/>
      <sub><code>/ensembra:run feature</code> — 5-phase pipeline with consensus and reuse evaluation</sub>
    </td>
    <td align="center">
      <img src="./assets/screenshot-config.png" width="360" alt="/ensembra:config Reuse-First Policy picker"/><br/>
      <sub><code>/ensembra:config</code> — interactive picker with cascade-safe custom mode</sub>
    </td>
  </tr>
  <tr>
    <td align="center" colspan="2">
      <img src="./assets/screenshot-transfer.png" width="500" alt="/ensembra:transfer output"/><br/>
      <sub><code>/ensembra:transfer</code> — 10-section handover document with devils-advocate pitfalls</sub>
    </td>
  </tr>
</table>

## What is Ensembra?

Ensembra is a Claude Code plugin that orchestrates **six specialist agents** and **one scribe** through a **5-phase pipeline** to produce structured code reviews, mutual supervision, automatic documentation, and project handover documents. Built for solo developers who want team-level deliberation without the team.

**Key ideas**:
- **Separation of deliberation and execution**: external LLMs (Ollama / Gemini) debate, Claude Code executes.
- **Reuse-First cross-cutting policy**: four toggleable devices force every performer to consider existing code before writing new code.
- **Deep Source Inspection**: 10-item checklist (6 forced + 4 optional) prevents shallow reads.
- **Consensus-driven flow**: 70/40 thresholds gate Phase 2 execution and halt pipeline on strong disagreement.
- **Automatic documentation**: every task produces a report; weekly roll-ups and handover documents are built-in.

## 5-Phase Pipeline

```
Phase 0 Gather     — Deep Scan produces a shared context snapshot
Phase 1 Deliberate — R1 → (optional R2) → Synthesis with peer signatures
Phase 2 Execute    — Claude Code edits files per the agreed plan
Phase 3 Audit      — designated performers verify the diff
Phase 4 Document   — scribe records Task / Design / Request / Daily / Weekly
```

## Performers (v0.8.0+ Debate/Audit split)

v0.8.0 splits Performers into three tiers. **Opus is forbidden in debate** and used only by the `final-auditor` in Phase 3 — the unanimous-consensus judge.

**Debate (Phase 1) — external LLMs + sonnet-or-lower, no opus:**

| Role | Responsibility | Default Transport | Default Model |
|---|---|---|---|
| 🧭 **planner** | Requirements, acceptance criteria | Claude sub-agent | `sonnet` (v0.8.0: was opus) |
| 🏛 **architect** | Module boundaries, patterns | MCP (Gemini) → Ollama → Claude | `gemini-2.5-flash` |
| 🛠 **developer** | Implementation strategy | Claude sub-agent (opt-in external chain) | `sonnet` |
| 🛡 **security** | Threats, secrets, OWASP | Ollama → Claude | `qwen2.5:14b` |
| 🧪 **qa** | Edge cases, regression | Ollama → Claude | `llama3.1:8b` |
| 😈 **devils-advocate** | Counter-arguments, YAGNI | Claude sub-agent | `haiku` |

**Audit (Phase 3) — specialist auditors → final-auditor:**

| Role | Responsibility | Default Transport | Default Model |
|---|---|---|---|
| (specialists) | Preset-specific specialists (see presets table) | varies | varies |
| ⚖️ **final-auditor** | Unanimous-consensus judge, always last (v0.8.0) | Claude sub-agent | `opus` |

**Document (Phase 4):**

| Role | Responsibility | Default Transport | Default Model |
|---|---|---|---|
| ✍️ **scribe** | Phase 4 documentation | Claude sub-agent | `sonnet` |

Unanimous consensus (v0.8.0) = Phase 1 agreement ≥ 70% **AND** `final-auditor.verdict == pass`. Final-auditor rework is capped at 1 cycle (opus cost control). See `CONTRACT.md §8.8` for the generalized Transport Fallback Chain Protocol and `§11.3` for Final Audit details.

All models auto-fall back to Claude sub-agents when the external transport is unavailable.

## Skills

- `/ensembra:run <preset> <request>` — main pipeline entry point
- `/ensembra:config` — unified interactive settings picker (all options, all cascade-safe)
- `/ensembra:transfer [scope]` — project handover document (full project, path, or natural-language scope)
- `/ensembra:report daily|weekly` — roll-up reports

## Presets

| Preset | Performers | Rounds | Phase 2 | Phase 3 Audit | Phase 4 |
|---|---|---|---|---|---|
| `feature` | all 6 | R1→R2→Syn | on | specialists 5 + **final-auditor** | Task+Design+Request |
| `bugfix` | planner+architect+developer+qa | R1→Syn | on | qa+security + **final-auditor** | Task |
| `refactor` | architect+developer+devils+qa | R1→R2→Syn | on | architect+devils + **final-auditor** | Task+Design+Request |
| `security-audit` | security+devils+architect | R1→Syn | off | — (read-only) | Task |
| `source-analysis` | architect+security+developer | R1→Syn | off | — (read-only) | Task |
| `transfer` | all 6 + scribe | R1 only | off | off | handover doc |

## Installation

### Option A — Load directly for testing

```bash
cd /path/to/your/project
claude --plugin-dir /path/to/ensembra
```

### Option B — Install via marketplace

```bash
claude plugin marketplace add HotRedMat/ensembra
claude plugin install ensembra@ensembra
```

### Ollama setup (optional, for security/qa)

```bash
ollama pull qwen2.5:14b llama3.1:8b
```

### Gemini setup for architect (v0.7.0+, optional)

The architect Performer uses Gemini via MCP server as the primary transport. The MCP server is **automatically registered** when the plugin is installed (`plugin.json` declares `mcpServers`). To enable:

1. Set API key: `/plugin → ensembra → Configure options → gemini_api_key`
2. `/reload-plugins`

That's it — no manual `settings.local.json` editing needed. If Gemini is unavailable (no key set, API error), architect falls back to Ollama (`qwen2.5:14b`), then to a Claude sub-agent — Ensembra works fully without Gemini or Ollama. The API key is stored securely in the OS keychain (`sensitive: true`) and passed only to the MCP server process env — never exposed in skill/agent content or session logs. See [`SECURITY.md`](./SECURITY.md) and `CHANGELOG.md [0.7.0]` for details.

### Prerequisites per platform

The MCP server (`mcp-servers/gemini-architect/server.py`) runs under `python3` and uses only the Python standard library — no `pip install` required. Platform notes:

| OS | Status | Keychain backend | Notes |
|---|---|---|---|
| macOS | Primary | `security find-generic-password` | No extra setup. Keychain service name `Claude Code-credentials` |
| Linux | Secondary | `secret-tool` (libsecret / GNOME Keyring) | Install with `sudo apt install libsecret-tools` or equivalent. Alternative: set env `GEMINI_API_KEY=...` |
| Windows | Secondary | Win32 Credential Manager (`CredReadW`) | `python3` must resolve on PATH. If only `python` is available, add a `python3` alias via the `py` launcher or a PATH shim. Alternative: set `$env:GEMINI_API_KEY` in your PowerShell profile |

If `python3` is not on PATH, the MCP server silently fails and the architect Performer falls back to Ollama → Claude — you will see the fallback in the transport badge but not the underlying Python error. Run `python3 --version` once to confirm.

## Reuse-First Policy

Four devices, toggleable via `/ensembra:config → Reuse-First Policy`:

1. **Deep Scan Inventory** — Phase 0 collects all reusable symbols from `commons/`, `shared/`, `lib/`, etc.
2. **Schema Field** — every R1 output must include `reuse_analysis.decision: reuse | extend | new` with justification
3. **Auto Disagree** — R2 peers automatically disagree when `new` decisions have weak justification (regex-matched)
4. **Synthesis Report** — a fixed top-level section reports missed reuse opportunities

Quick Select: **Maximum** (default) / Strong / Balanced / Advisory / Off. Custom mode uses cascade rules so no invalid combination is reachable.

## Out of scope

- **Session handoff notes** (mid-work pause/resume) — use external plugins like `d2-ops-handoff`
- **ChatGPT integration** — excluded for ToS and stability reasons; use Claude/Gemini/Ollama

## Documentation

- [`CONTRACT.md`](./CONTRACT.md) — pipeline contract, schemas, Reuse-First policy (Korean)
- [`INTERVIEW.md`](./INTERVIEW.md) — design decision log (Korean)
- [`SECURITY.md`](./SECURITY.md) — threat model and secret handling (Korean)
- [`CHANGELOG.md`](./CHANGELOG.md) — version history and verification results
- [`docs/transfer/2026-04-15-project.md`](./docs/transfer/2026-04-15-project.md) — Ensembra's own handover document (generated by Ensembra itself)

## Verification status

`v0.8.0` is fully verified at the structural and behavioral level:

- `claude plugin validate` passes
- All 9 agents invoked individually in live sessions (6 debate performers + scribe + orchestrator + final-auditor)
- End-to-end runs on `feature`, `bugfix`, `refactor`, `security-audit`, `source-analysis` presets
- `transfer` generated a 528-line handover document for the Ensembra project itself
- `/ensembra:report daily|weekly` handles both populated and empty-week states
- **Rework loop** triggered twice on an intentionally-weak email validator, converging on pass with 19 tests
- **Halt-on-low-consensus** triggered on a deliberately controversial refactor request (0% consensus, pipeline stopped before Phase 2)
- **Ensembra's `source-analysis` preset caught 4 real drift bugs in Ensembra's own code** — the strongest possible proof that the plugin catches real bugs
- **All three transports verified end-to-end**: Ollama (`qwen2.5:14b`, `llama3.1:8b`), Gemini (`gemini-2.5-flash`), Claude sub-agents

See [`CHANGELOG.md`](./CHANGELOG.md) for the full verification log.

## License

MIT © 2026 Seungho Lee
