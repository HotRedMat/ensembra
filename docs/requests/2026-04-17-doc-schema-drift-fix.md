# Request Spec — v0.8.x 문서·스키마 drift 3건 일괄 수정

- **Date**: 2026-04-17
- **Requester**: misstal80@gmail.com
- **Preset**: `refactor`
- **Origin**: 선행 source-analysis 권고 TOP3

## 1. 원 요청

> "/ensembra:run refactor \"v0.8.x 문서·스키마 drift 3건 일괄 수정 (schemas/agent-output.json + README line 182 + SECURITY.md v0.8.x 섹션)\""

(선행 source-analysis run "현재 프로젝트에서 문서나 기타 업데이트할게 있는지 확인해줘" 의 권고 TOP3 를 일괄 실행.)

## 2. 정식화된 요구사항

### R1. schemas/agent-output.json 스키마 정합성
- [x] `role` enum 에 `"final-auditor"` 추가
- [x] `properties` 에 `unanimous: {type: boolean}` 추가 (optional)
- [x] `properties` 에 `consensus_rate: {type: integer, 0-100}` 추가 (optional)
- [x] `required` 배열 불변 (backward compat)
- [x] JSON syntax 유지 (parse 성공)

### R2. README.md agent 수 정정
- [x] line 182 "All 8 agents" → "All 9 agents"
- [x] 구성 명시 (6 debate + scribe + orchestrator + final-auditor)
- [x] 다른 라인 변경 없음

### R3. SECURITY.md v0.8.x 섹션 추가
- [x] `## v0.8.0 추가 위협 모델 — Debate/Audit 분리` 신설
  - [x] final-auditor Transport 고정 불변식 (§11.3 금지선)
  - [x] developer opt-in 외부 Transport 체인 데이터 경계
- [x] `## v0.8.1 추가 위협 모델 — Live Indicators 3 레이어 (§8.6.4 금지선)` 신설
  - [x] 차단어 표 (API 키·인증 헤더·쿼리스트링·프롬프트·응답 본문)
  - [x] 실패 `<reason>` 마스킹 규칙 (허용/금지 예시)
  - [x] 단일 토글 원칙
  - [x] Gate3 전제조건 유지 확인 (3가지 체크박스)
- [x] Gate2 이월 항목에 TODO 2건 추가 (차단어 검사기 + Final Audit Rework 실증)

### R4. Reuse-First
- [x] 신규 파일 0
- [x] 신규 추상화 0
- [x] 신규 의존성 0
- [x] 3 건 모두 기존 파일 extend

### R5. v0.8.1 Live Indicators 2번째 실사용 검증
- [x] Phase 1 레이어 1 배지 출력
- [x] 레이어 2 `▶` `◀` 실시간 배지 출력 (architect + qa 실제 호출)
- [x] 레이어 3 `📊` Phase 종료 집계 출력
- [x] 외부 LLM 활용률 50% (2/4) 정확 계산
- [x] 보안 불변식 (API 키·프롬프트·응답 본문 미노출) 적용

### R6. v0.8.0 Final Audit 만장일치 판정
- [x] 전문 감사자 (architect, Conductor 대행) verdict: pass
- [x] final-auditor (실제 opus subagent) verdict: pass
- [x] unanimous: true
- [x] consensus_rate: 100
- [x] Rework 0회

## 3. 수용 기준 (Acceptance Criteria)

### AC1 — schema 변경
- [x] `grep "final-auditor" schemas/agent-output.json` → 1건 매치 (role enum)
- [x] `grep "unanimous" schemas/agent-output.json` → 1건 매치 (properties)
- [x] `grep "consensus_rate" schemas/agent-output.json` → 1건 매치 (properties)
- [x] `python3 -c "import json; json.load(open('schemas/agent-output.json'))"` 성공

### AC2 — README 수정
- [x] `grep "All 9 agents" README.md` → 1건 매치
- [x] `grep "All 8 agents" README.md` → 0건
- [x] "6 debate performers + scribe + orchestrator + final-auditor" 문구 포함

### AC3 — SECURITY.md 섹션
- [x] `grep "v0.8.0 추가 위협 모델" SECURITY.md` → 1건
- [x] `grep "v0.8.1 추가 위협 모델" SECURITY.md` → 1건
- [x] 차단어 표 (Markdown `|` 테이블) 포함
- [x] Gate2 TODO 2건 추가

### AC4 — Backward compat
- [x] `required` 배열 변경 없음 (schemas/agent-output.json)
- [x] 기존 Performer role 7개 enum 보존
- [x] 기존 필드 제거 없음

### AC5 — v0.8.1 검증
- [x] MCP Gemini 호출 성공 (architect) — HTTP 200
- [x] Ollama 호출 성공 (qa) — 11650ms
- [x] 레이어 2 실시간 배지 4건 출력 (▶×2, ◀×2)
- [x] 레이어 3 집계 1건 출력

### AC6 — 만장일치
- [x] final-auditor 실제 subagent 호출 (agentId 생성)
- [x] JSON 응답에 `unanimous: true`, `consensus_rate: 100`, `verdict: "pass"` 포함
- [x] 전문 감사자 모두 pass

## 4. 비요구사항 (Non-Requirements)

- `unanimous`/`consensus_rate` 를 `required` 에 포함 — **제공하지 않음** (backward compat)
- SECURITY.md 를 v2 로 분할 — **제공하지 않음** (단일 파일 유지)
- README 의 다른 outdated bullet 갱신 (e.g., "All three transports verified" 행) — **본 실행 범위 밖** (별도 run 으로 분리)
- Gate2 TODO 의 실제 구현 — **Gate2 범위**
- daily/weekly report 자동 생성 — `/ensembra:report` 명시 호출 시만
- docs/transfer/* 의 v0.8.x 반영 — 안정화 후 별도 `/ensembra:transfer` 로 처리

## 5. 관련 문서

- [Task Report](../reports/tasks/2026-04-17-doc-schema-drift-fix.md)
- [Design Doc](../design/doc-schema-drift-fix.md)
- [선행 source-analysis](../reports/tasks/2026-04-17-doc-drift-source-analysis.md)
- [v0.8.0 Task Report](../reports/tasks/2026-04-17-external-llm-max-refactor.md)
- [v0.8.1 Task Report](../reports/tasks/2026-04-17-live-llm-badge-layers.md)
