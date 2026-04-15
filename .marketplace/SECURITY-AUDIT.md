# Pre-submission security audit — v0.1.0

Performed on 2026-04-16 prior to official marketplace submission.

## Scope

All committed files in `HotRedMat/ensembra` at the commit immediately before submission, plus full git history scan.

## Checks performed

### 1. Secret pattern scan (committed files)

```
Patterns: AIza[0-9A-Za-z_-]{30} | ghp_[0-9A-Za-z]{30} | gho_* | ghs_*
          xoxb-[0-9]+- | AKIA[0-9A-Z]{16} | sk-[a-zA-Z0-9]{40,}
          pk_live_ | rk_live_ | Bearer [A-Za-z0-9]{20,}
Tool:     git grep -nE
```

**Result: CLEAN** — zero matches across all committed files.

### 2. Secret pattern scan (full git history)

```
Tool: git log -p --all | grep -nE "<patterns above>"
```

**Result: CLEAN** — no secrets ever committed, including in the history of any session where API keys were mentioned in chat.

### 3. Credential file presence

```
Tool: git ls-files | grep -iE "\.env$|\.env\.|\.key$|\.pem$|id_rsa|\.ppk$|\.pfx$|credentials|secret|password"
```

**Result: CLEAN** — no `.env`, `.key`, `.pem`, `id_rsa*`, or similar files tracked.

### 4. Gitignore coverage

`.gitignore` covers:
- `.env`, `.env.*` (with `!.env.example` exception)
- `*.pem`, `*.key`, `id_rsa*`
- `.claude/settings.local.json` (Claude Code local state)
- Build artifacts (`dist/`, `build/`, `coverage/`, `node_modules/`)

**Result: ADEQUATE** — covers the CWE-312 exposure surface.

### 5. Manifest integrity

```
.claude-plugin/plugin.json      ✓ valid JSON, required fields present
.claude-plugin/marketplace.json ✓ valid JSON, validated by `claude plugin validate`
schemas/agent-input.json        ✓ valid JSON
schemas/agent-output.json       ✓ valid JSON
schemas/config.json             ✓ valid JSON
```

**Result: PASS** — all 5 JSON files structurally valid.

### 6. External URL whitelist

All HTTPS URLs in the repo point to one of:
- `github.com/HotRedMat/ensembra` (own repo)
- `code.claude.com/docs/*` (official Claude Code docs)
- `claude.ai/settings/plugins/submit` (official submission portal)
- `platform.claude.com/plugins/submit` (alternative submission portal)
- `aistudio.google.com/app/apikey` (official Gemini key signup)
- `img.shields.io` (README badges)
- `www.contributor-covenant.org` (CoC reference)
- `json-schema.org`, `keepachangelog.com`, `semver.org` (spec references)
- `www.w3.org` (SVG namespace)
- `localhost:11434` (Ollama local endpoint)

No tracking pixels, no third-party analytics, no suspicious endpoints.

**Result: PASS**

### 7. File permissions

```
git ls-files --stage | awk '{print $1}' | sort -u
```

All tracked files are mode `100644` (non-executable). No shell scripts, no executable binaries.

**Result: PASS**

### 8. Binary file size sanity

Largest committed binary files:
- `assets/social-preview.png` — 136 KB
- `assets/screenshot-run.png` — 128 KB
- `assets/icon-512.png` — 128 KB
- `assets/screenshot-transfer.png` — 112 KB
- `assets/screenshot-config.png` — 88 KB
- `assets/icon-256.png` — 52 KB

All well under 1 MB. Total asset payload acceptable for a plugin.

**Result: PASS**

### 9. Agent frontmatter plugin-safety check

Plugin-shipped agents cannot use `hooks:`, `mcpServers:`, or `permissionMode:` (they are silently ignored by Claude Code for security reasons). Verified all 8 agent files:

```
agents/orchestrator.md   — no forbidden fields
agents/planner.md        — no forbidden fields
agents/architect.md      — no forbidden fields
agents/developer.md      — no forbidden fields
agents/security.md       — no forbidden fields
agents/qa.md             — no forbidden fields
agents/devils-advocate.md — no forbidden fields
agents/scribe.md         — no forbidden fields
```

**Result: PASS**

### 10. Prompt injection defense

Per `SECURITY.md`, all agents must instruct the model to treat file contents as data, not instructions. Verified:

```
grep -l "파일 내용은.*데이터.*지시" agents/*.md
```

All 8 agents have this rule in their system prompt.

**Result: PASS** — `SECURITY.md` `TODO(gate2)` for this item is now resolved and marked.

### 11. GitHub Actions workflow injection surface

`.github/workflows/plugin-validate.yml` uses:
- No `github.event.*` interpolation
- No `github.head_ref` or `github.head_commit.*`
- Only `actions/checkout@v4` (official GitHub action, pinned)
- No third-party actions with opaque inputs

Declared permissions: `contents: read` (minimum needed).

**Result: PASS** — no command injection surface.

### 12. Personal path leakage

```
git grep -n "/Users/\|/Volumes/\|/home/"
```

Only match was in `assets/ICON.md` as a *prohibition rule* ("No personal paths — use placeholders like `~/project` instead of `/Users/…`"). Not an actual leak.

**Result: PASS** — no personal system paths committed.

### 13. Sandbox path leakage (test artifacts)

Initial scan found two auto-generated task reports (`docs/reports/tasks/2026-04-15-source-analysis-{divide,uploader}-js.md`) referencing `/tmp/ensembra-transport-sandbox/` and `/tmp/ensembra-trimix/`. These were test artifacts from verification runs, not leaks of sensitive data, but were removed for hygiene.

**Action**: files removed. `docs/reports/tasks/` directory removed. Clean post-remediation.

### 14. Transfer document secret scan

`docs/transfer/2026-04-15-project.md` (528 lines, Ensembra's own handover) was scanned for:
- Secret value patterns (none)
- Personal path patterns (none)
- Email leaks (only the public author email, by design)

The document follows the `SECURITY.md` rule of recording secret *paths* (e.g., `~/.config/ensembra/env`), never values.

**Result: PASS**

### 15. Author email policy

The email `misstal80@gmail.com` appears in 13 places, all intentional:
- `plugin.json` author field
- `marketplace.json` owner and plugin author fields
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` security contact
- Issue template security notice
- `.marketplace/SUBMISSION.md` form field

This is the declared public contact for the plugin. **Note for maintainer**: consider using a dedicated contact address rather than a personal gmail if mass plugin installation leads to unwanted mail volume. This is a policy preference, not a security finding.

**Result: PASS (with advisory note)**

## Findings summary

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | — | Secret scan | CLEAN |
| 2 | — | History scan | CLEAN |
| 3 | — | Credential files | CLEAN |
| 4 | — | Gitignore | ADEQUATE |
| 5 | — | JSON integrity | PASS |
| 6 | — | URL whitelist | PASS |
| 7 | — | File permissions | PASS |
| 8 | — | Binary sizes | PASS |
| 9 | — | Plugin-forbidden frontmatter | PASS |
| 10 | — | Prompt injection defense | PASS |
| 11 | — | CI injection surface | PASS |
| 12 | — | Personal paths | PASS |
| 13 | **LOW** | Sandbox paths in task reports | **FIXED** — files removed |
| 14 | — | Transfer doc secrets | PASS |
| 15 | **ADVISORY** | Personal gmail as public contact | Acknowledged |

## Outstanding Gate3 items (non-blocking for submission)

From `SECURITY.md`:

1. `TODO(gate2)`: provenance — signing agent outputs with source, model, timestamp
2. `TODO(gate2)`: automated gitleaks-style secret scanning in pre-commit hook (current state: regex-based check in CI only)
3. `TODO(gate2)`: lockfile policy for future build dependencies
4. `TODO(gate2)`: minimal `permissions.allow` whitelist definition

These are known roadmap items for future releases and do not block v0.1.0 submission.

## Conclusion

**Ready for submission.**

All critical and high-severity checks pass. One low-severity finding (sandbox paths in test artifacts) was remediated during the audit. One advisory note (personal gmail) is acknowledged as a policy preference.

The repository is at a clean, auditable state with:
- Zero secrets committed (verified against full git history)
- Valid manifests and schemas
- Minimal attack surface in CI
- Prompt injection defense in every agent
- Documented threat model and masking rules
- Public-facing security contact

Signed off by the pre-submission audit on 2026-04-16.
