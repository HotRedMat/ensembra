# Marketplace Submission — Ensembra v0.5.0

This file contains the exact text and assets to paste into the official Claude Code plugin marketplace submission form at **https://claude.ai/settings/plugins/submit** (or the equivalent at platform.claude.com/plugins/submit).

All assets are committed to this repository under `assets/`. Copy the fields below verbatim.

---

## Form field: Plugin name

```
ensembra
```

## Form field: Repository URL

```
https://github.com/HotRedMat/ensembra
```

## Form field: Version

```
0.5.0
```

## Form field: License

```
MIT
```

## Form field: Short description (≤ 140 chars)

```
Six specialist agents + scribe orchestrated through a 5-phase pipeline with Reuse-First cross-cutting policy. Built for solo developers.
```

*Character count: 133*

## Form field: Long description (Markdown)

```markdown
## Ensembra — where agents perform in concert

Ensembra orchestrates **six specialist agents** (planner, architect, developer, security, qa, devils-advocate) plus **one scribe** through a **5-phase pipeline** to produce structured code reviews, mutual supervision, automatic documentation, and project handover documents. Built for solo developers who want team-level deliberation without the team.

## What makes it different

- **Pure Markdown plugin** — no Node or Python runtime required
- **Three transport options** — Ollama (local, free), Gemini (official free API), Claude sub-agents, with automatic fallback
- **Reuse-First cross-cutting policy** with 4 toggleable devices (Maximum default) — prevents duplication before it happens
- **Deep Scan 10-item checklist** (6 forced + 4 optional) — prevents shallow reads
- **Consensus-driven flow** — 70% confirm, 40% halt; pipeline will refuse to execute on strong disagreement
- **Rework loop** with a 2-attempt limit for iterative bug fixes
- **Automatic documentation** — every task produces a report; weekly roll-ups and handover documents are built-in

## 5-phase pipeline

1. **Gather** — Deep Scan produces a shared context snapshot
2. **Deliberate** — R1 → R2 → Synthesis with peer signatures, 70/40 thresholds
3. **Execute** — Claude Code edits files per the agreed plan
4. **Audit** — designated auditors verify the diff; one fail triggers rework
5. **Document** — scribe writes Task Report / Design Doc / Request Spec / Daily / Weekly

## Skills

- `/ensembra:run <preset> <request>` — main pipeline
- `/ensembra:config` — unified interactive settings picker, cascade-safe
- `/ensembra:transfer [scope]` — handover document generator
- `/ensembra:report daily|weekly` — roll-up reports

## Presets

`feature`, `bugfix`, `refactor`, `security-audit`, `source-analysis`, `transfer`

## Verification

This release has been verified end-to-end:

- ✅ `claude plugin validate` passes
- ✅ All 8 agents individually invoked in live sessions
- ✅ End-to-end runs on 5 presets with real file modifications and passing tests
- ✅ `transfer` generated a 528-line handover document for Ensembra itself
- ✅ **Rework loop triggered twice** on an intentionally-weak email validator, converging on pass with 19 tests
- ✅ **Halt-on-low-consensus triggered** on a deliberately controversial refactor request (0% consensus, pipeline stopped before Phase 2)
- ✅ **Ensembra's `source-analysis` found 4 real drift bugs in Ensembra's own code** — the strongest proof of real bug-catching capability
- ✅ **All three transports verified end-to-end**: Ollama (`qwen2.5:14b`, `llama3.1:8b`), Gemini (`gemini-2.5-flash`), Claude sub-agents

## Out of scope

- **Session handoff notes** (mid-work pause/resume) are handled by external plugins like `d2-ops-handoff`
- **ChatGPT integration** is excluded for ToS and stability reasons
```

## Form field: Category

```
Productivity
```

(Alternative if Productivity is not available: `Developer Tools` or `Code Review`)

## Form field: Tags / Keywords (comma-separated)

```
orchestrator, multi-agent, deliberation, code-review, auto-documentation, reuse-first, handover, ollama, gemini, solo-developer
```

## Form field: Homepage URL

```
https://github.com/HotRedMat/ensembra
```

## Form field: Author name

```
Seungho Lee
```

## Form field: Author email

```
misstal80@gmail.com
```

## Form field: Icon

Upload `assets/icon-256.png` (or `assets/icon-512.png` if a larger size is requested).

SVG source: `assets/icon.svg`

## Form field: Screenshots

Upload the following in order:

1. `assets/screenshot-run.png` — caption: `Main pipeline output with consensus and reuse evaluation`
2. `assets/screenshot-config.png` — caption: `Interactive Reuse-First Policy picker with cascade rules`
3. `assets/screenshot-transfer.png` — caption: `Project handover document with pitfalls section`

## Form field: Social preview / cover image (optional)

Upload `assets/social-preview.png` (1280×640).

Also recommended: on the GitHub repo, set the same file as the repository Social Preview at **Settings → Options → Social preview → Upload image**.

## Form field: Installation instructions

```markdown
\`\`\`bash
claude plugin marketplace add HotRedMat/ensembra
claude plugin install ensembra@ensembra
\`\`\`

### Optional: enable external transports

**Ollama** (for security and qa performers):
\`\`\`bash
ollama pull qwen2.5:14b llama3.1:8b
\`\`\`

**Gemini** (for architect performer):

During plugin install, Claude Code will prompt for the Gemini API key via the native `userConfig` mechanism with `sensitive: true` — the key is stored in the OS keychain (macOS Keychain / Windows Credential Manager / Linux Secret Service), never in a plaintext file.

\`\`\`bash
claude plugin install ensembra
# Prompt: "gemini_api_key (sensitive)" — paste the key, or leave blank to skip
\`\`\`

Free Gemini key at https://aistudio.google.com/app/apikey. Default model: \`gemini-2.5-flash\`. Leave the prompt blank to skip Gemini — the architect performer will use a Claude sub-agent instead.
```

## Form field: Support / contact

- Issues: https://github.com/HotRedMat/ensembra/issues
- Discussions: https://github.com/HotRedMat/ensembra/discussions
- Security: `misstal80@gmail.com` (do not file security issues publicly)

## Form field: Changelog reference

```
https://github.com/HotRedMat/ensembra/blob/main/CHANGELOG.md
```

## Form field: Documentation URL

```
https://github.com/HotRedMat/ensembra#readme
```

---

## Submission checklist

Before clicking submit, verify:

- [ ] Latest main is pushed to `HotRedMat/ensembra`
- [ ] `v0.5.0` tag exists and points to the release commit
- [ ] GitHub Release for `v0.5.0` is published
- [ ] `claude plugin validate .` passes locally
- [ ] `.github/workflows/plugin-validate.yml` CI run is green on main
- [ ] All 7 PNG icons + 3 screenshots + 1 social preview are committed under `assets/`
- [ ] `README.md` header shows the icon and the 3 screenshots
- [ ] No secrets in any commit (gitleaks or grep for `AIza`, `ghp_`, etc.)
- [ ] `.marketplace/SUBMISSION.md` (this file) is up to date with the version being submitted

## After submission

- Anthropic review may take several days
- Check `misstal80@gmail.com` for approval / rejection email
- If approved, the plugin will be listed at `claude.ai/settings/plugins` under Productivity or Developer Tools
- Announce the release: create a GitHub Discussion post, update the README status badge

## If rejected

Common rejection reasons and fixes:

| Reason | Fix |
|---|---|
| Name collision | Change `name` in `plugin.json` and `marketplace.json`, re-tag, resubmit |
| Missing icon | Re-upload from `assets/icon-256.png` |
| Schema validation failure | Run `claude plugin validate .` locally; fix the reported issue |
| Description too long | Use the 140-char short description; move details to long description |
| Inappropriate category | Try `Developer Tools` instead of `Productivity` |
| Missing security contact | Add email to `SECURITY.md` and `plugin.json` author field |
