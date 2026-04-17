---
description: Ensembra 파이프라인의 메인 진입점. 프리셋과 요청을 받아 Phase 0~4 를 순차 실행한다. 사용법 "/ensembra:run <preset> <요청>" 예 "/ensembra:run feature 결제에 쿠폰 할인 추가". 프리셋 feature/bugfix/refactor/ops/ops-safe/security-audit/source-analysis 중 선택 (v0.9.0+ ops/ops-safe 신설).
disable-model-invocation: false
---

# Ensembra Run

너(Claude Code)는 이 스킬이 호출되면 **Conductor** 역할을 맡아 Ensembra 파이프라인을 실행한다.

## 인자 파싱
사용자 입력 `$ARGUMENTS` 를 다음 형식으로 파싱:
```
<preset> [--tier=pro|max] <요청 문자열>
```
- `<preset>`: `feature` / `bugfix` / `refactor` / **`ops`** / **`ops-safe`** / `security-audit` / `source-analysis` 중 하나 (v0.9.0+ `ops`/`ops-safe` 신설 — 운영업무 전용 경량 경로)
- `--tier=` (선택): 본 실행에 한해 Plan Tier 강제. 생략 시 config → 기본값 `pro` 순으로 해석
- `<요청>`: 자연어 문자열

프리셋이 없거나 불명확하면 사용자에게 되묻는다. `--tier` 값이 `pro|max` 외이면 오류로 중단.

## Plan Tier Resolution

Phase 0 진입 **직전** 에 tier 를 확정한다. 우선순위:

1. `--tier=` 인자 (본 실행 한정)
2. `~/.claude/config/ensembra/config.json` 의 `plan_tier` 필드
3. 기본값 `"pro"`

확정된 tier 는 Phase 0~4 전 과정에 동일하게 적용된다. Conductor 는 **Phase 0 시작 전** 한 줄 배지로 반드시 알린다:

```
🎚 plan_tier: pro (Deep Scan 3/10, Context=symbols, R2=diff-only, Audit=1명)
🎚 plan_tier: max (Deep Scan preset 원본, Context=full, R2=full, Audit=preset 전원)
```

### Tier 프로파일 (고정값)

| 축 | **pro** (기본) | **max** |
|---|---|---|
| Deep Scan 강제 6항목 | 1·2·9 는 전문 수행, 3·4 는 압축(핵심 심볼만), 10 은 상위 디렉토리 목록만 | 현행 전부 수행 |
| Deep Scan 선택 4항목 | preset `deep_scan.optional` 지시 **무시**, 전부 off | preset `deep_scan.optional` 지시 따름 |
| Context Snapshot | 심볼 목록·경로 인벤토리만 (파일 본문 생략) | 현행 (본문 발췌 포함) |
| Phase 1 R2 전달 | 이전 라운드 출력의 **diff 요약** (신규 쟁점·변경 위치만) | 이전 라운드 **전체 출력** |
| Phase 1 R2 스킵 | R1 Peer Signature 합의율 ≥ 85% 면 R2 자동 스킵 (rounds yaml 무시) | preset `rounds` 그대로 |
| Phase 3 Audit 감사자 | preset `audit.auditors` 의 **첫 1명** 만 호출 | preset `audit.auditors` 전원 |
| Phase 4 scribe 입력 | Phase 0~3 기록의 **요약본** (각 Phase 당 500자 이내) | Phase 0~3 **원본 기록** |

### 금지선 (pro 에서도 절대 양보 불가)

- feature preset 의 `security` / `qa` Performer 는 pro 에서도 참여 유지
- 합의율 임계값 (`rounds.*_consensus`) 은 tier 와 무관 — config 값 그대로 사용
- Reuse-First 장치 4개 (config `reuse_first.device_*`) 는 tier 로 토글 금지
- Deep Scan 강제 6항목은 "압축"·"범위 축소" 는 허용하되 "미수행" 은 불가 (§ 금지 참조)

### 합의율 저하 시 Auto-Escalation

pro 로 실행 중 R1 합의율이 40~70% 구간에 진입하면 Conductor 는 사용자에게 제안:
```
⚠ R1 합의율 62% — pro tier 에서 R2 전체 전달로 임시 상향 조정하시겠습니까? (y/n)
```
`y` → 해당 실행 한정으로 R2 는 max 방식으로 전환. `n` → pro R2 diff 방식 유지 또는 중단.

## Profile Resolution (v0.9.0+)

Phase 0 진입 **직전** Plan Tier 와 함께 프로파일도 확정한다. 우선순위:

1. `/ensembra:run --profile=...` 인자 (본 실행 한정)
2. `~/.claude/config/ensembra/config.json` 의 `profile` 필드
3. 기본값 `"pro-plan"`

확정된 프로파일의 YAML (`profiles/{name}.yaml`) 에서 다음을 로드:
- `transport_routing.*` — Performer 별 Transport 체인 (8.8 체인 규약 적용)
- `output_limits_multiplier` — 에이전트 출력 길이 상한 계수
- `rounds_override.*` — 합의율 임계값
- `phase3_override.max_auditors` — Phase 3 감사자 수 제한
- `phase4_override.scribe_max_chars_per_phase` — scribe 입력 압축 길이
- `policy_relaxations.*` — 정책 완화 플래그

`profile_overrides` 가 있으면 프로파일 기본값 위에 얹어 적용 (JSON pointer 형태의 키로 구체 항목 오버라이드).

Conductor 는 프로파일 확정 시 배지 출력:
```
🪙 profile: pro-plan  (transport=Gemini/Ollama priority, audit=2명, output=60%, final-auditor=sonnet)
💎 profile: max-plan  (transport=Claude priority, audit=전원, output=100%, final-auditor=opus)
```

## Risk Routing — Stage A (요청 Triage, v0.9.0+)

`risk_routing.enabled: true` (기본) 일 때, 사용자 입력을 Phase 0 진입 **이전** 에 Gemini flash 로 분류해 preset/profile 초기 제안을 수립한다.

### Stage A 실행

1. **입력 수집**: `$ARGUMENTS` + 프로젝트 개요 (최상위 디렉토리 목록)
2. **Gemini flash 호출** (MCP `gemini-triage` server, tool `triage_request`):

   ```
   프롬프트 (요약):
   "당신은 소프트웨어 운영 위험 분석가입니다.
    아래 요청의 위험도를 평가하세요.
    요청: {user_input}
    레포 최상위: {top_dirs}

    위험 키워드(+5): config.risk_routing.critical_keywords 목록
    위험 경로(+5):   config.risk_routing.critical_paths 목록
    High 키워드(+3): config.risk_routing.high_keywords 목록

    출력 JSON (schema 준수):
    {
      intent: 'bugfix|feature|refactor|ops|diagnosis|deployment|migration|question',
      detected_domain: [...],
      action_type: 'read|add|modify|delete|replace',
      initial_risk_score: 0-20,
      confidence: 0.0-1.0,
      reasoning: '한 문장'
    }
    confidence<0.6 면 score 를 +3 보수적 가산."
   ```

3. **폴백**: Gemini 호출 실패 시 Claude Code 본체가 키워드 매칭 기반 간이 스코어링 수행 (정확도 낮음).

4. **초기 경로 결정**:

   | 점수 | 제안 preset | 제안 profile |
   |-----|----------|-----------|
   | 0 (read-only) | Ensembra 생략 권장 (Claude 직접 대화) | — |
   | 1~2 | 제안 생략 또는 `ops` | pro-plan |
   | 3~5 | `ops` | pro-plan |
   | 6~9 | `bugfix` | pro-plan |
   | 10~14 | `ops-safe` | pro-plan |
   | 15~19 | `feature` | max-plan |
   | 20+ | `feature` + 강제 전문 감사 전원 | max-plan |

5. **사용자 확인** (`risk_routing.mode == always_ask` 또는 초기 점수 ≥ 10):

   ```
   🛡 Stage A Triage 결과

   감지 intent:        bugfix (confidence 0.82)
   감지 domain:        [auth, session]
   initial_risk_score: 15
   reasoning:          "로그인 함수 null 체크 추가 — auth 도메인 + modify 액션"

   제안: /ensembra:run feature --profile=max-plan
   예상 Claude 토큰: ~90

   [1] 권장대로 진행 (Enter)
   [2] ops-safe 로 낮추기
   [3] 사용자 직접 지정
   [4] Ensembra 생략 (직접 수정)
   [5] 취소
   ```

   `mode == staged` 이고 점수 < 10 이면 사용자 확인 없이 자동 진행 (배지 알림만).
   `mode == aggressive` 이면 사용자 확인 생략.

6. **로깅** (`log_risk_decisions: true`): `docs/reports/risk/runs.jsonl` 에 한 줄로 기록.

### Stage A 미활성 시 (risk_routing.enabled: false)

사용자가 명시적으로 preset 과 profile 을 지정해야 한다. 자동 판정 없음.

## 파이프라인 실행 순서

### Phase 0 — Gather (Deep Scan)
`presets/{preset}.yaml` 의 `deep_scan` 설정을 읽되, **Plan Tier Resolution** 결과를 겹쳐 적용한다. `tier=pro` 면 optional 4항목은 모두 off, forced 6항목 중 3·4·10 은 압축 모드. `tier=max` 면 preset 지시 그대로. 확정된 체크리스트로 다음을 **병렬 tool call** 로 수행:

1. **강제 6항목** (끌 수 없음):
   - 구조 파악: `Glob "**/*"` 상위 디렉토리 + 진입점 파일(`main.*`, `index.*`, `app.*`) 식별
   - 키워드 역추적: 요청 문자열에서 심볼 추출 후 `Grep` 전 레포 역참조
   - 호출 그래프: 대상 함수 정의 + 호출 지점 + import 관계
   - 데이터 흐름: 대상 데이터의 생성→변형→소비 경로
   - 공통 모듈 인벤토리: `Glob` 으로 `commons/`, `shared/`, `lib/`, `utils/`, `helpers/`, `framework/`, `core/` 전수 + `Read` 로 공개 심볼 나열
   - 프로젝트 문서 인벤토리: `Glob` 으로 `docs/`, `spec/`, `requirements/`, `design/`, `adr/` 전수

2. **선택 4항목** (`~/.claude/config/ensembra/config.json` 의 Deep Scan 토글 확인):
   - 테스트 맵: `Glob` 으로 `tests/`, `__tests__/`, `spec/`
   - git 히스토리: `git log -p --all -n 5 <대상 파일>` (Bash)
   - 의존성: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` Read
   - 설정: `.env.example`, `config/*` Read

3. 수집 결과를 단일 **Context Snapshot** (Markdown) 으로 압축. 각 Performer 입력 `constraints.context_snapshot` 에 첨부.
   - `tier=pro`: 심볼 목록·경로 인벤토리만 포함. 파일 본문 발췌 금지.
   - `tier=max`: 현행 — 핵심 파일 본문 발췌 포함.

4. **Reuse 인벤토리 공유 (v0.9.0+ 공통 기반)**: 강제 항목 5(공통 모듈 인벤토리) + 선택 항목 5(테스트 맵) + 선택 항목 7(의존성) 의 결과를 Context Snapshot 내 **`reuse_inventory`** 섹션으로 구조화한다. 구조:

   ```yaml
   reuse_inventory:
     common_modules:
       - path: commons/auth/token.js
         public_symbols: [verifyToken, refreshToken, ...]
     shared_utilities:
       - path: shared/validation.ts
         public_symbols: [validateEmail, validatePhone, ...]
     test_fixtures:
       - path: tests/fixtures/user.factory.ts
         exports: [userFactory, adminFactory]
     dependencies:
       - { name: zod, version: ^3.22.0, purpose: validation }
   ```

   Phase 1 전 Performer 는 이 인벤토리를 **재탐색 없이** `reuse_analysis` 의 근거로 사용한다. Performer 가 `commons/`, `shared/`, `lib/`, `utils/`, `helpers/` 를 자체적으로 재귀 Read 하는 행위는 **금지** — 이미 Phase 0 에서 완료된 작업이다. 인벤토리에 누락된 영역을 발견하면 Performer 는 `issues` 에 기록하고 Conductor 는 Phase 0 으로 1회 복귀해 재수집 가능 (재수집 상한: 1회/실행).

   **토큰 절감 효과**: Performer 당 평균 5~8회의 중복 Read 호출 제거. feature 프리셋 기준 Phase 1 R1/R2 합쳐 Read tool call 약 60~100건 감소.

### Phase 0.5 — Risk Re-evaluation (Stage B, v0.9.0+)

`risk_routing.enabled: true` 일 때 Phase 0 Deep Scan 수집 결과를 재활용해 **코드 컨텍스트 기반 위험 재평가** 수행. 추가 tool call 없이 Deep Scan 산출물만 사용.

#### 재평가 신호 (Phase 0 산출물 → 점수 가산)

| 신호 | 출처 | 가중치 |
|------|-----|------|
| **Blast Radius** | 호출 그래프 (항목 3) | |
| ├ 1~5 호출자 | | +0 |
| ├ 6~20 호출자 | | +3 |
| ├ 20+ 호출자 | | +7 |
| └ public export / API 경계 | | +5 |
| **데이터 흐름 위험** | 데이터 흐름 (항목 4) | |
| ├ 로그만 | | +0 |
| ├ 캐시 접근 | | +2 |
| ├ DB write | | +5 |
| ├ 외부 API 호출 | | +3 |
| └ 세션/인증 상태 변경 | | +10 (치명) |
| **테스트 커버리지 갭** | 테스트 맵 (항목 5) | |
| ├ 단위 테스트 존재 | | +0 |
| ├ 테스트 없음 | | +4 |
| └ 테스트 없음 + 위 위험 중첩 | | 추가 +3 |
| **파일 경로** | 구조 파악 (항목 1) | |
| ├ `/auth/`, `/session/`, `/middleware/` | | +5 |
| ├ `/migrations/`, schema 파일 | | +7 |
| ├ `/payment/`, `/billing/` | | +6 |
| ├ `.env*`, `/config/` | | +4 |
| ├ `/docs/`, `/test/` | | +0 |
| **git churn** | git 히스토리 (항목 6) | |
| ├ 최근 30일 10+ 커밋 (불안정) | | +2 |
| └ 6개월 안정 | | -1 |
| **횡단 영향** | 공통 모듈 인벤토리 (항목 9) | |
| └ commons/shared/lib 위치 | | +8 |

#### Kill Switch — 치명 신호 감지

다음은 점수 누적 없이 **즉시 강제 중단 + max-plan 승인 요구** (`kill_switch: strict` 기본):

| 치명 신호 | 조건 |
|---------|-----|
| 세션/인증 상태 변경 | auth·session 파일 수정 + 테스트 없음 |
| Schema migration | `/migrations/` 경로 + DROP/ALTER 액션 |
| 환경변수 삭제·변경 | `.env*` 파일 DELETE/UPDATE |
| public API 시그니처 변경 | exported 함수 시그니처 변경 + 6+ 호출자 |
| 위험 명령어 | `rm -rf`, `git push --force`, DB TRUNCATE/DROP |

Kill Switch 발동 시:

```
⛔ Kill Switch: session middleware 수정 + 테스트 없음

파이프라인 일시 중단. 이 작업은 max-plan 프로파일 및 feature 프리셋으로 진행해야 안전합니다.

[1] max-plan + feature 로 재시작 (권장)
[2] 현재 경로 유지 (위험 감수 확인 — 로그 기록됨)
[3] 중단 (수동 검토)
```

`kill_switch: warn` 이면 배지 경고만 띄우고 진행. `off` 이면 감지 비활성화.

#### 자동 업그레이드 3모드 처리

Stage A 점수(`initial_risk_score`) 와 Stage B 점수(`refined_risk_score`) 의 차이가 **변동폭**이다.

**`mode: always_ask`**:
- 변동 ≥ +3 이면 사용자 확인 프롬프트 (경로 업그레이드 제안)
- 변동 < +3 이면 조용히 진행

**`mode: staged`** (기본 권장):
- 변동 < `notify_threshold` (기본 3): 조용히 진행 (로그만)
- `notify_threshold` ≤ 변동 < `auto_upgrade_threshold` (기본 3~9): 알림 배지 표시, 현 경로 유지
- 변동 ≥ `auto_upgrade_threshold` (기본 10): 자동 업그레이드 + 명시 알림
- Kill Switch 치명 신호: 별도 레이어로 중단 또는 경고

**`mode: aggressive`**:
- 변동 ≥ `notify_threshold`: 자동 업그레이드 (묻지 않음)
- Kill Switch 치명 신호: 별도 레이어

#### 업그레이드 경로 매핑

현재 경로 → 업그레이드 경로:
- `ops` + pro-plan → `ops-safe` + pro-plan
- `ops-safe` + pro-plan → `feature` + pro-plan
- `feature` + pro-plan → `feature` + max-plan
- `feature` + max-plan → `feature` + max-plan + 강제 전문 감사 전원 (최고 경로)

#### 배지 출력 예시

```
🛡 Stage B 재평가

Stage A 점수:  5 (ops + pro-plan 시작)
Stage B 점수: 18 (변동 +13)

감지 신호:
  - 호출 그래프: 47 호출자 (+7)
  - 데이터 흐름: session 상태 변경 (+10, ⚠ 치명)
  - 테스트 맵:   단위 테스트 없음 (+4)
  - 파일 경로:   /auth/validateToken.js (+5)

판정: auto_upgrade_threshold 10 초과 + 치명 신호 감지
     → Kill Switch strict 모드 발동

⛔ 파이프라인 중단. 권장: /ensembra:run feature --profile=max-plan
```

#### Stage B 로깅

`log_risk_decisions: true` 일 때 `docs/reports/risk/runs.jsonl` 에 항목 추가:

```jsonl
{
  "ts": "2026-04-17T10:23:45Z",
  "request": "null 체크 추가 auth/validateToken",
  "stage_a": {"score": 5, "confidence": 0.72, "reasoning": "..."},
  "stage_b": {"score": 18, "signals": [...], "kill_switch": true},
  "final_route": "feature + max-plan (kill-switch upgrade)",
  "user_action": "accepted",
  "outcome": null
}
```

주기 리뷰 (월 1회) 로 false-positive/false-negative 분석 → 프로젝트 고유 위험 키워드 발견.

### Phase 1 — Deliberate

1. **R1 독립 분석**: `presets/{preset}.yaml` 의 `performers` 목록의 각 Performer 를 순차 호출 (subagent 또는 외부 Transport). 각자에게 **동일한** `problem` + `context_snapshot` + `reuse_inventory` 전달. 서로의 답을 보지 못함. Performer 는 `reuse_inventory` 범위 내에서만 재사용 후보를 검토하며, 인벤토리 외 심볼 참조 시 Phase 0 재수집 요청 또는 `new_creation_justified` 근거 제시 필수.

2. **R2 반론** (조건부): `rounds` 설정 + **Plan Tier** 에 따라.
   - `tier=max`: preset `rounds: [R1, R2, synthesis]` 이면 항상 실행. `prior_outputs` 는 이전 라운드 **전체 출력**.
   - `tier=pro`: R1 Peer Signature 합의율 ≥ 85% 면 R2 **자동 스킵**. 85% 미만이면 실행하되 `prior_outputs` 는 **diff 요약** (신규 쟁점, 반대 지점, 변경 제안 위치만 — 각 Performer 당 400자 이내).
   - 합의율 40~70% 구간 진입 시 §Plan Tier Resolution 의 Auto-Escalation 규칙 적용.

   R2 출력엔 `peer_signatures` 필수.

3. **합의율 계산**:
   - Peer Signature 매트릭스에서 agree 비율 계산
   - ≥ 70% → Plan 확정, Phase 2 진행
   - 40~70% → R3 또는 사용자 수동 판정
   - < 40% → 파이프라인 중단, 쟁점 목록 사용자 반환

4. **Synthesis**: Conductor(또는 지정된 synthesizer Performer) 가 최종 Plan 합성. 최상단에 **"⚠ 재사용 기회 평가"** 섹션 강제 배치 (`CONTRACT.md` §16.4).

### Transport 호출 규약 (architect = MCP → Ollama → Claude, v0.7.0+)

Phase 1 R1 에서 architect Performer 를 호출할 때 **3단 폴백 체인**을 따른다.

**1단: MCP server (gemini-ensembra)**

`settings.local.json` 에 `mcpServers.gemini-ensembra` 가 등록되어 있고, `GEMINI_API_KEY` 가 설정된 경우. Conductor 는 MCP tool-use 로 `architect_deliberate` tool 을 호출한다. API 키는 MCP server 프로세스 환경변수에만 존재하며 skill/agent content 에는 절대 노출되지 않는다.

**2단: Ollama (폴백)**

MCP 가용 실패 시 (MCP server 미등록, GEMINI_API_KEY 미설정, Gemini API 오류). `userConfig.ollama_endpoint` (비시크릿) 치환으로 엔드포인트를 얻는다. 치환 결과가 빈 문자열이면 (사용자가 Configure options 에서 비움) Ollama 를 건너뛰고 3단(Claude) 으로 직행:

```bash
# endpoint 가 비어 있지 않을 때만 호출
curl -s -X POST "${user_config.ollama_endpoint}/api/generate" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"qwen2.5:14b\",\"prompt\":\"$prompt\",\"stream\":false}"
```

**3단: Claude 서브에이전트 (최종 폴백)**

Ollama 도 실패 시 Claude `sonnet` 서브에이전트로 폴백. 항상 가용.

**폴백 시 배지 표시**:
```
⚠ architect: gemini-2.5-flash (MCP) 실패 → ollama/qwen2.5:14b (fallback)
⚠ architect: ollama 실패 → claude-sonnet (fallback)
```

### LLM 호출 배지 (v0.8.0 Debate/Audit + v0.8.1 Live Indicators)

`config.json logging.show_transport_badge: true` (기본) 일 때, Conductor 는 **3 레이어** 배지를 출력한다 (`CONTRACT.md §8.6`).

#### 레이어 1: Phase 시작 현황판 (v0.7.0+)

Phase 1 R1 / Phase 3 시작 직전 1회. **opus 는 토론에 보이지 않는다** (v0.8.0 금지선):

```
📡 Phase 1 R1 — Transport 현황:
  [Gemini  ] architect     → gemini-2.5-flash  @ MCP(gemini-ensembra)
  [Ollama  ] security      → qwen2.5:14b       @ localhost:11434
  [Ollama  ] qa            → qwen2.5:14b       @ localhost:11434
  [Claude  ] planner       → sonnet            @ subagent    (v0.8.0 opus→sonnet)
  [Claude  ] developer     → sonnet            @ subagent    (opt-in 외부 체인 off)
  [Claude  ] devils-adv    → haiku             @ subagent
```

Phase 3 직전 감사 순서 배지:
```
📡 Phase 3 Audit — 예정 순서:
  [Claude  ] architect     → sonnet   @ subagent
  [Claude  ] devils-adv    → haiku    @ subagent
  [⚖ opus ] final-auditor  → opus     @ subagent   (만장일치 판정)
```

#### 레이어 2: 개별 호출 실시간 배지 (v0.8.1+)

**각 Performer 호출 이벤트**(시작·완료·폴백·최종실패) 를 개별 라인으로 실시간 출력. 외부 LLM 이 실제로 어느 시점에 돌고 있는지 사용자가 직접 확인 가능:

```
▶ [Gemini  ] architect — 호출 시작 (gemini-2.5-flash @ MCP(gemini-ensembra))
⚠ [Gemini  ] architect — HTTP 429 rate limit → Ollama 폴백
▶ [Ollama  ] architect — 호출 시작 (qwen2.5:14b @ localhost:11434)
◀ [Ollama  ] architect — 응답 수신 (4721ms, 2.3KB)
```

심볼 규약: `▶` 호출 시작, `◀` 호출 완료, `⚠` 실패/폴백, `✗` transport-chain 전체 소진.

#### 레이어 3: Phase 종료 집계 배지 (v0.8.1+)

Phase 1·3 각 종료 시 외부 LLM 사용 통계 1회 출력:

```
📊 Phase 1 외부 LLM 호출 집계:
  MCP(Gemini)    2회 호출 / 2 성공 / 0 폴백
  Ollama         2회 호출 / 1 성공 / 1 폴백
  Claude 폴백    1회
  외부 LLM 활용률: 3/4 (75%)
```

**활용률** = (MCP 성공 + Ollama 성공) / (Performer 호출 총 수) × 100. 상세·해석 가이드·금지 항목은 `CONTRACT.md §8.6.3` 참조.

#### 금지선 (전 레이어 공통)

- API 키·Authorization·토큰 절대 포함 금지
- 프롬프트·응답 본문 원문 금지 — 메타데이터(bytes/ms/상태) 만 허용
- `logging.show_transport_badge: false` → 3 레이어 **모두** 억제 (단일 토글)

### Phase 2 — Execute

Conductor(= 현재 Claude Code 세션) 가 **본인** 도구(`Edit`, `Write`, `Bash`) 로 Plan 을 실행. 외부 Performer 는 이 단계에 관여하지 않는다.

Plan 의 각 파일 변경 항목에 대해:
- `create`: `Write` 로 신규 파일 생성
- `modify`: `Read` 후 `Edit` 로 수정
- `delete`: `Bash rm` (신중하게)

실행 중 오류 발생 시 즉시 중단하고 사용자에게 보고.

### Phase 3 — Audit (v0.8.0+ 2단계: 전문 감사자 → final-auditor)

`presets/{preset}.yaml` 의 `audit.auditors` 목록을 **Plan Tier** 로 필터링 후 순차 호출. **final-auditor 는 tier 필터링 대상이 아니며 (pro/max 모두 필수)** 항상 마지막에 1회 호출된다.

#### 3-1. 전문 감사자 호출

`audit.auditors` 에서 `final-auditor` 를 제외한 항목을 순차 호출. `tier=pro` 면 **첫 1명** 만, `tier=max` 면 전원. 각자에게 Plan + Phase 2 diff 전달.

감사자 출력 스키마:
```json
{
  "phase": "audit",
  "role": "architect|devils-advocate|...",
  "verdict": "pass|fail|rework",
  "issues": [{"severity": "high|medium|low", "file": "...", "line": N, "message": "..."}]
}
```

판정:
- 한 명이라도 `verdict: "fail"` → Rework 트리거 (**final-auditor 호출되지 않음**, opus 비용 절감)
- 2명 이상 `rework` → Rework 트리거
- 모두 `pass` → **3-2 final-auditor 호출 진행**

Rework 시 Phase 1 복귀, **Plan diff 만** 전달. Rework 상한 2회 (config 조정 가능).

#### 3-2. final-auditor 호출 (v0.8.0+)

전문 감사자 전원 `pass` 직후 Conductor 는 `final-auditor` 서브에이전트를 호출한다. 입력: 원 요청 + Phase 1 Synthesis + Phase 2 diff + 전문 감사자 출력 전체.

final-auditor 출력 스키마 (§11.3):
```json
{
  "phase": "audit",
  "role": "final-auditor",
  "verdict": "pass|fail|rework",
  "unanimous": true|false,
  "consensus_rate": 84,
  "summary": "1~3문장 종합 판단",
  "issues": [...]
}
```

판정:
- `verdict: "pass"` AND `consensus_rate >= 70` → **만장일치 도달**, `unanimous: true`, Phase 4 진행
- `verdict: "rework"` → **Final Audit Rework** (별도 카운터, 상한 **1회**). Phase 1 복귀, `prior_outputs` 에 Plan diff + final-auditor issues 주입, 전문 감사자 재호출 없음
- `verdict: "fail"` → 파이프라인 중단, 사용자 수동 판정
- Final Audit Rework 1회 소진 후에도 rework/fail → 파이프라인 중단

Phase 3 진입 전에 감사 순서 배지를 1회 출력:
```
📡 Phase 3 Audit — 예정 순서:
  [Claude  ] architect     → sonnet   @ subagent
  [Claude  ] devils-adv    → haiku    @ subagent
  [⚖ opus ] final-auditor  → opus     @ subagent   (만장일치 판정)
```

### Phase 4 — Document

`audit.phase4` 설정에 따라 scribe 호출. 생성할 문서 유형은 프리셋별:
- `feature`/`refactor`: Task Report + Design Doc + Request Spec
- 그 외: Task Report 만

scribe 의 입력은 **Plan Tier** 로 결정:
- `tier=pro`: Phase 0~3 기록의 **요약본** (각 Phase 당 500자 이내, Conductor 가 사전 압축)
- `tier=max`: Phase 0~3 **원본 기록** 전체

scribe 는 받은 입력으로 템플릿 슬롯을 채운다. 완료 후 파일 저장 경로를 사용자에게 보고.

## 출력 포맷
최종 사용자 응답은 다음 구조 (v0.8.0+ `unanimous` 필드, v0.8.1+ `외부 LLM 활용률` 필드):
```
## Ensembra Run — {preset}

🎚 **plan_tier**: pro    (또는 max)
**결과**: Pass (Audit 통과)
**합의율**: 84%
**만장일치**: ✅ 도달 (토론 합의율 ≥70% AND final-auditor pass)
**Rework 횟수**: 전문 감사 0 / Final Audit 0
**외부 LLM 활용률**: Phase 1 75% / Phase 3 50% (합산 66%)

### 변경 파일
- src/payment/checkout.ts (+24 -3)
- tests/payment/coupon.test.ts (+52)

### 생성된 문서
- docs/reports/tasks/2026-04-15-add-coupon.md
- docs/design/payment.md (append)
- docs/requests/2026-04-15-add-coupon.md

### 재사용 기회 평가
(Synthesis 최상단 섹션 복사)

### Final Auditor 총평
(final-auditor.summary 1~3문장 복사)
```

**외부 LLM 활용률** 산식: `(MCP 성공 + Ollama 성공) / (Performer 호출 총 수) × 100`. 상세는 `CONTRACT.md §8.6.3` 참조. Phase 별 집계는 `📊` 배지로 실시간 출력되며, 본 요약 행은 파이프라인 종료 시 1회 합산 표시.

## 보안
- 시크릿 파일(`.env`, `*.key`)은 Phase 0 에서 경로만 수집, 내용 전달 금지
- 로그·보고서에 마스킹 키 적용 (`SECURITY.md`)
- Phase 2 의 비가역 동작(`git push`, `rm -rf` 등)은 사용자 확인 후에만

## 금지
- Phase 0 Deep Scan 강제 6항목 미수행 시 Phase 1 진입 금지
- 외부 Performer(Ollama/Gemini) 에게 파일 쓰기 권한 위임 금지
- Plan 외 파일 수정 금지 (Phase 2)
