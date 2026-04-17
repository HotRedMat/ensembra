# Ensembra — 오케스트레이터 ↔ 에이전트 계약 (Gate1)

이 문서는 Ensembra 오케스트레이터와 서브에이전트(연주자) 사이의 **데이터·프로토콜 계약**을 정의한다. 언어·런타임에 중립적이며, 구현은 Gate2 범위다.

`TODO(gate2)`: 이 계약을 실제 코드(스키마 검증기, 라운드 러너)로 구현하는 것은 Gate2 범위. Gate1 에서는 문서 합의만 한다.

---

## 1. 용어
- **Conductor**: 파이프라인을 진행하는 오케스트레이터. 라운드 전환·합성·종료 조건을 책임진다.
- **Performer**: 단일 서브에이전트. 한 턴에 한 입력을 받아 한 출력을 낸다.
- **Round**: 한 번의 동시 실행 묶음. R1, R2, R3 ... 순서로 진행.
- **Score**: 파이프라인 전체 상태 (입력 문제 + 누적 출력).

---

## 2. 에이전트 입력 스키마

Performer 가 매 라운드 시작 시 받는 JSON.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["round", "problem", "role", "prior_outputs"],
  "properties": {
    "round": {
      "type": "string",
      "enum": ["R1", "R2", "R3", "synthesis", "audit"]
    },
    "problem": {
      "type": "string",
      "description": "사용자가 제기한 원 문제. 라운드 내내 불변."
    },
    "role": {
      "type": "string",
      "description": "이 Performer 의 역할 ID (예: architect, security, performance)"
    },
    "prior_outputs": {
      "type": "array",
      "description": "이전 라운드의 모든 Performer 출력. R1 에서는 빈 배열.",
      "items": { "$ref": "#/$defs/agentOutput" }
    },
    "constraints": {
      "type": "object",
      "description": "선택. 토큰 한도·금지 주제·참조 파일 등.",
      "additionalProperties": true
    }
  }
}
```

---

## 3. 에이전트 출력 스키마

Performer 가 매 턴 반환하는 JSON.

```json
{
  "$defs": {
    "agentOutput": {
      "type": "object",
      "required": ["role", "round", "status", "summary", "reuse_analysis"],
      "properties": {
        "role": { "type": "string" },
        "round": { "type": "string", "enum": ["R1", "R2", "R3", "synthesis", "audit"] },
        "status": { "type": "string", "enum": ["ok", "abstain", "error"] },
        "summary": {
          "type": "string",
          "description": "1~3문장 핵심 주장."
        },
        "arguments": {
          "type": "array",
          "items": { "type": "string" },
          "description": "근거 bullet. status=ok 일 때 1개 이상 권장."
        },
        "risks": {
          "type": "array",
          "items": { "type": "string" }
        },
        "references": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "path": { "type": "string" },
              "line": { "type": "integer" }
            }
          }
        },
        "reuse_analysis": {
          "type": "object",
          "description": "Reuse-First 교차 원칙 장치 2. R1 에서 필수, 장치 2 가 켜진 경우에만.",
          "required": ["inventory_checked", "reusable_candidates", "decision"],
          "properties": {
            "inventory_checked": { "type": "boolean" },
            "reusable_candidates": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "path": { "type": "string" },
                  "symbol": { "type": "string" },
                  "why": { "type": "string" }
                }
              }
            },
            "decision": { "type": "string", "enum": ["reuse", "extend", "new"] },
            "new_creation_justified": { "type": "string" }
          }
        },
        "peer_signatures": {
          "type": "array",
          "description": "R2 라운드에서 필수. 다른 Performer 에 대한 서명.",
          "items": {
            "type": "object",
            "required": ["target_role", "vote"],
            "properties": {
              "target_role": { "type": "string" },
              "vote": { "type": "string", "enum": ["agree", "disagree", "abstain"] },
              "note": { "type": "string" }
            }
          }
        },
        "_error": {
          "type": "object",
          "description": "status=error 일 때만 존재.",
          "properties": {
            "code": { "type": "string" },
            "message": { "type": "string" }
          }
        }
      }
    }
  }
}
```

---

## 4. 라운드 실행 프로토콜

### R1 — 독립 분석
- Conductor 는 모든 Performer 에게 **동일한 `problem`** 과 **빈 `prior_outputs`** 를 전달.
- Performer 는 서로의 답을 보지 못한 상태에서 독립적으로 응답한다.
- 목표: 편향 없는 1차 관점 수집.

### R2 — 반론
- Conductor 는 R1 의 전체 출력을 `prior_outputs` 로 재전달.
- 각 Performer 는 자신의 R1 을 제외한 다른 Performer 의 주장을 **비판·보강·수용** 한다.
- 목표: 합의 가능 지점과 진짜 이견을 분리.

### R3 — 선택적 보강 (Optional)
- Conductor 가 R2 결과 합의율이 임계값 미만일 때만 실행.
- R2 와 동일한 입력 구조지만 `round: "R3"`.

### Synthesis — 합성
- Conductor 가 단독으로 (또는 전용 synthesizer Performer 로) 실행.
- `round: "synthesis"`, `prior_outputs` 에 R1~R3 전체 누적.
- 출력은 최종 권고 1개 + 소수 의견 목록.

---

## 5. 에러 처리 규약

- Performer 가 예외를 던지거나 스키마 위반을 반환하면 Conductor 는 **해당 Performer 의 출력만** `status: "error"`, `_error: { code, message }` 로 마킹하고 라운드를 계속 진행한다.
- 한 라운드에서 절반 이상의 Performer 가 `error` 면 Conductor 는 라운드를 **중단**하고 부분 결과를 사용자에게 반환한다.
- `abstain` 은 에러가 아니다. 해당 Performer 가 의견 없음을 명시한 것으로 간주한다.
- 타임아웃은 Conductor 가 Performer 별로 별도 관리. 타임아웃 초과 시 `_error.code = "timeout"`.

---

## 6. 종료 조건

Conductor 는 다음 중 하나를 만족하면 파이프라인을 종료한다:

1. Synthesis 라운드 완료.
2. 어느 라운드에서든 과반 Performer 가 `error`.
3. 사용자 취소 신호.
4. 누적 라운드 수가 상한(`max_rounds`, Gate2 에서 결정)을 초과.

---

## 7. 불변식 (Invariants)

- `problem` 은 파이프라인 시작 시점에 고정되며 어떤 라운드에서도 변경되지 않는다.
- Performer 는 `prior_outputs` 를 **읽기 전용**으로 취급한다.
- Conductor 는 Performer 출력을 수정하지 않고 그대로 누적한다. 합성은 오직 synthesis 라운드에서만 일어난다.
- Performer 는 Conductor 의 내부 상태를 관찰하지 못한다.

---

## 8. Transport (Performer 호출 방식)

Performer 는 이종(heterogeneous) 이다. Conductor 는 각 Performer 의 `transport` 유형에 따라 호출 방식을 달리 한다. 입력·출력 스키마는 transport 와 무관하게 §2, §3 을 따른다.

### 8.1 Transport 유형

| Transport | 대상 | 호출 방식 | 시크릿 |
|---|---|---|---|
| `mcp` | MCP stdio server | Claude Code MCP tool-use (JSON-RPC 2.0 over stdin/stdout) | MCP server env var (skill content 미노출) |
| `ollama` | 로컬 Ollama | `POST http://localhost:11434/api/chat`, `"stream": false` | 없음 |
| `gemini` | Google Gemini 공식 API (레거시, v0.6.0 폐지) | `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | `GEMINI_API_KEY` (⚠ skill content 유출) |
| `claude-subagent` | Claude Code 내장 서브에이전트 | in-process (Claude Code 가 자동 처리) | 없음 (세션 토큰) |

`chatgpt-web`, `gemini-web` 등 웹 UI 스크래핑 기반 transport 는 **명시적으로 제외**한다. ToS 위반 및 유지보수 취성 사유.

### 8.2 Performer 레지스트리

각 Performer 는 다음 필드로 선언된다 (형식은 Gate2 에서 파일 포맷 확정).

```json
{
  "role": "performance",
  "transport": "ollama",
  "model": "qwen2.5:14b",
  "endpoint": "http://localhost:11434/api/chat",
  "timeout_sec": 120
}
```

- `transport: "mcp"` 일 때는 `mcp_server_name` 필수 (예: `"gemini-architect"`). `model` 은 MCP tool 인자로 전달.
- `transport: "gemini"` 은 레거시 (v0.6.0 폐지). 신규 사용 금지 — `mcp` transport 를 사용하라.
- `transport: "claude-subagent"` 일 때는 `model` 에 Claude 모델(`opus`/`sonnet`/`haiku`) + `agent_name` 으로 `.claude/agents/*.md` 의 `name` 참조.

### 8.3 외부 LLM 응답 파싱 계약

`ollama`, `gemini` Performer 는 구조화 JSON 출력을 보장하지 못한다. 계약:

1. Conductor 는 시스템 프롬프트 말미에 고정 구분선과 출력 템플릿을 주입한다:
   ```
   반드시 응답 마지막에 다음 블록을 포함하라:
   ===ENSEMBRA-OUTPUT===
   {"status": "ok|abstain|error", "summary": "...", "arguments": [...], "risks": [...]}
   ===END===
   ```
2. Conductor 는 `===ENSEMBRA-OUTPUT===` ~ `===END===` 사이를 추출해 §3 스키마로 검증.
3. 블록이 없거나 JSON 파싱 실패 시 Performer 출력을 `status: "error"`, `_error.code: "format"` 로 마킹. §5 에러 규약에 따름.
4. 자연어 서술은 절대 Conductor 가 재정리하지 않는다. `summary`, `arguments` 는 Performer 가 선언한 그대로 보존.

### 8.4 Architect Transport — MCP 기반 Gemini 재도입 (v0.7.0+)

**이력**:
- v0.5.1: `sensitive: false` + skill content 치환 → 매 실행마다 세션 로그에 키 평문 유출 (구조적 결함)
- v0.6.0: Gemini 폐지, Ollama 이관, `sensitive: true` 복구
- **v0.7.0: MCP server 기반 Gemini 재도입** — Gate3 전제조건 3가지 충족

**Gate3 전제조건 충족 현황**:
1. ✅ architect Performer 를 **MCP server** (`mcp-servers/gemini-architect/server.py`) 로 이전
2. ✅ `sensitive: true` 값은 MCP server config 의 `env.GEMINI_API_KEY` 로만 접근 (skill/agent content 미노출)
3. ✅ skill/agent content 는 MCP tool 호출 결과만 참조, 키 직접 참조 없음

**v0.7.0 architect Transport 3단 폴백 체인**:

```
1. MCP(gemini-architect) — GEMINI_API_KEY 설정 + MCP server 응답 시
   └─ tool: architect_deliberate(prompt, model, timeout_sec)
   └─ 실패 시 → 2번으로 폴백

2. Ollama(qwen2.5:14b) — localhost:11434 응답 시
   └─ curl POST /api/generate
   └─ 실패 시 → 3번으로 폴백

3. Claude(sonnet) — 최종 폴백 (항상 가용)
   └─ in-process 서브에이전트
```

**MCP server 등록**: `plugin.json` 의 `mcpServers` 필드에 선언되어 플러그인 설치 시 **자동 등록** 된다:
```json
"mcpServers": {
  "gemini-architect": {
    "command": "python3",
    "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/gemini-architect/server.py"],
    "env": {
      "GEMINI_API_KEY": "${user_config.gemini_api_key}"
    }
  }
}
```
`${CLAUDE_PLUGIN_ROOT}` 는 Claude Code 가 플러그인 설치 경로로 자동 치환한다. 사용자가 `settings.local.json` 을 수동 편집할 필요 없음.

**`sensitive: true` 불변식 유지**: `gemini_api_key` 는 OS 키체인에 저장, MCP server config 의 `${user_config.gemini_api_key}` 치환으로만 프로세스 env 에 전달. skill/agent content, 시스템 프롬프트, 세션 로그에 키가 노출되지 않음.

**gemini Transport (레거시)**: v0.6.0 에서 폐지된 `transport: "gemini"` 은 하위 호환을 위해 스키마에 남되 **신규 사용 금지**. `transport: "mcp"` + `mcp_server_name: "gemini-architect"` 를 사용하라.

**로그 마스킹**: `x-goog-api-key`, `Authorization`, `key=`, `CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY`, `user_config.gemini_api_key`, `GEMINI_API_KEY` 전부 `[REDACTED]` (v0.5.x 관례 유지)

**제거된 경로** (v0.5.0~v0.6.0 누적):
- `~/.config/ensembra/env` 파일 폴백 (v0.5.0)
- `bin/ensembra-set-key` 스크립트 (v0.5.0)
- `/ensembra:config → 5) c)` 대화창 키 붙여넣기 (v0.5.0)
- `sensitive: false` 평문 저장 + `${user_config.gemini_api_key}` skill content 치환 (v0.6.0)
- architect 의 Gemini Transport 기본값 (v0.6.0)
- `/ensembra:config → 5) c)` 에서 인터랙티브 파일 쓰기

**이전 버전 참고**:
- v0.1.x: env 파일 단일 소스
- v0.2.x: userConfig 단일 소스 시도 (스키마 결함 + Claude Code 이해 부족으로 실패 판단)
- v0.3.x: 하이브리드 (userConfig + env 파일)
- v0.4.x: 하이브리드 + `bin/ensembra-set-key` 편의 스크립트
- **v0.5.0**: 순수 userConfig 복귀. 바이너리 리버싱으로 Claude Code 실제 규격 확인 (`sensitive: true` 완전 구현, `/plugin → Configure options` UI 경로 존재) 후 모든 워크어라운드 제거.

**마이그레이션**: v0.1.x~v0.4.x 에서 `~/.config/ensembra/env` 파일을 사용하던 사용자는:
1. 해당 파일 수동 삭제: `rm -rf ~/.config/ensembra`
2. `/plugin → ensembra → Configure options` 에서 키 재설정
3. `/reload-plugins`

### 8.5 MCP Transport 호출 규약

`transport: "mcp"` 인 Performer 호출 시:

1. Conductor 는 MCP tool-use 를 통해 해당 MCP server 의 tool 을 호출한다
2. MCP server 는 외부 API 호출 후 결과를 `content[].text` 로 반환
3. Conductor 는 반환된 텍스트에서 `===ENSEMBRA-OUTPUT===` 블록을 추출 (§8.3 동일)
4. MCP tool 의 `isError: true` 응답 시 `transport-failure` 로 마킹, 폴백 체인 진행

**Health Check**: Phase 0 직전에 MCP server 가용 여부를 확인한다. MCP tool-use 호출이 가능한지 Claude Code 에 위임. 불가 시 즉시 다음 폴백으로 전환하고 배지 출력.

### 8.6 LLM 호출 배지 규약 (v0.7.0+, v0.8.1 Live Indicators)

Conductor 는 `config.json logging.show_transport_badge: true` (기본) 일 때 외부 LLM 호출 현황을 배지로 출력한다. 배지는 **3 레이어** 로 구성된다 — (1) Phase 시작 현황판, (2) 개별 호출 실시간 표시(v0.8.1+), (3) Phase 종료 집계(v0.8.1+).

#### 8.6.1 Phase 시작 현황판 (v0.7.0+)

Phase 1 R1 / Phase 3 Audit 시작 직전 **1회** 전체 Performer 의 Transport/Model 계획을 한 번에 표시.

```
📡 Phase 1 R1 — Transport 현황:
  [Gemini  ] architect  → gemini-2.5-flash  @ MCP(gemini-architect)
  [Ollama  ] security   → qwen2.5:14b       @ localhost:11434
  [Ollama  ] qa         → llama3.1:8b       @ localhost:11434
  [Claude  ] planner    → sonnet            @ subagent    (v0.8.0 opus→sonnet)
  [Claude  ] developer  → sonnet            @ subagent
  [Claude  ] devils-adv → haiku             @ subagent
```

#### 8.6.2 개별 호출 실시간 배지 (v0.8.1+)

각 Performer 호출의 **시작·완료·폴백·최종실패** 이벤트를 개별 라인으로 출력한다. 사용자가 "외부 LLM 이 지금 실제로 돌고 있는가" 를 시각적으로 확인할 수 있게 한다 (v0.8.0 까지는 Phase 시작 1회 배지 외에는 호출 진행이 불가시했음).

| 이벤트 | 심볼 | 포맷 |
|---|---|---|
| 호출 시작 | `▶` | `▶ [<Transport>] <role> — 호출 시작 (<model> @ <endpoint>)` |
| 호출 완료 | `◀` | `◀ [<Transport>] <role> — 응답 수신 (<ms>ms, <bytes>B)` |
| 호출 실패/폴백 | `⚠` | `⚠ [<Transport>] <role> — <reason> → <next-transport> 폴백` |
| 최종 체인 소진 | `✗` | `✗ [<Transport>] <role> — transport-chain-exhausted, Performer.status=error` |

**예시 (architect 가 MCP 실패 → Ollama 성공)**:
```
▶ [Gemini  ] architect — 호출 시작 (gemini-2.5-flash @ MCP(gemini-architect))
⚠ [Gemini  ] architect — HTTP 429 rate limit → Ollama 폴백
▶ [Ollama  ] architect — 호출 시작 (qwen2.5:14b @ localhost:11434)
◀ [Ollama  ] architect — 응답 수신 (4721ms, 2.3KB)
```

**실시간 배지 필드 규약**:
- `<Transport>` : `Gemini` / `Ollama` / `Claude` (사람이 읽는 이름. 내부 transport 식별자와 다를 수 있음)
- `<model>` : 모델 ID 그대로. `gemini-2.5-flash`, `qwen2.5:14b`, `sonnet`, `haiku`, `opus`
- `<endpoint>` : MCP 는 `MCP(<server_name>)`, Ollama 는 호스트만(`localhost:11434`, 포트 포함, 경로·쿼리스트링 금지), Claude 는 `subagent`
- `<ms>` : wall-clock 밀리초. 1000 이하면 `<1000ms`, 이상이면 `1234ms` 형식
- `<bytes>` : 응답 본문 바이트 (`===ENSEMBRA-OUTPUT===` 블록 포함 전체). 1024 이상이면 KB 단위 소수 1자리(`2.3KB`), 미만이면 바이트(`812B`)
- `<reason>` : 실패 원인 1줄 요약. HTTP 상태코드, 타임아웃, 스키마 위반 등

**보안 불변식 (실시간 배지에서도 유지)**:
- API 키·Authorization 헤더·토큰 **절대 출력 금지** (§8.6.4 금지 항목 참조)
- MCP stdio payload 원문·Ollama request body·프롬프트 본문 **출력 금지** — 길이(bytes)·소요시간(ms) 만 노출
- `<reason>` 은 오류 메시지에서 헤더·응답 본문을 제외한 짧은 문자열만 (GEMINI_API_KEY 같은 키가 에러에 포함돼 있어도 Conductor 가 마스킹 후 출력)

#### 8.6.3 Phase 종료 집계 배지 (v0.8.1+)

Phase 1·3 종료 시 각 1회 해당 Phase 의 외부 LLM 호출 통계를 출력한다.

```
📊 Phase 1 외부 LLM 호출 집계:
  MCP(Gemini)    2회 호출 / 2 성공 / 0 폴백
  Ollama         2회 호출 / 1 성공 / 1 폴백
  Claude 폴백    1회
  외부 LLM 활용률: 3/4 (75%)
```

**"외부 LLM 활용률" 정의**:
```
활용률 = (MCP 성공 호출 수 + Ollama 성공 호출 수) / (해당 Phase 의 Performer 호출 총 수) × 100
```
- 분모: 실제 호출된 Performer 수 (R2 에서 skip 된 Performer 는 제외)
- 분자: transport_chain 에서 외부(MCP/Ollama) 단계가 성공적으로 응답 반환한 건수. 폴백 결과로 Claude 가 실제 처리한 건은 분자 제외
- 한 Performer 가 여러 단계에서 재시도해 성공한 경우 `MCP 실패 → Ollama 성공` 은 Ollama 성공 1건으로 집계

**활용률 해석 가이드**:
- `≥ 70%`: 외부 LLM 우선 정책이 정상 동작 중. Claude 토큰 절감 목표 달성
- `40~70%`: 일부 외부 Transport 불안정. Ollama 엔드포인트·GEMINI_API_KEY 점검 권장
- `< 40%`: 외부 경로 대부분 실패 중. 구조적 진단 필요 — 이 경우 Conductor 는 다음 Phase 로 진입하지 않고 사용자에게 경고 배지 한 번 더 출력

**최종 출력 포맷 통합 (§skills/run)**: 파이프라인 종료 시 전체 Phase 합산을 1행 요약:
```
**외부 LLM 활용률**: Phase 1 75% / Phase 3 50% (합산 66%)
```

#### 8.6.4 배지 금지 항목 (전 레이어 공통)

- 배지에 API 키, Authorization 헤더, 인증 토큰, GEMINI_API_KEY·user_config.gemini_api_key 문자열 절대 포함 금지
- 모델명 + endpoint 호스트명만 표시. 전체 URL(쿼리스트링·키 파라미터) 금지
- 실시간 배지에서 프롬프트 본문·응답 본문 출력 금지 — 메타데이터(길이·소요시간·상태) 만 허용
- `logging.show_transport_badge: false` 설정 시 §8.6.1 / §8.6.2 / §8.6.3 **3 레이어 모두** 억제 (단일 토글, 선택적 활성화 없음 — 설정 일관성)

### 8.7 라운드 피로도 대응

Ollama 는 즉시 응답하지만 Gemini 무료 티어는 분당 15 요청 제한이 있다. Conductor 는:
- 같은 라운드 내 Performer 호출을 Transport 별로 그룹화해 병렬 실행 (ollama·gemini·claude-subagent 는 상호 독립)
- Gemini Performer 가 여러 개면 순차 직렬화(RPM 보호) + 지수 백오프

### 8.8 Transport Fallback Chain Protocol (v0.8.0+)

v0.7.0 이 architect 1명에 국한된 3단 폴백(MCP→Ollama→Claude) 을 도입한 뒤, v0.8.0 은 그 패턴을 **모든 Performer 에 적용 가능한 일반 프로토콜** 로 승격한다. 역할별 특수 분기를 제거하고 단일 공통 로직으로 처리한다.

#### 8.8.1 `transport_chain` 필드

각 Performer 는 `schemas/config.json` 의 `performerConfig.transport_chain` (배열) 으로 선언한다:

```json
{
  "transport_chain": [
    {"transport": "mcp", "mcp_server_name": "gemini-architect", "mcp_tool_name": "developer_deliberate", "model": "gemini-2.5-pro", "timeout_sec": 90},
    {"transport": "ollama", "model": "gpt-oss:20b",      "endpoint": "http://localhost:11434", "timeout_sec": 120},
    {"transport": "claude-subagent", "model": "sonnet"}
  ]
}
```

체인이 선언되면 단일 `transport`/`model` 필드는 무시된다. 체인이 없으면 기존 v0.7.x 호환 경로(단일 transport + 같은 파일의 `fallback` 필드) 로 실행한다.

#### 8.8.2 공통 실행 루프

Conductor 는 체인의 각 단계를 순서대로 시도한다:

1. 가용 검사 (Health Check, §8.8.3). 실패 시 즉시 다음 단계
2. 호출 (transport 별 방식은 §8.1 표 그대로)
3. 응답 파싱 (§8.3 `===ENSEMBRA-OUTPUT===` 추출)
4. 성공 시 결과 반환 + 배지 출력 (§8.6)
5. 실패(`isError`, 타임아웃, 스키마 위반, 비어있는 응답) 시 다음 단계로 폴백
6. 전 단계 실패 시 해당 Performer 의 출력을 `status: "error"`, `_error.code: "transport-chain-exhausted"` 로 마킹

#### 8.8.3 단계별 Health Check

| Transport | Health Check | 실패 판정 기준 |
|---|---|---|
| `mcp` | MCP tool-use `tools/list` 로 대상 tool 존재 확인 (Phase 0 1회 캐시, TTL 300초) | tool 미노출, stdio 응답 없음, timeout 3초 초과 |
| `ollama` | `GET {endpoint}/api/tags` 200 + `.models[].name` 에 지정 모델 포함 | HTTP 실패, 모델 미존재, timeout 3초 초과 |
| `claude-subagent` | 항상 available 간주 | 실패 시 최종 오류 (폴백 없음) |

#### 8.8.4 external_first 토글 (v0.8.0+)

`config.external_first: true` 일 때 Conductor 는:
- 체인에 `claude-subagent` 가 있고 그 **앞 단계** 중 외부(MCP/Ollama) 가 Health Check 실패 중이면, 경고 배지 `⚠ {role}: external unavailable → claude-subagent fallback` 를 Phase 1 시작 시 한 번 더 강조
- 체인이 선언되지 않은 Performer 중 `planner`/`scribe` 는 예외 (금지선). 그 외 Performer 에 대해 자동 추천 체인 제시 (`developer` → 외부 우선 체인 제안 등)

#### 8.8.5 tool 이름 유추

`transport: "mcp"` 단계에서 `mcp_tool_name` 이 생략되면 Conductor 는 `{role}_deliberate` 로 유추한다 (예: architect → `architect_deliberate`). 명시적으로 지정하려면 `mcp_tool_name` 을 기록한다. Ensembra 가 기본 제공하는 MCP server `gemini-architect` 는 v0.8.0 부터 `architect_deliberate` 와 `developer_deliberate` 2개 tool 을 노출한다.

#### 8.8.6 기존 v0.7.0 architect 체인 재해석

v0.7.0 의 architect 전용 3단 체인은 v0.8.0 에서 다음 선언과 의미가 같다:

```json
"architect": {
  "transport_chain": [
    {"transport": "mcp", "mcp_server_name": "gemini-architect", "mcp_tool_name": "architect_deliberate", "model": "gemini-2.5-flash"},
    {"transport": "ollama", "model": "qwen2.5:14b"},
    {"transport": "claude-subagent", "model": "sonnet"}
  ]
}
```

즉 v0.7.x 사용자의 동작은 설정 마이그레이션 없이도 그대로 유지된다. `agents/architect.md` 의 Transport 섹션은 위 선언의 의미를 그대로 서술하는 것이고, 코드 경로는 §8.8 공통 루프에 흡수되었다.

## 9. Work Phases (5단 파이프라인)

```
Phase 0 Gather       — Claude Code 가 Deep Scan (§12) 수행, 공용 Context Snapshot 생성
Phase 1 Deliberate   — R1 → (조건부 R2) → Synthesis, Peer Signature (§10) 기반 합의율 집계
Phase 2 Execute      — Claude Code 본체가 합의된 Plan 대로 파일 수정/생성
Phase 3 Audit        — 지정 감사 Performer 들이 diff + Plan 을 받아 Pass/Fail/Rework 판정
Phase 4 Document     — scribe Performer 가 결과물을 문서화 (§15)
```

- Phase 2 는 Claude Code 만 접근. 외부 Performer(Ollama/Gemini) 는 파일 쓰기 권한 없음.
- Phase 3 Fail 시 Phase 1 로 복귀하되 **Plan diff 만** 전달. Rework 상한 2회.
- Phase 4 는 scribe 단독 수행. 토론 참여하지 않음. Peer Signature 대상 아님.
- **범위 제외**: 세션 중단·재개 노트(Handoff) 는 Ensembra 가 다루지 않는다. 외부 플러그인(예: `d2-ops-handoff`) 이 담당한다. Ensembra 의 `transfer` 프리셋(§11, §15) 은 프로젝트 이관용 독립 문서에 한정된다.

## 10. Peer Signature (상호 감시)

R2 라운드에서 각 Performer 출력에 `peer_signatures` 필드가 필수 (§3 참조).

### 10.1 합의율 임계값 (Q8 결정)

Synthesis 는 서명 매트릭스로 합의율을 계산:
- **≥ 70% agree** → Plan 확정, Phase 2 진행
- **40~70%** → R3 또는 사용자 수동 판정
- **< 40%** → 파이프라인 중단, 쟁점 목록 반환

임계값은 `/ensembra:config → Rounds` 에서 조정 가능.

### 10.2 Reuse-First 자동 disagree 규칙

다음 조건을 만족하는 경우, 평가자 Performer 는 **의무적으로 `vote: "disagree"`** 를 부여한다 (§16 장치 3 활성화 시):

1. 대상 Performer 의 `reuse_analysis.reusable_candidates` 가 비어있지 않음
2. 대상 Performer 의 `reuse_analysis.decision === "new"`
3. `new_creation_justified` 가 다음 중 하나에 해당:
   - 50자 미만
   - "깨끗", "간단", "가독성", "스타일" 등 측정 불가 어휘만 사용
   - `reusable_candidates` 의 구체 심볼을 사유에서 전혀 언급하지 않음

자동 disagree 의 `note` 에는 다음 문구 자동 삽입:
`"Reuse-First 원칙: {path}#{symbol} 재사용 후보 존재, 기각 사유 부실"`

**예외**: devils-advocate 는 자동 disagree 규칙에서 제외. 반론 역할상 "재사용 강제에 대한 반대" 가 합법적 의견이므로.

## 11. Preset (작업 유형별 파이프라인)

### 11.1 Performer 풀 (§12 참조)

v0.8.0+ 는 Performer 를 **역할군 3개** 로 분리한다:

**토론(Phase 1) Performer — 6명** (opus 금지선, 외부 LLM + sonnet 이하):
- 🧭 **planner** (`claude-subagent` / `sonnet`) — v0.8.0 부터 opus → sonnet 강등
- 🏛 **architect** (`mcp` → `ollama` → `claude-subagent` / `gemini-2.5-flash` → `qwen2.5:14b` → `sonnet`, §8.8 체인)
- 🛠 **developer** (`claude-subagent` / `sonnet`, opt-in MCP 체인 §8.8)
- 🛡 **security** (`ollama` → `claude-subagent` / `qwen2.5:14b` → `sonnet`)
- 🧪 **qa** (`ollama` → `claude-subagent` / `llama3.1:8b` → `sonnet`)
- 😈 **devils-advocate** (`claude-subagent` / `haiku`) — opus 계열 아니므로 유지

**감사(Phase 3) Performer — preset 전문 감사자 + 최종 감사자 1명**:
- 전문 감사자: preset 별 `audit.auditors` 지정 (예: refactor → architect+devils)
- ⚖️ **final-auditor** (`claude-subagent` / `opus`, Phase 3 전용) — v0.8.0 신설. **모든 preset 의 audit 체인 마지막에 자동 배치**. Phase 1 토론·Phase 4 문서화 불참. 만장일치 판정자 (§11.3)

**문서화(Phase 4) Performer — 1명**:
- ✍️ **scribe** (`claude-subagent` / `sonnet`, Phase 4 전용)

**Debate/Audit 분리 원칙 (v0.8.0 불변식)**:
- 토론 Performer 전체는 opus 사용 금지. 외부 LLM 또는 sonnet/haiku/외부 소형 모델 조합만 허용.
- opus 는 Phase 3 `final-auditor` 1명에만 배치. 토론·문서화 참여 금지.
- 이 분리를 토글할 수 있는 config 옵션은 존재하지 않는다 (금지선).

### 11.2 프리셋 매트릭스

v0.8.0+ 기준. Phase 3 Audit 의 **final-auditor** 는 파일 수정이 발생하는 preset(`feature`/`bugfix`/`refactor`) 에 자동 배치된다. 읽기 전용 preset(`security-audit`/`source-analysis`/`transfer`) 은 audit 자체가 off 이므로 해당 없음.

| Preset | Phase 0 | Performer | Rounds | Phase 2 | Phase 3 Audit (전문 → final-auditor) | Phase 4 |
|---|---|---|---|---|---|---|
| `feature` | Deep Scan | 전원 6 | R1→R2→Syn | on | architect+developer+security+qa+devils+**final-auditor** | Task+Design+Request |
| `bugfix` | Deep Scan + 스택트레이스 | planner+architect+qa+developer | R1→Syn | on | qa+security+**final-auditor** | Task |
| `refactor` | Deep Scan + 호출 그래프 | architect+developer+devils+qa | R1→R2→Syn | on | architect+devils+**final-auditor** | Task+Design+Request |
| `security-audit` | Deep Scan + 의존성 | security+devils+architect | R1→Syn | off | — (읽기 전용) | Task |
| `source-analysis` | Deep Scan | architect+security+developer | R1→Syn | off | — (읽기 전용) | Task |
| `transfer` | **Wide Scan** (전 레포) | 전원 6 + scribe | R1 only | off | off | **특수** (인수인계서, §15) |

호출: `/ensembra:run <preset> "<요청>"`  또는  `/ensembra:transfer [scope]`

### 11.3 Final Audit & Unanimous Consensus (v0.8.0+)

Phase 3 의 감사는 **전문 감사자 다수 → final-auditor 1명 (opus)** 2단계 구조다. 최종 판정은 `final-auditor` 가 내린다.

#### 11.3.1 호출 순서

1. 전문 감사자(`preset.audit.auditors` 의 final-auditor 를 제외한 항목들) 를 선언된 순서로 호출
2. 전문 감사자 전원 `verdict: pass` 면 → `final-auditor` 호출
3. 전문 감사자 중 1명이라도 `fail` → 기존 Rework 규약(Phase 1 복귀, 상한 2회) 적용. final-auditor 는 호출되지 않음 (opus 비용 절감)
4. `final-auditor` 가 `verdict: pass` → **만장일치 도달**, Phase 4 진행
5. `final-auditor` 가 `verdict: rework` → **Final Audit Rework** 트리거 (§11.3.3, 상한 1회)
6. `final-auditor` 가 `verdict: fail` → 파이프라인 중단, 사용자 수동 판정

#### 11.3.2 만장일치(Unanimous) 정의

다음 2개 조건을 **모두** 만족할 때만 Conductor 가 `unanimous: true` 플래그를 출력한다:

- Phase 1 Synthesis 합의율 ≥ 70% (기존 §10.1 임계값)
- `final-auditor.verdict == "pass"`

둘 중 하나라도 불충족이면 `unanimous: false` 로 표시되며, Conductor 는 사용자에게 **쟁점 목록** 을 반환한다.

"100% agree" 같은 엄격한 정의는 사용하지 않는다 — 실효성 없이 Rework 루프만 증가시키기 때문이다. 70% 합의 + opus 종합 판단이 "실질적 만장일치" 의 조작적 정의다.

#### 11.3.3 Final Audit Rework (신규, 상한 1회)

기존 Rework(§11.2 "Rework 상한 2회") 는 전문 감사자 `fail` 에서만 트리거된다. `final-auditor` 의 `rework` 판정은 별도 카운터를 갖는다:

- Rework 상한: **1회** (opus 호출 비용 제어)
- 트리거 조건: `final-auditor.verdict == "rework"` AND `final_audit_rework_count < 1`
- 동작: Phase 1 복귀, **Plan diff + final-auditor issues** 를 `prior_outputs` 에 주입. 전문 감사자는 재호출되지 않음 (비용 절감)
- 1회 소진 후에도 `rework` 면 파이프라인 중단

#### 11.3.4 금지선

- `final-auditor` 를 토론(Phase 1) 에 참여시키는 config 금지
- `final-auditor` 모델을 opus 외로 변경하는 config 금지 (v0.8.0 불변식)
- preset `audit.auditors` 에서 `final-auditor` 를 제거하는 것은 허용하지 않는다 — 자동 마지막 배치가 강제됨
- 읽기 전용 preset(`audit: false`) 에는 final-auditor 도 호출되지 않음 (유일한 예외)

## 12. Deep Source Inspection (필수)

문제 파악·소스 수정·분석 작업에서 Phase 0 은 **Deep Scan** 을 강제한다. 얕은 읽기(파일 1개만 열람) 는 금지.

### 12.1 체크리스트 10항목

| # | 항목 | 강도 |
|---|---|---|
| 1 | **구조 파악** — 디렉토리 트리, 진입점 식별 | **강제** |
| 2 | **키워드 역추적** — 심볼을 전 레포 Grep | **강제** |
| 3 | **호출 그래프** — 정의부 + 호출 지점 + import | **강제** |
| 4 | **데이터 흐름** — 생성→변형→소비 경로 | **강제** |
| 5 | 테스트 맵 — 연결된 테스트 수집 | 선택 |
| 6 | git 히스토리 — 최근 변경 5건 | 선택 |
| 7 | 의존성 — package.json 등 관련 라이브러리 | 선택 |
| 8 | 설정 — env·설정 파일 관련 키 | 선택 |
| 9 | **공통 모듈 인벤토리** — `commons/`/`shared/`/`lib/`/`utils/`/`framework/` 전수 | **강제** (Reuse-First 기반) |
| 10 | **프로젝트 문서 인벤토리** — `docs/`/`spec/`/`requirements/`/`design/` 전수 | **강제** (문서 담당 기반) |

**강제 항목 (1,2,3,4,9,10)** 은 사용자가 끌 수 없다. 선택 항목 (5,6,7,8) 은 `/ensembra:config → Deep Scan` 에서 토글.

### 12.2 Wide Scan (`transfer` 프리셋 전용)

인수인계서 생성 시엔 Deep Scan 대신 **Wide Scan** 을 수행한다. 범위가 전 레포로 확대됨:
- 강제 10항목 모두 수행
- git 히스토리: 대상 파일이 아닌 **전 레포 최근 30일** 대상
- 문서 인벤토리: `docs/` 전체 구조 + 최근 Task Report/Weekly Report 집계
- TODO/FIXME/XXX 주석 전수 집계

### 12.3 산출물

단일 **Context Snapshot** (Markdown). 모든 Performer 의 R1 입력 `constraints.context_snapshot` 에 첨부.

Deep Scan 은 Claude Code 의 병렬 tool call 로 수행. 외부 Performer 는 파일시스템 접근하지 않는다.

`TODO(gate2)`: Deep Scan 체크리스트 미수행 시 Conductor 가 Phase 1 진입을 거부하도록 게이트 구현.
`TODO(gate2)`: 확장 후보 11~16 (lint, typecheck, runtime logs, TODO 집계, benchmark, API/DB schema) 를 언어 확정 후 선택 항목으로 추가 검토.

## 13. Model Resolution & Fallback

각 Performer 는 `transport` + `model` 을 선언하지만, 런타임에 해당 모델을 이용할 수 없으면 다음 순서로 자동 폴백한다.

### 13.1 해석 순서
1. **사용자 config** (`~/.config/ensembra/config.json`) 의 `performers.<role>` 지정값
2. **Preset 기본값** (`presets/*.yaml` 에 선언된 기본 Transport·모델)
3. **폴백**: Claude Code 본체의 현재 세션 모델 (`claude-subagent` transport, 모델은 세션 기본)

### 13.2 Health Check (매 Phase 0 직전 수행)
- `ollama`: `GET http://localhost:11434/api/tags` 200 + 목록에 지정 모델 포함 여부
- `gemini`: `GET https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY` 200 + 목록에 지정 모델 포함 여부
- `claude-subagent`: 항상 available 로 간주

Health check 실패 시:
1. 같은 transport 내 다른 모델로 폴백 가능하면 폴백 (예: `qwen2.5:14b` 실패 → `llama3.1:8b` 로)
2. 그것도 불가능하면 **Claude Code 본체 모델로 폴백** (transport=claude-subagent)
3. 폴백 발생은 Conductor 출력 상단에 배지로 고지 (`⚠ architect: gemini-2.5-flash → claude-sonnet (fallback)`)

### 13.3 Config 파일 스키마 (`~/.config/ensembra/config.json`)

```json
{
  "performers": {
    "planner":         {"transport": "claude-subagent", "model": "opus"},
    "architect":       {"transport": "gemini",          "model": "gemini-2.5-flash"},
    "security":        {"transport": "ollama",          "model": "qwen2.5:14b"},
    "qa":              {"transport": "ollama",          "model": "llama3.1:8b"},
    "devils-advocate": {"transport": "claude-subagent", "model": "haiku"}
  },
  "fallback": {
    "transport": "claude-subagent",
    "model": "sonnet"
  }
}
```

**기본 모델표** (Q1 확정):
- planner=opus / architect=gemini-2.5-flash / developer=sonnet / security=qwen2.5:14b / qa=llama3.1:8b / devils-advocate=**haiku** / scribe=sonnet

주의: 위 §13.3 JSON 예시에는 `developer` 와 `scribe` 항목이 생략되어 있지만 실제 기본값은 포함된다. 예시는 차이 나는 항목만 보이기 위한 축약.

파일 권한 권장: `chmod 600`. 시크릿은 포함되지 않지만 사용자 설정 노출 방지.

## 14. Interactive Configuration — `/ensembra:config` (Unified Picker)

**모든 설정은 플래그나 수동 JSON 편집 없이 `/ensembra:config` 의 선택형 대화로만 구성된다.** Claude Code 의 `/config` 와 유사한 UX 를 목표로 한다. 수동 편집은 금지가 아니라 **비권장** — 항상 `/ensembra:config` 가 1차 진입점이다.

### 14.1 메인 메뉴

```
/ensembra:config

Ensembra 설정
──────────────
1) Performers         — 역할별 모델 및 활성화 (scribe 포함 7명)
2) Presets            — 프리셋별 Phase 구성·감사자·Deep Scan·Phase 4 문서
3) Rounds             — 합의 임계값 (기본 70/40), Rework 상한 (기본 2)
4) Deep Scan          — 체크리스트 10항목 (강제 6 + 선택 4)
5) Transports         — Ollama endpoint, Gemini API 키 설정
6) Timeouts           — transport 별 타임아웃
7) Logging            — 마스킹 키, 로그 레벨
8) Reports            — Phase 4 문서별 on/off, 경로, 언어, 템플릿
9) Reuse-First Policy — 4개 장치 Quick Select 5프리셋 또는 Custom
10) Reset             — 모든 값을 기본값으로 복원
0) 저장 후 종료
```

사용자는 숫자 입력으로 서브메뉴 진입. 각 서브메뉴도 동일 패턴의 numbered menu 로 구성. 자유입력은 **엔드포인트 URL·API 키 등 필연적 텍스트 값**에만 허용.

### 14.2 서브메뉴 상세

#### (1) Performers
- 역할 리스트 표시 → 역할 선택 → 그 역할에 대해:
  - a) 모델 변경 (live 조회 기반 picker, §14.4)
  - b) 활성화/비활성화 토글
  - c) 이 역할에 Peer Signature 부여 권한 toggle
  - 0) 상위 메뉴

#### (2) Presets
- 프리셋 리스트 (`feature`/`bugfix`/`refactor`/`security-audit`/`source-analysis`) → 프리셋 선택 → :
  - a) 참여 Performer 집합 편집 (체크박스 형태, 숫자 입력으로 토글)
  - b) 라운드 구성 (R1→Syn / R1→R2→Syn / R1→R2→R3→Syn)
  - c) Phase 2 Execute on/off
  - d) Phase 3 Audit on/off + 감사 Performer 선택
  - e) Deep Scan 체크리스트 선택 (§14.2 (4) 에서 선택한 항목 중 부분집합)
  - 0) 상위 메뉴

#### (3) Rounds
- a) R2 자동 트리거 파일 개수 임계값 (기본 5) — 숫자 입력
- b) R2 자동 트리거 합의율 임계값 (기본 70%) — 숫자 입력
- c) Synthesis 확정 합의율 (기본 80%) — 숫자 입력
- d) 중단 합의율 (기본 50%) — 숫자 입력
- e) Rework 상한 (기본 2) — 숫자 입력
- 0) 상위 메뉴

#### (4) Deep Scan
`CONTRACT.md` §12 의 10항목 체크리스트. 강제 6개 + 선택 4개:
```
강제 (끌 수 없음):
  [x] 1) 구조 파악
  [x] 2) 키워드 역추적
  [x] 3) 호출 그래프
  [x] 4) 데이터 흐름
  [x] 9) 공통 모듈 인벤토리       ← Reuse-First 의존
  [x] 10) 프로젝트 문서 인벤토리   ← 문서 담당 의존

선택 (글로벌 기본값):
  [x] 5) 테스트 맵
  [x] 6) git 히스토리
  [x] 7) 의존성
  [x] 8) 설정

번호 입력 시 5~8 토글. 1~4, 9, 10 은 토글 시도 시 정책 안내만 출력.
0) 저장 후 상위 메뉴
```

#### (5) Transports
- a) Ollama endpoint (기본 `http://localhost:11434`) — 자유입력 텍스트
- b) Ollama health check 수행 → 성공/실패 배지 표시
- c) Gemini API 키 설정 → 가이드 표시 + 자유입력 → `~/.config/ensembra/env` 에 저장, `chmod 600`
- d) Gemini health check 수행
- e) Claude 본체 폴백 모델 선택 (picker)
- 0) 상위 메뉴

#### (6) Timeouts
- a) Ollama 타임아웃 (기본 120)
- b) Gemini 타임아웃 (기본 60)
- c) Claude 서브에이전트 타임아웃 (기본 300)
- d) Phase 0 Deep Scan 총 타임아웃 (기본 180)
- 0) 상위 메뉴

#### (7) Logging
- a) 로그 레벨 (quiet / normal / verbose) — 선택형
- b) 추가 마스킹 키 등록 — 자유입력 (쉼표 구분)
- c) 폴백 발생 시 배지 출력 on/off
- 0) 상위 메뉴

### 14.3 저장 규약
- 메인 메뉴 `0) 저장 후 종료` 시 전체 설정을 `~/.config/ensembra/config.json` 에 **원자적 쓰기** (tmp → rename)
- 스키마 버전 필드 `"version": 1` 포함 → 마이그레이션 대비
- 파일 권한 `chmod 600`
- `ESC` 로 저장 없이 탈출 시 변경분 폐기

### 14.4 Live 모델 조회 (Performer 모델 picker)
1. Ollama: `curl -s http://localhost:11434/api/tags` → `.models[].name`
2. Gemini: `curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"` → `.models[]` (`supportedGenerationMethods` 에 `generateContent` 포함 필터)
3. Claude: 정적 목록 (`opus`, `sonnet`, `haiku` + 현재 세션 최신 모델 ID)
4. numbered menu 로 출력, 사용자가 숫자 입력 → `{transport, model}` 확정

### 14.5 가용성 예외
- Ollama unreachable → 섹션 생략 + 경고 배지 `⚠ Ollama unreachable`
- `GEMINI_API_KEY` 없음 → `(5) Transports → c` 로 유도하는 안내
- 외부 transport 전부 실패 → Claude 목록만 표시, 최종 폴백 경고

### 14.x Reports 서브메뉴 (메인 (8))
- a) Task Report on/off (**off 불가, 표시만**)
- b) Design Doc on/off (기본 on, feature·refactor 에만 적용)
- c) Request Spec on/off (기본 on, feature·refactor 에만 적용)
- d) Daily Report 템플릿 (표준 / 간략)
- e) Weekly Report 템플릿 (표준 / 상세)
- f) 보고서 출력 경로 (기본 `docs/reports/`, `docs/design/`, `docs/requests/`, `docs/transfer/`)
- g) 보고서 언어 (원 요청 언어 자동 / 한국어 고정 / English 고정)
- h) 인수인계서 기본 scope (전체 / 대화형 묻기)
- i) 인수인계서 템플릿 (표준 10섹션 / 간략 6섹션)
- j) 인수인계서 devils-advocate 섹션 포함 (기본 on, 권장 유지)

### 14.y Reuse-First Policy 서브메뉴 (메인 (9))
```
Ensembra > Reuse-First Policy
────────────────────────────────────
현재 상태: Maximum (4/4)
  [x] 1) Deep Scan Inventory
  [x] 2) Schema Field (reuse_analysis)
  [x] 3) Auto Disagree
  [x] 4) Synthesis Report

Quick Select:
  1) Maximum    — 1+2+3+4 (기본, 추천)
  2) Strong     — 1+2+4
  3) Balanced   — 1+2
  4) Advisory   — 1 only
  5) Off        — 전부 off (비권장)
  0) Custom (체크박스 편집, cascade 자동 처리)
  9) 저장 후 상위 메뉴
```

Custom 편집 시 cascade 규칙은 §16.3 참조. Grey out 없음, 무효 상태 도달 불가.

### 14.6 구현 제약
- Claude Code 슬래시 스킬은 진정한 TUI 없음. 모든 메뉴는 **대화 기반 picker** (스킬 프롬프트가 메뉴 문자열 출력 → 다음 사용자 메시지를 숫자로 파싱 → 다음 상태로 전이).
- 상태 머신은 스킬 본문에 명시적으로 기술. 세션 간 복구는 없음 (사용자가 중단 시 처음부터).
- 순수 Markdown + Bash 툴. Node/Python 없음 → Q2=a 유지.

`TODO(gate2)`: `skills/ensembra-config/SKILL.md` 를 상태 머신 프롬프트로 작성. 각 서브메뉴를 독립 상태로 정의, 전이 규칙을 테이블화.

## 15. Scribe & Document Phase (Phase 4)

scribe 는 Phase 1~3 에 참여하지 않는 **기록 전용** Performer 다. Phase 4 에서만 활성화되며 Peer Signature 대상이 아니다.

### 15.1 scribe 입력
- 원 요청
- Phase 0 Context Snapshot
- Phase 1 전체 (R1/R2 출력, Peer Signature 매트릭스, Synthesis Plan, 합의율)
- Phase 2 diff (파일별)
- Phase 3 감사 Verdict·Issue 목록

### 15.2 scribe 가 생성하는 문서 5종

| 문서 | 경로 | 프리셋 |
|---|---|---|
| **Task Report** (ADR 스타일) | `docs/reports/tasks/{YYYY-MM-DD}-{slug}.md` | 모든 프리셋 (강제, 끌 수 없음) |
| **Design Doc** | `docs/design/{feature}.md` | `feature`, `refactor` (append 모드, 덮어쓰기 금지) |
| **Request Spec** | `docs/requests/{YYYY-MM-DD}-{slug}.md` | `feature`, `refactor` |
| **Daily Report** | `docs/reports/daily/{YYYY-MM-DD}.md` | 수동 호출 `/ensembra:report daily` |
| **Weekly Report** | `docs/reports/weekly/{YYYY-Www}.md` | 수동 호출 `/ensembra:report weekly` |

### 15.3 scribe 품질 보장
- **템플릿 슬롯 기반**: 자유 작문 아님. 각 섹션은 명시적 입력→슬롯 매핑
- **금지**: 창작(Phase 0~3 에 없는 정보), 의견(비평·재토론), Plan 수정
- **출력 검증**: Conductor 가 필수 섹션 누락, Plan 외 파일명 등장, 합의율 불일치 검사. 실패 시 1회 재생성. 재실패 시 rawdump 모드로 저장 + 경고

### 15.4 `transfer` 프리셋 — 인수인계서 미니 파이프라인

`/ensembra:transfer [scope]` 호출 시 전용 흐름:

1. **Wide Scan** (§12.2)
2. **R1 only** — 6 Performer 병렬 실행, 각자 담당 섹션 1개씩 작성 (토론·서명 없음)
3. **Phase 2/3 건너뜀** (읽기 전용)
4. **Phase 4 특수 모드** — scribe 가 6 섹션을 표준 템플릿으로 취합

#### 섹션 분담
| Performer | 섹션 |
|---|---|
| planner | 프로젝트 목적·목표, 마일스톤, 열린 요구사항 |
| architect | 아키텍처 개요, 모듈 경계, 설계 결정 이력 |
| developer | 빌드·실행·테스트·개발환경, 스타일, 기술 부채 |
| security | 시크릿 경로(값 아님), 외부 계정 소유권, 보안 이슈 |
| qa | 테스트 커버리지, 신뢰/불안정 영역, 플래키 테스트 |
| devils-advocate | ⚠ 주의할 함정, 과거 시행착오, 반직관 지점, "고치지 마라" 영역 |

#### 표준 템플릿 (10 섹션)
0. 요약 (scribe, 3~5줄) / 1. 프로젝트 목적·목표 / 2. 아키텍처 / 3. 빌드·실행·개발환경 / 4. 보안·시크릿·계정 / 5. 테스트 현황 / 6. ⚠ 주의할 함정 / 7. 최근 변경 이력 / 8. 열린 이슈·다음 단계 / 9. 참고 문서 / 10. 부록: 의존성 스냅샷

#### scope 파라미터
- 인자 없음 → 프로젝트 전체 (`docs/transfer/{YYYY-MM-DD}-project.md`)
- 경로 → 해당 디렉토리 (`docs/transfer/{YYYY-MM-DD}-{path-slug}.md`)
- 자연어 → planner 가 파일 집합 추론 (`docs/transfer/{YYYY-MM-DD}-{slug}.md`)

#### 생성 정책
- **자동 생성 없음**. 사용자 명시 호출만
- 초기 프로젝트에선 devils-advocate 섹션이 빈약할 수 있음. 이 경우 "해당 없음, Task Report 누적 후 풍부해짐" 으로 마크
- 시크릿은 **경로만** 기록하고 내용 절대 포함 금지 (§SECURITY.md 마스킹 규칙 적용)

---

## 16. Reuse-First Policy (교차 원칙)

유지보수 우선을 위한 재사용 강제 정책. 전담 Performer 대신 **교차 원칙** 으로 전 Performer 에게 적용.

### 16.1 4개 장치

| # | 장치 | 어디서 | 의존 |
|---|---|---|---|
| 1 | **Deep Scan Inventory** | Phase 0 항목 9번 | 없음 |
| 2 | **Schema Field** (`reuse_analysis` 필수) | R1 에이전트 출력 | 1 권장 |
| 3 | **Auto Disagree** | R2 Peer Signature | **장치 2 필수** |
| 4 | **Synthesis Report** | Synthesis 최상단 고정 섹션 | **장치 2 필수** |

### 16.2 Quick Select 프리셋

| 프리셋 | 구성 | 강도 |
|---|---|---|
| **Maximum** (기본) | 1+2+3+4 | 강 |
| **Strong** | 1+2+4 | 중강 |
| **Balanced** | 1+2 | 중 |
| **Advisory** | 1 only | 약 |
| **Off** | 전부 off | 없음 (비권장) |

**기본값**: Maximum.

### 16.3 Custom 편집 — Cascade 규칙 (함정 방지)

사용자가 `/ensembra:config → Reuse-First Policy → Custom` 에서 개별 토글할 때, 다음 cascade 규칙이 자동 적용되어 **무효 상태는 존재할 수 없다**:

- **장치 2 를 off** → 장치 3, 4 자동 off ("의존성으로 함께 껐습니다" 안내)
- **장치 3 또는 4 를 on** (장치 2 가 off 상태에서) → 장치 2 자동 on ("의존성으로 함께 켰습니다" 안내)
- Undo 1단계 지원 (`u` 키)
- 저장 전 확인 화면 1단계 (변경 요약 + y/n)
- `0` 키로 취소 (변경 폐기)

유효 조합은 2⁴=16 중 **10가지만** 도달 가능. Grey out 없음, 모든 항목 언제든 토글 가능, cascade 가 알아서 처리.

### 16.4 Synthesis 고정 리포트 (장치 4)

Synthesis 최상단에 항상 배치 (해당 없으면 "없음" 표시):

```
## ⚠ 재사용 기회 평가
| 항목 | 발견 | 선택 | 정당화 설득력 |
|---|---|---|---|
| {path}#{symbol} | N/M Performer 언급 | reuse/extend/new | OK/부실 |
권장 조치: ...
```

### 16.5 조정 경로
`/ensembra:config → Reuse-First Policy` (Quick Select 5개 + Custom 편집)

---

## 17. Plan Tier Profiles

Ensembra 는 Claude 플랜(Pro / Max) 에 따라 파이프라인 실행 강도를 조절하는 **Plan Tier** 오버레이를 갖는다. Tier 는 preset 위에 겹쳐 적용되며, preset 자체는 수정하지 않는다.

### 17.1 Tier 값

- `pro` (기본) — Claude Pro 사용자. 5시간 롤링 메시지 한도를 고려해 토큰·호출 횟수를 최소화
- `max` — Claude Max 사용자. preset 원본 동작을 그대로 수행 (기존 Ensembra 동작과 동일)

### 17.2 우선순위

1. `/ensembra:run --tier=pro|max` 인자 (본 실행 한정)
2. `~/.claude/config/ensembra/config.json` 의 `plan_tier` 필드
3. 기본값 `"pro"`

### 17.3 프로파일 규칙

| 축 | pro | max |
|---|---|---|
| Deep Scan forced | 1·2·9 전문, 3·4·10 압축 | 전부 전문 |
| Deep Scan optional | 전부 off (preset 지시 무시) | preset 지시 따름 |
| Context Snapshot | 심볼·경로 인벤토리만 | 본문 발췌 포함 |
| Phase 1 R2 실행 | R1 합의율 ≥85% 면 스킵 | preset `rounds` 그대로 |
| Phase 1 R2 prior_outputs | diff 요약 (400자/Performer) | 전체 출력 |
| Phase 3 Audit 감사자 | preset `auditors` 첫 1명 | 전원 |
| Phase 4 scribe 입력 | Phase 요약본 (500자/Phase) | 원본 기록 |

### 17.4 금지선 (tier 로 토글 불가)

- `feature` preset 의 `security` / `qa` Performer 참여
- `rounds.*_consensus` 임계값
- `reuse_first.device_*` 토글
- Deep Scan 강제 6항목의 "미수행" (압축·범위 축소는 허용, 완전 skip 은 금지 — §4 참조)

### 17.5 Auto-Escalation

pro tier 실행 중 R1 합의율이 40~70% 구간에 진입하면 Conductor 는 사용자에게 1회 한정 max 승격을 제안한다. 승격 수락 시 해당 실행에 한해 R2 를 max 방식(전체 출력 전달)으로 수행한다. Auto-Escalation 은 Audit·scribe 단계에는 적용되지 않는다 (비용 급증 방지).

### 17.6 조정 경로

- 본 실행 한정: `/ensembra:run <preset> --tier=max <요청>`
- 영구 저장: `/ensembra:config → Plan Tier`

---

## 18. Gate2 이월 항목

- `TODO(gate2)`: 위 JSON Schema 를 실제 파일(`schemas/*.json`)로 분리하고 런타임 검증기 연결.
- `TODO(gate2)`: 라운드 타임아웃·재시도 정책 숫자 확정.
- `TODO(gate2)`: `max_rounds` 기본값 및 사용자 오버라이드 방식 결정.
- `TODO(gate2)`: Performer 를 Claude Code 서브에이전트로 바인딩하는 방식 결정 (agent name 매핑 vs 동적 프롬프트 주입).
- `TODO(gate2)`: synthesis 단계를 전용 Performer 로 둘지 Conductor 내장 로직으로 둘지 결정.
- `TODO(gate2)`: Performer 레지스트리 파일 포맷 확정 (`ensembra.performers.json` vs YAML frontmatter vs agents/*.md 확장).
- `TODO(gate2)`: Gemini API 엔드포인트 스펙 확인 및 `generateContent` vs `streamGenerateContent` 선택.
- `TODO(gate2)`: Ollama·Gemini Performer 가 `===ENSEMBRA-OUTPUT===` 블록을 누락할 때 1회 재시도 정책.
- `TODO(gate2)`: Gemini 무료 티어 쿼터 소진 시 fallback 경로 (Ollama 로 대체? 에러 반환?).
- `TODO(gate2)`: Deep Scan Context Snapshot 의 토큰 예산 계산식 (모델별 context window 에 맞춘 압축 전략).
- `TODO(gate2)`: Health Check 캐싱 정책 (매 Phase 0 마다 조회 vs TTL 기반).
- `TODO(gate2)`: `/ensembra:config` 의 대화 기반 picker 가 사용자 숫자 입력을 안정적으로 해석하는 프롬프트 설계.
- `TODO(gate2)`: Config 파일 마이그레이션 (스키마 변경 시 v1→v2 upgrade).
- `TODO(gate2)`: scribe 출력 검증기 (템플릿 슬롯 매핑 + 창작 방지 + 합의율 일치 검사).
- `TODO(gate2)`: Task Report slug 생성 로직 (planner 의 요청 해석 결과에서 3~5단어 추출).
- `TODO(gate2)`: Design Doc append 모드 (기존 파일 충돌 없이 섹션 추가).
- `TODO(gate2)`: Reuse-First Custom picker 상태 머신 + Undo 1단계 구현.
- `TODO(gate2)`: Phase 3 Audit 감사자 verdict 집계 로직 (한 명이라도 fail → Rework).
- `TODO(gate2)`: Wide Scan 성능 최적화 (범위 축소 자동 제안, 진행률 표시).
- `TODO(gate2)`: Deep Scan 확장 후보 11~16 (lint/typecheck/runtime log/TODO/benchmark/API spec) 언어 확정 후 추가 검토.
- `TODO(gate2)`: devils-advocate 섹션 품질 개선 (git log 주석·롤백 커밋·과거 Task Report 학습).
- `TODO(gate2)`: **Plan Tier × Model 축 확장 검토** — §17 Plan Tier 오버레이에 Claude Performer 모델 다운그레이드 축 추가 여부. 선행 조건: pro/max 실측 3~5회 샘플로 실제 토큰 소비·합의율 차이 수집. 금지선: `security`/`qa`/`planner` 는 tier 무관 원본 모델 유지. 사용자가 `performerConfig.model` 을 명시 지정한 경우 tier override 는 덮어쓰지 않음.
- `TODO(gate2)`: `/ensembra:report daily|weekly` 스킬 구현 + Task Report 집계 로직.
- `TODO(gate2)`: `/ensembra:transfer` 스킬 구현 + scope 자연어 해석 (planner 연계).
