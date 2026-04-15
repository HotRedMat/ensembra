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
- [x] **Gemini (공식 무료 API)** — `gemini-2.0-flash`, Google AI Studio 키, Bash+curl
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

출처:
- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/plugins-reference (미확인, Gate2 이전 재확인 필요)

### 매니페스트 경로
- 플러그인 매니페스트는 **`<plugin-root>/.claude-plugin/plugin.json`** 에 위치한다.
- `commands/`, `agents/`, `skills/`, `hooks/`, `.mcp.json`, `.lsp.json`, `bin/`, `settings.json` 은 **plugin root** 에 두며 `.claude-plugin/` **안에 넣으면 안 된다**.
- 주의: Gate1 에서는 `plugin.json` 생성 금지 (publish 불가역성). 따라서 현재 레포는 standalone `.claude/` 레이아웃을 사용한다. Gate2 에서 플러그인으로 승격할 때 `.claude/agents/*` → `<plugin-root>/agents/*` 로 이동 필요.

### plugin.json 필수·권장 필드
- 필수: `name`, `description`, `version`
- 권장: `author`(object: name, email, url), `homepage`, `repository`, `license`
- 참고: 버전은 SemVer. `name` 은 스킬/커맨드 네임스페이스 프리픽스로 사용됨 (`/ensembra:<skill>`).

### agents frontmatter 규약 (`.claude/agents/*.md` 또는 plugin `agents/*.md`)
- 필수: `name`, `description`
- 선택: `tools` (쉼표 구분 문자열), `model` (`opus`|`sonnet`|`haiku`), `disallowedTools`, `permissionMode`, `mcpServers`, `hooks`, `maxTurns`, `skills`, `initialPrompt`, `memory`, `effort`, `background`, `isolation`, `color`
- 플러그인에서 로드되는 에이전트는 보안상 `hooks`, `mcpServers`, `permissionMode` 필드가 **무시**됨. 필요하면 사용자 `.claude/agents/` 로 복사하거나 `settings.json permissions.allow` 활용.
- 에이전트 본문(Markdown)은 시스템 프롬프트로 사용됨.

### 마켓플레이스 등록
- 공식 마켓플레이스 제출은 claude.ai/settings/plugins/submit 또는 platform.claude.com/plugins/submit 인앱 폼.
- 별도 `marketplace.json` 요구사항은 공식 문서에서 확인되지 않음 — Gate2 이전 `plugin-marketplaces` 문서 재확인 필요.

### 불확실 항목 (TODO, Gate2 이전 해소)
1. `TODO(gate2)`: `plugins-reference` 페이지에서 `plugin.json` 의 전체 JSON Schema 와 옵션 필드 목록 확인.
2. `TODO(gate2)`: 팀/사내 마켓플레이스 레포 구조 (`.claude-plugin/marketplace.json` 유사 파일 존재 여부) 확인.
3. `TODO(gate2)`: 플러그인 배포 시 아이콘/스크린샷 요구사항 확인.
4. `TODO(gate2)`: `settings.json` 의 `agent` 키로 오케스트레이터를 main thread 로 활성화하는 방식이 Ensembra 모델과 적합한지 검증.
5. `TODO(gate2)`: agents 간 통신이 필요한 경우 `sub-agents` vs `agent-teams` 어느 쪽을 쓸지 결정 (`/en/agent-teams` 문서 미확인).

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
    - architect (gemini / gemini-2.0-flash)
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
