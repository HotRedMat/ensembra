# Ensembra — 설계 결정 인터뷰 (Gate1)

Gate2 진입 전 반드시 답해야 할 질문지. 모든 질문에 답이 채워지고 STEP 0 불확실 항목이 해소되어야 Gate2 로 진입한다.

## Q1. 배포 타깃
- [ ] (a) Claude Code 플러그인 전용 (.claude-plugin/plugin.json 기반, Node 런타임 없음, Markdown 중심)
- [ ] (b) Claude Code 플러그인 + Node CLI 병행 (플러그인에서 bin/ 활용)
- [ ] (c) 미정

## Q2. 언어·런타임
- [ ] (a) 순수 Markdown + YAML frontmatter (가장 가벼움, 런타임 의존 없음)
- [ ] (b) Node.js 20 LTS + TypeScript
- [ ] (c) Python 3.12
- [ ] (d) 미정

## Q3. 오케스트레이션 범위
- [ ] agents/ 만 (서브에이전트 정의만 제공, 호출은 Claude Code 가 담당)
- [ ] commands/ 또는 skills/ 만 (슬래시 커맨드/스킬 형태로 파이프라인 트리거)
- [ ] agents/ + skills/ + hooks/ 전체 (복합 플러그인)

## Q4. 배포 채널
- [ ] 공개 Claude Code 마켓플레이스 (claude.ai/settings/plugins/submit)
- [ ] 사내 private marketplace (팀 레포 기반)
- [ ] 둘 다

## Q5. 시크릿 취급 정책
- [x] **Gemini 공식 API 키 1종 예외 허용**. 저장 위치: `~/.config/ensembra/env` (레포 밖, 사용자 홈).
- 나머지 Performer (Ollama, Claude 서브에이전트) 는 시크릿 불필요.
- ChatGPT 는 Performer 에서 제외 (ToS·안정성 사유).

## Q6. Transport 전략 (추가)
Performer 호출 방식은 3종 혼용으로 확정:
- [x] **Ollama (HTTP)** — `POST http://localhost:11434/api/chat`, `stream: false`, Bash+curl
- [x] **Gemini (공식 무료 API)** — `gemini-2.5-flash`, Google AI Studio 키, Bash+curl
- [x] **Claude 서브에이전트 (in-process)** — Claude Code 내장, 세션 토큰 사용
- [ ] ChatGPT 는 본체에서 제외. 필요 시 Gate3 이후 `ensembra-bridge-chatgpt` 별도 플러그인으로 분리.

## Q8. Deep Source Inspection 강제 (추가)
- [x] 문제 파악·소스 수정·분석 작업은 Phase 0 에서 Deep Scan 8항목 체크리스트를 **필수 수행**. 얕은 읽기 금지.
- [x] Deep Scan 미수행 시 Conductor 는 Phase 1 진입을 거부한다.
- 상세 체크리스트는 `CONTRACT.md` §12 참조.

## Q9. Model Resolution & Fallback (추가)
- [x] 해석 순서: 사용자 config → preset 기본값 → Claude Code 본체 모델(최종 폴백)
- [x] Health check: Ollama `/api/tags`, Gemini `/v1beta/models`, Claude 항상 available
- [x] 외부 transport 실패 시 같은 transport 내 다른 모델 → 그것도 실패면 Claude 본체 모델로 폴백
- [x] 폴백 발생은 Conductor 출력에 배지로 고지

## Q10. Config 방식 (추가, Q11 로 확장됨)
- [x] 플래그·옵션·수동 편집이 **아닌** `/ensembra:config` 선택형 대화로 구성
- [x] Live 모델 목록 조회: Ollama `api/tags`, Gemini `v1beta/models`, Claude 정적 목록
- [x] 저장 경로: `~/.config/ensembra/config.json`, 원자적 쓰기, `chmod 600`
- [x] Claude Code 슬래시 스킬로 구현, Node/Python 런타임 없이 Bash+Markdown 만 사용

## Q11. 설정 전면 통합 (추가)
- [x] **모든 설정**(모델뿐 아니라 프리셋·라운드·Deep Scan·Transport·타임아웃·로깅)을 `/ensembra:config` 선택형 picker 로 관리
- [x] 메인 메뉴 8개 + 서브메뉴 구조. 상세는 `CONTRACT.md` §14
- [x] 수동 JSON 편집은 비권장 (금지 아님). 항상 picker 가 1차 진입점
- [x] `chmod 600`, 원자적 쓰기, 스키마 버전 필드 포함, Reset 지원
- [x] Deep Scan 체크리스트 중 1~4번은 강제 on (얕은 읽기 방지)

## Q7. Gemini 키 관리 (추가)
- [x] 저장 경로: `~/.config/ensembra/env` (레포 외부, gitignore 무관)
- [x] 포맷: `GEMINI_API_KEY=...` 단일 키
- [x] 로딩: Conductor 가 호출 직전 Bash 로 `source ~/.config/ensembra/env` 후 curl 실행
- [x] 로그 마스킹: `Authorization`, `x-goog-api-key`, 쿼리스트링 `key=` 모두 `[REDACTED]`

---

## STEP 0 확인 결과 (Claude Code 공식 스펙)

출처 (2026-04-15 확인):
- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/plugins-reference ✅ 확인
- https://code.claude.com/docs/en/plugin-marketplaces ✅ 확인

### plugin.json 완전 스키마

**위치**: `<plugin-root>/.claude-plugin/plugin.json`
**모든 필드 선택**: 매니페스트 자체가 선택 사항이며, 생략 시 컴포넌트는 기본 디렉토리에서 자동 발견됨. 매니페스트에 포함할 경우 `name` 만 **유일한 필수 필드**.

**메타데이터 필드** (모두 선택):
- `version` (string, SemVer) — 버전 관리, plugin.json 이 marketplace.json 보다 우선
- `description` (string) — 플러그인 목적 요약
- `author` (object) — `name`, `email`, `url`
- `homepage` (string) — 문서 URL
- `repository` (string) — 소스 URL
- `license` (string) — SPDX 식별자 (예: `"MIT"`)
- `keywords` (array) — 검색 태그

**컴포넌트 경로 필드** (기본 디렉토리 대체용, 모두 선택):
- `skills` (string|array) — 기본 `skills/` 대체. `<name>/SKILL.md` 구조
- `commands` (string|array) — 기본 `commands/` 대체. flat `.md` 파일
- `agents` (string|array) — 기본 `agents/` 대체
- `hooks` (string|array|object) — 기본 `hooks/hooks.json` 대체 또는 인라인
- `mcpServers` (string|array|object) — 기본 `.mcp.json` 대체 또는 인라인
- `lspServers` (string|array|object) — 기본 `.lsp.json` 대체 또는 인라인
- `outputStyles` (string|array) — 기본 `output-styles/` 대체
- `monitors` (string|array|object) — 기본 `monitors/monitors.json` 대체
- `userConfig` (object) — 설치 시 사용자에게 물을 값. `sensitive: true` 면 키체인 저장
- `channels` (array) — Telegram/Slack 스타일 메시지 채널

**경로 규칙**:
- 모든 경로는 plugin root 기준 상대 경로, `./` 로 시작 필수
- 커스텀 경로를 지정하면 **기본 디렉토리는 스캔되지 않음** (대체 관계)
- 기본 + 추가 디렉토리 병행하려면 배열로: `"skills": ["./skills/", "./extras/"]`

**환경 변수** (hook/MCP/agent/skill 본문에 치환 가능):
- `${CLAUDE_PLUGIN_ROOT}` — 플러그인 설치 디렉토리. 업데이트 시 변경되므로 **파일 쓰기 금지**
- `${CLAUDE_PLUGIN_DATA}` — 영속 데이터 디렉토리 (`~/.claude/plugins/data/{id}/`). 업데이트 간 유지됨

### 플러그인 디렉토리 레이아웃 (표준)

```
ensembra/
├── .claude-plugin/
│   └── plugin.json              # 매니페스트 (여기에만 위치)
├── agents/                      # 서브에이전트 (plugin root)
│   ├── orchestrator.md
│   ├── planner.md
│   ├── architect.md
│   ├── developer.md
│   ├── security.md
│   ├── qa.md
│   ├── devils-advocate.md
│   └── scribe.md
├── skills/                      # 스킬 (plugin root)
│   ├── ensembra-run/SKILL.md
│   ├── ensembra-config/SKILL.md
│   ├── ensembra-transfer/SKILL.md
│   └── ensembra-report/SKILL.md
├── LICENSE
├── README.md
└── CHANGELOG.md
```

**⚠ 중요**: `agents/`, `skills/`, `commands/`, `hooks/` 등은 **plugin root** 에 두며, `.claude-plugin/` **안에 넣으면 컴포넌트가 로드되지 않음**. `.claude-plugin/` 안에는 **오직 `plugin.json` 만** 둔다.

### Agent frontmatter (플러그인에서 로드 시)

지원 필드: `name`, `description`, `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`, `background`, `isolation`, `color`

**보안상 미지원** (플러그인 agent 에선 무시됨): `hooks`, `mcpServers`, `permissionMode`
- 필요 시 사용자 `.claude/agents/` 로 복사하거나 `settings.json permissions.allow` 활용
- Ensembra 는 이 3개 필드를 orchestrator.md 에서 쓰지 않으므로 **문제 없음**

`isolation` 유효값: `"worktree"` 만.

### 매니페스트 필수 최소 예시 (Ensembra 용 초안)

```json
{
  "name": "ensembra",
  "version": "1.0.0",
  "description": "Multi-agent orchestrator plugin for Claude Code — agents perform in concert",
  "author": {
    "name": "Seungho Lee",
    "email": "misstal80@gmail.com"
  },
  "homepage": "https://github.com/HotRedMat/ensembra",
  "repository": "https://github.com/HotRedMat/ensembra",
  "license": "MIT",
  "keywords": ["orchestrator", "multi-agent", "deliberation", "review", "audit"]
}
```

### marketplace.json 완전 스키마

**위치**: `<marketplace-root>/.claude-plugin/marketplace.json`

**필수 필드**:
- `name` (string, kebab-case) — 마켓플레이스 식별자, 공개됨
- `owner` (object) — `name` 필수, `email` 선택
- `plugins` (array) — 플러그인 목록

**선택 메타데이터**:
- `metadata.description` (string)
- `metadata.version` (string)
- `metadata.pluginRoot` (string) — 상대 경로 prefix (예: `"./plugins"`)

**Plugin entry 필드**:
- `name` (필수) — 플러그인 식별자
- `source` (필수) — 다음 유형 중 하나:
  - 상대 경로: `"./plugins/my-plugin"` (마켓플레이스 레포 내 로컬)
  - `github`: `{"source": "github", "repo": "owner/repo", "ref": "...", "sha": "..."}`
  - `url`: `{"source": "url", "url": "https://...", "ref": "...", "sha": "..."}`
  - `git-subdir`: `{"source": "git-subdir", "url": "...", "path": "tools/plugin", "ref": "..."}`
  - `npm`: `{"source": "npm", "package": "@org/plugin", "version": "^2.0.0"}`
- 선택: `description`, `version`, `author`, `license`, `keywords`, `category`, `tags`, `strict` (기본 true)

**Reserved names** (사용 불가): `claude-code-marketplace`, `anthropic-marketplace`, `official-claude-plugins` 등 — 공식 Anthropic 용으로 예약됨.

### Ensembra 배포 전략 (Q4 공개 마켓플레이스 결정 기반)

두 가지 방식 가능:

**(A) 단일 플러그인 레포** (권장, 간단):
- 이 레포(`HotRedMat/ensembra`) 자체를 플러그인으로 구성
- `.claude-plugin/plugin.json` 만 있으면 됨
- 사용자는 `claude plugin marketplace add HotRedMat/ensembra` 로 추가 후 설치
- 또는 더 간단히: 누군가의 마켓플레이스에 등록 요청하거나 공식 Anthropic 마켓플레이스(claude.ai/settings/plugins/submit) 에 제출

**(B) 자체 마켓플레이스 + 플러그인 공존**:
- 같은 레포에 `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` 둘 다
- 마켓플레이스 entry 에서 `source: "./"` 로 자기 자신 지칭
- 확장성 있음 (나중에 `ensembra-bridge-*` 같은 보조 플러그인 추가 가능)

**결정**: Gate2 초기엔 **(A) 단일 플러그인 레포**. 나중에 보조 플러그인이 생기면 (B) 로 마이그레이션. `metadata.pluginRoot` 로 경로 관리.

### 공식 마켓플레이스 제출

제출 폼: https://claude.ai/settings/plugins/submit  또는  https://platform.claude.com/plugins/submit
- 아이콘/스크린샷 요구사항은 문서에 명시되지 않음 (제출 폼에서 확인 예정)
- 검증: `claude plugin validate .` 또는 `/plugin validate`

### 해소된 TODO
1. ✅ **`plugin.json` 전체 스키마** — 위에 완전 기술
2. ✅ **마켓플레이스 레포 구조** — `.claude-plugin/marketplace.json` 스키마 완전 확인
3. ⏸ **아이콘/스크린샷 요구사항** — 공식 제출 폼에서 확인 (Gate3 이전)
4. ⏸ **`settings.json agent` 키 적합성** — Ensembra 는 `/ensembra:run` 스킬 진입점 방식이라 `settings.json agent` 로 main thread 활성화 **불필요**. 일반 서브에이전트 호출로 충분. 해소됨.
5. ⏸ **sub-agents vs agent-teams** — Ensembra 는 Conductor 가 서브에이전트를 순차 호출하는 단일 세션 모델이므로 **sub-agents** 가 맞음. `agent-teams` 는 다중 세션 협업용으로 Ensembra 범위 밖.

### Gate2 진입 조건
**모두 해소됨** ✅. Gate2 진입 가능.

---

## 결정 로그

- **2026-04-15 — Q1~Q7 1차 확정**
  - Q1=a: Claude Code 플러그인 전용
  - Q2=a: 순수 Markdown + YAML frontmatter (단 Gemini/Ollama 호출용 Bash+curl 허용)
  - Q3=agents/+skills/: 오케스트레이션 범위 최소화 (hooks/ 제외)
  - Q4=공개 마켓플레이스 단일 채널
  - Q5=Gemini 키 1종 예외, 나머지 시크릿 없음
  - Q6=Ollama HTTP + Gemini 공식 API + Claude 서브에이전트 3종 Transport
  - Q7=Gemini 키는 `~/.config/ensembra/env` 에 저장, 레포 외부
  - **근거**: ChatGPT 자동화는 OpenAI ToS 위반 + 봇 탐지로 불안정. Gemini 무료 티어(15 RPM, 1,500 RPD)로 충분. 로컬 Ollama `qwen2.5:14b` 가 ChatGPT 의 다른 목소리 역할 대체.
  - **Gate2 진입 조건**: STEP 0 TODO(gate2) 1, 2번(plugins-reference 전체 스키마, marketplace 레포 구조) 해소 시.

- **2026-04-15 — Q8~Q10 확정 (아키텍처 보강)**
  - Q8=Deep Scan 필수, 8항목 체크리스트 (`CONTRACT.md` §12)
  - Q9=Model Resolution 3단 폴백: config → preset → Claude 본체
  - Q10=`/ensembra:config` 선택형 picker, 대화 기반, Bash+Markdown
  - **근거**: 1인 개발자 UX 중심. CLI 옵션 학습 비용 제거, 외부 LLM 가용성 변화에 탄력적, 실제 소스를 얕게 보는 실수를 구조적으로 차단.

- **2026-04-15 — Q11 확정 (설정 전면 통합)**
  - 모델뿐 아니라 프리셋·라운드·Deep Scan·Transport·타임아웃·로깅 **모든 설정**을 `/ensembra:config` 하나의 선택형 picker 로 관리
  - 메인 메뉴 8개 + 서브메뉴, 상세 `CONTRACT.md` §14
  - **근거**: Claude Code `/config` 와 동일한 UX 일관성. 1인 개발자가 플래그·JSON 문법을 외울 필요 없음. 모든 런타임 결정을 한 곳에 집중.

- **2026-04-15 — Gate1 아키텍처 2차 확정 (Q12~Q20 상당)**
  - **Performer 구성 (6명 토론 + scribe 1명)**:
    - planner (claude-subagent / opus)
    - architect (gemini / gemini-2.5-flash)
    - developer (claude-subagent / sonnet) ← 신규, "어떻게 구현" 담당
    - security (ollama / qwen2.5:14b)
    - qa (ollama / llama3.1:8b)
    - devils-advocate (claude-subagent / haiku)
    - scribe (claude-subagent / sonnet) ← 신규, Phase 4 전용, 토론 불참
  - **Reuse-First 교차 원칙 (4개 장치)**:
    - 장치 1: Deep Scan 9번 "공통 모듈 인벤토리" 강제
    - 장치 2: `reuse_analysis` 필드 필수 (스키마 강제)
    - 장치 3: R2 에서 부실 new 사유에 대한 자동 disagree
    - 장치 4: Synthesis 최상단 고정 "재사용 기회 평가" 리포트
    - 기본값: **Maximum (4개 전부 on)**
    - Quick Select 5프리셋 (Maximum/Strong/Balanced/Advisory/Off) + Custom (cascade 자동 처리, 함정 없음)
    - 조정: `/ensembra:config → Reuse-First Policy`
  - **Work Phase 5단 파이프라인**: Gather → Deliberate → Execute → Audit → **Document (Phase 4, 신규)**
  - **Phase 4 문서 5종** (scribe 담당):
    - Task Report (강제, 끌 수 없음)
    - Design Doc (feature/refactor append 모드)
    - Request Spec (feature/refactor)
    - Daily Report (수동 호출 `/ensembra:report daily`)
    - Weekly Report (수동 호출 `/ensembra:report weekly`)
    - ~~Handoff Note~~ Ensembra 범위 밖, 외부 플러그인(`d2-ops-handoff`) 담당
  - **`transfer` 프리셋** (인수인계서 전용):
    - Wide Scan → R1 only (섹션 분담) → Phase 4 특수 모드
    - 10 섹션 표준 템플릿, devils-advocate "⚠ 주의할 함정" 섹션 포함
    - scope 3가지: 인자 없음(전체) / 경로 / 자연어(planner 추론)
    - 자동 생성 없음, 명시적 호출만 (`/ensembra:transfer [scope]`)
  - **Phase 3 Audit 프리셋별 매트릭스**:
    - feature: 전원 6
    - bugfix: qa + security
    - refactor: architect + devils-advocate
    - security-audit / source-analysis / transfer: off
    - Rework 상한 2회
  - **합의 임계값 70/40** (상위 70% 확정, 하위 40% 중단, 중간 R3 또는 수동)
  - **Deep Scan 10항목**:
    - 강제 6개: 1(구조), 2(역추적), 3(호출그래프), 4(데이터흐름), 9(공통모듈), 10(프로젝트문서)
    - 선택 4개: 5(테스트맵), 6(git히스토리), 7(의존성), 8(설정)
    - 기본값: 선택 4개 전부 on
    - 프리셋별 차등 가능
  - **근거 총괄**: 1인 개발자 UX, 유지보수 우선(재사용), 얕은 읽기 방지(Deep Scan 강제), 실행/토론 분리(Claude Code=실행, 외부 LLM=토론), 문서 자동화로 미래의 나 지원.
  - **모든 결정은 `/ensembra:config` 에서 런타임 조정 가능** — Gate1 은 기본값 확정. 운영 중 피드백 기반으로 Gate2 이후 보완.
