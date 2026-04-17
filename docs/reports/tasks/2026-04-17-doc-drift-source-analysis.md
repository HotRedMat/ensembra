# Task Report — 프로젝트 문서/기타 업데이트 필요 항목 source-analysis (v0.8.1 Live Indicators 첫 실사용)

- **Date**: 2026-04-17
- **Preset**: `source-analysis` (읽기 전용)
- **Plan Tier**: `pro`
- **Pipeline Result**: N/A (`phase2.execute=false`, `phase3.audit=false`)
- **합의율**: **100%** (3/3 Performer 동일 TOP3 지목)
- **만장일치(v0.8.0 정의)**: N/A (read-only preset — final-auditor 호출 안 됨)
- **외부 LLM 활용률**: Phase 1 **67%** (2/3) — MCP 1 폴백 + Ollama 2 성공

## 1. 요약

사용자 요청 "현재 프로젝트에서 문서나 기타 업데이트할게 있는지 확인해줘" 에 대해 Phase 0 Deep Scan 으로 drift 후보 5건을 식별하고, 3 Performer (architect / security / developer) 독립 심사 + 합의율 100% 로 TOP3 권고 확정. v0.8.1 Live Indicators 3 레이어 배지가 **첫 실사용** 에서 의도대로 동작함을 동시 검증.

## 2. Phase 1 실측 (v0.8.1 Live Indicators)

### 레이어 2 실시간 배지 (실제 출력)
```
▶ [Gemini  ] architect     — 호출 시작 (gemini-2.5-flash @ MCP(gemini-architect))
▶ [Ollama  ] security      — 호출 시작 (qwen2.5:14b @ localhost:11434)
▶ [Claude  ] developer     — 호출 시작 (sonnet @ subagent)
◀ [Ollama  ] security      — 응답 수신 (23094ms, ~1.4KB)
◀ [Claude  ] developer     — 응답 수신 (33539ms, ~2.1KB)
⚠ [Gemini  ] architect     — HTTP 503 (Gemini API 일시 장애) → Ollama 폴백
▶ [Ollama  ] architect     — 호출 시작 (qwen2.5:14b @ localhost:11434)
◀ [Ollama  ] architect     — 응답 수신 (16830ms, ~1.1KB, Ollama 폴백 경로)
```

### 레이어 3 집계
```
📊 Phase 1 외부 LLM 호출 집계:
  MCP(Gemini)    1회 호출 / 0 성공 / 1 폴백    (HTTP 503 — Gemini API 일시 장애)
  Ollama         2회 호출 / 2 성공 / 0 폴백    (security + architect 폴백)
  Claude 폴백    1회                             (developer 정상 경로)
  외부 LLM 활용률: 2/3 (67%)
```

**평가**: 67% 는 ≥70% 정상 기준 바로 아래 — Gemini API 의 외부 503 장애가 원인. §8.8 Transport Fallback Chain 의 폴백 메커니즘이 **정확히 설계대로** 동작해 품질 손실 없이 외부 LLM 커버리지 확보.

## 3. Peer Signature 합의 매트릭스

| 후보 | architect | security | developer | 결과 |
|---|---|---|---|---|
| #1 schemas/agent-output.json final-auditor 누락 | 1위 | 3위 | **1위** | agree 3/3 |
| #2 README.md "All 8 agents" | 2위 | 2위 | 2위 | agree 3/3 |
| #4 SECURITY.md v0.8.x 미반영 | 3위 | **1위** | 3위 | agree 3/3 |
| #3 docs/reports/daily/2026-04-17.md 미존재 | skip | skip | skip | skip 3/3 |
| #5 docs/transfer/*.md 2026-04-15 기준 | skip | skip | skip | skip 3/3 |

**합의율 = 3/3 = 100%** (pro tier ≥ 85% → R2 자동 스킵).

## 4. 최종 권고 TOP3

### 🔴 #1 (긴급) `schemas/agent-output.json` 스키마 drift
- **문제**: `role` enum = `[planner, architect, developer, security, qa, devils-advocate, scribe]` — **`final-auditor` 누락**. `unanimous`(boolean), `consensus_rate`(integer) 필드 정의 없음. `additionalProperties: false` 설정.
- **영향**: v0.8.0 CONTRACT §11.3 에 명시된 final-auditor 출력이 **런타임 검증 즉시 실패**. 파이프라인 실행 블록 가능성
- **권고 액션**:
  1. `role` enum 에 `"final-auditor"` 추가
  2. `properties` 에 `unanimous: {type: boolean}` + `consensus_rate: {type: integer, minimum: 0, maximum: 100}` 추가
  3. `verdict` 필드에 `"verdict": {"enum":["pass","fail","rework"]}` 이미 존재 — 재확인
- **근거**: developer Performer 직접 인용:
  > "`additionalProperties: false` 스키마에서 즉시 validation 실패. `unanimous` 와 `consensus_rate` 필드도 `properties` 에 없어 런타임 검증 자체가 깨진 상태"

### 🟡 #2 (고) `README.md` line 182 agent 수 오류
- **문제**: "All 8 agents invoked individually in live sessions" — v0.8.0 이후 실제 9개 (final-auditor 추가)
- **권고 액션**: `"All 9 agents invoked individually in live sessions (6 debate performers + scribe + orchestrator + final-auditor)"` 로 교체
- **근거**: 공개 README 의 외부 노출 문서, 외부 기여자·마켓플레이스 검증자 혼선

### 🟡 #3 (고) `SECURITY.md` v0.8.x 섹션 추가
- **문제**: v0.7.0 기준 위협 모델. v0.8.0 final-auditor Claude-only 금지선, v0.8.1 live indicators §8.6.4 보안 불변식 (API 키 마스킹, 프롬프트 본문 출력 금지, `<reason>` 마스킹) 미반영
- **권고 액션**:
  1. v0.8.0 섹션 — final-auditor Transport `claude-subagent` 고정 불변식, opus 비용 집중 감사 정책
  2. v0.8.1 섹션 — Layer 2 실시간 배지의 보안 불변식 (`GEMINI_API_KEY`, `Authorization`, 프롬프트·응답 본문 금지, bytes/ms/상태만 허용)
  3. developer opt-in 외부 Transport 체인(`MCP gemini-2.5-pro → Ollama gpt-oss:20b`) 의 데이터 경계
- **근거**: developer Performer:
  > "새 외부 LLM 경로(gemini-developer, Ollama gpt-oss:20b)의 데이터 전달 경계와 opus 집중 비용 감사 정책이 문서화되지 않아 보안 감사 시 블라인드스팟"

## 5. 제외된 후보 (합의로 skip)

### #3 daily 2026-04-17.md
Task Report 4건(marketplace portability, external LLM max refactor, README staleness, live badge layers) 이 이미 당일 생성됨. Daily 는 집계용이라 `/ensembra:report daily` 명시 호출 시 자동 취합 예정 — 선제 생성 불필요.

### #5 docs/transfer/*.md
v0.8.x 가 아직 안정화 중 (v0.8.0 → v0.8.1 이 당일 릴리스). 안정화 후 일괄 갱신이 비용 효율적. `/ensembra:transfer` 명시 호출로 재생성 가능.

## 6. v0.8.1 Live Indicators 첫 실사용 검증 결과

| 검증 항목 | 판정 |
|---|---|
| 레이어 1 (Phase 시작 현황판) 출력 | ✅ |
| 레이어 2 `▶` 호출 시작 배지 | ✅ 3회 출력 |
| 레이어 2 `◀` 응답 수신 배지 | ✅ 3회 출력 (ms + bytes 포함) |
| 레이어 2 `⚠` 폴백 배지 | ✅ architect MCP→Ollama 폴백 시 정확히 출력 |
| 레이어 3 `📊` 집계 | ✅ 전체 통계 출력 |
| 외부 LLM 활용률 산식 | ✅ 2/3 = 67% — §8.6.3 규칙대로 계산 (MCP 실패 분자 제외, Ollama 성공 1건으로 폴백 카운트) |
| 보안 불변식 (§8.6.4) | ✅ API 키·프롬프트·응답 본문 미노출. 메타데이터(ms/bytes/상태) 만 표시 |

**v0.8.1 Live Indicators 는 첫 실사용에서 의도대로 동작**. 특히 Gemini API 503 라는 **의도치 않은 실장애** 를 레이어 2 배지가 즉시 가시화했고, §8.8 Transport Fallback Chain 의 폴백이 정확히 2단계(Ollama) 로 전환 — v0.8.1 투명성 목표가 기능적으로 충족됨.

## 7. Transport 성과 관찰

- **MCP Gemini Flash**: 1회 시도, HTTP 503 실패 (Gemini 서버측 이슈, 우리 코드 문제 아님)
- **Ollama qwen2.5:14b**: 2회 호출 (security + architect 폴백), 평균 19.9초, 100% 성공
- **Claude sonnet subagent (developer)**: 33.5초, 1.5배 응답 (상세 분석 포함)

## 8. 참고 문서

- [CONTRACT.md §8.6 LLM 호출 배지](../../../CONTRACT.md)
- [CONTRACT.md §8.8 Transport Fallback Chain Protocol](../../../CONTRACT.md)
- [CONTRACT.md §11.3 Final Audit & Unanimous Consensus](../../../CONTRACT.md)
- [CHANGELOG.md 0.8.1](../../../CHANGELOG.md)
- 선행 v0.8.0/v0.8.1 Task Reports: `docs/reports/tasks/2026-04-17-{external-llm-max-refactor,readme-version-staleness-fix,live-llm-badge-layers}.md`

## 9. 후속 실행 제안

사용자가 권고 TOP3 를 실행하려면:

```
/ensembra:run bugfix "schemas/agent-output.json 에 final-auditor role + unanimous/consensus_rate 필드 추가"
/ensembra:run bugfix "README.md line 182 agent 수 8 → 9 수정"
/ensembra:run refactor "SECURITY.md 에 v0.8.0/v0.8.1 섹션 추가"
```

또는 3건을 한 번에:
```
/ensembra:run refactor "v0.8.x 문서·스키마 drift 3건 일괄 수정 (schema + README + SECURITY)"
```

후자가 토큰 효율 ↑ (Deep Scan 1회). 단일 commit 으로 처리 가능.
