# Request Spec — 외부 LLM 최대 활용 + 만장일치 감사 (v0.8.0)

- **Date**: 2026-04-17
- **Requester**: misstal80@gmail.com
- **Scope**: Ensembra 플러그인 내부 아키텍처 리팩토링

## 1. 원 요청 (자연어)

> "이제 이 오류 이전의 외부 LLM을 최대한 이용을 하여 퀄리티, 정확도, 토큰 사용량 감소 등등 리펙토링 하려고해. 확인해줘."

후속 추가 요구:

> "추가 사항으로 토론을 할때 외부모델과 토론을 하고 클루드 코드의 opus보다 한단계 낮은 모델로 토론을 하는거야. 그리고 나중에 감사를 하나두고 그 감사는 클루드 코드의 opus여서 감사진행한 다음 만장 일치로 결론에 도달하는 방법은 어떨까?"

## 2. 정식화된 요구사항

### R1. 외부 LLM 활용 폭 확대 (퀄리티·정확도·토큰 축)
- [x] architect 외의 Performer 도 외부 LLM 체인을 가질 수 있어야 한다
- [x] 역할별 특수 분기 없이 **단일 공통 프로토콜** 로 모든 외부 체인을 처리해야 한다
- [x] 기존 v0.7.0 architect 3단 체인 동작이 그대로 유지되어야 한다 (하위 호환)

### R2. 토론 단계에서 opus 완전 제거
- [x] Phase 1 모든 Performer 가 opus 를 사용하지 않아야 한다
- [x] 외부 LLM + "opus 한 단계 아래(sonnet)" + 외부 소형 모델 조합만 허용
- [x] 기존 planner(opus) 는 sonnet 으로 강등되어야 한다
- [x] 이 금지선은 config 로 토글 불가해야 한다

### R3. 감사 단계에 opus 1명 배치
- [x] Phase 3 에 **최종 감사자(final-auditor)** 1명이 추가되어야 한다
- [x] final-auditor 는 Claude `opus` 고정이며 외부 이관 불가해야 한다
- [x] 모든 수정 preset(`feature`/`bugfix`/`refactor`) 의 Phase 3 체인 **마지막** 에 자동 배치
- [x] 읽기 전용 preset (`security-audit`/`source-analysis`) 은 해당 없음

### R4. 만장일치 판정 규약
- [x] "만장일치" 의 조작적 정의가 명확해야 한다
- [x] 토론 합의 + final-auditor 승인의 **2단 조건** 이어야 한다
- [x] 도달 실패 시 명확한 Rework·중단 경로가 있어야 한다

### R5. 토큰 사용량 감소
- [x] planner opus → sonnet 으로 토론 단계 opus 호출 0 회
- [x] final-auditor 는 전문 감사자 전원 `pass` 후에만 호출 (opus 조건부 투입)
- [x] Final Audit Rework 상한 1회 (opus 호출 총 최대 2회)

### R6. 호환성
- [x] v0.7.2 사용자의 설정 파일 수동 편집이 필요 없어야 한다
- [x] 기존 `performers.architect` 단일 Transport 선언이 계속 동작해야 한다
- [x] `/reload-plugins` 만으로 v0.8.0 활성

## 3. 수용 기준 (Acceptance Criteria)

### AC1 — Transport Fallback Chain Protocol
- [x] `CONTRACT.md §8.8` 이 존재한다
- [x] `schemas/config.json` 에 `transport_chain` 배열 + `transportStep` 정의가 있다
- [x] `transport: "gemini"` 는 `transportStep` enum 에서 제외된다 (MCP 경유로만 허용)
- [x] `mcp_tool_name` 생략 시 `{role}_deliberate` 유추 규칙 명시

### AC2 — developer_deliberate MCP tool
- [x] `mcp-servers/gemini-architect/server.py` 가 2개 tool 을 노출한다 (`architect_deliberate`, `developer_deliberate`)
- [x] 단일 서버 프로세스에서 두 tool 모두 처리 (파일 중복 없음)
- [x] Python `ast.parse` 통과

### AC3 — final-auditor 활성
- [x] `agents/final-auditor.md` 가 존재하고 frontmatter `model: opus`, `name: final-auditor`
- [x] 3개 수정 preset 의 `audit.auditors` 마지막 항목이 `final-auditor`
- [x] `audit.final_auditor: final-auditor` 명시 필드 포함

### AC4 — 만장일치 규약
- [x] `CONTRACT.md §11.3` 이 존재한다
- [x] 만장일치 정의 = "합의율 ≥ 70% AND final-auditor.verdict == pass" 명시
- [x] Final Audit Rework 상한 1회 별도 카운터 명시
- [x] `skills/run/SKILL.md` Phase 3 섹션에 2단계 호출 순서 명시
- [x] 출력 포맷에 `unanimous` 필드 추가

### AC5 — 토큰 절감 구조
- [x] `agents/planner.md` frontmatter `model: sonnet`
- [x] Phase 3 전문 감사자 `fail` 시 final-auditor 호출 **안 됨** (CONTRACT §11.3.1)
- [x] `config.external_first` 토글 존재 (schemas/config.json)

### AC6 — 호환성
- [x] `schemas/config.json.version` 값 `1` 유지 (스키마 호환)
- [x] `CONTRACT.md §8.8.6` 에 v0.7.0 architect 체인 재해석 예시 존재
- [x] CHANGELOG `[0.8.0]` 의 Migration 섹션에 "설정 수동 편집 불필요" 명시

## 4. 테스트 체크리스트 (수동)

- [ ] `/reload-plugins` 후 `/plugin list` 에 ensembra v0.8.0 표시
- [ ] `/ensembra:run refactor "테스트용 사소한 변경"` 실행 시:
  - [ ] Phase 1 배지에서 planner 가 `sonnet` 으로 출력됨 (opus 아님)
  - [ ] Phase 3 배지에서 `[⚖ opus ] final-auditor` 라인 출력됨
  - [ ] 최종 요약에 `**만장일치**: ✅/❌` 라인 출력됨
- [ ] `developer_transport: "external"` 설정 후 architect 호출이 성공 / 실패(폴백) 배지 표시
- [ ] `GEMINI_API_KEY` 미설정 상태에서도 파이프라인이 완주 (Claude 폴백)
- [ ] 읽기 전용 preset (`security-audit`) 실행 시 final-auditor 호출되지 않음

## 5. 비요구사항 (Explicit Non-Requirements)

- planner 를 외부 LLM 으로 이관하는 config 옵션 — **제공하지 않음** (금지선)
- scribe 를 외부 LLM 으로 이관 — **제공하지 않음** (금지선)
- final-auditor 의 Transport 를 config 로 변경 — **제공하지 않음** (v0.8.0 불변식)
- "100% agree" 엄격 만장일치 — **제공하지 않음** (§11.3.2 기각)
- Gemini direct API 호출 (MCP 미경유) — **제공하지 않음** (v0.6.0 키 유출 이슈)

## 6. 관련 문서

- [Task Report](../reports/tasks/2026-04-17-external-llm-max-refactor.md)
- [Design Doc](../design/transport-and-audit.md)
- [CONTRACT §8.8, §11.3](../../CONTRACT.md)
- [CHANGELOG 0.8.0](../../CHANGELOG.md)
