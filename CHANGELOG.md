# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.2] — 2026-04-17

### Fixed (marketplace portability)

- **신규 사용자 키 설정 경로 복구**. 직전 WIP 에서 `plugin.json` 의 `userConfig` 블록을 제거했으나, 이 경우 `/plugin → ensembra → Configure options` UI 자체가 사라져 마켓에서 신규 설치한 사용자가 API 키를 등록할 공식 경로가 없어지는 문제가 확인되었다 (`docs/reports/tasks/2026-04-17-marketplace-portability-audit.md`). v0.7.0 형태의 `userConfig.gemini_api_key` (sensitive:true) + `ollama_endpoint` (sensitive:false) 를 복원하고, `mcpServers.gemini-architect.env` 블록(`GEMINI_API_KEY: "${user_config.gemini_api_key}"`) 도 함께 되살렸다.
- **Windows 지원 추가**. `mcp-servers/gemini-architect/server.py` 에 `_read_keychain_windows()` 를 추가하여 Windows Credential Manager 의 `Claude Code-credentials` 항목을 Win32 `CredReadW` (ctypes, stdlib 유지) 로 직접 조회한다. API 키 해석 폴백 체인은 이제 macOS / Linux / Windows 3 플랫폼 모두에서 동작한다.
- **시작 로그에 Python 버전·플랫폼 노출**. `server.py` start 메시지가 `python=3.x.y, platform=Darwin/Linux/Windows` 를 출력하여, MCP 서버가 조용히 실패할 때 원인 진단이 쉬워진다.
- **Ollama 빈 endpoint 처리 명문화**. `skills/run/SKILL.md` 2단 폴백 설명에 `userConfig.ollama_endpoint` 가 빈 문자열일 때 Ollama 를 건너뛰고 3단(Claude) 으로 직행한다는 규칙을 추가했다.

### Changed

- `mcp-servers/gemini-architect/server.py`: `SERVER_VERSION` 0.7.1 → 0.7.2
- `.claude-plugin/plugin.json` / `.claude-plugin/marketplace.json`: version 0.7.1 → 0.7.2
- `.gitignore`: 프로젝트 루트의 `.mcp.json` (로컬 MCP 등록용, 절대 경로 포함) 제외

### Platform support

- **macOS**: 1차 지원 (Keychain via `security find-generic-password`)
- **Linux**: 2차 지원 (Secret Service via `secret-tool`). secret-tool 이 설치되어 있지 않으면 env `GEMINI_API_KEY` 설정 필요
- **Windows**: 2차 지원 (Credential Manager via Win32 `CredReadW`). `python3` 명령이 PATH 에 없으면 `py launcher` 로 `python` alias 를 마련하거나 env `GEMINI_API_KEY` 를 PowerShell 프로파일에 설정 (`$env:GEMINI_API_KEY = "..."`)

## [0.7.0] — 2026-04-16

### Added

- **MCP server 기반 Gemini architect 재도입** (Gate3 충족). `mcp-servers/gemini-architect/server.py` — Python 3 표준 라이브러리만 사용하는 stdio MCP server. `GEMINI_API_KEY` 를 프로세스 환경변수로만 받아 Gemini REST API 호출. `sensitive: true` 불변식 유지.
  - Gate3 전제조건 3가지 충족: (1) architect 를 MCP server 로 이전, (2) MCP server config 에서만 sensitive 치환, (3) skill/agent content 는 결과만 참조
- **`transport: "mcp"` 추가** — `schemas/config.json` 의 `performerConfig.transport` enum 에 `mcp` 추가 + `mcp_server_name` 필드 신설
- **LLM 호출 배지 규약** — Phase 1 시작 시 각 Performer 의 Transport/Model 현황을 `📡` 배지로 출력 (`CONTRACT.md §8.6`). `config.json logging.show_transport_badge` 로 토글 가능

### Changed

- **architect Transport**: Ollama 단독 → MCP(Gemini) → Ollama → Claude 3단 폴백 체인
  - `agents/architect.md`: Transport 섹션 전면 재작성
  - `agents/orchestrator.md`: Performer 풀 architect 행 갱신 + LLM 호출 배지 출력 의무 추가
  - `skills/run/SKILL.md`: Transport 호출 규약 MCP 분기 추가 + 배지 규약 추가
- `.claude-plugin/plugin.json`: `version` 0.6.0 → 0.7.0, `gemini_api_key` title/description MCP 재도입 반영
- `CONTRACT.md`:
  - §8.1 Transport 테이블에 `mcp` 행 추가
  - §8.2 Performer 레지스트리에 `mcp` transport 설명 추가
  - §8.4 "Gemini 폐지" → "MCP 기반 Gemini 재도입" 으로 전면 재작성
  - §8.5 MCP Transport 호출 규약 신설
  - §8.6 LLM 호출 배지 규약 신설
  - §8.5 (기존 라운드 피로도 대응) → §8.7 로 번호 이동
- `SECURITY.md`: v0.7.0 위협 모델 갱신. MCP server stdout 역류 방지 섹션 추가. Gate3 충족 현황 갱신
- `skills/config/SKILL.md`: (5) Transports 에 Gemini MCP 상태 확인 서브메뉴 복원

### Migration

1. 플러그인 업데이트: `plugin.json` 의 `mcpServers` 필드로 MCP server 가 **자동 등록** 됨 (수동 `settings.local.json` 편집 불필요)
2. Gemini API 키 설정: `/plugin → ensembra → Configure options` 에서 키 입력
3. `/reload-plugins` 실행
4. 키 미설정 시 기존처럼 Ollama → Claude 폴백으로 동작 (행동 변화 없음)

## [0.6.0] — 2026-04-16

### Security (critical — closes structural Gemini key leak)

- **Gemini 경로 폐지 + `sensitive: true` 불변식 복구**. v0.5.1 은 `userConfig.gemini_api_key.sensitive: false` 로 선언해 `${user_config.gemini_api_key}` 치환이 skill/agent content 에서 작동하도록 했으나, 이 치환이 **스킬 호출 시 시스템 프롬프트로 주입** 되어 매 `/ensembra:run` 실행마다 세션 로그(`~/.claude/projects/.../*.jsonl`)와 화면 트랜스크립트에 키가 평문으로 재기록되는 구조적 유출이 실측 확인됨.
  - 실측: 2026-04-16 세션에서 두 번의 키 로테이션에도 불구하고 각 `/ensembra:run` 호출이 새 키를 즉시 재유출하는 것을 확인
  - 근본 원인: skill/agent content 에 sensitive 값을 치환하는 설계는 "스킬 본문 = 시스템 프롬프트" 라는 Claude Code 불변식과 충돌. sensitive 값은 하류 로깅 시스템 전체에 전파되어야만 스킬에서 사용 가능
- **Architect Performer 를 Ollama(`qwen2.5:14b`) 로 이전**. 로컬 HTTP 는 시크릿 불필요하므로 구조적으로 안전. Ollama 가용 실패 시 Claude 서브에이전트(`sonnet`)로 폴백

### Changed

- `.claude-plugin/plugin.json`:
  - `version`: 0.5.1 → 0.6.0
  - `userConfig.gemini_api_key.sensitive`: `false` → `true`
  - `title`, `description` 재작성 — "architect uses Ollama by default; Gemini field reserved for future MCP integration"
- `agents/architect.md`: 기본 Transport 를 `gemini` → `ollama` / `qwen2.5:14b`. Transport 섹션 재작성. Gemini 폐지 배경 설명 추가
- `skills/run/SKILL.md`: "Transport 호출 규약 (architect = Gemini 경우)" 섹션을 "Transport 호출 규약 (architect = Ollama, v0.6.0+)" 로 완전 대체. `${user_config.gemini_api_key}` 참조 제거
- `CONTRACT.md §8.4`: 제목 "Gemini 키 취급 (v0.5.1+ `sensitive: false` — 의식적 타협)" → "Architect Transport 및 Gemini 폐지 (v0.6.0+)" 로 교체. v0.5.1 타협의 실패 배경 + Ollama 이관 + Gate3 이월 조건 기록
- `SECURITY.md`: Gemini 섹션 전면 재작성. "Ensembra 파이프라인은 시크릿을 요구하지 않는다" 를 최상위 원칙으로 승격. v0.5.1 구조적 유출을 근거로 `sensitive: true` 복구 정당화

### Removed

- skill/agent content 내 `${user_config.gemini_api_key}` 치환 참조 전부
- architect 의 Gemini 기본 Transport
- Gemini curl 예시 전부 (CONTRACT/SECURITY/INTERVIEW/README/SKILL.md)

### Migration

사용자는 별도 조치 불필요. 기존 설정된 `gemini_api_key` 값은 OS 키체인에 남되 파이프라인이 참조하지 않는다. 원하면 `/plugin → ensembra → Configure options` 에서 값을 지워도 됨. Ollama 가 localhost 에 없으면 architect 는 Claude 서브에이전트로 자동 폴백하므로 행동 변화 없음.

### Gate3 이월

Gemini 재도입은 architect Performer 를 MCP server 또는 hook command 로 이전한 뒤에만 가능. 선행 조건:
1. architect 를 MCP server 로 구현 (stdio 프로토콜 + manifest)
2. MCP server config 에서 sensitive 치환 사용 (`${user_config.gemini_api_key}`)
3. skill/agent content 는 architect 호출 결과만 참조

### Added (Plan Tier Overlay — prior commit 1c19cc3)

- **`plan_tier` 설정 신설** — Claude 플랜(Pro/Max) 별로 파이프라인 실행 강도를 조절하는 오버레이. preset 자체는 건드리지 않고 위에 겹쳐 적용된다.
  - `pro` (기본): Deep Scan 선택 4항목 off + 강제 6항목 중 3·4·10 압축, Context Snapshot 심볼 목록만, R2 합의율 ≥85% 면 스킵·아니면 diff 요약 전달, Audit 감사자 첫 1명, scribe 입력 요약본. feature 1회 실행 기준 **예상 토큰 ~30%**
  - `max`: preset 원본 동작 그대로 (기존 Ensembra 와 동일)
- **우선순위**: `/ensembra:run --tier=pro|max` 인자 > `~/.claude/config/ensembra/config.json.plan_tier` > 기본값 `"pro"`
- **Auto-Escalation**: pro 실행 중 R1 합의율 40~70% 구간 진입 시 Conductor 가 1회 한정 max R2 승격을 사용자에게 제안
- **금지선** (tier 로 토글 불가): `feature` preset 의 `security`/`qa` Performer 참여, `rounds.*_consensus` 임계값, `reuse_first.device_*` 토글, Deep Scan 강제 6항목의 "미수행" (압축·범위 축소는 허용)
- `/ensembra:config` 메인 메뉴에 **10) Plan Tier** 추가. 기존 "Reset" 은 11번으로 이동
- `schemas/config.json`: `plan_tier` 속성 추가 (enum `pro`/`max`, 기본값 `pro`)
- `skills/run/SKILL.md`: 인자 파싱에 `--tier=` 옵션, **Plan Tier Resolution** 섹션, Phase 0/1/3/4 본문 tier 훅, 출력 포맷 `🎚 plan_tier` 배지
- `skills/config/SKILL.md`: 메인 메뉴 재번호(Reset 10→11), Plan Tier 서브메뉴 신설
- `CONTRACT.md`: §17 "Plan Tier Profiles" 신설. 기존 §17 "Gate2 이월 항목" 은 §18 로 이동
- `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/feature_request.yml`: Gate2 참조 §18 로 갱신

### Design rationale (Plan Tier)

Claude Pro 5시간 롤링 윈도우에서는 토큰 총량보다 **메시지 호출 횟수·컨텍스트 크기**가 실질 병목이다. Performer 수·라운드 수는 preset 정체성이므로 건드리지 않고, **Performer 에 전달되는 입력 크기**와 **R2·Audit 호출 횟수** 를 줄이는 축으로 절감한다. 품질에 가장 민감한 `security`/`qa` 참여와 합의율 임계값은 금지선으로 보호해 "절약 때문에 결론이 뒤집히는" 사고를 구조적으로 차단.

## [0.5.1] — 2026-04-16

### Fixed (critical — v0.5.0 was non-functional for Gemini)

- **`gemini_api_key` marked `sensitive: false`**. v0.5.0 declared it `sensitive: true` and expected Claude Code to substitute `${user_config.gemini_api_key}` in skill/agent content, but actual testing revealed Claude Code intentionally blocks sensitive values from skill/agent content — substituting them with `[sensitive option 'gemini_api_key' not available in skill content]` placeholder. This is an explicit Claude Code security invariant, confirmed both empirically (the v0.5.0 config skill showed the placeholder when loaded into a real session) and by reverse-engineering the binary strings, which document the substitution policy as `"Available as ${user_config.KEY} in MCP/LSP server config, hook commands, and (non-sensitive only) skill/agent content"`. v0.5.0's architect performer could never actually reach the key.

### Trade-off acknowledged

v0.5.1 stores the key in `~/.claude/settings.json` under `pluginConfigs.ensembra@ensembra.options.gemini_api_key` (plaintext, `chmod 0600`). This is a conscious trade-off:

- ✗ Not stored in the OS keychain
- ✓ Actually accessible from skill/agent content (which is where the architect performer dispatches from)
- ✓ Unix home-directory convention — AWS CLI (`~/.aws/credentials`), gcloud, git credentials, `~/.netrc`, `~/.ssh/config` all follow the same pattern
- ✓ File permission `chmod 0600` isolates the key from other user accounts on the same machine
- ✓ `/plugin → Configure options` UI flow remains the only supported setup path
- ✗ Input is **no longer masked** in the `/plugin` dialog (masking was the `sensitive: true` behavior); users should enter the key with nobody looking over their shoulder

### Alternative paths considered and rejected

- **Keep `sensitive: true`, accept architect fallback**: loses the entire Gemini transport
- **Rearchitect architect performer as a hook or MCP server**: hooks can access `$CLAUDE_PLUGIN_OPTION_*` env vars and MCP/LSP configs can substitute sensitive values, but this would require dropping the "all performers are agents/skills" design invariant and is a much larger refactor
- **Hybrid (userConfig + env file fallback)**: this was the v0.3.x–v0.4.x design that the user explicitly asked to remove

### Changed

- `plugin.json`: `userConfig.gemini_api_key.sensitive` set to `false`; `title` and `description` updated with storage location and rotation guidance
- `agents/architect.md`: transport section rewritten to reflect plaintext-home-dir storage
- `SECURITY.md`: full threat model rewritten with the new storage policy, comparison to Unix CLI conventions, and explicit list of residual risks and mitigations
- `CONTRACT.md` §8.4: rewritten for v0.5.1 `sensitive: false` design
- `README.md`: Gemini setup section updated; input-visible warning added; pointer to SECURITY.md rationale
- `INTERVIEW.md`: Q7 decision log extended with the v0.5.1 deliberation

### Migration from v0.5.0

If you configured a key in v0.5.0 via `/plugin → Configure options`, it's currently sitting in the OS keychain where Ensembra cannot read it. Re-enter it in v0.5.1:

```bash
claude plugin marketplace update ensembra
claude plugin update ensembra@ensembra
```

Then in Claude Code:
```
/reload-plugins
/plugin
# → ↓ to ensembra → Enter → Configure options
# → enter the key in gemini_api_key (input is now visible)
# → Save
/reload-plugins
```

The old keychain entry from v0.5.0 can be deleted manually with `security delete-generic-password -s "Claude Safe Storage" -a "Claude Key"` if desired (it's no longer read by Ensembra).

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

[Unreleased]: https://github.com/HotRedMat/ensembra/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/HotRedMat/ensembra/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/HotRedMat/ensembra/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/HotRedMat/ensembra/releases/tag/v0.5.1
[0.5.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.5.0
[0.4.1]: https://github.com/HotRedMat/ensembra/releases/tag/v0.4.1
[0.4.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.4.0
[0.3.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.3.0
[0.2.1]: https://github.com/HotRedMat/ensembra/releases/tag/v0.2.1
[0.2.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.2.0
[0.1.0]: https://github.com/HotRedMat/ensembra/releases/tag/v0.1.0
