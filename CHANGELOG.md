# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.12.1] — 2026-04-19 (pro-plan 자동 승격 금지선 불변식)

### Added — pro-plan Lock 불변식 (CONTRACT §19.3 / §19.9)

**문제 인식**: v0.12.0 까지 `risk_routing.mode: staged` (기본) 에서 `auto_upgrade_threshold ≥ 10` 도달 시 Conductor 가 `pro-plan → max-plan` 으로 **자동 승격** 가능. 사용자가 pro-plan 을 선택한 의도는 "토큰 절감 명시 의사표시" 인데, 이 원칙이 문서화되지 않아 Stage A 추천·Stage B 자동 업그레이드가 사용자 의도를 무시할 수 있는 설계 공백이었음.

- `CONTRACT.md §19.3` 에 pro-plan lock 불변식 명시 — "profile='pro-plan' 은 어떤 자동 경로(Stage A 추천 / Stage B auto_upgrade / Auto-Escalation)도 max-plan 으로 승격 불가. `risk_routing.mode` 와 무관하게 강제".
- max-plan 진입은 **오직 3가지 명시 경로**로만 가능:
  1. `/ensembra:run <preset> --profile=max-plan <요청>` 인자
  2. `/ensembra:config → Profile → max-plan` 영구 변경
  3. Kill Switch 치명 신호 + 사용자 **명시 승인 y** (승인 없으면 중단)

### Changed — §19.9 업그레이드 경로 매핑 pro-plan lock 반영

- `feature + pro-plan → feature + max-plan` 경로를 **`feature + pro-plan → feature + pro-plan` (profile 승격 없음)** 으로 변경.
- lock 상세 적용 규칙 표 신설 (profile 별 Stage A/B/Auto-Escalation/Kill Switch 동작 차이).
- `aggressive` 모드도 pro-plan 은 lock 됨을 명시.

### Changed — §19.4 로깅 스키마 `pro_plan_lock` 필드 신설

- `.claude/ensembra/reports/risk/runs.jsonl` 스키마에 `pro_plan_lock` 객체 추가 (active/suppressed_suggestions/user_config_profile).
- Stage A 의 `suggested_profile` 필드도 추가해 lock 에 의해 억제된 원래 추천 값 추적.
- 용도: 감사 추적 + 사용자 통계 (lock 발동 빈도로 설계 원칙 유효성 검증).

### Changed — `skills/run/SKILL.md` Stage A 섹션

- pro-plan Lock 전용 서브섹션 신설 — 활성 조건·동작·배지 포맷 (`🔒 pro-plan lock`)·명시 경로 3종.
- Stage A 흐름 프롬프트 설명에 lock 활성 시 `[3] 직접지정` 으로만 max-plan 진입 가능함을 명시.

### Changed — `schemas/config.json` `risk_routing` description

- 최상위 `risk_routing` description 에 pro-plan lock 불변식 요약 추가.
- `mode` 필드 description 에 "aggressive 도 pro-plan lock 됨" 명시.
- `auto_upgrade_threshold` 필드 description 에 pro-plan 에서의 실제 동작 (preset 만 승격) 명시.

### Design Rationale

- **사용자 명시 의사 존중**: pro-plan 선택은 토큰 예산 제약의 명시적 선언. 자동 승격은 이를 무시하는 것.
- **회귀 위험 0**: 기존 `pro-plan → max-plan` 자동 승격은 v0.12.0 까지 발동 사례 없음 (레포 records 기반). 이 불변식 추가는 **잠재적 미래 회귀 방지** 성격.
- **사용자 오버라이드 유지**: 정말 max 가 필요하면 3가지 명시 경로로 진입 가능 — 토글/제어권은 사용자에게 남김.

### Migration (v0.12.0 → v0.12.1)

- 사용자 작업 **불필요** — 기본 동작 변경이며 기존 config 그대로 동작.
- `risk_routing.mode: aggressive` 사용자도 pro-plan 이면 자동으로 lock 적용.
- max-plan 사용자는 기존과 동일 (lock 미적용).

## [0.12.0] — 2026-04-19 (Artifact Offload 스펙 + Transport Context Window 상한 + 캐시 경로 .claude/ 이관)

### Added — `_error.code: "token_limit"` 표준 분기 (CONTRACT §5.1/§5.2)

**문제 인식**: 이전 구현은 응답 절단을 `_error.code: "format"` 으로 흡수. final-auditor (opus 서브에이전트 200K) 가 긴 Phase 0~3 기록을 받을 때 응답이 잘려도 Conductor 가 "포맷 오류" 로 오인하는 silent fail 잠복 회귀.

- `CONTRACT.md §5.1` 에 `_error.code` 표준 분기표 7종 신설 (timeout / format / schema / transport-chain-exhausted / **token_limit** / rate_limit / unauthorized).
- `§5.2` 에 token_limit 탐지 휴리스틱 4종 (사전 1건: 입력 크기 사전 측정, 사후 3건: `===END===` 미도달·응답 에러 키워드·길이 0).
- Conductor 는 `token_limit` 발생 시 `artifact_offload.enabled=true` 면 자동 요약 재전송, false 면 사용자 프롬프트로 escalate.

### Added — Transport Context Window 상한표 (CONTRACT §8.11/§8.12)

**문제 인식**: max tier 의 `scribe_max_chars_per_phase: -1` · R2 `prior_outputs` 전체 전달 등 "무제한" 선언은 Conductor(본 세션 1M) 관점일 뿐. 실제 Performer 전송 시 Transport 수용량 (MCP Gemini 1M / Ollama 32~128K / Claude subagent 200K) 에 막힘. Claude subagent 1M 확장은 세션 한정, 서브에이전트엔 전파되지 않음.

- `§8.11` Transport 별 `max_input_chars` 상한 테이블 (각 모델별 80% 안전선).
- 핵심 불변식 5건: Claude subagent 1M 확장 비전파 / Ollama num_ctx 상한 / 호출 직전 입력 크기 측정 / 폴백 전환 시 재검증 / max tier "무제한" 의 실질 제약.
- 배지 연동: 입력 크기 ≥ 80% 도달 시 `⚠ Context 접근` 배지, 100% 도달 시 token_limit 분기.
- `§8.12` max tier "무제한" 실질 정의 — Conductor 비압축 선언이지 수신 측 수용량 무시가 아님.

### Added — Artifact Offload 스펙 (CONTRACT §21, opt-in 기본 off)

**문제 인식**: Phase 1 Performer 출력 · Phase 3 감사 출력이 본 세션 컨텍스트에 직접 누적. 1M 세션에선 견디지만 서브에이전트 200K 엔 오버플로우 리스크. 기존 Phase 0 캐시(§20) 만 파일화되어 있음.

- `schemas/config.json` 에 `artifact_offload` 블록 신설 (enabled/path/summary_chars/retention_days/context_handoff_mode 5속성).
- `CONTRACT.md §21` 전체 신설 — 9개 서브섹션 (원칙/구조/manifest 스키마/run_id 규칙/retention/보안/Transport 별 전달 전략/롤아웃/참조).
- 기본값 `enabled: false` — 실측 200K 근접 사례 축적까지 opt-in. v0.13 이후 기본 on 검토.
- Performer Write 금지선 (§11.3) 유지: Conductor 가 저장 중개, Performer 는 필요 시 Read 로 재로딩.
- `run_id` 는 ISO8601 compact + uuid4 first 4 hex 조합으로 동시 실행 경로 충돌 방지.
- `skills/run/SKILL.md` 에 Artifact Offload 훅 규약 섹션 추가.

### Changed — Phase 0 캐시 경로 `.claude/ensembra/cache/` 이관

**문제 인식**: 기존 `.ensembra/cache/` (프로젝트 루트 직속) 는 v0.11.0 의 "플러그인 산출물 `.claude/` 격리" 원칙과 불일치. Phase 0 캐시만 이 원칙에서 벗어나 있었음.

- `schemas/config.json` `deep_scan.cache_path` 기본값: `.ensembra/cache` → `.claude/ensembra/cache`.
- **하위 호환**: 구 경로에 기존 캐시가 있으면 Conductor 가 Read fallback 으로 HIT 허용. 신규 저장은 항상 새 경로. v0.13 에서 구 경로 지원 제거 예정.
- `CONTRACT.md §20.3/§20.4/§20.6` 및 `skills/run/SKILL.md` 경로 문구 갱신.
- `.gitignore`: 신규 경로는 `.claude/ensembra/` 전체 무시 라인에 자연 포함. 구 `.ensembra/cache/` 엔트리는 fallback 환경 지원용으로 당분간 유지.

### Security

- `artifact_offload` 파일 저장 직전 `gemini_client.scrub_outbound()` 동일 패턴으로 시크릿 마스킹 검증 (§21.6).
- Performer 는 artifact 경로 Write·Read 권한 없음 — Conductor 가 중개.

### Design Rationale

- **Reuse-First**: Phase 0 캐시 패턴(§20)을 `.claude/ensembra/cache/` 이관 + §21 Artifact Offload 로 그대로 확장. 신규 추상화 0건.
- **실측 게이트**: devils-advocate 가 R1 에서 "실측 없이 가지 말라" 게이트 제시. Stage 0 측정 결과 현 레포지토리 기록상 200K 초과 사례 0건 확인 → Conductor runtime 구현은 보류, 문서·스키마 레벨 (token_limit 분기·Transport 상한표·artifact_offload 스키마 opt-in) 만 선행 도입.
- **회귀 위험 0**: `artifact_offload.enabled: false` 기본값으로 기존 v0.11.x 파이프라인 동작 완전 보존. opt-in 활성화 시에만 신규 경로 작동.

### Migration (v0.11 → v0.12)

- 사용자 작업 **불필요** — 모든 변경은 기본값 유지로 기존 동작 보존.
- `artifact_offload` 사용을 원하면 `/ensembra:config` 또는 `~/.config/ensembra/config.json` 에 `"artifact_offload": { "enabled": true }` 추가.
- 구 `.ensembra/cache/` 디렉토리는 삭제해도 무방 (git commit 직후 Phase 0 HIT 재생성). 유지해도 fallback Read 로 동작.

## [0.11.0] — 2026-04-19 (토큰 비용 추가 절감 + 플러그인 출력 격리)

### Changed — SKILL.md slim (56% 축소) · CONTRACT.md 정본 승격

**문제 인식**: `skills/run/SKILL.md` 가 35.9KB (약 9,000 토큰) 로 매 `/ensembra:run` 호출 시 Conductor system prompt 에 inline 삽입. 상당 부분이 CONTRACT.md 와 중복 서술. 호출당 고정 토큰 비용이 불필요하게 높음.

- `skills/run/SKILL.md` **35,962B / 766 lines → 15,655B / 302 lines (-56%)**. Stage A/B Risk Routing 상세, Transport 3단 폴백 상세, Ollama 모델 해석, Badge 4레이어 예시, Deep Scan 캐시 포맷 등 상세 규약을 모두 `CONTRACT.md` 로 이관하고 요약·분기·금지선만 유지.
- `CONTRACT.md` **정본 승격** — §19 opening 의 "skills/run/SKILL.md 가 권위" 선언 반전. §19.6 (Stage A 흐름 + 점수표), §19.7 (Stage B 신호 가중치), §19.8 (Kill Switch 치명 신호 5종), §19.9 (자동 업그레이드 3모드 + 경로 매핑) 신규.
- `agents/orchestrator.md`: Badge 섹션 54줄 → 1문단 (CONTRACT.md §8.6 참조).
- `agents/architect.md`: Transport 섹션 32줄 → 1문단 (CONTRACT.md §8.8 참조).

**예상 토큰 절감**: **약 5,500 토큰/call** (매 /ensembra:run 호출 시 system prompt 축소분).

### Changed — Deep Scan 캐시 기본값 연장

- `schemas/config.json` `deep_scan.cache_ttl_hours.default`: **6 → 12 시간**. git HEAD 해시 기반 무효화가 주 신호이므로 TTL 연장은 안전. Cache HIT 율 상승으로 반복 작업 환경에서 20~40% 토큰 절감.
- `CONTRACT.md §20.4/§20.6` 동기화.

### Added — Deep Scan 항목 10 pro tier off 플래그

- `schemas/config.json` 신규 필드 `deep_scan.docs_inventory_pro_off` (기본 `true`).
- pro tier + 이 플래그가 true 면 Deep Scan 항목 10 (프로젝트 문서 인벤토리 Glob 5회) 을 완전 생략. `source-analysis`·`security-audit` preset 은 플래그 무시하고 항상 수행 (docs 분석이 핵심).
- **예상 토큰 절감**: 약 1,000 토큰/call.

### Added — Outbound 시크릿 스크러버 (HIGH 보안)

- `mcp-servers/gemini-ensembra/gemini_client.py` 에 신규 함수 `scrub_outbound()` 추가.
- `call_gemini()` 는 API 요청 본문 전송 **직전** 에 user_prompt 를 자동 마스킹:
  - 8 정규식 패턴: Gemini/OpenAI/Anthropic/GitHub/Slack/AWS/JWT/Bearer
  - `.env` 스타일 `KEY=VALUE` 라인 (KEY 에 KEY/TOKEN/SECRET/PASSWORD/PRIVATE 포함 시 VALUE 마스킹)
- 자가 테스트 8/8 통과 (plain text 무변경, 모든 시크릿 `[REDACTED:*]` 치환).
- 목적: Context Snapshot 이 `.env` 내용 등을 우연히 포함할 때 외부 LLM (Gemini/Ollama) 으로 평문 송신 방지. 기존 응답 본문 마스킹(§8.1)에 대칭되는 요청 본문 방어.

### Changed — 플러그인 출력 격리 (docs/ → .claude/ensembra/)

**문제 인식**: `docs/reports/tasks/`, `docs/design/`, `docs/requests/`, `docs/transfer/` 는 대상 프로젝트 자체의 `docs/` 와 경로 충돌. 사용자가 자기 프로젝트 문서를 `docs/` 에 보관하면 플러그인 런타임 산출물과 섞임.

- `schemas/config.json` 의 `reports.path_*` 6개 기본값을 `.claude/ensembra/...` 로 이관:
  - `path_tasks`: `docs/reports/tasks` → `.claude/ensembra/reports/tasks`
  - `path_daily/weekly/design/requests/transfer` 동일 패턴 이관
  - 신규 `path_risk`: `.claude/ensembra/reports/risk` (Risk Routing 로그)
- `CONTRACT.md §15.2, §15.4, §8.6.5, §19.4` · `agents/scribe.md` · `skills/report/SKILL.md` · `skills/transfer/SKILL.md` · `skills/run/SKILL.md` · `README.md` · `examples/quickstart.md` 모두 신규 경로로 참조 갱신.
- **Ensembra 자체 레포 정리**: 기존 `docs/` 하위 19개 플러그인 생성 파일을 `.claude/ensembra/` 로 `git mv` 후 `git rm --cached` 처리. 로컬 디스크엔 보존되지만 git 추적에서 제외.
- `.gitignore` 에 `.claude/ensembra/` + `.claude/logs/` 추가 (플러그인 런타임 산출물 격리). 이전 세션에서 임시 추가되었던 `docs/` 일괄 제외 규칙은 제거 (프로젝트 자체 `docs/` 는 다시 추적 가능).

**사용자 영향**: 하위 호환 유지 (`reports.path_*` 사용자 오버라이드 지정돼 있으면 그 값 우선). v0.10.0 이하에서 v0.11.0 업그레이드 시 과거 `docs/` 위치의 기록은 수동 이동 또는 그대로 방치 가능 (scribe 는 신 경로에 새로 작성).

### Security

- 외부 LLM 경로에 대한 송신 본문 자동 스크러빙으로 `sensitive: true` 불변식 확장.
- 플러그인 출력을 `.claude/` 하위로 격리해 대상 프로젝트 git 에 의도치 않게 커밋되는 경로 제거.

### Migration

기존 사용자:
- 별도 조치 불필요. 신규 실행부터 `.claude/ensembra/` 에 산출물 생성.
- 과거 `docs/` 위치의 기록은 그대로 두거나 수동 이동 (선택).
- `reports.path_*` 를 명시 지정한 사용자는 그 설정 유지됨.

## [0.10.0] — 2026-04-17 (Ollama 모델 동적 선택 — default + 역할별 override)

### Added — 사용자가 설치된 모델을 picker 로 선택

**문제 인식**: v0.9.x 까지 모든 Ollama 호출이 `qwen2.5:14b` 로 hardcoded → 사용자가 다른 모델(`qwen2.5-coder:14b`, `gpt-oss:20b` 등) 을 쓰려면 `profiles/*.yaml` 직접 편집 필요. 마켓 사용자에게 큰 진입 장벽.

#### A. `transports.ollama.model` (default) + `transports.ollama.models.{role}` (override)

`schemas/config.json` 의 `transports.ollama` 섹션 확장:
```json
"ollama": {
  "endpoint": "http://localhost:11434",
  "model": "qwen2.5-coder:14b",        // 모든 역할 default
  "models": {                           // 선택적 역할별 override
    "security": "qwen2.5:14b",
    "qa": "qwen2.5:14b"
  }
}
```

- 두 모드를 한 데이터 모델로 통합 — 단일 default 만 쓰거나, default 위에 역할별 override 추가하거나
- 미설정 시 `profiles/*.yaml` 의 hardcoded model 사용 (backward compat)

#### B. `/ensembra:config` (5)f Ollama 모델 picker

`Bash curl ${ollama_endpoint}/api/tags` 실시간 호출 → 설치된 모델 목록 번호 선택. 6 작업 메뉴 (기본 변경 / override 추가 / override 제거 / 전체 override 제거 / 다시 fetch / Ollama 비활성). 저장 직전 자동 검증으로 미설치 모델 감지.

#### C. Phase 1 Health Check 통합

기존 Health Check 의 "Ollama: `/api/tags` 200" 검사 확장:
- 각 Performer 의 `resolved_model` 이 응답의 `models[].name` 에 존재하는지 확인
- 미설치 시 자동 fallback (같은 패밀리 14b 모델) 또는 Claude 단계로 직행 + 사용자 알림

#### D. Special-case 보존

profile yaml 의 hardcoded model 이 명시적으로 다른 모델인 경우 (예: pro-plan 의 developer = `gpt-oss:20b`), config default 가 설정되어 있어도 **role-specific override 가 없으면 yaml 값 우선 존중**. 의도적 설계 선택을 보호.

### Changed

- `skills/run/SKILL.md` 의 Transport 호출 규약에 "Ollama 모델 해석 우선순위" 섹션 추가
- `skills/config/SKILL.md` (5) Transports 서브메뉴에 (5)f 항목 추가
- `agents/{architect,security,qa}.md` description 갱신 — "기본 qwen2.5:14b — v0.10.0+ config 로 변경 가능"
- `profiles/{pro,max}-plan.yaml` description 에 v0.10.0+ 안내 추가 (실제 model 라인은 backward compat 위해 유지)
- `schemas/config.json` 의 `transports.ollama` 에 `model`, `models` 필드 정의 추가

### Backward Compatibility

- `transports.ollama.model` 미설정 → 기존 동작 그대로 (`qwen2.5:14b` 사용)
- 기존 사용자 무중단 마이그레이션 — `/ensembra:config` 한 번 실행으로 신 기능 활용 가능

## [0.9.3] — 2026-04-17 (폴백 승인 프로토콜 — 예상치 못한 Claude 토큰 소비 차단)

### Added — 폴백 승인 3종 메커니즘

**문제 인식**: v0.9.2 까지 외부 LLM (Gemini MCP / Ollama) 실패 시 **조용히 자동 폴백** → Claude 토큰 예기치 못한 소비. 비용 절감 의도를 무시하는 동작이었음. v0.9.3 은 폴백 발생 전 사용자 명시 승인을 요구.

#### A. 사전 Transport Health Check + Phase 배치 처리

- Phase 1 R1 / Phase 3 Audit 시작 **직전** 외부 Transport 일괄 Health Check
- Gemini MCP: `tools/list` 응답 (300초 TTL 캐시)
- Ollama: `GET /api/tags` 200 + 모델 존재
- Rate limit 근접 감지: `X-RateLimit-Remaining` 헤더 모니터링
- 예상 폴백을 **단일 프롬프트**로 배치 처리 → 개별 프롬프트 피로 방지

#### B. 3단 승인 모드 (`fallback.confirmation_mode`)

- `strict`: 모든 단계 폴백(외부→외부 포함) 확인
- `critical_only` (기본): 외부 체인 전부 실패 → Claude 최종 폴백만 확인
- `none`: 자동 폴백 (v0.9.2 동작)

#### C. Session Auto-Approve

- 사용자 `[6] 이번 세션 동안 자동 승인` 선택 시 세션 한정 자동 처리
- config 파일에 저장 안 함 (다음 세션에서 다시 물음)
- 이후 동일 유형 폴백은 배지 알림만

#### 프롬프트 UX

```
📡 Phase 1 R1 — 사전 Transport Health Check

외부 LLM 가용성:
  ✓ Gemini MCP       정상 (14/15 RPM 사용 중)
  ✗ Ollama localhost 연결 실패
  ✓ Claude           항상 가용

영향 Performer:
  - qa:       Ollama → Claude sonnet 폴백 예정 (~3KB)
  - security: Ollama → Claude sonnet 폴백 예정 (~3KB)

예상 Claude 토큰: ~6KB

[1] 2명 모두 Claude 폴백 진행
[2] qa 만 폴백, security 스킵
[3] security 만 폴백, qa 스킵
[4] 둘 다 스킵 (⚠ 결과 불완전 가능)
[5] 중단하고 Ollama 재기동 후 다시 시도 (30초 대기)
[6] 이번 세션 동안 자동 승인
```

#### 예측 경고 배지 (§8.6.1 Transport 현황판 확장)

```
📡 Phase 1 R1 — Transport 계획:
  [Gemini]  architect   → gemini-2.5-flash   ⓘ rate limit 근접
  [Ollama]  qa          → qwen2.5:14b        ⚠ health check 실패
  
⚠ 예상 폴백 1건: qa → Claude sonnet (~3KB)
```

### Changed

- `CONTRACT.md §8.9 폴백 승인 프로토콜` 신설 (4개 하위섹션)
- `skills/run/SKILL.md` Phase 1 시작 섹션에 Health Check + 프롬프트 플로우 추가
- `skills/config/SKILL.md (5)e Fallback 승인 설정` 서브메뉴 추가
- `schemas/config.json` `fallback` 섹션에 4개 필드 추가:
  - `confirmation_mode` (기본 critical_only)
  - `session_auto_approve` (기본 false, 세션 한정)
  - `batch_by_phase` (기본 true)
  - `retry_delay_sec` (기본 30초)

### Version bump

- `0.9.2` → `0.9.3` (PATCH, 사용성·안전성 강화)
- 기존 사용자 영향: 첫 외부 LLM 실패 시 프롬프트 노출 시작. 이전 자동 폴백 동작을 원하면 `/ensembra:config → Transports → Fallback → 승인 모드: none` 선택.

## [0.9.2] — 2026-04-17 (Pre-flight Bailout + Deep Scan 캐싱)

### Added — 프롬프트 해석 비용 절감 2종

**문제 인식**: Conductor(Claude Code 본체) 의 프롬프트 해석·Phase 0 Deep Scan·오케스트레이션 로직은 사용자 Claude 세션 토큰을 소비한다. Gemini/Ollama 로 이관 불가능한 영역. v0.9.2 는 이 "해석 비용" 자체를 줄이는 2가지 메커니즘을 도입.

#### A. Pre-flight Bailout

- **Stage A Gemini Triage 확장**: 기존 preset/profile 제안에 더해 `ensembra_needed: boolean` + `bailout_reason` + `suggested_action` 필드 추가 출력
- 하나의 Gemini 호출로 "Ensembra 필요 여부 + 초기 경로" 동시 판정 → Gemini 호출 수 증가 없음
- `ensembra_needed: false` 판정 시 Phase 0 진입 없이 사용자 안내로 종료 (`direct_edit` 또는 `claude_chat` 권장)
- 안전 편향: Critical 키워드·경로 감지 시 자동 `true` override
- `pre_flight.auto_bailout: false` (기본) 면 사용자 확인 프롬프트, `true` 면 자동 종료

**효과**: 일 75건 중 **30~40건이 bailout** 예상 → Phase 0 Deep Scan·Phase 1 진입 전 종료

#### B. Phase 0 Deep Scan 캐싱

- Phase 0 수행 결과를 `.ensembra/cache/phase0-{key}.json` 에 저장
- 캐시 키: `sha256(project_path + git_head + preset + tier + intent)[0:16]`
- HIT 조건: 파일 존재 + TTL 이내 + git HEAD 동일 + schema_version 호환
- HIT 시 Read 1회로 context_snapshot 복원. Glob/Grep/Bash 수십 회 tool call 생략
- TTL 기본 6시간. git commit 발생 시 자동 무효화
- `.gitignore` 에 `.ensembra/cache/` 추가

**효과**: 같은 프로젝트 반복 작업 시 Phase 0 비용 ~80% 절감. 운영업무 다수 작업에서 캐시 히트 비율 70%+ 예상

### Changed

- `roles/triage.py` SYSTEM_PROMPT 에 Pre-flight Bailout 판정 로직 추가 (ensembra_needed, bailout_reason, suggested_action 필드)
- `skills/run/SKILL.md` Stage A 섹션에 Bailout 판정 플로우 + Phase 0 캐시 조회 로직 추가
- `CONTRACT.md` §19.5 Pre-flight Bailout, §20 Deep Scan Caching 2개 섹션 신설
- `schemas/config.json` 에 4개 필드 추가:
  - `deep_scan.cache_enabled` (기본 true)
  - `deep_scan.cache_ttl_hours` (기본 6)
  - `deep_scan.cache_path` (기본 `.ensembra/cache`)
  - `pre_flight.enabled` (기본 true)
  - `pre_flight.auto_bailout` (기본 false)
- `.gitignore` 에 `.ensembra/cache/` 추가

### 예상 효과 (v0.9.1 대비)

일 75건 운영업무 기준:

| 단계 | v0.9.1 누적 | v0.9.2 누적 | 추가 절감 |
|------|------------|------------|---------|
| 단일 실행 평균 | ~2.6% | ~1.0% | -62% |
| 일일 누적 | ~193% | ~69% | -64% |

v0.8.1 대비 누적 절감률: **~96%**

### Version bump

- `0.9.1` → `0.9.2` (PATCH, 기능 추가만)
- 기존 사용자 영향: 없음. 기본값 활성화로 재설치 시 자동 적용.
- Gemini 미설정 시 Pre-flight 폴백 — Claude Code 본체의 간이 키워드 매칭 사용 (정확도 낮음, `risk_routing.critical_keywords` 설정 권장)

## [0.9.1] — 2026-04-17 (외부 LLM 사용 증명 4종 강화)

### Added — Proof-of-Invocation 4종 메커니즘

사용자가 "외부 LLM 이 정말로 호출되었는가" 를 여러 시점에서 반복 확인할 수 있도록 4종 증거 메커니즘 강제. v0.8.1 Live Indicators 3 레이어 위에 얹어진 추가 보증 레이어.

- **A. 응답 증명 배너 (Response Proof Banner)**: 각 Performer 응답 본문 최상단에 `┌─ 🌐 EXTERNAL LLM VERIFIED ─┐` 메타데이터 블록 강제 prepend. Transport / model / duration / resp_size / endpoint 표시. Claude 폴백 시에는 `⚪ CLAUDE SUBAGENT (FALLBACK)` + `fallback_reason` 으로 명시적 구분.
- **B. Phase 종료 역할별 상세표**: `📊 Phase 1 외부 LLM 사용 증거:` 표 형식으로 각 Performer 호출의 실제 Transport 노출. ✓/✗ 마커로 외부·내부 구분.
- **C. Task Report Proof-of-Invocation 섹션**: scribe 가 생성하는 Task Report 맨 아래에 "외부 LLM 사용 증거" 표 강제 포함. 사후 감사 가능한 영구 기록.
- **D. 파이프라인 종료 배너**: 파이프라인 완료 시 박스형 증명 배너. Phase별 호출 분포 + 외부 LLM 활용률 + Claude API 예상 소비 + 프로파일 라벨.

### Changed

- `CONTRACT.md` §8.6.5 신설. 4종 증거 메커니즘 규약·보안 불변식·토글 명시.
- `skills/run/SKILL.md` 에 "레이어 4: Proof-of-Invocation 강화" 섹션 추가.
- `agents/scribe.md` Task Report 템플릿에 "외부 LLM 사용 증거" 섹션 강제 포함 규약 명시.
- `roles/scribe.py` system prompt 에 증거 섹션 필수 규약 내장.
- `schemas/config.json` 에 2개 토글 필드 추가:
  - `logging.proof_of_invocation` (기본 true) — A/B/D 3종 활성화
  - `reports.task_report_proof_section` (기본 true) — C 활성화

### Version bump

- `0.9.0` → `0.9.1` (PATCH, 기능 추가만)
- 기존 사용자 영향: 없음. 기본값 활성화로 재설치 시 자동 적용.
- 배지 출력이 길어지는 것이 싫으면 `/ensembra:config → Logging → proof_of_invocation: false` 로 비활성 가능 (비권장 — 증명 기능이 핵심)

## [0.9.0] — 2026-04-17 (토큰 절약 + 프로파일 체계 + 위험 기반 라우팅)

### Added

#### Stage 0 — 사용자 교육
- **`WHEN_NOT_TO_USE.md`** 신규 추가. Ensembra 를 언제 쓰지 말아야 하는지 판단 기준 제시. 2~3줄 수정·질문·주석은 직접 처리 권장. 위험 키워드·경로 체크리스트 + 실전 Case A~E 예시. 운영업무 15사이트 환경 기준 **일 75건 요청 대응**, 약 60~70% 절감 효과 예상.

#### Stage 1 — 공통 기반
- **에이전트 출력 길이 상한** (`agents/*.md`). 8개 에이전트(planner/architect/developer/qa/security/devils-advocate/scribe/final-auditor) 각각에 역할별 출력 상한 섹션 추가. R1/R2/Audit 본문 토큰 제한으로 컨텍스트 누적 약 30% 감소 추정.
- **Phase 0 Reuse 인벤토리 공유** (`skills/run/SKILL.md`). 강제 항목 5(공통 모듈)·선택 항목 5(테스트 맵)·선택 항목 7(의존성) 결과를 Context Snapshot 내 `reuse_inventory` 구조로 전 Performer 공유. Performer 자체 재귀 Read 금지. feature 프리셋 기준 Read tool call 약 60~100건 감소.

#### Stage 1.5 — 운영 프리셋 신설
- **`ops` 프리셋** (`presets/ops.yaml`). 경량 운영 작업용 (로그·설정·문서 패치). performers 3명 (planner+qa+security), R1 only. feature 대비 ~15% 토큰 소모.
- **`ops-safe` 프리셋** (`presets/ops-safe.yaml`). 운영 중요 작업용 (auth·payment·session 관련). performers 5명 (planner+developer+qa+security+devils), R1+R2+Synthesis, qa·security·devils 3명 강제 감사. feature 대비 ~60% 토큰 소모. **change_impact_report** 자동 생성 플래그 포함.

#### Stage 2 — 프로파일 체계
- **`profile` 필드** (`schemas/config.json`). Claude 요금제 기반 통합 프로파일. 값: `pro-plan` / `max-plan` / `custom`. 기본값 `pro-plan`.
- **`profiles/pro-plan.yaml`** — Claude Pro 플랜 대상. 모든 Performer 1순위 Gemini/Ollama. final-auditor sonnet/Gemini pro 허용 (opus 완화). planner/scribe 외부 이관 허용. 출력 상한 60% 적용. 예상 Claude API 절감 85~90%.
- **`profiles/max-plan.yaml`** — Claude Max5 플랜 대상. planner/developer/scribe/final-auditor Claude 고정. opus 유지. 출력 상한 100%. 품질 저하 없음.
- **`/ensembra:config` picker** 에 `(0) Profile` 선택 메뉴 추가.

#### Stage 3 — 정책 완화
- **v0.8.0 final-auditor opus 불변식** 을 `pro-plan` 프로파일에서 완화. `policy_relaxations.final_auditor_opus_optional: true` 로 sonnet/Gemini pro 실행 가능. `max-plan` 에서는 opus 유지.
- **planner/scribe 외부 이관 금지선** 을 `pro-plan` 에서 완화. `policy_relaxations.planner_external_allowed` / `scribe_external_allowed` 플래그로 토글.
- CONTRACT.md §11.3 에 완화 조항 명시.

#### Stage 3.5~3.8 — 위험 기반 자동 라우팅
- **Stage A — 요청 Triage** (`skills/run/SKILL.md`). Gemini flash (MCP `gemini-triage`) 로 사용자 입력 분류 → preset·profile 자동 제안. intent/domain/risk_score/confidence 반환.
- **Stage B — 코드 컨텍스트 재평가**. Phase 0 Deep Scan 산출물 재활용해 호출 그래프·데이터 흐름·테스트 맵·파일 경로·git churn 기반 점수 가산. 추가 tool call 없음.
- **Kill Switch — 치명 신호 감지**. 세션/인증 상태 변경·schema migration·.env 삭제·public API 시그니처 변경·위험 명령어 감지 시 강제 중단 + max-plan 승인 요구. 3모드 (`strict`/`warn`/`off`).
- **자동 업그레이드 3모드** (`risk_routing.mode`). `always_ask` (모든 +3 변동 확인), `staged` (알림·자동 임계값 분리, 기본), `aggressive` (모든 +3 변동 자동).
- **`risk_routing` 설정** (`schemas/config.json`). 키워드·경로·임계값·로그 옵션 일체.
- **로그 파일** `docs/reports/risk/runs.jsonl`. 위험 판정 결정 기록. 주기 리뷰로 프로젝트 고유 키워드 발견용. 원문 미보존 (sha256 prefix 8자).
- `CONTRACT.md §19 Risk Routing` 신설. 설계 원칙·금지선·로깅 스키마 명시.

#### 기타
- qa Ollama 모델 `llama3.1:8b` → `qwen2.5:14b` 승격. security 와 모델 공유 → Ollama 메모리 14.5GB → 9GB (단일 인스턴스). 추론 품질 향상.

### Changed

- `skills/config/SKILL.md` 메인 메뉴에 `(0) Profile`, `(11) Risk Routing` 항목 추가. 프리셋 6 → 8 (ops/ops-safe 포함).
- `skills/run/SKILL.md` 에 `Profile Resolution`, `Risk Routing — Stage A`, `Phase 0.5 — Risk Re-evaluation (Stage B)` 섹션 신설.
- `CONTRACT.md §11.1` Debate/Audit 분리 원칙에 v0.9.0 완화 조항 추가.
- `CONTRACT.md §11.2` 프리셋 매트릭스에 ops/ops-safe 행 추가.
- `README.md`, `CONTRIBUTING.md`, `examples/quickstart.md`, `.marketplace/SUBMISSION.md` 에서 qa 모델 `llama3.1:8b` → `qwen2.5:14b` 교체, 프리셋 리스트에 ops/ops-safe 추가.

### Expected Impact

| 지표 | 현재 (v0.8.1) | v0.9.0 (pro-plan) | v0.9.0 (max-plan) |
|------|-------------|-------------------|-------------------|
| 단일 실행 컨텍스트 | 20~25% | **8~10%** | 15~18% |
| Claude API 토큰 | 100% | **~10~15%** | ~90% |
| 일일 75건 컨텍스트 누적 | ~1,875% (한도 초과) | **~193%** | ~1,200% |
| 절감률 (vs v0.8.1) | — | **~90%** | ~15% |

### Pending Verification (Stage 4)

- 실제 파이프라인 실행 시 Stage A/B 동작 검증 (Gemini MCP 호출 흐름)
- 프로파일 YAML 로드 + 오버라이드 적용 흐름 검증
- Kill Switch 치명 신호 감지 정확도 측정
- 자동 업그레이드 3모드 UX 검증
- ~~MCP server 추가 등록 필요~~ → **v0.9.0 초기 결정 재수정**: 단일 MCP server 통합 구조 채택. 기존 `gemini-architect` 를 `gemini-ensembra` 로 리네임하고 9개 역할별 tool 제공. 참조: CONTRACT.md §18.5.

### Refactored (MCP server 구조)

- **역할별 모듈 분할**: 단일 `server.py` (406줄) → 다중 모듈 구조
  - `server.py` — 메인 엔트리 + MCP dispatch (축소, ~180줄)
  - `keychain.py` — OS 키체인 통합 (macOS/Linux/Windows)
  - `gemini_client.py` — Gemini REST API 호출 + system prompt 주입
  - `roles/__init__.py` — 역할 registry (동적 로드)
  - `roles/{architect,planner,developer,security,qa,devils,scribe,final_auditor,triage}.py` — 9개 역할별 모듈. 각각 TOOL_NAME, DEFAULT_MODEL, DEFAULT_TIMEOUT, TEMPERATURE, RESPONSE_MIME_TYPE, DESCRIPTION, SYSTEM_PROMPT 제공
- **역할별 system prompt**: `agents/*.md` 의 책임·출력 규칙·Reuse-First·금지사항을 각 역할 모듈의 `SYSTEM_PROMPT` 에 한국어로 내장. Gemini 가 역할에 맞는 응답을 내도록 유도.
- **역할별 Temperature 차등**: security 0.3, triage 0.2 (결정적) / devils 0.8 (창의적) / architect 0.6 (균형) 등 역할 특성 반영
- **`triage_request` 는 `responseMimeType: "application/json"` 강제**: Stage A 분류 결과가 항상 파싱 가능한 JSON

### Breaking Changes

- **MCP server 리네임**: `gemini-architect` → **`gemini-ensembra`**
  - 디렉토리: `mcp-servers/gemini-architect/` → `mcp-servers/gemini-ensembra/`
  - server.py `SERVER_NAME`: `ensembra-gemini-architect` → `ensembra-gemini`
  - plugin.json `mcpServers` 등록 이름 변경
  - 기존 `gemini-architect` 등록 사용자는 **`/plugin reload` 필요**. 설치된 MCP server 는 새 경로로 자동 재등록됨 (plugin.json 기준).
  - 마이그레이션: `settings.local.json` 의 `mcpServers.gemini-architect` 엔트리가 있으면 사용자가 수동 제거 또는 Claude Code 가 자동 정리.
  - 리네임 근거: v0.9.0 에서 server 가 Ensembra 전체 Performer (9종) 를 담당하는 만큼, "architect" 이름은 실제 범위를 왜곡. `gemini-ensembra` 로 통일해 명확성 확보.

### Version bump

- `0.8.1` → `0.9.0` (MINOR with breaking: MCP server name)
- 기존 사용자 영향: (1) profile 기본값 `pro-plan` 으로 Transport 체인 변경. (2) MCP server 이름 변경으로 `/plugin reload` 1회 필요. 마이그레이션 대화 첫 실행 시 자동 표시 예정 (Stage 4).

## [0.8.1] — 2026-04-17

### Added (외부 LLM 호출 실시간 가시화 — Live Indicators 3 레이어)

- **개별 호출 실시간 배지 (`CONTRACT.md §8.6.2`)**. Conductor 가 각 Performer 호출의 **시작(`▶`)·완료(`◀`)·폴백(`⚠`)·최종실패(`✗`)** 를 개별 라인으로 실시간 출력한다. 사용자는 외부 LLM (MCP Gemini · Ollama) 이 어느 시점에 실제로 돌고 있는지, 어느 단계에서 폴백되었는지를 직관적으로 확인 가능. v0.8.0 까지는 Phase 시작 1회 배지만 존재해 중간 호출 진행이 불가시였던 문제를 해소.
  - 포맷 예: `▶ [Gemini  ] architect — 호출 시작 (gemini-2.5-flash @ MCP(gemini-architect))`
  - 포맷 예: `◀ [Ollama  ] architect — 응답 수신 (4721ms, 2.3KB)`
  - 포맷 예: `⚠ [Gemini  ] architect — HTTP 429 rate limit → Ollama 폴백`
- **Phase 종료 집계 배지 (`§8.6.3`)**. Phase 1·3 각 종료 시 **외부 LLM 활용률** 을 1회 출력한다. 활용률 산식: `(MCP 성공 + Ollama 성공) / (Performer 호출 총 수) × 100`. 사용자는 토큰 절감 목표가 실제 달성됐는지 실측 가능.
  - 포맷 예: `📊 Phase 1 외부 LLM 호출 집계: MCP(Gemini) 2회 / 2 성공 / 0 폴백 ... 외부 LLM 활용률: 3/4 (75%)`
  - 해석 가이드: ≥70% 정상 / 40~70% Transport 일부 불안정 / <40% 구조적 진단 필요 (Conductor 가 사용자에게 경고 1회 추가)
- **최종 출력 포맷 `외부 LLM 활용률` 필드**. 파이프라인 종료 시 전체 Phase 합산 1행 요약. `**외부 LLM 활용률**: Phase 1 75% / Phase 3 50% (합산 66%)`.

### Changed

- `CONTRACT.md §8.6` 을 3 하위절로 재편 (§8.6.1 Phase 시작 현황판, §8.6.2 Live Call 실시간, §8.6.3 Phase 종료 집계, §8.6.4 전 레이어 금지 항목 통합). 기존 v0.7.0 현황판 · v0.7.0 폴백 배지 규약은 §8.6.1 로 흡수되어 동작 변화 없음.
- `skills/run/SKILL.md` 의 LLM 호출 배지 섹션을 3 레이어 구조로 재작성. 출력 포맷에 `외부 LLM 활용률` 행 추가.
- `agents/orchestrator.md` 의 LLM 호출 배지 섹션에 레이어 2·3 설명 및 예시 추가.

### Version bump

- `.claude-plugin/plugin.json` / `marketplace.json`: 0.8.0 → 0.8.1
- `mcp-servers/gemini-architect/server.py` `SERVER_VERSION`: 0.8.0 → 0.8.1
- `README.md` version 배지: 0.8.0 → 0.8.1

### Security

보안 불변식은 v0.8.0 그대로 유지. **추가 불변식** (실시간 배지 확장으로 인한 신규 리스크 차단):

- 모든 레이어에서 API 키·Authorization·토큰·`GEMINI_API_KEY`·`user_config.gemini_api_key` 문자열 절대 포함 금지
- 실시간 배지 (`§8.6.2`) 에서 프롬프트 본문·응답 본문 원문 출력 금지 — bytes/ms/상태 메타데이터만 허용
- 실패 `<reason>` 에 오류 메시지의 헤더·응답 본문은 포함하지 않고 짧은 요약만 (HTTP 상태코드, 타임아웃, 스키마 위반 등)

### Migration

사용자 설정 변경 불필요. `/reload-plugins` 후 다음 `/ensembra:run` 부터 자동 적용. `logging.show_transport_badge: false` 로 3 레이어 **모두** 억제 가능 (단일 토글, 부분 토글 없음).

### Design rationale (실시간 배지)

v0.8.0 은 외부 LLM 활용 폭을 크게 넓혔지만 **실제 돌고 있는지 불가시** 했다. 사용자 관점에서 "Phase 1 배지 출력 → 몇 초~수십 초 정적 구간 → 다음 출력" 사이에 MCP/Ollama 가 정말 호출되는지, 실패해서 Claude 로 조용히 폴백되는지를 구분할 수 없었다. v0.8.1 은 호출 시작·완료 타임스탬프 레벨 배지를 도입해:

1. **투명성**: 외부 LLM 실제 사용 여부를 사용자가 눈으로 확인 — v0.8.0 의 "외부 LLM 최대 활용" 슬로건이 구호가 아니라 측정 가능한 숫자가 됨
2. **디버깅**: GEMINI_API_KEY 만료·Ollama 다운·네트워크 지연 등 Transport 장애를 즉시 식별
3. **비용 통제**: 외부 LLM 활용률이 낮게 나오면 Claude 토큰이 의도치 않게 쓰이는 중임을 인지 → 설정 점검 유도

"개별 호출 시간 측정" 자체는 성능 오버헤드가 무시할 수준 (wall-clock timestamp 2회) 이고, 배지 렌더링 비용도 라인당 수십 바이트로 전체 토큰 영향 미미.

## [0.8.0] — 2026-04-17

### Added (Debate/Audit 분리 원칙 — unanimous 만장일치)

- **`final-auditor` Performer 신설**. Claude `opus` 전용, Phase 3 전용, Phase 1 토론 불참. 모든 수정 preset(`feature`/`bugfix`/`refactor`) 의 `audit.auditors` 체인 마지막에 자동 배치되어 **만장일치 판정자** 역할을 수행한다. `agents/final-auditor.md` 신규 생성.
- **만장일치(unanimous) 정의**. Phase 1 Synthesis 합의율 ≥ 70% AND `final-auditor.verdict == pass` 둘 다 충족할 때만 `unanimous: true`. "100% agree" 엄격 해석은 의도적으로 채택하지 않음 — Rework 루프 폭발 방지 (`CONTRACT.md §11.3.2`).
- **Final Audit Rework (별도 카운터, 상한 1회)**. 전문 감사자 Rework(상한 2회) 와 분리. opus 호출 비용을 제어하기 위해 final-auditor 의 `rework` 판정은 1회만 Phase 1 복귀, 이후에는 파이프라인 중단 + 사용자 판정 (`§11.3.3`).
- **`CONTRACT.md §8.8 Transport Fallback Chain Protocol`** 신설. v0.7.0 의 architect 전용 3단 폴백을 **모든 Performer 에 적용 가능한 일반 프로토콜** 로 승격. `performerConfig.transport_chain` 배열 필드 + 공통 실행 루프 + 단계별 Health Check 표 + `external_first` 토글 + tool 이름 유추 규칙.
- **`developer_deliberate` MCP tool**. `mcp-servers/gemini-architect/server.py` 가 v0.8.0 부터 2개 tool 을 노출한다: 기존 `architect_deliberate` (기본 `gemini-2.5-flash`) + 신규 `developer_deliberate` (기본 `gemini-2.5-pro`). 단일 MCP server 프로세스가 두 역할을 모두 처리 (파일 중복 방지).
- **`userConfig.developer_transport` opt-in 필드**. `plugin.json` 에 추가. 값 `"external"` 설정 시 developer Performer 가 MCP(gemini-2.5-pro) → Ollama(gpt-oss:20b) → Claude(sonnet) 3단 체인으로 전환. 기본값은 Claude sonnet (Phase 2 실행자와 모델 계열 일치, Plan→실행 간극 최소).
- **`schemas/config.json`** 에 `transport_chain`, `transportStep`, `external_first`, `mcp_tool_name` 필드 추가. `transport: "gemini"` 는 `transportStep` enum 에서 제외 (v0.6.0 구조적 폐지 원칙 유지 — Gemini 호출은 MCP 경유로만 허용).

### Changed (Debate tier — opus 제거)

- **planner 모델 강등: `opus` → `sonnet`**. 토론 Performer 전체에서 opus 사용을 금지선으로 규정. 요구사항 해석 정확도는 sonnet 에서도 충분히 확보되며, opus 는 Phase 3 final-auditor 에 단 1회 집중적으로 사용된다.
- **Phase 3 감사 순서 2단계화**. `presets/feature.yaml`, `presets/refactor.yaml`, `presets/bugfix.yaml` 의 `audit.auditors` 에 `final-auditor` 를 마지막 항목으로 추가. 전문 감사자 전원 `pass` 직후에만 final-auditor 호출 (전문 `fail` 시 final-auditor 미호출 — opus 비용 절감). 읽기 전용 preset(`security-audit`/`source-analysis`) 은 audit 자체가 off 이므로 final-auditor 도 해당 없음.
- **feature preset audit 에서 planner 제거**. v0.8.0 부터 planner 는 Phase 3 감사에 참여하지 않는다. 요구사항 충족 여부는 final-auditor 가 큰 그림으로 종합 판정.
- **LLM 호출 배지 확장**. `agents/orchestrator.md` + `skills/run/SKILL.md` 배지에 Phase 3 예정 순서를 추가 출력. `[⚖ opus ] final-auditor` 로 최종 판정자 위치 강조.
- **`agents/architect.md` Transport 섹션**. §8.8 Transport Fallback Chain Protocol 참조로 서술 재정리 (코드 경로는 §8.8 공통 루프에 흡수되었고, architect 전용 체인은 §8.8.6 의 예시로 재해석).
- **`agents/developer.md`**. Transport 섹션 신설. 기본값 Claude sonnet 유지 + opt-in 외부 체인 선언 규약.
- **`.claude-plugin/plugin.json` / `marketplace.json` / `README.md`**: version 0.7.2 → 0.8.0. README Performer 표 및 프리셋 매트릭스 Debate/Audit split 반영.

### Security

- `final-auditor` 의 Transport 를 `claude-subagent` 로 고정 (외부 이관 금지). v0.6.0 이후 유지된 "Ensembra 파이프라인은 토론 단계에 시크릿을 요구하지 않는다" 원칙은 그대로 유지 — architect 의 MCP 경유 Gemini 호출 방식 (`sensitive: true` + MCP server env-only) 은 변경 없음.
- v0.8.0 은 opus 토큰 집중 사용 지점이 명확히 1곳(final-auditor) 으로 한정되어, 사용량 감사·요금 통제가 용이.

### Migration

기존 v0.7.2 사용자:
1. 플러그인 업데이트 후 `/reload-plugins`
2. config 파일을 수동 편집하지 않으면 자동으로 v0.8.0 기본값이 적용됨 (planner sonnet, final-auditor 자동 배치)
3. `developer_transport: "external"` 를 원하면 `/plugin → ensembra → Configure options` 에서 명시 설정
4. 기존 `performers.architect.transport` 단일 선언은 호환 유지 (§8.8.6). `transport_chain` 선언이 우선하나 미선언 시 기존 3단 폴백 동작 그대로

### Design rationale (Debate/Audit 분리)

기존 구조(v0.7.x) 는 planner(opus) + developer(sonnet) + devils(haiku) + scribe(sonnet) 등 토론 6명 중 1~2명이 opus 를 사용하고 Phase 3 감사도 전문 감사자 다수가 각자 병행 판정했다. 이 구조의 문제:

1. opus 가 토론 중간에 투입되면 다른 sonnet/외부 모델 의견을 과도하게 압도 — 토론의 다양성 손실
2. 감사 단계에서 여러 전문가가 각자 pass/fail 내는 방식은 "다수결" 에 가깝지 "만장일치" 가 아님
3. opus 호출 비용이 파이프라인 전역에 분산되어 예측·통제 어려움

v0.8.0 은 **토론은 외부 LLM + sonnet 이하 다양성 조합**, **감사는 opus 1명이 큰 그림 종합** 이라는 구조로 재편. 이 분리는:

- 토론: 모델 편향·쏠림 방지 (동형 모델 군집 회피)
- 감사: 최상위 모델 1명 = 일관된 기준 + 비용 예측 가능
- 만장일치: 70% 합의 + opus pass 라는 2단 조건으로 "실질적 만장일치" 조작적 정의

"100% agree" 를 쓰지 않는 이유는 실무 실행 가능성 — 6명이 모두 동의하는 상태는 현실적으로 Rework 루프를 폭증시킨다.

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
