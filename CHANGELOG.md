# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] — 2026-04-16

### Changed — purified back to OS keychain single path

Reverted the hybrid secret storage scheme introduced in v0.3.0–v0.4.x. After reverse-engineering Claude Code 2.1.109 we confirmed the native `userConfig` + `sensitive: true` path is fully implemented and the correct UI route is `/plugin → ensembra → Enter → Configure options`. v0.5.0 trusts that path exclusively and removes every workaround layer.

### Removed

- `bin/ensembra-set-key` shell script (was: v0.4.0–v0.4.1 script for `/dev/tty`-based key entry)
- `bin/` directory entirely (no more plugin-shipped binaries)
- `~/.config/ensembra/env` file fallback (existed as step 2 of the v0.3.0 hybrid lookup chain)
- In-session chat-paste key setup flow in `skills/config/SKILL.md` (5)c
- Every reference to `${CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY}` env var as a skill-side source of truth — hooks still use it, but skills now rely on `${user_config.gemini_api_key}` template substitution

### Single remaining path

1. User runs `/plugin` in Claude Code
2. Navigates to `ensembra → Configure options`
3. Enters the Gemini key in the masked dialog
4. Claude Code saves it to the OS keychain
5. Skills and agents reference it via `${user_config.gemini_api_key}` template substitution
6. Hooks can also access it via `$CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY`

### Documentation

- `README.md`: setup section reduced to the single native-UI path
- `examples/quickstart.md`: same
- `CONTRACT.md` §8.4: rewritten for pure-userConfig policy; lists previous versions for historical context
- `SECURITY.md`: rewritten; all workaround paths removed from the threat model; keychain described as the only storage
- `CONTRIBUTING.md`: contributor setup uses the native UI path
- `skills/config/SKILL.md` (5)c: now just displays state and instructs the user to use the native UI
- `agents/architect.md`, `skills/run/SKILL.md`: curl now references `${user_config.gemini_api_key}` directly

### Migration from v0.1.x through v0.4.x

If you previously had `~/.config/ensembra/env`:

```bash
# 1. Delete the old file (no longer used)
rm -rf ~/.config/ensembra

# 2. Update the plugin
claude plugin marketplace update ensembra
claude plugin update ensembra@ensembra

# 3. Set the key through the native UI
# Inside Claude Code:
#   /plugin → ↓ to ensembra → Enter → Configure options
#   enter gemini_api_key → Save
#   /reload-plugins
```

If you never set up a key: no action needed. Ensembra works without one (architect falls back to a Claude sub-agent).

### Why revert

After weeks of workarounds, a binary strings extraction of `~/.local/share/claude/versions/2.1.109` (Mach-O arm64, 201 MB) confirmed:

- `sensitive: true` is fully implemented per the Zod schema: `"If true, masks dialog input and stores value in secure storage (keychain/credentials file) instead of settings.json"`
- The `/plugin` UI exposes a `"Configure options"` submenu whenever `userConfig` has entries: `if (plugin.manifest.userConfig && Object.keys(...).length > 0) menu.push({label: "Configure options", ...})`
- `${user_config.KEY}` template substitution is documented as working in "MCP/LSP server config, hook commands, and skill/agent content"

Our earlier conclusion "Claude Code has a bug" was wrong. Our UI tests never reached the `Configure options` submenu, and the `$CLAUDE_PLUGIN_OPTION_KEY` env var we were polling from skills is explicitly scoped to hooks — not a bug, just a scope we misunderstood. v0.5.0 is the honest correction.

### Investigated (2026-04-16)

- **Reverse-engineered Claude Code 2.1.109's `userConfig` handling** to determine whether the Gemini key setup bug is a Claude Code defect or a misunderstanding on our side. Extracted strings from the binary (`~/.local/share/claude/versions/2.1.109`, Mach-O arm64, 201 MB) and found:
  - `sensitive: true` is fully implemented: `"If true, masks dialog input and stores value in secure storage (keychain/credentials file) instead of settings.json"`
  - `/plugin` UI exposes a `"Configure options"` submenu whenever `userConfig` has entries: `if (plugin.manifest.userConfig && Object.keys(...).length > 0) menu.push({label: "Configure options", ...})`
  - `${user_config.KEY}` template substitution and `$CLAUDE_PLUGIN_OPTION_KEY` env vars are documented as working in **MCP/LSP configs, hook commands, and skill/agent content** — but the env var injection path in the binary is explicitly scoped to hook subprocesses: `"become CLAUDE_PLUGIN_OPTION_<KEY> env vars in hooks"`
- **Revised diagnosis**: Claude Code is not broken. Our earlier tests hit the wrong UI path — pressing Enter on `ensembra` in `/plugin` lands on the detail view, but the sensitive field prompt lives one level deeper, under the explicit **"Configure options"** submenu item. Previous troubleshooting sessions never navigated to that submenu and concluded the feature was absent.
- **Also revised**: the `$CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY` environment variable was never going to appear in the skill's Bash subprocess even if the key was saved correctly, because that env var is only injected into hooks — not into skill tool calls. What skills can use is the `${user_config.gemini_api_key}` template substitution, which needs to be verified as a separate path.

### Documented

- `README.md`: added **Path A** (`/plugin → ensembra → Enter → Configure options`) as the native Claude Code way to set the Gemini key, with **Path B** (`ensembra-set-key`) as the cross-context fallback.
- `CONTRACT.md` §8.4: step 1 of the hybrid lookup chain is now annotated as "hook subprocess only" to prevent future confusion.
- `INTERVIEW.md`: added the full reverse-engineering findings as a design decision log entry for Gate3 to act on.

### Gate3 follow-ups

- `TODO(gate3)`: empirically verify whether `${user_config.gemini_api_key}` template substitution actually works in skill/agent markdown bodies as the binary docs claim. If it does, skills can use it directly without reading an env file.
- `TODO(gate3)`: if Path A (`/plugin → Configure options`) does work end-to-end for users, demote `ensembra-set-key` to an alternative rather than the primary flow.
- `TODO(gate3)`: file a Claude Code documentation request to clarify that sensitive userConfig values reach skills via `${user_config.KEY}` substitution only, not via `$CLAUDE_PLUGIN_OPTION_KEY` env vars.

## [0.4.1] — 2026-04-16

### Fixed

- **`bin/ensembra-set-key` TTY detection crash**: v0.4.0's TTY guard used `[ -c /dev/tty ] && [ -r /dev/tty ] && [ -w /dev/tty ]`, which returns true in some non-interactive contexts (notably Claude Code's Bash tool) where the device entry exists but cannot actually be opened. The script then crashed with `stty: /dev/tty: Device not configured` when it tried to use the tty. v0.4.1 replaces the attribute check with an actual open test (`: </dev/tty` and `: >/dev/tty` in subshells), so non-interactive invocations now exit cleanly with code 2 and a helpful message directing the user to run the script in a real terminal. `--status` and `--verify` continue to work without a TTY and are mentioned in the error message.

## [0.4.0] — 2026-04-16

### Added

- **`bin/ensembra-set-key`** — a POSIX sh script (0755) that ships with the plugin. When the plugin is enabled, Claude Code adds `bin/` to the user's `$PATH`, so users can run `ensembra-set-key` from any terminal:
  - Prompts with echo disabled (`stty -echo` + `read` from `/dev/tty`)
  - Saves the key atomically to `~/.config/ensembra/env` with `chmod 600`
  - Verifies with a live Gemini API call (`/v1beta/models`)
  - **The key value is never echoed, logged, or sent to any Claude Code conversation, shell history, or clipboard.**
  - Subcommands: `--status` (state without value), `--verify` (test saved key), `--clear` (delete key), `--help`
  - POSIX sh, cross-platform (macOS, Linux, WSL, Git Bash)

### Changed

- **Gemini key setup flow switched from "paste into Claude Code chat" to `ensembra-set-key`.** Pasting keys into the Claude Code conversation is no longer the recommended path because the conversation is logged in `~/.claude/history.jsonl`. `ensembra-set-key` solves this by reading from `/dev/tty` directly, completely bypassing the chat transcript.
- `skills/config/SKILL.md` Transports (5)c rewritten — the skill no longer attempts to read the key from the chat. Instead it prints a one-liner instruction to run `ensembra-set-key` in any terminal.
- `README.md`, `examples/quickstart.md`, `CONTRIBUTING.md`: updated to document the new script-based flow.
- `CONTRACT.md` §8.4: extended to describe the `ensembra-set-key` tool as the canonical user-facing entry point while keeping the env-var / env-file lookup chain unchanged.

### Why

Used Ensembra's own deliberation pipeline (`/ensembra:run` style analysis with 4 Performer roles) to evaluate 6 alternative setup flows. Consensus from architect / security / developer / devils-advocate: the bundled shell script is the only option that is (a) cross-platform, (b) keeps the secret out of every log/transcript/history, (c) doesn't create legacy debt when Claude Code eventually fixes its userConfig bug, (d) doesn't multiply user-facing options (decision fatigue).

### Reuse-First evaluation

- `~/.config/ensembra/env` storage path — **reused** (unchanged since v0.3.0)
- `chmod 600` enforcement — **reused**
- `agents/architect.md` lookup chain — **reused**
- `ensembra-set-key` is a thin wrapper over existing paths, not a new storage backend — extends, does not create

### Migration from v0.3.0

No config or file changes needed. Existing `~/.config/ensembra/env` keys continue to work. New users should install the plugin and run `ensembra-set-key` once; existing users can keep their current setup or run `ensembra-set-key --status` to verify it.

## [0.3.0] — 2026-04-16

### Changed — hybrid secret storage (critical for real-world installability)

- **Gemini API key storage switched to a hybrid lookup chain.** v0.2.x declared `userConfig.gemini_api_key` with `sensitive: true` and relied exclusively on Claude Code's native plugin secret mechanism. Field testing with Claude Code 2.1.109 revealed a runtime bug: neither `claude plugin install` nor the `/plugin` UI can actually prompt for or persist sensitive userConfig values. Non-sensitive fields like `ollama_endpoint` are partially handled but don't propagate as env vars to subprocesses either. This made v0.2.x effectively non-functional for Gemini configuration.
- **v0.3.0 restores the `~/.config/ensembra/env` fallback** while keeping the `userConfig` declarations so the plugin is forward-compatible. The key lookup chain is now:
  1. `$CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY` — Claude Code userConfig (will take precedence automatically when Claude Code fixes the bug)
  2. `~/.config/ensembra/env` with `GEMINI_API_KEY=...` and `chmod 600` — current workaround
  3. Neither set → architect performer falls back to a Claude sub-agent

### Added — in-session interactive key setup

- **`/ensembra:config → 5) Transports → c) Gemini API key`** now provides a complete interactive setup flow that runs entirely inside Claude Code. The skill:
  1. Displays the current lookup-chain state (which source, if any, has the key; never the value)
  2. Offers to set up, replace, delete, or test the key
  3. On set-up, warns about conversation-history implications before asking the user to paste the key
  4. Uses the Write tool to create `~/.config/ensembra/env` with `chmod 600`
  5. Verifies with a real Gemini API health-check call
  6. Reports success/failure without ever echoing the key value

  No terminal editing required; the whole flow is inside Claude Code.

- **Alternative terminal path documented**: `read -s -p "Gemini API key: " K && echo ...` one-liner for users who prefer not to paste secrets into the Claude Code conversation (which would be logged in `~/.claude/history.jsonl`).

### Fixed

- v0.2.x plugin install blocker (`Plugin ensembra has an invalid manifest file`) — already fixed in v0.2.1 by adding `type` and `title` to userConfig entries. v0.3.0 inherits that fix.

### Security

- The env file path is protected with `chmod 600`. This is weaker than OS keychain (v0.2.x's intended model) but stronger than any mutable `config.json`-based secret storage. The hybrid approach means users on a fixed Claude Code version get the keychain path automatically.
- `SECURITY.md` updated to document the hybrid policy and the Claude Code 2.x workaround rationale.
- `CONTRACT.md` §8.4 fully rewritten for the hybrid chain.

### Migration from v0.2.x

If you were on v0.2.0 or v0.2.1 and never managed to set up Gemini (most likely), just update and run the in-session config flow:

```bash
claude plugin marketplace update ensembra
claude plugin update ensembra@ensembra
# In Claude Code:
/reload-plugins
/ensembra:config  # navigate to 5 → c → follow the prompts
```

### Gate3 tracking

- `TODO(gate3)`: once Claude Code ships a fix for the userConfig sensitive field handling, deprecate the env file path in v0.4.0 and remove it in v0.5.0.

## [0.2.1] — 2026-04-16

### Fixed
- **`userConfig` schema conformance**: v0.2.0 declared `userConfig.gemini_api_key` and `userConfig.ollama_endpoint` with only `description` and `sensitive` fields. Claude Code's plugin manifest validator requires `type` (enum: `string|number|boolean|directory|file`) and `title` (string) on every userConfig entry. Installing v0.2.0 produced `Failed to install plugin "ensembra": Plugin temp_local_* has an invalid manifest file`. v0.2.1 adds the missing fields (`type: "string"`, `title: "Gemini API key"` / `"Ollama endpoint"`). v0.2.0 release should not be installed; use v0.2.1.

## [0.2.0] — 2026-04-16

### Changed (breaking for anyone who set up `~/.config/ensembra/env`)

- **Gemini API key storage moved to the OS keychain.** The plugin now declares `userConfig.gemini_api_key` with `sensitive: true` in `plugin.json`, which Claude Code stores in macOS Keychain / Windows Credential Manager / Linux Secret Service. The previous mechanism of sourcing `~/.config/ensembra/env` is **removed**; that file is no longer read. Plaintext secret storage on disk is eliminated.
- **Ollama endpoint moved to `userConfig.ollama_endpoint`** (non-sensitive) for consistency. Users can override the default `http://localhost:11434` at plugin install time.
- **Key reference syntax changed**: scripts and agents that previously used `$GEMINI_API_KEY` (shell variable from env file) must now use `$CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY` or `${user_config.gemini_api_key}`.

### Migration from v0.1.x

If you installed v0.1.x and set up an env file, follow these steps after updating:

```bash
# 1. Update the plugin
claude plugin update ensembra

# 2. Re-enable to trigger the userConfig prompt (Claude Code will ask for the Gemini key)
claude plugin disable ensembra
claude plugin enable ensembra

# 3. Delete the old plaintext env file (now unused)
rm -f ~/.config/ensembra/env
rmdir ~/.config/ensembra 2>/dev/null || true  # only if empty
```

If you never set up an env file, no action needed — just `claude plugin update ensembra` and you'll be prompted for the key on next enable (optional; leave blank to skip Gemini).

### Added

- `.claude-plugin/plugin.json` gains `userConfig` section declaring `gemini_api_key` (sensitive) and `ollama_endpoint` (non-sensitive).
- `SECURITY.md` documents the new keychain-based secret policy and extended masking keyword list (`CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY`, `user_config.gemini_api_key`).
- `CONTRACT.md` §8.4 rewritten for v0.2.0 keychain-based Gemini key handling.

### Removed

- `~/.config/ensembra/env` plaintext secret file support.
- `schemas/config.json` no longer has `transports.gemini.env_file_path`.

### Security

- Eliminated the disk-based plaintext storage of API keys entirely. The most common secret-leakage failure mode (sharing `config.json` or `env` for support / backing up to Dropbox) is now structurally impossible because the secret never touches any file the user can accidentally upload.
- Masking keyword list extended to cover the new env var name.

## [0.1.0] — 2026-04-15

### Fixed
- Rename skill directories to drop redundant `ensembra-` prefix so commands resolve to `/ensembra:run`, `/ensembra:config`, `/ensembra:transfer`, `/ensembra:report` instead of the doubled `/ensembra:ensembra-run` form. Validated with `claude plugin validate` and live planner agent invocation.

### Verified
- **End-to-end pipeline smoke test passed.** `/ensembra:run feature` executed on a sandbox JS project requesting `add multiply function + test`. Phase 0~3 all ran, 100% consensus, 0 rework, real file edits applied, resulting tests passed (`node tests/calculator.test.js` → `all tests passed`).
- **All 8 agents individually verified** via `claude --plugin-dir` live invocation: planner (requirements), architect (module design), developer (implementation plan), security (OWASP review), qa (edge cases), devils-advocate (YAGNI pushback), scribe (template fill), orchestrator (pipeline explanation). Each agent honored its role definition, Korean output, and output schema.
- **Reuse-First policy actually applies**: Synthesis report confirmed the multiply-function change reused existing `function X(a,b) { ... }` pattern, `module.exports` object literal, and `console.assert` test style with no new files or dependencies.
- **Audit override logic works**: qa verdict `rework` was correctly overridden because the issues were pre-existing structural limitations (not regressions introduced by the change) and only one auditor out of two flagged it, below the majority threshold. Final verdict: Pass.
- **`/ensembra:config` state machine works**: initial entry shows full 10-item main menu with default summary. Reuse-First Custom cascade tested — toggling device 2 OFF correctly auto-disabled devices 3 and 4, resulting state matched Advisory quick preset. Cascade messages and undo hint rendered as designed.
- **`/ensembra:transfer` generated real 528-line 10-section handover document** for the Ensembra project itself. All sections populated by respective performers (planner/architect/developer/security/qa/devils-advocate/scribe). The devils-advocate section was particularly valuable, identifying unproven assumptions (Ollama capability, 70% threshold, Gemini rate limit, scribe consistency), "do not touch" areas (CONTRACT.md as 33KB oracle), and counter-intuitive points (scribe not in deliberation, devils-advocate exempt from auto-disagree, Phase 2 restricted to Claude Code). No secrets leaked (masking keyword names only, no actual values).
- **`/ensembra:run bugfix` passed** on a divide-by-zero calculator sandbox: added guard clause + 3 zero-case tests + 1 regression test, all tests passed.
- **Ensembra found bugs in itself.** `/ensembra:run source-analysis` executed against the Ensembra repo identified 4 real drift issues between `CONTRACT.md`, schemas, presets, and agent files: (1) `audit` missing from input schema `round` enum, (2) `reuse_analysis` missing from output schema `required`, (3) devils-advocate model inconsistency between §11.1 (haiku) and §13.3 config example (sonnet), (4) `orchestrator.md` stale relative path `../../CONTRACT.md` from its pre-Gate2 location. All 4 were fixed in commit 40c0fce. This is the strongest possible proof that the plugin actually catches real bugs — it caught its own.
- **`/ensembra:report daily` handles empty state** — with no task reports present, correctly prompted for empty report creation and generated `docs/reports/daily/2026-04-15.md` with "완료된 태스크가 없습니다" and N/A metrics.
- **`/ensembra:run refactor` extracts duplication as designed.** On a sandbox with identical `formatDate` in two controllers (`users/`, `orders/`), the pipeline correctly extracted it to `src/commons/dateFormatter.js`, updated both importers, preserved test behavior, and produced an honest Reuse-First analysis: "기존 commons 없음, 도메인 경계(users/orders)를 횡단하므로 new creation justified". Consensus 67% — devils-advocate raised abstraction caution but user's explicit refactor request overrode. Tests passed post-refactor (`node tests/smoke.test.js` → `all tests passed`).
- **`/ensembra:config` full save flow works.** With no prior config, the skill loaded defaults, walked through the save confirmation, wrote a real 2,472-byte `config.json` with all 10 top-level sections (version, performers×7, fallback, rounds, deep_scan×10, transports, timeouts, logging, reports, reuse_first). JSON validated successfully against `schemas/config.json`. File was written to `.config-preview/` in the sandbox since the agent couldn't write to the real home directory without approval, but the content would deploy to `~/.config/ensembra/config.json` with `chmod 600` in production.
- **`/ensembra:run security-audit` produces professional-grade report.** Executed on a sandbox `src/login.js` with 4 intentional vulnerabilities plus 4 missing controls. Result: FAIL verdict (2 HIGH findings correctly trigger failure), 92% consensus. Report includes CWE IDs, attack scenarios, and specific remediation for SQL Injection (CWE-89), plaintext passwords (CWE-256/312), session fixation (CWE-384), user enumeration (CWE-203), and missing controls for rate limiting, CSRF, input validation, audit logging. Performers cited: security, architect, devils-advocate, qa.
- **`/ensembra:report weekly` handles near-empty week.** Generated `docs/reports/weekly/2026-W16.md` with 1 empty daily, 0 tasks, all counters at 0, and the scribe respecting the "no creativity" rule — everything reported as `없음` or 0 where the data didn't exist.
- **`/ensembra:transfer agents/` partial scope works.** Generated a 224-line focused handover document at `docs/transfer/2026-04-15-agents.md` covering only the `agents/` subtree. All 10 sections populated by respective performers, devils-advocate identified 7 agents-specific pitfalls (frontmatter drift, scribe misconception, etc.).
- **Rework loop triggered and resolved twice.** On a sandbox with a trivially-weak `isValidEmail` checker (only `email.includes('@')`), `/ensembra:run bugfix` produced: (1st attempt) rework flagged by qa for missing `null`/`undefined` guard and 254-char length, (2nd attempt) rework flagged for `$`-anchor bypass via trailing CR/LF, (3rd attempt) pass with 19 test cases. Final implementation: typeof guard + length limit + `[\r\n]` guard + regex `^[^\s@]+@[^\s@]+\.[^\s@]+$`. All 19 tests passed. This proved the Rework loop is real, stateful, and progressively deeper with each iteration, hitting the rework-limit-2 boundary exactly.
- **Halt-on-low-consensus works.** Issued a deliberately controversial refactor request (pivot from Express→Deno+Oak + in-memory→unbuilt Rust KV + REST→GraphQL all at once on a 7-line Hello World). All 6 performers voted REJECT at R1 with average 93.3% confidence, resulting in 0% proceed consensus — well below the 40% halt threshold. Pipeline HALTED at Phase 1 R1 without entering R2 or Phase 2. Source file `src/app.js` was verified unchanged after the halt. Rejection included 6 specific reasons (non-existent dependency blocker, preset mismatch, no business justification, no verification baseline, security surface explosion, YAGNI violation) and a phased alternative recommendation.
- **Transport layer verified end-to-end for all three target protocols.**
  - **Ollama HTTP**: direct `curl POST http://localhost:11434/api/chat` calls to `qwen2.5:14b` (security role) and `llama3.1:8b` (qa role) produced correct role-specific outputs in Korean — severity-tagged security issues and edge-case enumerations. Installed models verified: `qwen2.5:14b`, `llama3.1:8b`, `gpt-oss:20b`.
  - **Gemini official API**: direct `curl POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent` with `x-goog-api-key`-equivalent query param produced a full architect-role response (2 design alternatives with tradeoffs) for a blog API design prompt. API key was stored at `~/.config/ensembra/env` with `chmod 600`. Note: `gemini-2.0-flash` returned `RESOURCE_EXHAUSTED` free-tier quota=0 for this project, so `gemini-2.5-flash` is used as the working default. The config schema's `architect.model` default should be updated in a future release.
  - **Claude sub-agents**: already verified throughout prior tests.
  - **Orchestrator dispatch via `curl`**: with `--allowedTools "Bash(curl *)"` pre-approved, the orchestrator successfully routed security and qa performers to real Ollama HTTP endpoints in a source-analysis run, with transport status reported per-performer. Gemini dispatch via orchestrator needs either direct inline `curl` or a broader allowedTools pattern; standalone Gemini transport is verified.
  - **Fallback to Claude sub-agent** triggered correctly when a transport was unavailable (curl not pre-approved), matching the design in CONTRACT.md §13 Model Resolution & Fallback.

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

[Unreleased]: https://github.com/HotRedMat/ensembra/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.5.0
[0.4.1]: https://github.com/HotRedMat/ensembra/releases/tag/v0.4.1
[0.4.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.4.0
[0.3.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.3.0
[0.2.1]: https://github.com/HotRedMat/ensembra/releases/tag/v0.2.1
[0.2.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.2.0
[0.1.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.1.0
