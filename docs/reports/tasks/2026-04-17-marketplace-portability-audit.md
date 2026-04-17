# Task Report: Marketplace Portability Audit (v0.7.1 WIP)

- **일시**: 2026-04-17
- **프리셋**: source-analysis
- **Plan Tier**: pro (Deep Scan 3/4/10 압축, optional off)
- **합의율**: 100% (3개 공통 이슈에서 architect/security/developer 전원 동의)
- **Rework**: 0회 (R2 자동 스킵, 합의율 ≥ 85%)

## ⚠ 재사용 기회 평가 (Reuse-First 최상단 섹션)

**결정**: `reuse + extend` — 신규 구현 없이 이전 자산 복원/재연결로 해결 가능.

| 재사용 대상 | 위치 | 활용 |
|---|---|---|
| `userConfig.gemini_api_key` / `ollama_endpoint` 블록 | v0.7.0 `plugin.json` (git 이력) | 복원 |
| 3단 폴백 키 해석 로직 | `mcp-servers/gemini-architect/server.py` v0.7.1 | 유지 + Windows 분기 추가 |
| `transports.ollama.endpoint` 기본값 필드 | `schemas/config.json` | SKILL.md 참조 경로 일원화 |
| CONTRACT.md §8 mcpServers 템플릿 | 기존 계약서 | env 블록 복원 근거 |

## 목적

직전 WIP(v0.7.1 후보) 변경 — `plugin.json` 에서 `userConfig` 및 `mcpServers.env` 제거 + `server.py` 에 OS 키체인 직접 조회 폴백 추가 — 이 마켓 배포 시 **신규 사용자의 이식성**을 보장하는지 감사.

## 핵심 결론

**현 WIP 는 마켓 배포 불가**. 로컬 PC에서는 동작하지만(키체인에 구 `userConfig` 로 저장된 API 키가 잔존), 신규 사용자는 `claude plugin install ensembra@ensembra` 후 **키를 설정할 공식 경로 자체가 사라짐**. 직전 `/mcp` 가 connected 로 보였던 것은 기존 키가 keychain 에 남아있었기 때문 — 진짜 이식성 검증이 아님.

## 블로커 (High)

### B1. userConfig 제거로 키 설정 UI 전면 소실

- **발견**: `plugin.json` 에서 `userConfig` 블록 삭제 → `/plugin → ensembra → Configure options` 메뉴가 사라진다 (Claude Code 2.1.x 바이너리 분석 결과, userConfig 엔트리가 없으면 Configure options 항목 미생성 — `CHANGELOG.md [0.5.0]`).
- **영향**: 신규 사용자는 README/SUBMISSION.md 안내("/plugin → ensembra → Configure options → gemini_api_key")를 따라도 해당 메뉴를 찾을 수 없음. 설치 성공 경로 없음.
- **합의**: architect / security / developer 전원.
- **수정**: `userConfig.gemini_api_key (sensitive:true)` + `userConfig.ollama_endpoint (sensitive:false)` 복원. `mcpServers.env` 블록도 `env: { GEMINI_API_KEY: "${user_config.gemini_api_key}" }` 로 복원.

### B2. Windows 미지원 (command + keychain)

- **발견**:
  1. `plugin.json` 의 `command: "python3"` 은 Windows 에서 기본 alias 부재 → Windows Store redirect 발생 또는 not-found. MCP server 프로세스 자체가 뜨지 않음.
  2. `server.py` 의 키체인 폴백은 `Darwin` / `Linux` 만 분기. `platform.system() == "Windows"` 분기 없음 → `_cached_api_key = None` 으로 귀결되어 `RuntimeError`.
- **합의**: architect / security / developer 전원.
- **수정(옵션)**:
  - A) `plugin.json` 에 OS 분기된 command 선언이 가능하다면 macOS/Linux=python3, Windows=python. 불가하면 shim (`run.sh` / `run.cmd`) 로 래핑.
  - B) `server.py` 에 `_read_keychain_windows()` 추가 — PowerShell `Get-StoredCredential` 또는 Windows Credential Manager API 호출.
  - C) Claude Code 가 이미 `pluginSecrets` 를 env 로 주입한다면(Gemini architect 의 `${user_config.gemini_api_key}` 치환) 키체인 직접 조회 자체를 제거하고 env 전용 단순화도 유효. 단 sensitive:true 치환 경로의 동작을 v0.5.1 이슈 재발 없이 재검증해야 함.

### B3. SKILL.md 의 `${user_config.ollama_endpoint}` 참조 깨짐

- **발견**: `skills/run/SKILL.md` Phase 1 Transport 호출 예시에 Ollama endpoint 를 userConfig 치환으로 가정. v0.7.1 에서 userConfig 전부 제거 시 빈 문자열 치환 → curl 오류.
- **합의**: developer + architect(간접).
- **수정**: userConfig 복원 시 자동 해결. 복원하지 않는다면 SKILL.md 의 endpoint 참조를 `~/.claude/config/ensembra/config.json` 의 `transports.ollama.endpoint` (기본값 `http://localhost:11434`) 로 일원화 — `schemas/config.json` 재사용.

## 블로커 (Medium)

### B4. README / SUBMISSION / SECURITY 문서 불일치

- 현 WIP 를 고수할 경우 아래 문서의 "Configure options" 안내가 모두 거짓이 됨:
  - `README.md:114-121` (Gemini setup 섹션)
  - `.marketplace/SUBMISSION.md:125, 179, 212`
  - `CONTRIBUTING.md:33`
  - `examples/quickstart.md:144`
  - `server.py:150-153` RuntimeError 메시지
- **수정**: B1 복원 시 문서 그대로 유지. 제거 유지 시 4개 파일 일괄 수정 필요.

### B5. `python3` 의존성 사전 검증 없음

- `server.py` 는 stdlib 만 사용(pip 의존성 0) — 이건 장점. 하지만 Python 자체가 없으면 MCP 서버가 조용히 실패하고 architect 는 Ollama → Claude 로 폴백되어 **사용자는 Gemini 가 왜 안 붙는지 알 수 없다**.
- **수정**: `.marketplace/SUBMISSION.md` / README Prerequisites 에 `python3 --version` 확인 단계 추가. `server.py` 시작 로그(stderr)에 Python 버전 출력 추가 (이미 `started` 로그는 있음 → `sys.version_info` 노출로 확장).

## 비블로커 / 의도 확인됨

- `LICENSE`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md` 의 `misstal80@gmail.com` — 저자 연락처 의도적 공개. `.marketplace/SECURITY-AUDIT.md:166-172` 에서 이미 재검토 완료.
- `.mcp.json` — 절대 경로 포함. 이번 WIP 에서 `.gitignore` 에 추가함 — OK.
- `.claude/settings.local.json` — 이미 `.gitignore` 대상.
- `assets/ICON.md:42` 의 `/Users/…` 문자열 — 금지 규칙 명시용 (false positive).

## 권고 조치 순서

현재 브랜치는 `main` 이고 `origin/main` 보다 1 commit 앞서 있음 (1a93fff v0.7.0). 순서:

1. **plugin.json 복원**: v0.7.0 형태의 `userConfig` 2필드 + `mcpServers.env` 블록 되살림. `sensitive:true` 치환 경로가 v0.5.1 의 로그 유출 재발하지 않는지 한 번 더 실측 검증 (`/ensembra:run` 실행 후 `~/.claude/projects/.../*.jsonl` grep 으로 키 존재 여부 확인).
2. **Windows 대응 결정**:
   - A안) Windows 지원 선언 유보 — `.marketplace/SUBMISSION.md` 및 README 에 "Supported OS: macOS, Linux" 명시. 간단·정직.
   - B안) Windows 분기 구현 — `server.py _read_keychain_windows()` + `plugin.json` command OS 분기/shim. 작업량 높음.
3. **server.py 버전 판단**: userConfig 가 복원되고 env 주입이 재가동되면 키체인 직접 조회는 "폴백 전용" 으로 남기되, 우선순위를 env → keychain → error 로 유지. 현재 구조 그대로 사용 가능.
4. **문서 갱신**: B1~B3 결정에 따라 최소한의 diff 로 정합화.
5. **커밋 분할 제안**:
   - `fix(plugin): v0.7.1 — userConfig 복원 + Windows 지원 범위 선언`
   - `fix(mcp-server): server.py 시작 로그에 Python 버전 노출`
   - `docs: v0.7.1 문서 정합화`

## 검증 방법 (다음 세션)

- `/mcp` 에서 기존 키가 캐시되어 있지 않은 완전 신규 환경 시뮬레이션: `security delete-generic-password -s "Claude Code-credentials"` 로 키체인 비운 뒤 `claude plugin install` → `/plugin → Configure options` 보이는지 확인 → 키 입력 → `/ensembra:run source-analysis 간단한 요청` E2E 성공.
- 합의율이 다시 ≥ 70% 나와야 통과.

## 참고

- 직전 E2E 검증(오늘 오전) 에서 `/mcp connected` + `mcp__gemini-architect__architect_deliberate` → `pong from gemini` 성공은 **기존 키 잔존** 때문이었음. 마켓 배포 적합성을 보장하지 않음.
- 이 보고서는 Phase 2 실행을 트리거하지 않음 (source-analysis preset). 수정은 사용자가 본 권고를 받아 지시 후 별도 러닝(`feature` 또는 `bugfix` preset)으로 진행.

## Implementation follow-up (2026-04-17, 동일 세션)

사용자가 블로커 해결 옵션 중 "Windows 포함 지원" 방향을 선택하여 이번 사이클에서 즉시 구현 완료. v0.7.1 (WIP) 은 출시하지 않고 v0.7.2 로 바로 점프.

### 반영된 변경

| 블로커 | 조치 |
|---|---|
| B1 userConfig 제거 | `plugin.json` 에 `userConfig.gemini_api_key (sensitive:true)` + `ollama_endpoint (sensitive:false)` + `mcpServers.gemini-architect.env` 블록 복원 (v0.7.0 형태) |
| B2 Windows 미지원 | `server.py` 에 `_read_keychain_windows()` 추가 — Win32 `CredReadW` ctypes (stdlib 유지). `resolve_api_key()` 에 Windows 분기. `plugin.json` 의 `command: "python3"` 은 유지하되 Windows 사용자 대상 Prerequisites 안내를 README 에 추가 |
| B3 SKILL.md endpoint 참조 | userConfig 복원으로 자동 해결. 추가로 "빈 endpoint 시 Claude 직행" 규칙 명문화 |
| B4 문서 불일치 | README 에 Prerequisites per platform 표 추가. CHANGELOG `[0.7.2]` 엔트리 추가. Gemini setup 섹션 문구 미세 수정 |
| B5 python3 fallback 진단 | `server.py` 시작 로그에 `python=x.y.z, platform=...` 노출. README 트러블슈팅 1줄 추가 |

### 변경 파일

- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (version 0.7.2)
- `mcp-servers/gemini-architect/server.py` (v0.7.2, Windows 분기 + 버전 로그)
- `README.md` (Prerequisites 표, 배지 0.7.2)
- `CHANGELOG.md` (`[0.7.2]` 엔트리 신설)
- `skills/run/SKILL.md` (빈 endpoint 처리 문구)
- `.gitignore` (`.mcp.json` 제외)

### 로컬 검증

- `python3 -c "ast.parse(...)"` → OK
- `json.load()` on plugin.json / marketplace.json → OK
- `echo '{"jsonrpc":...}' | python3 server.py` → `v0.7.2 started (python=3.14.2, platform=Darwin)` + `initialize` + `tools/list` 모두 정상 응답

### 미해결 (사용자 수동)

- **신규 사용자 시뮬 E2E**: `security delete-generic-password -s "Claude Code-credentials"` 로 키체인 비움 → `/plugin → ensembra → Configure options → gemini_api_key` 재입력 → `/reload-plugins` → `/mcp connected` 확인 → `/ensembra:run source-analysis "ping"` E2E. 키체인 파괴는 Claude 가 수행하지 않음 (비가역).
- **Windows 실기 검증**: 작성자 환경에는 Windows 머신이 없으므로 `_read_keychain_windows()` 는 스펙 기반 구현 — Windows 사용자 피드백을 받아 이번 사이클 내 후속 패치 여지.
- **git commit**: 사용자 글로벌 규칙상 Claude 가 직접 실행 금지. 변경 파일 검토 후 사용자가 직접 커밋.
