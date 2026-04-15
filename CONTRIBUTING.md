# Contributing to Ensembra

Thanks for your interest. Ensembra is designed for solo developers, but contributions that stay aligned with the core design are welcome.

## Before you start

1. **Read `CONTRACT.md`** — this is the project's design oracle (in Korean). Every runtime behavior is specified there. Do not propose changes that contradict it without also updating it in the same PR.
2. **Read `INTERVIEW.md`** — the decision log explains *why* design choices were made. If you want to change a decision, say why that rationale no longer holds.
3. **Read the out-of-scope list** in `README.md`:
   - **ChatGPT integration**: excluded for ToS and stability reasons. Do not open PRs that add it.
   - **Session handoff notes**: delegated to external plugins like `d2-ops-handoff`. Do not reimplement it here.

## Development setup

Ensembra is a pure Markdown plugin — no Node or Python runtime is required to develop it.

```bash
git clone https://github.com/HotRedMat/ensembra
cd ensembra
claude plugin validate .
```

To test locally against a sandbox project:

```bash
claude --plugin-dir /path/to/ensembra
/ensembra:run feature "<small request>"
```

### Optional transport setup

- **Ollama**: `ollama pull qwen2.5:14b llama3.1:8b`
- **Gemini**: get a free key at `https://aistudio.google.com/app/apikey`. Claude Code will prompt for it when you install or enable the plugin (`claude plugin install ensembra` or `claude plugin disable ensembra && claude plugin enable ensembra`). The key is stored in your OS keychain, not on disk.

## Making changes

### Scope hierarchy

1. **Small bug fix** (no schema/preset change) — open a PR directly
2. **New feature or behavior change** — open a discussion or issue first; describe the design alignment before coding
3. **Schema or preset change** — requires `CONTRACT.md` update in the same PR, plus a `config.json.version` bump if the config schema changed

### Commit message style

Follow the project convention (see `git log`):

```
<area>: <short title in Korean or English>

- Bulleted change list
- Each line < 80 chars
- End with why, not just what
```

Examples:
- `Gate2 fix: 스킬 디렉토리 이름 접두사 제거`
- `agents/qa: add timezone edge case guidance`

### PR requirements

- CI must pass (`.github/workflows/plugin-validate.yml`)
- `claude plugin validate .` locally
- `CHANGELOG.md` Unreleased section updated
- No secrets in any file — the CI has a regex check that will fail the PR if it finds API key patterns

## Design principles (please respect these)

1. **Separation of deliberation and execution** — external LLMs debate, Claude Code executes. Do not give external performers file-write permissions.
2. **Reuse-First is strict by default** — Maximum quick-preset is shipped as default. Do not weaken this without a documented reason.
3. **Deep Scan forced items are not toggleable** — items 1–4, 9, 10. Do not propose making them optional.
4. **Scribe never deliberates** — it's a recorder, not a critic. Do not give it peer signatures or allow it to modify plans.
5. **Devils-advocate is exempt from auto-disagree** — pushing back against reuse strictness is a legitimate role, not a policy violation.
6. **Consensus thresholds are configurable, not removable** — 70/40 is the default; users can change the values but the mechanism must stay in place.

## Reporting security issues

Do not file public issues for vulnerabilities. Email `misstal80@gmail.com` instead. See `SECURITY.md` for the threat model and secret handling rules.

## Code of Conduct

See `CODE_OF_CONDUCT.md`.

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.
