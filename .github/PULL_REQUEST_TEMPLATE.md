# Pull Request

## Summary
<!-- One or two sentences. What changes, and why? -->

## Type
<!-- Check all that apply -->
- [ ] Bug fix (does not change schemas, presets, or CONTRACT)
- [ ] New feature
- [ ] Documentation only
- [ ] Refactor (no behavioral change)
- [ ] Schema change (requires `config.json.version` bump)
- [ ] Preset change (may require CONTRACT.md §11 update)

## Changes
<!-- Bulleted list of concrete changes. Reference file paths. -->
-

## Design alignment
- [ ] Changes are consistent with `CONTRACT.md` §1–§17
- [ ] If behavior changed, `CONTRACT.md` was updated in the same PR
- [ ] If a performer role or transport changed, `INTERVIEW.md` decision log was updated
- [ ] `CHANGELOG.md` Unreleased section was updated

## Verification
- [ ] `claude plugin validate .` passes
- [ ] `jq -e . .claude-plugin/plugin.json schemas/*.json` passes (all JSON valid)
- [ ] I ran at least one live test with `claude --plugin-dir .` and confirmed the changed behavior
- [ ] If a schema changed, I ran a pipeline end-to-end to confirm it still validates

## Reuse-First self-audit
- [ ] I checked for existing utilities in `commons/`, `agents/`, `skills/`, `presets/`, `schemas/` before adding new ones
- [ ] If I added new code that duplicates existing patterns, I justified `decision: new` in the PR description

## Security
- [ ] No secrets (`GEMINI_API_KEY`, tokens, passwords, etc.) in commits or this PR description
- [ ] If the change touches `SECURITY.md` threat model, I updated the masking keyword list
- [ ] No new external network calls were added without documenting them

## Breaking changes
<!-- If any, describe migration for existing users. Leave blank if none. -->

## Out of scope reminder
- [ ] This PR does **not** add ChatGPT integration (design decision: excluded for ToS/stability)
- [ ] This PR does **not** add session Handoff functionality (delegated to external plugins like `d2-ops-handoff`)
