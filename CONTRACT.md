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

### 5.1 `_error.code` 표준 분기 (v0.12.0+)

Performer 실패 사유는 아래 코드 중 하나로 정규화한다. Conductor 는 코드별로 다른 회복 전략을 적용한다.

| 코드 | 의미 | Conductor 동작 |
|---|---|---|
| `timeout` | Performer 실행이 `timeout_sec` 초과 | 해당 Performer 만 error, 라운드 계속 |
| `format` | 출력 파싱 실패 (`===ENSEMBRA-OUTPUT===` 블록 미도달, JSON invalid) | 1회 재시도, 실패 시 error |
| `schema` | 출력 스키마 위반 (필수 필드 누락 등) | 1회 재시도, 실패 시 error |
| `transport-chain-exhausted` | §8.8 3단 체인 전부 실패 | 해당 Performer 만 error, 라운드 계속 |
| **`token_limit`** | **입력·출력이 transport 의 context window(§8.10) 초과로 잘림** | **Conductor 즉시 라운드 중단 판정. `artifact_offload.enabled=true` 면 자동 재시도(요약 전달). false 면 사용자 프롬프트로 escalate.** |
| `rate_limit` | 외부 LLM HTTP 429 (quota/throttle) | `fallback.retry_delay_sec` 대기 후 체인 다음 단계로 폴백 |
| `unauthorized` | 인증 실패 (401) | 체인 다음 단계로 폴백, 키 문제는 사용자에게 배지 경고 |

**`token_limit` 분기 신설 배경 (v0.12.0+)**: 이전 구현은 응답 절단을 `format` 으로 흡수해 silent fail 우려 있었음. final-auditor 같은 opus 서브에이전트에서 200K 초과 입력을 받으면 응답이 잘려 `===END===` 미도달 → Conductor 가 "포맷 오류" 로 오인. 전용 코드 분기로 **원인 가시성 확보 + `artifact_offload` 기반 자동 요약 재전송** 경로를 제공한다.

### 5.2 `token_limit` 탐지 휴리스틱

Conductor 는 다음 신호를 `token_limit` 로 판정:

1. 응답이 `===ENSEMBRA-OUTPUT===` 로 시작했으나 `===END===` 미도달 (절단 의심)
2. 입력 바이트 크기가 transport 의 `max_input_chars` (§8.11) 초과
3. 외부 LLM 응답 본문에 `"context length"`, `"token limit"`, `"too long"` 등 오류 메시지 포함
4. 서브에이전트 응답 길이가 0 + 별도 에러 없음 (컨텍스트 초과로 LLM 이 조용히 실패한 경우)

2번은 **사전 탐지** (호출 전 차단) 가능. 1·3·4 는 **사후 탐지** (응답 수신 후 판정).

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

- `transport: "mcp"` 일 때는 `mcp_server_name` 필수 (예: `"gemini-ensembra"`). `model` 은 MCP tool 인자로 전달.
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
1. ✅ architect Performer 를 **MCP server** (`mcp-servers/gemini-ensembra/server.py`) 로 이전
2. ✅ `sensitive: true` 값은 MCP server config 의 `env.GEMINI_API_KEY` 로만 접근 (skill/agent content 미노출)
3. ✅ skill/agent content 는 MCP tool 호출 결과만 참조, 키 직접 참조 없음

**v0.7.0 architect Transport 3단 폴백 체인**:

```
1. MCP(gemini-ensembra) — GEMINI_API_KEY 설정 + MCP server 응답 시
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
  "gemini-ensembra": {
    "command": "python3",
    "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/gemini-ensembra/server.py"],
    "env": {
      "GEMINI_API_KEY": "${user_config.gemini_api_key}"
    }
  }
}
```
`${CLAUDE_PLUGIN_ROOT}` 는 Claude Code 가 플러그인 설치 경로로 자동 치환한다. 사용자가 `settings.local.json` 을 수동 편집할 필요 없음.

**`sensitive: true` 불변식 유지**: `gemini_api_key` 는 OS 키체인에 저장, MCP server config 의 `${user_config.gemini_api_key}` 치환으로만 프로세스 env 에 전달. skill/agent content, 시스템 프롬프트, 세션 로그에 키가 노출되지 않음.

**gemini Transport (레거시)**: v0.6.0 에서 폐지된 `transport: "gemini"` 은 하위 호환을 위해 스키마에 남되 **신규 사용 금지**. `transport: "mcp"` + `mcp_server_name: "gemini-ensembra"` 를 사용하라.

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
  [Gemini  ] architect  → gemini-2.5-flash  @ MCP(gemini-ensembra)
  [Ollama  ] security   → qwen2.5:14b       @ localhost:11434
  [Ollama  ] qa         → qwen2.5:14b       @ localhost:11434
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
▶ [Gemini  ] architect — 호출 시작 (gemini-2.5-flash @ MCP(gemini-ensembra))
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

#### 8.6.5 Proof-of-Invocation 강화 (v0.9.1+)

사용자가 "외부 LLM 이 정말로 호출되었는가" 를 **여러 시점에서 반복적으로 확인**할 수 있도록 4종 증거 메커니즘을 강제한다. v0.8.1 Live Indicators 3 레이어 위에 얹어지는 **추가 보증 레이어** 로, `logging.proof_of_invocation: true` (기본) 일 때 활성화된다.

**A. 응답 증명 배너 (Response Proof Banner)**

각 Performer 응답 본문 **최상단**에 메타데이터 블록 강제 삽입. Conductor 는 Performer 결과를 수신한 직후, 본문을 렌더링하기 전에 이 블록을 prepend 한다.

외부 LLM 성공 시:
```
┌─ 🌐 EXTERNAL LLM VERIFIED ─────────────────┐
│  transport:  MCP(gemini-ensembra)          │
│  tool:       architect_deliberate          │
│  model:      gemini-2.5-flash              │
│  duration:   432ms                         │
│  resp_size:  1.2KB                         │
│  endpoint:   generativelanguage.googleapis │
└────────────────────────────────────────────┘

(이하 실제 Performer 응답 본문)
```

Ollama 성공 시:
```
┌─ 🌐 EXTERNAL LLM VERIFIED ─────────────────┐
│  transport:  Ollama                        │
│  model:      qwen2.5:14b                   │
│  duration:   887ms                         │
│  resp_size:  1.8KB                         │
│  endpoint:   localhost:11434               │
└────────────────────────────────────────────┘
```

Claude subagent 폴백 시 (명시적 구분):
```
┌─ ⚪ CLAUDE SUBAGENT (FALLBACK) ────────────┐
│  model:      sonnet                        │
│  duration:   2341ms                        │
│  fallback_reason: MCP HTTP 429 / Ollama timeout │
└────────────────────────────────────────────┘
```

Claude 가 기본 경로인 경우 (max-plan 의 planner 등):
```
┌─ ⚪ CLAUDE SUBAGENT (PRIMARY) ─────────────┐
│  model:      sonnet                        │
│  duration:   2341ms                        │
└────────────────────────────────────────────┘
```

**B. Phase 종료 집계 강화 — 역할별 상세 증거**

§8.6.3 의 기존 집계를 확장. Phase 종료 시점에 **각 Performer 호출의 실제 Transport 를 표 형식**으로 명시:

```
📊 Phase 1 외부 LLM 사용 증거:
  ✓ architect    Gemini  gemini-2.5-flash  432ms  1.2KB  ← 실제 호출
  ✓ qa           Ollama  qwen2.5:14b       887ms  1.8KB  ← 실제 호출
  ✓ planner      Gemini  gemini-2.5-flash  289ms  0.9KB  ← 실제 호출
  ✗ security     Claude  sonnet (fallback)              ← 내부 (Gemini HTTP 429 + Ollama timeout)
  ✗ developer    Claude  sonnet (primary)               ← 내부 (max-plan 기본)
  
  외부 LLM 활용률: 3/5 (60%)
  ⓘ 폴백 사유 별도 기록 (.claude/ensembra/reports/risk/runs.jsonl)
```

기존 §8.6.3 집계는 유지하며 본 표가 **상위에 추가 노출**된다.

**C. Task Report 영구 기록 — Proof-of-Invocation 섹션**

scribe 가 생성하는 Task Report (`.claude/ensembra/reports/tasks/{YYYY-MM-DD}-{slug}.md` — v0.11.0+ 기본 경로) 맨 아래에 "외부 LLM 사용 증거" 섹션을 **강제 포함**. 사후 감사 가능한 파일 기록.

템플릿:
```markdown
## 외부 LLM 사용 증거 (Proof-of-Invocation)

실제 호출된 Transport/Model 기록. 각 행은 한 번의 Performer 호출.

| Phase | Role | Transport | Model | Duration | Size |
|-------|------|-----------|-------|----------|------|
| 1-R1 | architect | Gemini MCP | gemini-2.5-flash | 432ms | 1.2KB |
| 1-R1 | planner | Gemini MCP | gemini-2.5-flash | 289ms | 0.9KB |
| 1-R1 | qa | Ollama HTTP | qwen2.5:14b | 887ms | 1.8KB |
| 1-R1 | security | Claude | sonnet (fallback) | 2341ms | 2.0KB |
| 3 | final-auditor | Gemini MCP | gemini-2.5-pro | 1834ms | 2.1KB |
| 4 | scribe | Gemini MCP | gemini-2.5-pro | 2298ms | 3.2KB |

**요약**
- 외부 LLM 호출: 5건 (Gemini 4, Ollama 1)
- Claude subagent: 1건 (security 폴백)
- **외부 LLM 활용률: 83%** (5/6)
```

본 섹션은 `policy_relaxations` 와 무관하게 모든 프로파일에서 강제. scribe 의 system prompt 에 해당 규약이 내장되어 템플릿 누락 방지.

**D. 파이프라인 종료 배너 — 최종 증명**

파이프라인 완료 시 사용자 터미널 상단에 크게 출력:

```
╔══════════════════════════════════════════════════╗
║  🌐 외부 LLM 사용 증명 — v0.9.1 pro-plan         ║
╠══════════════════════════════════════════════════╣
║  Phase 0:  (Deep Scan, 내부 tool)                ║
║  Phase 1:  Gemini 4회  Ollama 2회  Claude 1회    ║
║  Phase 3:  Gemini 2회  Claude(opus) 0회          ║
║  Phase 4:  Gemini 1회                            ║
║  ──────────────────────────────                  ║
║  외부 LLM 호출 총: 9회                            ║
║  Claude subagent:  1회 (폴백 1건)                ║
║  외부 LLM 활용률:  9/10  (90%)                   ║
║  Claude API 토큰:  예상 ~12% 사용                 ║
╚══════════════════════════════════════════════════╝
```

`plan_tier=max`/`profile=max-plan` 인 경우 Claude 호출 비율이 자연히 높아지므로 배너 상단에 `max-plan (quality-first)` 라벨을 붙여 기대치 명시.

**보안 불변식 (4종 공통)**:
- 증명 배너·표·배너 어느 곳에도 API 키·엔드포인트 full URL·프롬프트/응답 본문 **포함 금지**
- `duration` 은 wall-clock ms, `resp_size` 는 bytes. 토큰 수·비용·사용자 식별자 금지
- Claude fallback 시 `fallback_reason` 은 1줄 요약만 (HTTP status, timeout 등). 원본 에러 메시지·스택트레이스 금지

**토글**:
- `config.json logging.proof_of_invocation: true` (기본)
- 비활성화 시 §8.6.5 의 4종 전부 억제. §8.6.1~§8.6.4 Live Indicators 는 `show_transport_badge` 로 별도 토글
- 두 설정 모두 비활성화해도 Task Report 의 기본 "## 외부 LLM 사용 증거" 섹션은 **쓰기 전용 기본값으로 유지** (사후 감사 보장). 섹션 자체를 숨기려면 `reports.task_report_proof_section: false` 명시 필요 (비권장)

### 8.10 Ollama 모델 해석 우선순위 (v0.10.0+)

Phase 1 ollama 단계 진입 직전 Conductor 는 다음 우선순위로 모델을 결정한다:

```
1. ensembra_config.transports.ollama.models.{role}   ← 역할별 override
2. ensembra_config.transports.ollama.model           ← default
3. profiles/{profile}.yaml 의 transport_routing.{role}.chain[].model  ← yaml hardcoded
```

**Special-case 보존**: yaml hardcoded model 이 명시적으로 다른 모델인 경우 (예: pro-plan 의 developer = `gpt-oss:20b`), config 의 default (2단계) 가 설정되어 있어도 **role-specific override (1단계) 가 없으면 yaml 값을 우선 존중**. 이는 의도적 설계 선택을 보호한다.

| 시나리오 | config.json | yaml | resolved |
|---|---|---|---|
| config 미설정 | `{}` | `qwen2.5:14b` | `qwen2.5:14b` (yaml) |
| default 만 설정 | `{ollama:{model:"qwen2.5-coder:14b"}}` | `qwen2.5:14b` | `qwen2.5-coder:14b` (default) |
| role override | `{ollama:{models:{architect:"qwen2.5-coder:14b"}}}` | `qwen2.5:14b` | architect → `qwen2.5-coder:14b`, 그 외 → `qwen2.5:14b` |
| Special-case (developer) | `{ollama:{model:"qwen2.5-coder:14b"}}` | `gpt-oss:20b` (developer) | `gpt-oss:20b` (yaml 우선) |
| Override + special | `{ollama:{models:{developer:"qwen2.5-coder:14b"}}}` | `gpt-oss:20b` (developer) | `qwen2.5-coder:14b` (override) |

설정·picker 는 `/ensembra:config` (5)f, 호출 부 규약은 `skills/run/SKILL.md` 의 "Ollama 모델 해석 우선순위" 섹션 참조.

#### Phase 1 Health Check 통합 (§8.9.2 확장)

Health Check 의 "Ollama: `/api/tags` 200" 검사 시, 각 Performer 의 `resolved_model` 이 응답의 `models[].name` 에 존재하는지 확인. 미설치 시:

```
[1] 자동: 같은 패밀리 14b 모델 임시 폴백
[2] 임시 폴백 후보 없음: 해당 역할 ollama 단계 스킵 → Claude 폴백
[3] 사용자 알림 (`/ensembra:config` 또는 `ollama pull` 안내)
```

`fallback.confirmation_mode == strict` 면 사용자 승인 프롬프트, 그 외에는 자동 처리 + 배지 알림.

---

### 8.9 폴백 승인 프로토콜 (v0.9.3+)

외부 LLM (MCP/Ollama) 실패 → Claude 폴백 발생 시 사용자 명시적 승인을 요구하는 프로토콜. 예상치 못한 Claude 토큰 소비 사전 차단.

#### 8.9.1 3단 승인 모드 (`fallback.confirmation_mode`)

| 모드 | 동작 | 사용 시나리오 |
|-----|------|-------------|
| `strict` | 모든 단계 폴백(MCP→Ollama, Ollama→Claude) 마다 확인 | 최대 통제 (CI/자동화 환경) |
| **`critical_only`** (기본) | **외부 체인 전부 실패 → Claude 폴백**만 확인. 외부간 폴백(MCP→Ollama)은 자동 | **일반 권장** |
| `none` | 자동 폴백 (v0.9.2 동작) | 무인 실행 필요 시 |

#### 8.9.2 사전 Health Check + Phase 배치 (`batch_by_phase: true` 기본)

Phase 1 R1 / Phase 3 Audit 시작 **직전** Transport Health Check 를 일괄 수행:

```
📡 Phase 1 R1 — 사전 Transport Health Check

외부 LLM 가용성:
  ✓ Gemini MCP       정상 (health check 200, 14/15 RPM 사용 중)
  ✗ Ollama localhost 연결 실패 (connection refused)
  ✓ Claude           항상 가용

영향 Performer:
  - qa:       Ollama → Claude sonnet 폴백 예정 (~3KB)
  - security: Ollama → Claude sonnet 폴백 예정 (~3KB)

예상 Claude 토큰 소비: ~6KB
```

사용자 프롬프트:
```
[1] 2명 모두 Claude 폴백 진행
[2] qa 만 폴백, security 스킵
[3] security 만 폴백, qa 스킵
[4] 둘 다 스킵 (⚠ 결과 불완전 가능)
[5] 중단하고 Ollama 재기동 후 다시 시도 (30초 대기)
[6] 이번 세션 동안 자동 승인
```

선택에 따라 Phase 진행. 같은 Phase 내 개별 프롬프트 반복 없음.

#### 8.9.3 개별 폴백 프롬프트 (Health Check 이후 실행 중 발생 시)

Health Check 에서 예측하지 못한 실시간 실패(예: API가 갑자기 401)에는 개별 프롬프트:

```
┌─────────────────────────────────────────────┐
│  ⚠ 외부 LLM 폴백 승인 필요                   │
│                                              │
│  Performer:  architect (Phase 1 R2)          │
│  시도 내역:                                  │
│    ✗ Gemini MCP  gemini-2.5-flash  HTTP 429 │
│    ✗ Ollama      qwen2.5:14b       timeout  │
│    ? Claude      sonnet            (예정)    │
│                                              │
│  예상 Claude 토큰: ~3KB                      │
│                                              │
│  [1] Claude sonnet 으로 폴백 진행           │
│  [2] 이 Performer 스킵 (⚠ 결과 불완전)       │
│  [3] 파이프라인 중단                         │
│  [4] {retry_delay_sec} 초 대기 후 재시도    │
│  [5] 이번 세션 동안 자동 승인                │
└─────────────────────────────────────────────┘
```

#### 8.9.4 Session Auto-Approve

사용자가 `[5] 이번 세션 동안 자동 승인` 선택 시:
- 해당 세션 한정 `fallback.session_auto_approve: true` 로 메모리 전환
- config 파일에 저장하지 **않음** (다음 세션에서 다시 물음)
- 이후 동일 유형 폴백은 자동 진행 + 배지 알림만 유지

#### 8.9.5 예측 경고 배지 (v0.9.3+)

Phase 시작 시점의 Transport 현황판(§8.6.1) 에 폴백 예측 정보 추가:

```
📡 Phase 1 R1 — Transport 계획:
  [Gemini]  architect     → gemini-2.5-flash   ⓘ rate limit 근접 (14/15 RPM)
  [Ollama]  qa            → qwen2.5:14b        ⚠ health check 실패
  [Ollama]  security      → qwen2.5:14b        ⚠ health check 실패
  
⚠ 예상 폴백: qa, security → Claude sonnet (~6KB)
```

ⓘ = 정보, ⚠ = 경고. 이 배지는 `show_transport_badge: true` 로 토글.

#### 8.9.6 보안·로깅

- 폴백 결정은 `.claude/ensembra/reports/risk/runs.jsonl` 에 append (user_choice 필드 포함)
- API 키·에러 본문·프롬프트 내용 포함 금지 (HTTP status·timeout 사유만)
- 사용자 `[3] 중단` 선택 시 pipeline.status=cancelled_by_user 로 종료

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
    {"transport": "mcp", "mcp_server_name": "gemini-ensembra", "mcp_tool_name": "developer_deliberate", "model": "gemini-2.5-pro", "timeout_sec": 90},
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

`transport: "mcp"` 단계에서 `mcp_tool_name` 이 생략되면 Conductor 는 `{role}_deliberate` 로 유추한다 (예: architect → `architect_deliberate`). 명시적으로 지정하려면 `mcp_tool_name` 을 기록한다. Ensembra 가 기본 제공하는 MCP server `gemini-ensembra` 는 v0.8.0 부터 `architect_deliberate` 와 `developer_deliberate` 2개 tool 을 노출한다.

#### 8.8.6 기존 v0.7.0 architect 체인 재해석

v0.7.0 의 architect 전용 3단 체인은 v0.8.0 에서 다음 선언과 의미가 같다:

```json
"architect": {
  "transport_chain": [
    {"transport": "mcp", "mcp_server_name": "gemini-ensembra", "mcp_tool_name": "architect_deliberate", "model": "gemini-2.5-flash"},
    {"transport": "ollama", "model": "qwen2.5:14b"},
    {"transport": "claude-subagent", "model": "sonnet"}
  ]
}
```

즉 v0.7.x 사용자의 동작은 설정 마이그레이션 없이도 그대로 유지된다. `agents/architect.md` 의 Transport 섹션은 위 선언의 의미를 그대로 서술하는 것이고, 코드 경로는 §8.8 공통 루프에 흡수되었다.

### 8.11 Transport Context Window 상한표 (v0.12.0+)

각 Transport 는 고유한 context window 를 가진다. `max tier` 의 "무제한" 선언(§17)은 **Conductor(본 세션) 관점의 비압축 선언**일 뿐, 실제 Performer 전송 시 Transport 수용량에 맞춰 Conductor 가 자동 압축·요약·파일 참조로 변환해야 한다. 본 절이 그 기준값이다.

| Transport | Model | Context Window | `max_input_chars` (안전선, 80%) |
|---|---|---|---|
| MCP (`gemini-ensembra`) | `gemini-2.5-pro` | 1,000,000 토큰 (≈ 4,000,000 chars) | 3,200,000 |
| MCP (`gemini-ensembra`) | `gemini-2.5-flash` | 1,000,000 토큰 | 3,200,000 |
| MCP (`gemini-ensembra`) | `gemini-2.5-flash-lite` | 1,000,000 토큰 | 3,200,000 |
| Ollama | `qwen2.5:14b` (기본) | 32,768 토큰 (≈ 131,072 chars) | 104,857 |
| Ollama | `qwen2.5-coder:14b` | 32,768 토큰 | 104,857 |
| Ollama | `gpt-oss:20b` | 128,000 토큰 (≈ 512,000 chars) | 409,600 |
| Ollama | 기타 (보수 가정) | 32,768 토큰 | 104,857 |
| Claude subagent | `haiku` | 200,000 토큰 (≈ 800,000 chars) | 640,000 |
| Claude subagent | `sonnet` | 200,000 토큰 | 640,000 |
| Claude subagent | `opus` | 200,000 토큰 | 640,000 |
| Claude subagent | `opus` + 1M 확장 | 1,000,000 토큰 | **세션 한정, 서브에이전트엔 전파 안 됨** |

**핵심 불변식**:

1. **Claude 서브에이전트 1M 확장은 본 세션 한정**. `agents/*.md` 의 `model: opus` 는 기본적으로 200K context 로 호출된다.
2. **Ollama context window 는 모델별 Modelfile 에 선언된 `num_ctx` 가 상한**. 본 표는 기본값 가정이며 사용자가 Modelfile 수정 시 실제 상한이 달라질 수 있다.
3. Conductor 는 Performer 호출 **직전** 입력 크기를 측정해 `max_input_chars` 초과 시 다음 중 하나 수행:
   - `artifact_offload.enabled=true` 면 자동 요약 + 파일 경로 참조 (§21)
   - 기본값(off) 면 `_error.code: "token_limit"` 으로 사전 차단 + 사용자 알림
4. 체인 폴백 시 각 단계의 `max_input_chars` 가 다르므로 **같은 입력이 MCP 에선 성공, Claude subagent 에선 실패** 가능. Conductor 는 폴백 경로 전환 시 입력 재검증 필수.
5. §17 max tier 의 "scribe 무제한" · "R2 prior_outputs 전체 전달" 선언은 본 표의 Transport 상한에 의해 **실질 제약**된다. 선언은 Conductor 의 의도이고, 실행은 Transport 수용량에 종속된다.

**배지 연동**: Conductor 는 Performer 호출 시 입력 크기 ≥ `max_input_chars × 0.8` 도달 시 배지 `⚠ Context 접근 (Performer, bytes/limit)` 출력. ≥ 1.0 도달 시 즉시 `token_limit` 분기 (§5.1).

### 8.12 max tier "무제한" 선언의 실질 정의 (v0.12.0+)

§17 의 `scribe_max_chars_per_phase: -1`, R2 `prior_outputs` 전체 전달 등 "무제한" 선언은 다음과 같이 읽어야 한다:

- **Conductor 는 의도적 압축·절단을 수행하지 않는다**
- **Performer 전송 직전, §8.11 상한 내에서 Transport 별 자동 요약·파일 참조 변환은 허용·필수**
- **본 세션 컨텍스트 유지 측면에선 제한 없음** (1M 한도 내에서 원본 유지)

즉 "무제한" 은 **Conductor 의지에 의한 압축 금지**이지 **수신 측 수용량 무시**가 아니다. 이 정의는 §17 Tier 매트릭스와 §21 Artifact Offload 의 전제다.

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
- 🧪 **qa** (`ollama` → `claude-subagent` / `qwen2.5:14b` → `sonnet`) — v0.9.0+ `llama3.1:8b` 에서 승격. security 와 모델 공유로 Ollama 메모리 효율
- 😈 **devils-advocate** (`claude-subagent` / `haiku`) — opus 계열 아니므로 유지

**감사(Phase 3) Performer — preset 전문 감사자 + 최종 감사자 1명**:
- 전문 감사자: preset 별 `audit.auditors` 지정 (예: refactor → architect+devils)
- ⚖️ **final-auditor** (`claude-subagent` / `opus`, Phase 3 전용) — v0.8.0 신설. **모든 preset 의 audit 체인 마지막에 자동 배치**. Phase 1 토론·Phase 4 문서화 불참. 만장일치 판정자 (§11.3)

**문서화(Phase 4) Performer — 1명**:
- ✍️ **scribe** (`claude-subagent` / `sonnet`, Phase 4 전용)

**Debate/Audit 분리 원칙 (v0.8.0 불변식, v0.9.0 프로파일 기반 완화)**:
- 토론 Performer 전체는 opus 사용 금지 (프로파일 무관 유지).
- opus 는 Phase 3 `final-auditor` 1명에만 배치. 토론·문서화 참여 금지 (프로파일 무관 유지).
- **v0.9.0+ pro-plan 프로파일 완화**: `profiles/pro-plan.yaml` 의 `policy_relaxations.final_auditor_opus_optional: true` 설정 시 final-auditor 를 `sonnet` 또는 `gemini-2.5-pro` 로 실행 가능. 이 완화는 프로파일 YAML 에서만 토글 가능하며 개별 config 편집으로는 우회 불가 (명시적 프로파일 결정 필수).
- `max-plan` 프로파일은 원래 opus 불변식 유지.
- 완화 근거: Claude Pro 플랜 사용자의 5시간 토큰 한도 보호. opus 단일 호출 비용이 전체 파이프라인의 30~40% 를 차지 → pro-plan 에서는 sonnet 또는 Gemini pro 로 대체해 약 80% 비용 절감.

**Performer 외부 이관 금지선 (v0.8.0, v0.9.0 프로파일 기반 완화)**:
- `planner` 외부 이관 금지 (v0.8.0 원칙, max-plan 유지)
- `scribe` 외부 이관 금지 (v0.8.0 원칙, max-plan 유지)
- **v0.9.0+ pro-plan 프로파일 완화**: 해당 프로파일에서 `policy_relaxations.planner_external_allowed`·`scribe_external_allowed` true 설정 시 외부 이관 허용. 폴백 경로는 Claude sonnet 유지 (가용성 보장).

### 11.2 프리셋 매트릭스

v0.8.0+ 기준 (v0.9.0+ `ops`/`ops-safe` 추가). Phase 3 Audit 의 **final-auditor** 는 파일 수정이 발생하는 preset(`feature`/`bugfix`/`refactor`/`ops`/`ops-safe`) 에 자동 배치된다. 읽기 전용 preset(`security-audit`/`source-analysis`/`transfer`) 은 audit 자체가 off 이므로 해당 없음.

| Preset | Phase 0 | Performer | Rounds | Phase 2 | Phase 3 Audit (전문 → final-auditor) | Phase 4 |
|---|---|---|---|---|---|---|
| `feature` | Deep Scan | 전원 6 | R1→R2→Syn | on | architect+developer+security+qa+devils+**final-auditor** | Task+Design+Request |
| `ops` (v0.9.0+) | Deep Scan 축약 (3항목) | 3 (planner+qa+security) | R1→Syn | on | security+**final-auditor** | Task |
| `ops-safe` (v0.9.0+) | Deep Scan (5항목) | 5 (planner+developer+qa+security+devils) | R1→R2→Syn | on | qa+security+devils+**final-auditor** | Task+ChangeImpact |
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
1. 같은 transport 내 다른 모델로 폴백 가능하면 폴백 (예: developer opt-in 체인에서 `gemini-2.5-pro` 실패 → `gpt-oss:20b` 로)
2. 그것도 불가능하면 **Claude Code 본체 모델로 폴백** (transport=claude-subagent)
3. 폴백 발생은 Conductor 출력 상단에 배지로 고지 (`⚠ architect: gemini-2.5-flash → claude-sonnet (fallback)`)

### 13.3 Config 파일 스키마 (`~/.config/ensembra/config.json`)

```json
{
  "performers": {
    "planner":         {"transport": "claude-subagent", "model": "opus"},
    "architect":       {"transport": "gemini",          "model": "gemini-2.5-flash"},
    "security":        {"transport": "ollama",          "model": "qwen2.5:14b"},
    "qa":              {"transport": "ollama",          "model": "qwen2.5:14b"},
    "devils-advocate": {"transport": "claude-subagent", "model": "haiku"}
  },
  "fallback": {
    "transport": "claude-subagent",
    "model": "sonnet"
  }
}
```

**기본 모델표** (Q1 확정):
- planner=opus / architect=gemini-2.5-flash / developer=sonnet / security=qwen2.5:14b / qa=qwen2.5:14b (v0.9.0+) / devils-advocate=**haiku** / scribe=sonnet

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
- 프리셋 리스트 (`feature`/`bugfix`/`refactor`/`ops`/`ops-safe`/`security-audit`/`source-analysis`) → 프리셋 선택 → :
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
- f) 보고서 출력 경로 (v0.11.0+ 기본 `.claude/ensembra/reports/`, `.claude/ensembra/design/`, `.claude/ensembra/requests/`, `.claude/ensembra/transfer/` — 플러그인 격리 정책)
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

**v0.11.0+**: 모든 산출물은 대상 프로젝트의 **`.claude/ensembra/`** 하위에 저장 (플러그인 격리 정책). 프로젝트 자체 `docs/` 와 분리되어 git 추적·문서 오염 없이 로컬 기록 가능. 경로는 `reports.path_*` 필드로 개별 오버라이드 가능.

| 문서 | 기본 경로 | 프리셋 |
|---|---|---|
| **Task Report** (ADR 스타일) | `.claude/ensembra/reports/tasks/{YYYY-MM-DD}-{slug}.md` | 모든 프리셋 (강제, 끌 수 없음) |
| **Design Doc** | `.claude/ensembra/design/{feature}.md` | `feature`, `refactor` (append 모드, 덮어쓰기 금지) |
| **Request Spec** | `.claude/ensembra/requests/{YYYY-MM-DD}-{slug}.md` | `feature`, `refactor` |
| **Daily Report** | `.claude/ensembra/reports/daily/{YYYY-MM-DD}.md` | 수동 호출 `/ensembra:report daily` |
| **Weekly Report** | `.claude/ensembra/reports/weekly/{YYYY-Www}.md` | 수동 호출 `/ensembra:report weekly` |

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

#### scope 파라미터 (v0.11.0+ 기본 경로)
- 인자 없음 → 프로젝트 전체 (`.claude/ensembra/transfer/{YYYY-MM-DD}-project.md`)
- 경로 → 해당 디렉토리 (`.claude/ensembra/transfer/{YYYY-MM-DD}-{path-slug}.md`)
- 자연어 → planner 가 파일 집합 추론 (`.claude/ensembra/transfer/{YYYY-MM-DD}-{slug}.md`)

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

## 18.5 MCP Server 통합 구조 (v0.9.0+)

v0.9.0 에서 모든 Gemini 경유 호출은 **단일 MCP server** (`gemini-ensembra`) 로 통합되어 9개의 역할별 tool 을 제공한다.

### 18.5.1 설계 근거

- v0.7.0 에서 `gemini-ensembra` 도입 시 tool 2개 (`architect_deliberate`, `developer_deliberate`) 만 있었다
- v0.9.0 프로파일 체계에서 전 Performer 외부 이관 경로가 필요해지자 **역할별 server 8개 등록** 안이 나왔으나, API 키 관리·설치 복잡도를 고려해 **단일 server + 역할별 tool** 구조로 통합 결정
- server 이름은 역사적 유산 (`gemini-ensembra`). 실제 담당 범위는 Ensembra 전체 Gemini 경로

### 18.5.2 Tool 9종

| Tool | 기본 모델 | 사용처 |
|------|---------|------|
| `architect_deliberate`     | gemini-2.5-flash | Phase 1 architect, Phase 3 architect audit |
| `planner_deliberate`       | gemini-2.5-flash | Phase 1 planner (pro-plan 한정) |
| `developer_deliberate`     | gemini-2.5-pro   | Phase 1 developer (pro-plan 기본값) |
| `security_deliberate`      | gemini-2.5-flash | Phase 1 security, Phase 3 security audit |
| `qa_deliberate`            | gemini-2.5-flash | Phase 1 qa, Phase 3 qa audit |
| `devils_deliberate`        | gemini-2.5-flash | Phase 1 devils-advocate, Phase 3 devils audit |
| `scribe_deliberate`        | gemini-2.5-pro   | Phase 4 scribe (pro-plan 한정) |
| `final_auditor_deliberate` | gemini-2.5-pro   | Phase 3 final-auditor (pro-plan 한정) |
| `triage_request`           | gemini-2.5-flash | Stage A 요청 Triage (프로파일 무관) |

### 18.5.3 공유 불변식

- API 키 조회 경로 1곳 (`PLUGIN_SECRET_PATH`): 모든 tool 이 동일한 OS 키체인 조회 사용
- `sensitive: true` 불변식: tool 전부에 공통 적용. 응답 본문에 키·토큰 포함 금지
- Rate limit 보호: 같은 분 내 동일 tool 호출은 순차 직렬화 + 지수 백오프 (§8.7)
- `SERVER_VERSION` 단일 관리 (server.py 상단 상수)

---

## 19. Risk Routing (v0.9.0+)

요청 텍스트와 Phase 0 Deep Scan 결과를 2단계로 분석해 preset·profile 을 자동 결정하는 체계. **v0.11.0+ 본 섹션이 정본**. `skills/run/SKILL.md` 는 런타임 진입 요약만 보유.

### 19.1 설계 원칙

1. **사이트 분류 없이 작동**: 모든 사이트를 "중요"로 간주. 위험은 요청 내용과 코드 컨텍스트에서 파악.
2. **2단계 판정**: Stage A (Gemini flash 텍스트 분류) + Stage B (Deep Scan 컨텍스트 재평가). 두 단계 점수 변동으로 업그레이드 판단.
3. **안전 기본값**: 불확실하면 더 무거운 경로 선택. 자동화의 default 는 안전.
4. **Kill Switch 별도 레이어**: 점수 누적으로 잡히지 않는 "한 방에 위험" 케이스를 잡는 안전망. `kill_switch: strict` 기본.
5. **프로젝트 고유 키워드 발견**: 초기엔 범용 키워드로 시작, `.claude/ensembra/reports/risk/runs.jsonl` 로그로 프로젝트 고유 용어 학습.

### 19.2 우선순위

사용자 명시 > Stage A 추천 > 프로파일 기본값

- `/ensembra:run bugfix --profile=max-plan <요청>` → Risk Routing 우회 (명시 경로 고정)
- `/ensembra:run <요청>` (preset 생략) → Stage A 가 preset·profile 자동 결정
- `risk_routing.enabled: false` → 자동 라우팅 비활성, 사용자 명시 필수

### 19.3 금지선 (v0.9.0+ 불변식, v0.12.1+ pro-plan lock 추가)

- Kill Switch 치명 신호 감지 시 `kill_switch: off` 설정이 있어도 **배지 알림은 필수** (의미 없는 off 금지)
- `log_risk_decisions` 가 false 여도 Kill Switch 발동 기록은 강제 보존 (감사 추적)
- Stage A Gemini flash 호출 실패 시 Claude Code 본체의 간이 키워드 매칭으로 폴백 (라우팅 실패 금지)
- Stage B 재평가에서 초기 점수 대비 감소(-값) 라도 자동 경로 다운그레이드 금지 (보수적 편향 유지)
- **v0.12.1+ pro-plan 자동 승격 금지선**: 사용자 config 의 `profile: "pro-plan"` 은 **명시적 토큰 절감 의사표시**이며, 어떤 자동 경로(Stage A 추천 / Stage B `auto_upgrade_threshold` / Auto-Escalation)도 이를 `max-plan` 으로 승격시킬 수 없다. max-plan 진입은 오직 다음 3가지 경로로만 가능:
  1. 사용자가 `/ensembra:run <preset> --profile=max-plan <요청>` 명시
  2. 사용자가 `/ensembra:config → Profile → max-plan` 으로 영구 변경
  3. Kill Switch 치명 신호 발동 + 사용자 **명시 승인 프롬프트 y** (승인 없으면 중단, 자동 진행 금지)
- 이 불변식은 `risk_routing.mode` (`always_ask`/`staged`/`aggressive`) 설정과 무관하게 강제된다. 즉 `aggressive` 모드라도 pro-plan 에서 max-plan 으로 자동 전환은 불가.

### 19.4 로깅 스키마

`.claude/ensembra/reports/risk/runs.jsonl` — append-only, 한 실행당 한 줄.

```json
{
  "ts": "ISO8601",
  "request_hash": "sha256 prefix 8자리",
  "stage_a": {
    "intent": "...",
    "initial_risk_score": 0,
    "confidence": 0.0,
    "reasoning": "한 문장",
    "suggested_profile": "pro-plan|max-plan|null"
  },
  "stage_b": {
    "refined_risk_score": 0,
    "signals": [ { "type": "...", "weight": 0 } ],
    "kill_switch": false
  },
  "pro_plan_lock": {
    "active": true,
    "suppressed_suggestions": ["profile:max-plan"],
    "user_config_profile": "pro-plan"
  },
  "final_preset": "...",
  "final_profile": "...",
  "user_action": "accepted|overridden|cancelled",
  "outcome": "pass|fail|rework|null"
}
```

`request_hash` 로 원문 미보존 (개인정보·시크릿 유출 방지). v0.12.1+ `pro_plan_lock` 필드 신설 — lock 발동 시 어떤 자동 승격 제안이 억제되었는지 추적 (감사 + 사용자 통계 용도).

### 19.5 Pre-flight Bailout (v0.9.2+)

Stage A Triage 의 확장 기능. Gemini flash 가 "이 요청은 Ensembra 가치 없음" 을 판정할 수 있게 하여 Phase 0 진입 자체를 생략하는 비용 절감 메커니즘.

#### 19.5.1 판정 원칙

- `ensembra_needed: false` → Phase 0 진입하지 않고 종료
- `ensembra_needed: true` → 기존 Stage A → Phase 0 진입

Gemini 는 **하나의 호출**로 두 판정을 동시에 수행 (ensembra_needed + preset/profile 제안). 별도 호출 추가 없음.

#### 19.5.2 Bailout 시 권장 경로

Gemini 응답의 `suggested_action` 필드:

- `direct_edit`: Claude Code 가 직접 Edit 으로 수정 (예: 2줄 오타, 상수값 변경)
- `claude_chat`: `/ensembra:run` 없이 일반 대화로 진행 (예: 코드 설명, 원인 진단 질문)
- `ensembra_ops` / `ensembra_ops_safe` / `ensembra_bugfix` / `ensembra_feature_pro` / `ensembra_feature_max`: Ensembra 필요 (bailout 하지 않음)

Conductor 는 bailout 시 사용자에게 1회 확인 프롬프트 (`pre_flight.auto_bailout: false` 기본).

#### 19.5.3 안전 편향

다음은 `ensembra_needed: false` 판정 **불가** (Stage A 가 위반 시 Conductor 가 true 로 override):

- Critical 키워드 감지 (auth·payment·schema·.env 등)
- Critical 경로 수정 (/auth/, /payment/, /migrations/ 등)
- `confidence < 0.6` (불확실 → 안전)
- 치명 신호 (§19 Kill Switch 와 동일 목록)

#### 19.5.4 토글

- `pre_flight.enabled: true` (기본)
- `pre_flight.auto_bailout: false` (기본 — 사용자 확인 필수)

`pre_flight.enabled: false` 면 Gemini 응답의 `ensembra_needed` 필드 무시, 항상 Phase 0 진입 (v0.9.1 동작).

#### 19.5.5 로깅

Bailout 결정은 `.claude/ensembra/reports/risk/runs.jsonl` 에 기록 (기존 Risk Routing 로그와 같은 파일):

```json
{
  "ts": "...",
  "request_hash": "...",
  "stage_a": { "...": "..." },
  "pre_flight": {
    "ensembra_needed": false,
    "bailout_reason": "...",
    "suggested_action": "direct_edit",
    "user_accepted": true
  },
  "final_route": "bailout (no pipeline execution)"
}
```

### 19.6 Stage A 흐름 + 초기 경로 점수표

Stage A Triage 는 Phase 0 진입 **이전** Gemini flash-lite (MCP `triage_request` tool) 로 수행. Bailout 판정 + 초기 경로 제안을 **한 호출**로 동시 수행.

#### 19.6.1 Triage 입력 프롬프트 (요약)

```
요청: {user_input}
레포 최상위: {top_dirs}
위험 키워드(+5): config.risk_routing.critical_keywords
위험 경로(+5):   config.risk_routing.critical_paths
High 키워드(+3): config.risk_routing.high_keywords

출력 JSON schema:
{
  "intent":              "bugfix|feature|refactor|ops|diagnosis|deployment|migration|question",
  "detected_domain":     [...],
  "action_type":         "read|add|modify|delete|replace",
  "initial_risk_score":  0~20,
  "confidence":          0.0~1.0,
  "reasoning":           "한 문장",
  "ensembra_needed":     true|false,
  "bailout_reason":      "ensembra_needed=false 일 때",
  "suggested_action":    "direct_edit|claude_chat|ensembra_*"
}
```

`confidence < 0.6` 면 score +3 보수 가산.

#### 19.6.2 초기 경로 점수표 (`ensembra_needed: true` 일 때)

| 점수 | 제안 preset | 제안 profile |
|-----|----------|-----------|
| 0 (read-only + Critical 없음) | bailout (§19.5) | — |
| 1~2 | 제안 생략 또는 `ops` | pro-plan |
| 3~5 | `ops` | pro-plan |
| 6~9 | `bugfix` | pro-plan |
| 10~14 | `ops-safe` | pro-plan |
| 15~19 | `feature` | max-plan |
| 20+ | `feature` + 강제 전문 감사 전원 | max-plan |

#### 19.6.3 사용자 확인 조건

`risk_routing.mode == always_ask` 또는 초기 점수 ≥ 10 이면 프롬프트 `[1]권장 [2]낮추기 [3]직접지정 [4]Ensembra 생략 [5]취소`. `mode == staged` 이고 점수 <10 → 조용히 진행 (배지만). `mode == aggressive` → 항상 생략.

### 19.7 Stage B 재평가 신호 가중치

Phase 0 Deep Scan 산출물로 **추가 tool call 없이** 재평가. 가중치 합산으로 `refined_risk_score` 계산.

| 신호 | 출처 | 가중치 |
|---|---|---|
| Blast Radius 1~5 호출자 | 호출 그래프 (항목 3) | +0 |
| Blast Radius 6~20 호출자 | 호출 그래프 | +3 |
| Blast Radius 20+ 호출자 | 호출 그래프 | +7 |
| public export / API 경계 | 호출 그래프 | +5 |
| 데이터 흐름: 로그만 | 데이터 흐름 (항목 4) | +0 |
| 데이터 흐름: 캐시 접근 | 데이터 흐름 | +2 |
| 데이터 흐름: DB write | 데이터 흐름 | +5 |
| 데이터 흐름: 외부 API | 데이터 흐름 | +3 |
| 데이터 흐름: 세션/인증 변경 | 데이터 흐름 | +10 (치명) |
| 테스트 없음 | 테스트 맵 (항목 5) | +4 |
| 테스트 없음 + 위 중첩 | 테스트 맵 | 추가 +3 |
| 경로 `/auth/`·`/session/`·`/middleware/` | 구조 (항목 1) | +5 |
| 경로 `/migrations/`·schema | 구조 | +7 |
| 경로 `/payment/`·`/billing/` | 구조 | +6 |
| 경로 `.env*`·`/config/` | 구조 | +4 |
| git churn 30일 10+ 커밋 | git 히스토리 (항목 6) | +2 |
| git 6개월 안정 | git 히스토리 | -1 |
| 횡단 영향 (commons/shared/lib) | 공통 모듈 (항목 9) | +8 |

### 19.8 Kill Switch 치명 신호

점수 누적 없이 **즉시 강제 중단 + max-plan 승인 요구** (`kill_switch: strict` 기본):

| 치명 신호 | 조건 |
|---|---|
| 세션/인증 상태 변경 | auth·session 파일 수정 + 테스트 없음 |
| Schema migration | `/migrations/` 경로 + DROP/ALTER 액션 |
| 환경변수 삭제·변경 | `.env*` 파일 DELETE/UPDATE |
| public API 시그니처 변경 | exported 함수 시그니처 + 6+ 호출자 |
| 위험 명령어 | `rm -rf`, `git push --force`, DB `TRUNCATE`/`DROP` |

`kill_switch: warn` → 배지 경고만, `off` → 감지 비활성 (배지는 §19.3 불변식으로 유지).

### 19.9 자동 업그레이드 3모드

변동폭 = `refined_risk_score - initial_risk_score`.

**`mode: always_ask`**: 변동 ≥ +3 이면 프롬프트, 미만이면 조용히 진행.

**`mode: staged`** (기본 권장):
- 변동 < `notify_threshold` (기본 3): 로그만
- `notify_threshold` ≤ 변동 < `auto_upgrade_threshold` (기본 10): 배지 알림, 경로 유지
- 변동 ≥ `auto_upgrade_threshold`: 자동 업그레이드 + 명시 알림
- Kill Switch: 별도 레이어

**`mode: aggressive`**: 변동 ≥ `notify_threshold` → 자동 업그레이드 (묻지 않음). Kill Switch: 별도 레이어.

#### 업그레이드 경로 매핑 (preset 차원만)

- `ops` + pro-plan → `ops-safe` + pro-plan
- `ops-safe` + pro-plan → `feature` + pro-plan
- `feature` + pro-plan → `feature` + pro-plan (💡 **profile 승격 없음** — pro-plan lock, §19.3)
- `feature` + max-plan → `feature` + max-plan + 강제 전문 감사 전원 (최고 경로)

#### pro-plan lock 상세 적용 규칙 (v0.12.1+)

사용자 config 의 `profile` 값에 따라 자동 업그레이드가 실제로 다르게 동작한다:

| 설정 profile | Stage A 추천 | Stage B 자동 업그레이드 | Auto-Escalation (R2) | Kill Switch |
|---|---|---|---|---|
| **`pro-plan`** | preset 만 조정 제안 (profile 유지) | preset 만 승격 (profile 유지) | R2 R2 전체 전달 수락 가능 (profile 변경 아님) | 중단 + 승인 프롬프트. **승인 없으면 중단 유지, max 자동 진입 금지** |
| **`max-plan`** | preset + profile 양쪽 조정 가능 | preset + 필요 시 profile 유지·심화 경로 | R2 항상 전체 전달 (max tier 기본 동작) | 중단 + 승인 프롬프트. 승인 시 최고 경로 진입 |
| **`custom`** | `profile_overrides` 내용에 따라 pro-plan/max-plan 중 가까운 쪽 규칙 적용 (보수 판정) | 동상 | 동상 | 동상 |

**구현 원칙**:
- Conductor 는 Stage A 응답을 받은 직후 **사용자 config `profile` 확인**. `pro-plan` 이면 Stage A/B 의 "profile 승격" 필드를 무시하고 preset 만 수용
- 승격 배지 출력 시 pro-plan lock 발동 표시: `🔒 pro-plan lock (profile 승격 차단, preset 만 조정)`
- 사용자가 정말 max 진입을 원하면 **명시적 경로** 3가지만 가능: `--profile=max-plan` 인자, config 영구 변경, Kill Switch 명시 승인

---

## 20. Deep Scan Caching (v0.9.2+)

Phase 0 Deep Scan 결과를 로컬 파일로 캐시해 반복 실행 시 재사용. 운영업무처럼 같은 프로젝트에 여러 요청이 들어오는 환경에서 Phase 0 tool call 비용을 대폭 절감.

### 20.1 설계 근거

Phase 0 Deep Scan 은 Glob/Grep/Read/Bash 수십 회 tool call 을 수행한다. 결과가 Claude Code 컨텍스트에 누적되어 단일 실행에 ~5% 컨텍스트 소비. 같은 프로젝트·같은 유형 요청을 반복하면 매번 동일한 Deep Scan 을 다시 하는 낭비.

### 20.2 캐시 키 구성

```
key = sha256(
  project_root_absolute_path + "|"
  + git_head_commit_hash + "|"
  + preset_name + "|"
  + plan_tier + "|"
  + request_intent
)[0:16]
```

- 프로젝트별, 커밋별, preset·tier·intent 조합별 독립 캐시
- git 변경 시 자동 무효화

### 20.3 캐시 파일 경로·포맷

- 경로: `{deep_scan.cache_path}/phase0-{key}.json` (v0.12.0+ 기본 `.claude/ensembra/cache/phase0-{key}.json`)
- v0.12.0+ 기본 경로 이관: `.ensembra/cache/` → `.claude/ensembra/cache/`. 플러그인 산출물을 대상 프로젝트의 `.claude/` 하위에 격리해 프로젝트 자체 산출물과 충돌 방지
- **하위 호환**: 구 경로 `.ensembra/cache/` 에 캐시가 이미 있는 환경에서는 Conductor 가 Read 로 HIT 허용 (fallback). 신규 저장은 항상 새 경로. v0.13 에서 구 경로 지원 제거 예정
- `.gitignore` 에 `.claude/ensembra/cache/` 추가 (v0.12.0+ 기본값). 기존 `.ensembra/cache/` 엔트리도 당분간 유지
- 파일 스키마:

```json
{
  "schema_version": "0.11.0",
  "cached_at": "ISO8601",
  "git_head": "sha 7자+",
  "preset": "ops|bugfix|refactor|...",
  "plan_tier": "pro|max",
  "request_intent": "bugfix|...",
  "context_snapshot": "...",
  "reuse_inventory": { "common_modules": [...], "shared_utilities": [...], "test_fixtures": [...], "dependencies": [...] }
}
```

### 20.4 무효화 조건

- `git HEAD` 해시 불일치
- `cache_ttl_hours` 경과 (**v0.11.0+ 기본 12시간**, v0.9.2~v0.10.0 은 6시간)
- `schema_version` 불일치 (Ensembra 버전 업그레이드 시)
- 사용자 수동 삭제 (`rm -rf .claude/ensembra/cache/`)

### 20.5 보안 불변식

- 캐시 파일에 API 키·시크릿 포함 절대 금지
- 사용자 요청 원문 미보존 (request_intent 만 기록)
- Conductor 는 캐시 파일 저장 전 시크릿 마스킹 재확인 (v0.11.0+ `gemini_client.scrub_outbound()` 와 동일 패턴 사용)

### 20.6 토글·튜닝

- `deep_scan.cache_enabled: true` (기본)
- `deep_scan.cache_ttl_hours: 12` (v0.11.0+ 기본, 1~72 허용)
- `deep_scan.cache_path: ".claude/ensembra/cache"` (v0.12.0+ 기본, 이전 `.ensembra/cache` 는 fallback Read 만 지원)
- `deep_scan.docs_inventory_pro_off: true` (v0.11.0+ 기본) — pro tier 에서 Deep Scan 항목 10(docs inventory) 완전 off. `source-analysis`·`security-audit` preset 은 무시

CI/CD 환경이나 캐시 불필요한 경우 `cache_enabled: false`. git commit 없이 파일 수정 시 TTL 이 길수록 캐시 stale 가능성 커지나, 무효화 주신호는 git HEAD 이므로 commit 만 제대로 하면 안전. v0.11.0+ 기본 12h 연장은 Phase 0 HIT 율을 높여 평균 20~40% 추가 토큰 절감을 노린다.

---

## 21. Artifact Offload (v0.12.0+ 스펙, opt-in)

Phase 1 Performer 출력·Phase 3 감사 출력을 파일로 오프로드해 본 세션 컨텍스트 누적과 Transport context window 오버플로우(§8.11) 리스크를 완화하는 opt-in 장치. 기본값은 비활성(`artifact_offload.enabled: false`), 실측 200K 근접/초과 사례 축적 후 활성화 권장.

### 21.1 설계 원칙

- **Performer 는 파일 직접 쓰지 않는다**. Conductor 가 Performer 응답 수신 직후 `artifact_offload.path/{run_id}/` 에 저장 (§9 Performer Write 금지선 준수)
- **본 세션 컨텍스트엔 요약 + 경로**만 유지 (`artifact_offload.summary_chars`, 기본 300자)
- **후속 Performer 에게 전달 시** §8.11 `max_input_chars` 내에서 Conductor 가 요약 or `@{artifact_path}` 참조 경로 전달 방식 선택
- **`artifact_offload.enabled: false` 시 동작 무변경**. 기존 v0.11.x 파이프라인과 완전 동일 (회귀 없음)

### 21.2 디렉토리 구조

```
{artifact_offload.path}/                        # 기본 .claude/ensembra/artifacts/
├── {run_id}/                                   # UUID v4 + ISO8601 prefix (동시 실행 충돌 방지)
│   ├── manifest.json                           # 아래 §21.3 스키마
│   ├── phase1-r1-architect.md
│   ├── phase1-r1-developer.md
│   ├── phase1-r1-devils-advocate.md
│   ├── phase1-r1-qa.md
│   ├── phase1-r2-{role}.md                     # R2 수행 시만
│   ├── phase1-synthesis.md
│   ├── phase3-audit-architect.md
│   ├── phase3-audit-devils-advocate.md
│   └── phase3-final-auditor.md
```

### 21.3 `manifest.json` 스키마

```json
{
  "schema_version": "0.12.0",
  "run_id": "20260419T133042-a3f9",
  "started_at": "ISO8601",
  "preset": "refactor",
  "plan_tier": "pro|max",
  "profile": "pro-plan|max-plan|custom",
  "artifacts": [
    {
      "phase": "phase1-r1|phase1-r2|phase1-synthesis|phase3-audit|phase3-final-auditor",
      "role": "architect|developer|...",
      "file": "phase1-r1-architect.md",
      "bytes": 4281,
      "created_at": "ISO8601",
      "summary_chars_used": 287,
      "transport_used": "mcp|ollama|claude-subagent",
      "model_used": "gemini-2.5-flash|qwen2.5:14b|sonnet|..."
    }
  ]
}
```

### 21.4 run_id 생성 규칙 (동시 실행 충돌 방지)

`run_id = "{ISO8601 compact}-{uuid4 first 4 hex}"` (예: `20260419T133042-a3f9`).
- ISO8601 compact = `%Y%m%dT%H%M%S`
- uuid4 first 4 hex = 충돌 확률 1/65536. 동일 초 내 >2 실행 시 안전
- 극단적 경우 (대량 병렬) 는 uuid4 full 8 hex 로 확장 가능 (config 향후 필드)

### 21.5 retention 정책

- `artifact_offload.retention_days` (기본 7) 경과한 `{run_id}/` 디렉토리는 다음 Ensembra 실행 Phase 0 직전에 Conductor 가 일괄 정리
- git HEAD 기반 자동 정리는 하지 않음 (Phase 0 캐시와 달리 run_id 는 사후 감사·디버깅 목적이라 git 이력과 독립)
- 사용자 수동 삭제: `rm -rf .claude/ensembra/artifacts/` 안전

### 21.6 보안 불변식

- artifact 파일에 API 키·시크릿 포함 금지. 저장 직전 Conductor 가 `gemini_client.scrub_outbound()` 동일 패턴으로 마스킹 검증
- Performer 가 artifact 경로에 직접 쓰기 권한 없음 (Performer Read 도 허용하지 않음. 필요 시 Conductor 가 Read 하고 본문을 `prior_outputs` 로 전달)
- `.gitignore` 에 `.claude/ensembra/artifacts/` 자동 포함 (`.claude/ensembra/` 전체 이미 무시)

### 21.7 Transport 별 전달 전략

Conductor 가 후속 Performer 호출 시 artifact 를 어떻게 전달할지 결정하는 규칙:

| 후속 Transport | 입력 크기 판정 | 전달 방식 |
|---|---|---|
| MCP Gemini (1M) | artifact 전체 < 3.2M chars | **원본 인라인** 전달 |
| Claude subagent 200K | artifact 전체 < 640K chars | 원본 인라인 전달 |
| Claude subagent 200K | 그 이상 | **요약(300~1000자) + 경로 인용** 전달 (`@.claude/ensembra/artifacts/{run_id}/phase1-r1-architect.md`). Performer 프롬프트에 "필요 시 Read tool 로 원본 조회 가능" 명시 |
| Ollama 32K | artifact 전체 < 104K chars | 원본 인라인 |
| Ollama 32K | 그 이상 | 요약만 (Ollama 는 Read tool 없음, 원본 접근 불가) |

### 21.8 호환성 및 롤아웃

- **v0.12.0 도입, 기본 off**: 기존 v0.11.x 동작 완전 보존
- **v0.12.x 수집 기간**: 사용자 opt-in 으로 활성화한 환경에서 `manifest.json` 의 `bytes` 필드 분포 수집
- **v0.13 이후 기본 on 검토**: 200K 근접 사례 ≥10% 확인 시 기본값 변경. 이때 `artifact_offload.enabled: true` 를 SKILL.md 기본으로 이동

### 21.9 CONTRACT 관련 참조

- §5.1 `token_limit` 에러 코드: artifact 오프로드가 enabled 일 때 자동 요약 재전송 경로 제공
- §8.11 Transport Context Window 상한표: artifact 전달 방식 판정 기준
- §8.12 max tier "무제한" 실질 정의: artifact 오프로드가 max 의 "무제한" 을 실제로 뒷받침하는 구현 기반
- §20 Phase 0 Cache: 구조·보안·retention 원칙을 재사용 (신규 추상화 없음, §16 Reuse-First 준수)

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
