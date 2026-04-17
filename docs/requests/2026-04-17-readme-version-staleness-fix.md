# Request Spec — README 의 오타 1개 수정 (v0.8.0 E2E test)

- **Date**: 2026-04-17
- **Requester**: misstal80@gmail.com
- **Preset**: `refactor`
- **Scope**: 문서 staleness 1건

## 1. 원 요청

> "`/ensembra:run refactor "README 의 오타 1개 수정"`"

위 명령은 표면적으로 "README 의 오타 1건" 이지만 실제 실행 목적은 **v0.8.0 신규 컴포넌트 활성 검증** (final-auditor 실제 호출, 만장일치 판정, 배지 규약 출력) 이다.

## 2. 정식화된 요구사항

### R1. 오타·staleness 후보 1건 식별
- [x] Phase 0 Deep Scan 으로 README 전수 검토
- [x] 현재 버전(v0.8.0) 과 문서 내용이 충돌하는 staleness 또는 명백한 오탈자 1건 식별
- [x] 선택된 후보: line 179 `v0.1.0` → `v0.8.0` (version staleness)

### R2. 수정 적용
- [x] 1개 파일 수정 (`README.md`)
- [x] 단일 라인, 단일 문자열 교체
- [x] 다른 의미적 변화 없음

### R3. v0.8.0 검증 가치 최대화
- [x] Phase 1 Transport 배지 실제 출력 (planner/developer/qa/devils/architect)
- [x] Phase 3 Audit 배지 실제 출력 (specialists + final-auditor opus)
- [x] `ensembra:final-auditor` 서브에이전트 실제 호출 (새 agent 등록 검증)
- [x] final-auditor 출력 스키마 준수 (`verdict`, `unanimous`, `consensus_rate`)
- [x] 최종 요약에 `만장일치: ✅ 도달` 필드 출력

### R4. Phase 4 문서 3종 생성 (refactor preset 요건)
- [x] Task Report
- [x] Design Doc
- [x] Request Spec (본 문서)

## 3. 수용 기준

### AC1 — 파일 실측
- [x] `grep "v0.8.0 is fully verified" README.md` 매치 1건
- [x] `grep "v0.1.0 is fully verified" README.md` 매치 0건

### AC2 — v0.8.0 pipeline 실활성
- [x] final-auditor subagent 호출 성공 (agentId 반환)
- [x] final-auditor 가 v0.8.0 스키마(JSON) 로 응답
- [x] `unanimous: true` 플래그 실 출력

### AC3 — 문서 3종 생성
- [x] `docs/reports/tasks/2026-04-17-readme-version-staleness-fix.md`
- [x] `docs/design/readme-version-staleness-fix.md`
- [x] `docs/requests/2026-04-17-readme-version-staleness-fix.md` (본 문서)

## 4. 비요구사항

- Verification status 섹션 전체 재작성 — **본 실행 스코프 밖** (Task Report §7 에서 후속 run 으로 분리 제안)
- CHANGELOG 엔트리 추가 — **본 실행 스코프 밖** (staleness fix 는 v0.8.1 patch 대상 또는 다음 릴리스 일괄 처리)
- README 외 다른 문서의 버전 표기 일괄 점검 — 별도 `refactor "문서 전수 버전 식별자 감사"` 로 분리 권장

## 5. 관련 문서

- [Task Report](../reports/tasks/2026-04-17-readme-version-staleness-fix.md)
- [Design Doc](../design/readme-version-staleness-fix.md)
- [v0.8.0 Task Report (선행)](../reports/tasks/2026-04-17-external-llm-max-refactor.md)
- [CONTRACT.md §11.3](../../CONTRACT.md) Final Audit & Unanimous Consensus
