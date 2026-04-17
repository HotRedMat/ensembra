# Request Spec — 외부 LLM 사용 화면 표시 (v0.8.1 Live Indicators)

- **Date**: 2026-04-17
- **Requester**: misstal80@gmail.com
- **Preset**: `refactor`

## 1. 원 요청

> "외부 LLM을 사용하는 부분에 있어. 화면에 표시를 좀 해줬으면 좋겠어. 이 부분도 확인을 해줘."

## 2. 해석

v0.8.0 까지의 외부 LLM 관련 표시는 **Phase 시작 시점 1회 배지** (📡) + 폴백 발생 시 `⚠` 경고 뿐. 사용자는 "호출이 정말 외부에서 돌고 있는지" 를 중간에 확인할 수 없었음. 이 투명성을 높이는 것이 요청의 핵심.

## 3. 정식화된 요구사항

### R1. 개별 호출 실시간 가시화
- [x] 각 Performer 호출 시작/완료를 개별 라인으로 출력
- [x] 외부 LLM (MCP/Ollama) 과 Claude subagent 구분 가능
- [x] 폴백 발생 시 원인과 다음 transport 명시
- [x] 최종 실패(chain 소진) 시 별도 심볼

### R2. 호출 성과 측정
- [x] Phase 종료 시 외부 LLM 호출 횟수·성공·폴백 집계
- [x] **외부 LLM 활용률** 수치화 (예: 75%)
- [x] 수치 해석 가이드 (≥70% 정상 / 40~70% 주의 / <40% 점검)

### R3. 보안 불변식 유지
- [x] 실시간 배지에 API 키 출력 금지
- [x] 프롬프트·응답 본문 금지, bytes/ms/상태만 허용
- [x] 실패 `<reason>` 의 민감 정보 마스킹

### R4. 설정 일관성
- [x] 기존 `logging.show_transport_badge` 단일 토글로 3 레이어 전부 제어
- [x] 세분 토글 제공하지 않음 (복잡도 방지)

### R5. Reuse-First
- [x] 기존 `CONTRACT.md §8.6` 확장 (§8.6.1~§8.6.4 하위절)
- [x] `§8.8 Transport Fallback Chain Protocol` 의 공통 실행 루프 재사용 (배지 훅 삽입)
- [x] 신규 파일·추상화·의존성 0

### R6. 호환성
- [x] v0.8.0 → v0.8.1 설정 수동 편집 불필요
- [x] `logging.show_transport_badge` 값 그대로 유지

## 4. 수용 기준 (Acceptance Criteria)

### AC1 — 문서
- [x] `CONTRACT.md` §8.6 이 §8.6.1 (시작 현황판) / §8.6.2 (실시간) / §8.6.3 (집계) / §8.6.4 (금지선) 4 하위절로 재편
- [x] §8.6.2 심볼 규약 (`▶ ◀ ⚠ ✗`) 명시
- [x] §8.6.3 `외부 LLM 활용률` 산식 명시

### AC2 — 스킬
- [x] `skills/run/SKILL.md` LLM 호출 배지 섹션 3 레이어 구조로 재작성
- [x] 최종 출력 포맷에 `**외부 LLM 활용률**: Phase 1 X% / Phase 3 Y% (합산 Z%)` 행 추가

### AC3 — 오케스트레이터 참조
- [x] `agents/orchestrator.md` 배지 섹션 레이어 2·3 예시 추가

### AC4 — 버전 동기화
- [x] `.claude-plugin/plugin.json` v0.8.1
- [x] `.claude-plugin/marketplace.json` v0.8.1 (metadata + plugin 양쪽)
- [x] `mcp-servers/gemini-architect/server.py` SERVER_VERSION = "0.8.1"
- [x] `README.md` version 배지 0.8.1
- [x] `CHANGELOG.md [0.8.1]` 엔트리 (Added/Changed/Version bump/Security/Migration/Design rationale)

### AC5 — Syntax
- [x] 수정된 JSON 3개 파일 parse 성공
- [x] 수정된 Python 파일 AST parse 성공

### AC6 — 보안 불변식 재확인
- [x] §8.6.4 에 API 키·Authorization·토큰 금지선 명시
- [x] §8.6.2 에 프롬프트·응답 본문 출력 금지 명시
- [x] `<reason>` 마스킹 규칙 명시

## 5. 비요구사항 (Explicit Non-Requirements)

- 각 레이어별 독립 config 토글 — **제공하지 않음** (§2.5 단일 토글 원칙)
- 프롬프트 본문 일부 출력 — **제공하지 않음** (보안 리스크)
- JSON 로그 모드 — **v0.8.1 범위 밖**, Gate4 이월 (§7)
- 터미널 ANSI 컬러 — **v0.8.1 범위 밖**, Gate4 이월
- 프로젝트 누적 활용률 (일일·주간 리포트) — **v0.8.1 범위 밖**, Gate4 이월

## 6. 테스트 체크리스트 (수동)

- [ ] `/reload-plugins` 후 `/plugin list` 에 ensembra v0.8.1 표시
- [ ] `/ensembra:run refactor "테스트"` 실행 시:
  - [ ] Phase 1 중간에 `▶ [Gemini] ... 호출 시작` 같은 라인이 실제로 출력됨
  - [ ] Phase 1 종료 시 `📊 Phase 1 외부 LLM 호출 집계: ... 외부 LLM 활용률: X/Y (Z%)` 출력
  - [ ] 최종 요약에 `**외부 LLM 활용률**: Phase 1 X% / Phase 3 Y% (합산 Z%)` 행 출력
- [ ] `logging.show_transport_badge: false` 설정 후 실행 시 3 레이어 모두 억제됨
- [ ] 외부 LLM 실패 시 `⚠` 라인이 `→ Ollama 폴백` 형태로 출력됨

## 7. 관련 문서

- [Task Report](../reports/tasks/2026-04-17-live-llm-badge-layers.md)
- [Design Doc](../design/live-llm-badge-layers.md)
- [CONTRACT.md §8.6](../../CONTRACT.md) · [§8.8](../../CONTRACT.md) · [§11.3](../../CONTRACT.md)
- [CHANGELOG.md 0.8.1](../../CHANGELOG.md)
