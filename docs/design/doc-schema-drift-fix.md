# Design — v0.8.x 문서·스키마 drift 3건 일괄 수정

**Status**: Accepted (2026-04-17, applied)
**Scope**: 기존 문서·스키마 확장 (신규 파일 0)
**Related**: v0.8.0 CONTRACT §11.3 Final Audit, v0.8.1 CONTRACT §8.6 Live Indicators

## 1. 문제

v0.8.0 / v0.8.1 대규모 구조 변경 (Debate/Audit 분리 + Live Indicators 3 레이어) 이후 연쇄적으로 발생한 문서·스키마 drift:

1. `schemas/agent-output.json` 이 v0.8.0 `final-auditor` 출력 포맷을 수용하지 못함 — `additionalProperties: false` 환경에서 runtime validation 실패 위험
2. `README.md` 의 agent 총수 표기가 v0.8.0 신설 final-auditor 를 반영하지 않음
3. `SECURITY.md` 위협 모델이 v0.7.0 에서 정지 — v0.8.0 final-auditor 불변식, v0.8.1 live indicators 차단어 규약 미기재

선행 source-analysis 실행에서 4 Performer 합의 100% 로 TOP3 권고 확정.

## 2. 설계 결정

### 2.1 Schema 확장은 backward-compat 우선

```diff
"role": {
  "type": "string",
- "enum": ["planner", "architect", "developer", "security", "qa", "devils-advocate", "scribe"]
+ "enum": ["planner", "architect", "developer", "security", "qa", "devils-advocate", "scribe", "final-auditor"]
}

"properties": {
  ...
+ "unanimous": { "type": "boolean", "description": "v0.8.0+. Phase 3 final-auditor 전용. Phase 1 합의율 ≥ 70% AND verdict == 'pass' 일 때 true." },
+ "consensus_rate": { "type": "integer", "minimum": 0, "maximum": 100, "description": "v0.8.0+. Phase 3 final-auditor 전용. Phase 1 Synthesis 합의율 (0~100)." }
}
```

**`required` 배열은 변경하지 않는다** — 기존 6 Performer 의 과거 출력이 validation 통과를 유지하도록. `unanimous`·`consensus_rate` 는 final-auditor 출력에서만 의미 있는 선택 필드.

### 2.2 README 1라인 교체

```diff
- All 8 agents invoked individually in live sessions
+ All 9 agents invoked individually in live sessions (6 debate performers + scribe + orchestrator + final-auditor)
```

"9" 숫자만 아니라 **구성 요소 명시** — 외부 기여자가 한눈에 agent 집합 이해.

### 2.3 SECURITY.md 섹션 배치

기존 구조: `위협 모델 → 보호 대상 → 신뢰 경계 → 커밋 금지 → 로그 마스킹 → 비가역 동작 → Gate2 이월`

**Gate2 이월 직전에** 2개 섹션 삽입:
- `## v0.8.0 추가 위협 모델 — Debate/Audit 분리`
  - final-auditor Transport 고정 불변식 (§11.3 금지선)
  - developer opt-in 외부 Transport 체인 데이터 경계
- `## v0.8.1 추가 위협 모델 — Live Indicators 3 레이어 (§8.6.4 금지선)`
  - 배지 차단어 표
  - 실패 `<reason>` 마스킹
  - 단일 토글 원칙
  - Gate3 전제조건 유지

**시간순 흐름 유지** — v0.7.0 → v0.6.0 되돌린 경로 → v0.8.0 → v0.8.1 → Gate2. 기존 섹션 순서 재배치 없음.

### 2.4 Gate2 이월 TODO 2건 추가

v0.8.1 에서 파생된 미해결 과제:
- 차단어 검사기 구현 (정규식 + 키 이름 + 값 패턴 3중 체크)
- Final Audit Rework 상한 2회 상향 가능 여부 실증

## 3. 대안 및 기각 사유

| 대안 | 기각 사유 |
|---|---|
| `unanimous`/`consensus_rate` 를 required 로 선언 | 기존 6 Performer 출력이 전부 validation 실패 — qa 의심점 반영 |
| final-auditor 를 role enum 이 아닌 별도 타입으로 분리 | 신규 추상화 도입, Reuse-First 위반. role 은 이미 열거형이라 확장이 자연스러움 |
| SECURITY.md 섹션을 별도 파일로 분리 (`SECURITY-v0.8.md`) | 파일 분절 → 검색 비용 증가. 기존 파일의 시간순 구조 활용이 유지보수 우선 |
| README 에 agent 수 숫자만 수정 ("All 8" → "All 9") | 구성 요소 명시 없으면 다음 drift 재발 가능. 명시가 비용 대비 효과 큼 |
| schema 를 v2 로 bump (`$id` 경로 변경) | 과잉 설계. optional 필드 추가는 호환 변경이라 v1 유지가 정확 |

## 4. 영향 범위

### 4.1 사용자

- 외부 영향 0 (문서·스키마 수정만)
- 파이프라인 실행 동작 변화 없음
- 다음 `/ensembra:run` 부터 final-auditor 출력이 스키마 검증 통과

### 4.2 내부

- v0.8.0 에서 이미 final-auditor 가 호출되던 상태였으나 스키마가 따라가지 못했음 — 본 PR 로 정합성 확보
- Gate2 구현 시 이 스키마를 런타임 검증기의 입력으로 사용 가능

### 4.3 호환성

- `schemas/agent-output.json`: superset 변경 (enum 확장 + optional 필드) → 구 버전 Performer 출력 그대로 valid
- `README.md`: 순수 문서, 동작 변화 없음
- `SECURITY.md`: 신규 섹션 추가, 기존 섹션 보존

## 5. 검증

### 5.1 JSON schema syntax
```bash
python3 -c "import json; json.load(open('schemas/agent-output.json'))" → OK
```

### 5.2 자기참조 일관성
- CONTRACT.md §11.3 (final-auditor 규약) ↔ schemas/agent-output.json (role enum + 필드) ✅
- CONTRACT.md §8.6.4 (배지 금지선) ↔ SECURITY.md v0.8.1 차단어 표 ✅
- agents/final-auditor.md (frontmatter `model: opus`) ↔ SECURITY.md v0.8.0 Transport 고정 불변식 ✅

### 5.3 Backward compat 실증
기존 Task Report 4건 (2026-04-17 생성) 의 final-auditor 출력이 모두 새 스키마로 valid.

## 6. 참고

- [Task Report](../reports/tasks/2026-04-17-doc-schema-drift-fix.md)
- [Request Spec](../requests/2026-04-17-doc-schema-drift-fix.md)
- [선행 source-analysis 보고서](../reports/tasks/2026-04-17-doc-drift-source-analysis.md)
- [schemas/agent-output.json](../../schemas/agent-output.json)
- [SECURITY.md v0.8.0/v0.8.1 섹션](../../SECURITY.md)
