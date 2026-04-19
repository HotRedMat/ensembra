---
description: Ensembra 파이프라인의 메인 진입점. 프리셋과 요청을 받아 Phase 0~4 를 순차 실행한다. 사용법 "/ensembra:run <preset> <요청>" 예 "/ensembra:run feature 결제에 쿠폰 할인 추가". 프리셋 feature/bugfix/refactor/ops/ops-safe/security-audit/source-analysis 중 선택 (v0.9.0+ ops/ops-safe 신설).
disable-model-invocation: false
---

# Ensembra Run

너(Claude Code)는 이 스킬이 호출되면 **Conductor** 역할을 맡아 Ensembra 파이프라인을 실행한다. 모든 상세 규약의 정본은 [`../../CONTRACT.md`](../../CONTRACT.md) 이다. 본 파일은 Conductor 가 런타임에 따라야 할 **최소 진입점·분기·금지선** 만 담는다. 섹션 번호가 인용된 곳(`§X.Y`)은 CONTRACT.md 참조.

## 인자 파싱

사용자 입력 `$ARGUMENTS` 를 다음 형식으로 파싱:

```
<preset> [--tier=pro|max] [--profile=pro-plan|max-plan|custom] <요청 문자열>
```

- `<preset>`: `feature` / `bugfix` / `refactor` / `ops` / `ops-safe` / `security-audit` / `source-analysis`
- `--tier=`: 본 실행 한정 Plan Tier 강제. 생략 시 config → `pro` 기본
- `--profile=`: 본 실행 한정 프로파일 강제. 생략 시 config → `pro-plan` 기본
- `<요청>`: 자연어 문자열

프리셋 누락·불명확 시 사용자에게 재확인. `--tier` / `--profile` 잘못된 값은 오류 중단.

## Plan Tier & Profile Resolution

Phase 0 **직전** 에 아래 순서로 확정하고 배지 1줄 출력.

**Plan Tier 우선순위**: `--tier=` > `config.plan_tier` > `"pro"`
**Profile 우선순위**: `--profile=` > `config.profile` > `"pro-plan"`

### Tier 축 요약 (고정값, 상세 매트릭스는 CONTRACT.md §17)

| 축 | pro (기본) | max |
|---|---|---|
| Deep Scan 강제 6항목 | 1·2·9 전수, 3·4 압축, 10 은 `docs_inventory_pro_off`(v0.11.0+ 기본 true) 면 완전 off / false 면 상위 디렉토리만. `source-analysis`·`security-audit` preset 은 플래그 무시 | 현행 전부 |
| Deep Scan 선택 4항목 | 전부 off | preset 지시 |
| Context Snapshot | 심볼·경로 인벤토리만 | 본문 발췌 포함 |
| Phase 1 R2 | 합의율 ≥85% 자동 스킵, 수행 시 diff 요약 | 항상 수행, 전체 전달 |
| Phase 3 Audit | 전문 감사자 **첫 1명** + final-auditor | 전원 + final-auditor |
| Phase 4 scribe 입력 | Phase 별 ≤500자 요약 | 원본 기록 |

### 금지선 (pro 에서도 양보 불가)

- feature preset 의 `security`·`qa` Performer 참여 유지
- 합의율 임계값 (`rounds.*_consensus`) 은 tier 무관
- Reuse-First 장치 4개는 tier 로 토글 금지
- Deep Scan 강제 6항목은 "압축"·"범위 축소" 는 허용하되 **미수행 불가**

### 배지 포맷

```
🎚 plan_tier: pro  (Deep Scan 3/10, Context=symbols, R2=diff-only, Audit=1명)
🪙 profile: pro-plan  (transport=Gemini/Ollama priority, audit=2명, output=60%, final-auditor=sonnet)
```

max 의 경우 `🎚 plan_tier: max / 💎 profile: max-plan`.

### Auto-Escalation (합의율 저하)

pro 로 실행 중 R1 합의율 40~70% 구간 진입 시 Conductor 는 사용자에게 R2 전체 전달 상향을 제안 (`y/n`). 자세한 프로토콜은 CONTRACT.md §17.

### 프로파일 적용 필드

확정된 `profiles/{name}.yaml` 에서 로드:
- `transport_routing.*` (Performer 별 체인)
- `output_limits_multiplier`
- `rounds_override.*`
- `phase3_override.max_auditors`
- `phase4_override.scribe_max_chars_per_phase`
- `policy_relaxations.*`

`profile_overrides` 가 있으면 profile 기본값 위에 얹는다.

## Stage A — Pre-flight Bailout + Request Triage (v0.9.0+ / v0.9.2+)

`risk_routing.enabled: true` (기본) 일 때 Phase 0 **이전** 에 Gemini flash-lite 로 triage 한다. 한 번의 Gemini 호출로:

1. **Bailout 판정**: `ensembra_needed: false` 이면 Phase 0 진입 없이 종료 안내 (CONTRACT.md §19.5)
2. **초기 경로 제안**: 점수 기반 preset/profile 추천 (CONTRACT.md §19.6.2 점수표)

Gemini 호출은 MCP tool `triage_request` 사용. 실패 시 Claude 본체 키워드 스코어링 폴백 (정확도 낮음, §19.3 불변식).

### Stage A 흐름

- Bailout 판정 `false` → 안내 + `auto_bailout` 여부에 따라 자동 종료 또는 사용자 `[1]종료/[2]강행` 프롬프트
- `ensembra_needed: true` → 점수·confidence 표시 + 초기 경로 제안. `mode == always_ask` 또는 점수 ≥10 에서만 사용자 프롬프트 (`[1]권장 [2]낮추기 [3]직접지정 [4]Ensembra 생략 [5]취소`)
- `mode == staged` 이고 점수 <10 → 조용히 진행 (배지만)
- `log_risk_decisions: true` → `.claude/ensembra/reports/risk/runs.jsonl` 기록 (v0.11.0+ 기본, 스키마 CONTRACT.md §19.4)

상세 프롬프트 템플릿·점수표·사용자 확인 조건: CONTRACT.md §19.6.

`risk_routing.enabled: false` 면 사용자가 preset·profile 을 명시해야 함. 자동 판정 없음.

## Phase 0 — Gather (Deep Scan)

### 캐시 조회 (v0.9.2+)

`deep_scan.cache_enabled: true` (기본) 일 때 Phase 0 tool call **전** 캐시 조회. 상세 키 생성식·파일 포맷·무효화 트리거: CONTRACT.md §20.

**캐시 키 요약**: `sha256(project_root + git_head + preset + tier + request_intent)[0:16]`
**파일 경로**: `{deep_scan.cache_path}/phase0-{key}.json` (v0.12.0+ 기본 `.claude/ensembra/cache/phase0-{key}.json`, 이전 `.ensembra/cache/` 는 Read fallback 만)
**TTL**: `cache_ttl_hours` (v0.11.0+ 기본 12h, max 72h). git HEAD 변경 시 TTL 무관 무효화.

- **HIT**: Read 1회로 `context_snapshot` + `reuse_inventory` 복원. 아래 Deep Scan 수행 생략. 배지 `✅ Phase 0 Cache HIT (key=…, age=…, git=…)`
- **MISS**: 아래 수행 후 결과 캐시 저장. 배지 `⚠ Phase 0 Cache MISS (reason=…)`

**보안**: 캐시에 시크릿·API 키·사용자 요청 원문 금지 (마스킹된 값만).

### Artifact Offload 훅 (v0.12.0+, opt-in)

`artifact_offload.enabled: true` (기본 false) 이면 Conductor 는 Phase 1 R1/R2 및 Phase 3 전문 감사·final-auditor 응답 수신 **직후** 다음을 수행:

1. 응답 본문을 `{artifact_offload.path}/{run_id}/phase{n}-{stage}-{role}.md` 로 저장 (CONTRACT.md §21.2)
2. `manifest.json` 에 해당 entry append (§21.3 스키마 — bytes/transport_used/model_used 포함)
3. 본 세션 컨텍스트엔 **요약(`summary_chars` 이내) + 파일 경로**만 유지
4. 후속 Performer 전달 시 §21.7 Transport 별 전달 전략 적용 (MCP/Claude/Ollama 수용량 차등)

**금지선**:
- Performer 에 Write 권한 위임 금지. Conductor 가 Read 하고 `prior_outputs` 로 중개
- artifact 에 API 키·시크릿 포함 금지 (§21.6). 저장 직전 `gemini_client.scrub_outbound()` 동일 패턴 마스킹
- `run_id` 는 반드시 UUID+timestamp 조합 (§21.4) — 동시 실행 경로 충돌 방지
- opus 토론 금지선(§11.3) 우회 경로로 사용 금지. 역할별 승격은 별도 토론 필요 (Gate2 이월)

**`enabled: false` 시 동작 무변경**. 본 섹션 전체 skip, 기존 v0.11.x 파이프라인과 완전 동일.

### Deep Scan 수행 (캐시 MISS 시)

`presets/{preset}.yaml` 의 `deep_scan` + 확정된 tier 를 겹쳐 적용 (Tier 표 참조). 확정된 체크리스트로 **병렬 tool call** 수행:

**강제 6항목** (끌 수 없음 — 압축만 허용):
1. 구조 파악 — `Glob "**/*"` 상위 디렉토리 + 진입점
2. 키워드 역추적 — 요청 문자열 심볼 `Grep` 전 레포
3. 호출 그래프 — 함수 정의 + 호출 지점 + import
4. 데이터 흐름 — 생성→변형→소비 경로
5. (항목 9) 공통 모듈 인벤토리 — `commons/`, `shared/`, `lib/`, `utils/`, `helpers/`, `framework/`, `core/`
6. (항목 10) 프로젝트 문서 인벤토리 — `docs/`, `spec/`, `requirements/`, `design/`, `adr/`. **pro tier + `docs_inventory_pro_off: true` (v0.11.0+ 기본) 이면 생략**. `source-analysis`·`security-audit` preset 은 플래그 무시하고 항상 수행.

**선택 4항목** (config `deep_scan.item_5_test_map` 등 토글):
- 테스트 맵, git 히스토리, 의존성, 설정 파일 (pro tier 는 전부 off)

### Context Snapshot 조립

수집 결과를 단일 **Context Snapshot** (Markdown) 으로 압축. 각 Performer 입력 `constraints.context_snapshot` 에 첨부.

- pro tier: 심볼 목록·경로 인벤토리만 (파일 본문 생략)
- max tier: 핵심 파일 본문 발췌 포함

### Reuse Inventory (v0.9.0+)

강제 항목 9 + 선택 항목 5·7 을 Context Snapshot 의 `reuse_inventory` 섹션으로 구조화 (공통 모듈·테스트 픽스처·의존성). 스키마: CONTRACT.md §16.5.

Phase 1 Performer 는 이 인벤토리를 **재탐색 없이** `reuse_analysis` 근거로 사용한다. `commons/`·`shared/`·`lib/`·`utils/`·`helpers/` 의 **자체 재귀 Read 금지**. 누락 발견 시 Performer 는 `issues` 기록, Conductor 는 Phase 0 으로 1회 복귀 가능 (상한 1회).

## Phase 0.5 — Risk Re-evaluation (Stage B)

`risk_routing.enabled: true` 일 때 Phase 0 산출물로 **추가 tool call 없이** 위험 재평가. 가중치 표 (CONTRACT.md §19.7)·Kill Switch 치명 신호 5종 (§19.8)·자동 업그레이드 3모드 + 업그레이드 경로 매핑 (§19.9)·로깅 포맷 (§19.4) 이 정본.

판정 결과:
- 변동 < `notify_threshold` → 조용히 진행
- `notify_threshold` ≤ 변동 < `auto_upgrade_threshold` → 배지 알림, 경로 유지
- 변동 ≥ `auto_upgrade_threshold` → 자동 업그레이드 + 명시 알림
- Kill Switch 치명 신호 → `kill_switch: strict` 면 **중단 + max-plan 승인 프롬프트**

## Phase 1 — Deliberate

### 사전 Health Check + 폴백 승인 (v0.9.3+)

`fallback.batch_by_phase: true` (기본) 면 Phase 1 R1 **직전** 모든 외부 Transport 를 일괄 검사:

1. Gemini MCP: `tools/list` 응답 (300초 TTL 캐시)
2. Ollama: `GET /api/tags` + 각 Performer 의 resolved_model 존재 확인
3. Gemini rate limit 근접 감지 (헤더 `X-RateLimit-Remaining`)

**Ollama 모델 미설치**: 같은 패밀리 14b 자동 폴백 → 불가 시 Claude 폴백. `fallback.confirmation_mode == strict` 일 때만 승인 프롬프트.

**폴백 승인 모드** (`fallback.confirmation_mode`):
- `strict`: ⚠ 감지 시 매번 프롬프트
- `critical_only` (기본): 외부 체인 전부 실패로 Claude 최종 폴백 필요 시만
- `none`: 자동 진행

`session_auto_approve: true` 면 세션 한정 프롬프트 생략. 프롬프트 선택지·배지 포맷: CONTRACT.md §8.9.

### Deliberation 흐름

1. **R1 독립 분석**: `presets/{preset}.yaml` 의 `performers` 목록을 순차 호출. 동일한 `problem` + `context_snapshot` + `reuse_inventory` 전달. 상호 불가시. Performer 는 인벤토리 범위 내 재사용만 검토, 외부 심볼 참조 시 Phase 0 재수집 요청 또는 `new_creation_justified` 근거 필수.

2. **R2 반론** (조건부):
   - max: preset `rounds: [R1, R2, synthesis]` 면 항상, `prior_outputs` 전체 전달
   - pro: R1 Peer Signature 합의율 ≥ 85% 면 **R2 자동 스킵**, 미만이면 수행하되 `prior_outputs` 는 **diff 요약** (각 Performer 당 400자 이내)
   - 40~70% 구간은 §Tier Resolution 의 Auto-Escalation 적용
   - R2 출력엔 `peer_signatures` 필수

3. **합의율 계산** (Peer Signature 매트릭스 agree 비율):
   - ≥70% → Plan 확정, Phase 2 진행
   - 40~70% → R3 또는 사용자 수동 판정
   - <40% → 중단, 쟁점 목록 사용자 반환

4. **Synthesis**: Conductor(또는 지정된 synthesizer) 가 최종 Plan 합성. **최상단에 "⚠ 재사용 기회 평가" 섹션 강제** (CONTRACT.md §16.4).

### Transport 호출 규약

모든 Performer 는 프로파일 yaml 의 `transport_routing.{role}.chain` 순서로 폴백. 3단 체인의 정본 규약·Ollama 모델 해석 우선순위(config → default → yaml)·폴백 배지: **CONTRACT.md §8.8**.

핵심 요약:
- 1단 MCP (`gemini-ensembra` server) → 실패 시 2단
- 2단 Ollama (역할별 override → default → yaml, v0.10.0+) → 실패 시 3단
- 3단 Claude 서브에이전트 (항상 가용)
- API 키는 MCP server env 에만 존재 (skill/agent content 노출 금지, `sensitive: true` 불변식)
- v0.11.0+ gemini_client.py 의 outbound scrubber 로 요청 본문 내 API 키/토큰/.env 자동 마스킹

## LLM 호출 배지

`logging.show_transport_badge: true` (기본) → **3 레이어 배지**, `logging.proof_of_invocation: true` (기본) → **Proof-of-Invocation 4종** 추가. 정본 포맷·예시·토글: **CONTRACT.md §8.6 (레이어 1~3)** 과 **§8.6.5 (PoI A/B/C/D)**.

3 레이어 개요:
- 레이어 1: Phase 1 R1 / Phase 3 직전 1회 현황판 (`📡`)
- 레이어 2: 개별 호출 실시간 (`▶`·`◀`·`⚠`·`✗`)
- 레이어 3: Phase 종료 집계 (`📊` — MCP/Ollama/Claude + 외부 LLM 활용률)

Proof-of-Invocation 4종:
- A: 응답 증명 배너 (`┌─ 🌐 EXTERNAL LLM VERIFIED ─┐`)
- B: Phase 종료 역할별 상세표
- C: Task Report 증거 섹션 (`reports.task_report_proof_section` 별도 토글)
- D: 파이프라인 종료 배너

**금지선 (전 레이어 공통)**: API 키·Authorization·토큰 금지, 프롬프트·응답 본문 원문 금지 (bytes/ms/상태 메타데이터만 허용). `show_transport_badge: false` → 3 레이어 전원 억제. `proof_of_invocation: false` → A/B/D 억제 (C 는 별도 토글).

## Phase 2 — Execute

Conductor(= 현재 Claude Code 세션) 가 **본인** 도구 (`Edit`, `Write`, `Bash`) 로 Plan 실행. 외부 Performer 는 이 단계 관여 불가.

- `create` → `Write`
- `modify` → `Read` 후 `Edit`
- `delete` → `Bash rm` (신중)

오류 발생 시 즉시 중단 + 사용자 보고.

## Phase 3 — Audit (2단계)

`presets/{preset}.yaml` 의 `audit.auditors` 목록을 tier 로 필터링 후 순차 호출. final-auditor 는 tier 필터링 대상이 아니며 pro/max 모두 **마지막 1회 필수**.

### 3-1. 전문 감사자

tier=pro 는 목록 **첫 1명**, tier=max 는 전원. 각자에게 Plan + Phase 2 diff 전달. 출력 스키마 (`verdict`/`issues`): CONTRACT.md §11.2.

판정:
- 하나라도 `fail` → Rework 트리거 (**final-auditor 호출 안 함, opus 비용 절감**)
- 2명 이상 `rework` → Rework 트리거
- 모두 `pass` → **3-2 final-auditor 호출**

Rework: Phase 1 복귀, **Plan diff 만** 전달. 상한 2회 (config 조정 가능).

### 3-2. final-auditor

전원 pass 직후 Conductor 호출. 입력: 원 요청 + Synthesis + Phase 2 diff + 전문 감사자 출력 전체. 출력 스키마 (`verdict`/`unanimous`/`consensus_rate`/`summary`/`issues`): CONTRACT.md §11.3.

판정:
- `pass` AND `consensus_rate ≥ 70` → **만장일치 도달**, `unanimous: true`, Phase 4 진행
- `rework` → **Final Audit Rework** (별도 카운터, 상한 **1회**). Phase 1 복귀, Plan diff + final-auditor issues 주입, 전문 감사자 재호출 없음
- `fail` → 중단, 사용자 수동 판정

Phase 3 진입 전 감사 순서 배지 1회 출력 (`📡 Phase 3 Audit — 예정 순서: …`).

## Phase 4 — Document

`audit.phase4` 설정에 따라 scribe 호출. 생성 문서 유형은 프리셋별:
- `feature`/`refactor`: Task Report + Design Doc + Request Spec
- 그 외: Task Report 만

scribe 입력 = tier 로 결정:
- pro: Phase 0~3 기록의 요약본 (각 ≤500자, Conductor 사전 압축)
- max: 원본 기록 전체

scribe 는 받은 입력으로 템플릿 슬롯을 채운다. 완료 후 저장 경로를 사용자에게 보고.

## 출력 포맷

최종 사용자 응답:

```
## Ensembra Run — {preset}

🎚 **plan_tier**: pro (또는 max)
🪙 **profile**: pro-plan (또는 max-plan)
**결과**: Pass (Audit 통과)
**합의율**: 84%
**만장일치**: ✅ 도달 (토론 합의율 ≥70% AND final-auditor pass)
**Rework 횟수**: 전문 감사 0 / Final Audit 0
**외부 LLM 활용률**: Phase 1 75% / Phase 3 50% (합산 66%)

### 변경 파일
…

### 생성된 문서
…

### 재사용 기회 평가
(Synthesis 최상단 섹션 복사)

### Final Auditor 총평
(final-auditor.summary 복사)
```

**외부 LLM 활용률** = `(MCP 성공 + Ollama 성공) / Performer 총 호출 × 100` (CONTRACT.md §8.6.3).

## 보안

- 시크릿 파일(`.env`, `*.key`, `*.pem`)은 Phase 0 에서 경로만 수집, 내용 전달 금지
- 로그·보고서 마스킹은 `SECURITY.md` 정본
- Phase 2 비가역 동작(`git push`, `rm -rf`, `git reset --hard` 등)은 사용자 확인 후
- v0.11.0+: 외부 LLM 전송 경로에 `gemini_client.scrub_outbound()` 자동 적용 (API 키·JWT·Bearer·.env KEY=VALUE 마스킹)

## 금지

- Phase 0 Deep Scan 강제 6항목 미수행 시 Phase 1 진입 금지
- 외부 Performer(Ollama/Gemini) 에게 파일 쓰기 권한 위임 금지
- Plan 외 파일 수정 금지 (Phase 2)
- API 키 / Authorization / 토큰 / 프롬프트 원문 / 응답 본문을 배지·로그·보고서에 포함 금지
