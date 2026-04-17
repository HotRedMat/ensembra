# Design — Transport Fallback Chain & Debate/Audit Split

**Status**: Accepted (v0.8.0, 2026-04-17)
**Supersedes**: v0.7.0 architect-specific 3-step fallback design (now absorbed as §8.8.6 example)

## 1. 문제

v0.7.2 는 두 가지 분리된 불편을 내포했다:

### 1.1 Transport 다형성 없음
architect 만 3단 폴백(MCP→Ollama→Claude) 을 갖고, 다른 Performer 는 단일 Transport + 묵시적 Claude 폴백. developer 나 devils 를 외부 LLM 으로 이관하려 해도 매번 역할별로 특수 분기를 작성해야 했다.

### 1.2 opus 과분산 + "감사" 불명확
planner(opus) + scribe(sonnet) + developer(sonnet) + devils(haiku) 조합에서 opus 가 토론 중간에 들어가 다른 Performer 를 압도하는 쏠림 + 비용 예측 불가. Phase 3 "Audit" 는 전문 감사자들이 각자 pass/fail 내는 다수결 방식으로 "만장일치" 라는 조작적 정의가 없었다.

## 2. 설계 결정

### 2.1 Transport Fallback Chain Protocol (§8.8)

임의의 Performer 가 `transport_chain: [step1, step2, ...]` 배열로 선언. Conductor 는 배열 순서대로 시도하고 실패 시 다음 단계 폴백. 각 step 의 공통 필드:

```json
{
  "transport": "mcp|ollama|claude-subagent",
  "mcp_server_name": "...",       // transport=mcp 일 때
  "mcp_tool_name": "...",          // 생략 시 {role}_deliberate 유추
  "model": "...",
  "endpoint": "...",
  "timeout_sec": 120
}
```

공통 실행 루프는 §8.8.2. 각 단계는 Health Check (§8.8.3) → 호출 → 응답 파싱 (§8.3) → 실패 시 다음 단계. 전 단계 실패 시 `status: error, _error.code: transport-chain-exhausted`.

**v0.7.0 architect 전용 체인은 v0.8.0 의 §8.8.6 예시로 재해석** — 설정 마이그레이션 불필요, 사용자 동작 호환.

### 2.2 `transport: "gemini"` 는 `transportStep` enum 에서 제외

Gemini 호출은 **MCP server 경유로만** 허용한다. 이 제약은 v0.6.0 의 구조적 키 유출 이슈(skill/agent content 에 `${user_config.gemini_api_key}` 치환 주입) 를 재발 방지하는 불변식.

### 2.3 external_first 토글

`config.external_first: true` 일 때 Conductor 는 체인에서 외부(MCP/Ollama) 단계가 Health Check 실패하면 배지에 경고를 강조하고, 체인이 없는 Performer 에 대해 외부 우선 체인 **자동 추천** (planner/scribe 예외 — 금지선).

### 2.4 Debate/Audit 분리

Performer 풀을 3군으로 나눈다:

```
Phase 1 Debate        ← opus 금지, 외부 LLM + sonnet 이하
Phase 3 Audit          ← 전문 감사자 (preset 고유) → final-auditor (opus, 공통)
Phase 4 Document       ← scribe (sonnet)
```

**Debate tier 금지선 (config 로 토글 불가)**:
- 토론 Performer 전체에 opus 사용 금지
- planner/scribe 는 Claude 고정 (외부 이관 금지)
- security/qa 는 Ollama 기본 유지

**final-auditor 불변식**:
- `claude-subagent` Transport 고정
- 모델 `opus` 고정
- Phase 3 전용 — 토론·문서화 불참
- 모든 수정 preset 의 `audit.auditors` 체인 **마지막** 에 자동 배치
- Rework 상한 별도 카운터 1회 (일반 Rework 2회와 독립)

### 2.5 만장일치(unanimous) 조작적 정의

```
unanimous := (Phase 1 Synthesis 합의율 ≥ 70%) AND (final-auditor.verdict == "pass")
```

"100% agree" 를 채택하지 않는 이유: 실무에서 6명이 완전 합의하는 상태는 도달 불가능하거나 도달해도 의미 없는 "동조" 에 가까움. 70% 합의 + opus 종합 판단 = 실질적 만장일치.

`final-auditor.verdict == "rework"` → Final Audit Rework 1회 (Phase 1 복귀, 전문 감사자 재호출 없음 — opus 비용 제어).
1회 소진 후에도 rework/fail → 파이프라인 중단, 사용자 수동 판정.

## 3. 대안 및 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 모든 Performer 를 외부 LLM 이관 | planner/scribe 의 요구사항 해석·템플릿 슬롯 채움 품질이 외부 LLM 에서 편차 큼 |
| final-auditor 로 전문 감사자 완전 대체 | 전문성 손실, opus 1명에게 모든 시각 부담 → 판정 편향 |
| "만장일치 = 100% agree" 엄격 해석 | 실행 불가능, Rework 루프 폭발 |
| 신규 MCP server `gemini-developer` 분리 | 90% 동일 코드 중복. Reuse-First 위반 |
| `transport: "gemini"` 재허용 | v0.6.0 구조적 키 유출 재발 위험 |
| final-auditor Transport 를 config 로 외부 이관 허용 | 만장일치 판정 품질·일관성 리스크. 금지선 유지 |
| final-auditor Rework 상한을 2회로 | opus 호출 비용 2배. 1회 + 사용자 판정 이관이 비용·책임 명확 |

## 4. 영향 범위

### 4.1 사용자 마이그레이션

- **v0.7.x → v0.8.0**: 설정 파일 수동 편집 불필요. 플러그인 업데이트 + `/reload-plugins` 만으로 자동 적용
- planner 가 sonnet 으로 변경되어 **요구사항 해석 품질이 미세하게 달라질 수 있음** — 실제 사용 중 편차 발견 시 사용자 개별 평가 필요
- developer 외부화를 원하면 `/plugin → ensembra → Configure options → developer_transport: "external"` 설정

### 4.2 내부 영향

- `schemas/config.json` 버전 필드 `version: 1` 유지 (v0.8.0 은 스키마 호환 변경)
- 기존 v0.7.x 의 `performers.architect.transport = "mcp"` 단일 선언은 v0.8.0 의 `transport_chain` 미선언 시 호환 경로로 해석 (§8.8.6)

### 4.3 성능

- Phase 3 에서 opus 1회 추가 호출 → 전체 파이프라인 시간 ~10~30초 증가 예상
- 반대로 planner sonnet 강등으로 토론 6라운드 기준 **opus 호출 1~2회 감소** → 순증은 opus 호출 0~1회. 토큰 단가 기준 크게 증가하지 않음
- developer 외부 이관(opt-in) 시 Ollama gpt-oss:20b 로컬 호출 → Claude sonnet 호출 0으로 감소, 대기 시간은 하드웨어 의존

## 5. 확장 여지 (Gate4 이월)

- Gemini 외 LLM 도 MCP server 로 노출 가능 (예: Claude 외부 API, OpenAI 차단 유지)
- `transport_chain` 에 `cache: {ttl_sec: 300}` 같은 캐시 단계 삽입 제안 검토
- final-auditor 의 Rework 시 전문 감사자 선택적 재호출 (현재는 완전 스킵)
- `unanimous: false` 를 경고 배지로 강조하는 CI 연동 (git commit gate)

## 6. 참고

- `CONTRACT.md §8.8` Transport Fallback Chain Protocol
- `CONTRACT.md §11.3` Final Audit & Unanimous Consensus
- `agents/final-auditor.md`
- `agents/planner.md` (Transport 섹션)
- `agents/developer.md` (Transport 섹션)
- `CHANGELOG.md [0.8.0]`
