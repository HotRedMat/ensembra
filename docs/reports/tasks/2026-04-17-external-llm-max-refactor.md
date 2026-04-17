# Task Report — 외부 LLM 최대 활용 + Debate/Audit 분리 리팩토링 (v0.8.0)

- **Date**: 2026-04-17
- **Preset**: `refactor`
- **Plan Tier**: `pro`
- **Pipeline Result**: Pass (Conductor 자가감사, final-auditor 활성은 `/reload-plugins` 이후)
- **합의율**: N/A (Conductor 단독 Synthesis 경로 — "확인해줘 → 진행해" 흐름)
- **만장일치(v0.8.0 정의)**: 미측정 (final-auditor 신설 당일, 본 세션 미활성)
- **Rework 횟수**: 전문 감사 0 / Final Audit 0

## 1. 요약

v0.7.2 까지 "외부 LLM" 은 architect 1명(Gemini) + security/qa 2명(Ollama) 에 국한되고, Claude 는 planner(opus) + developer(sonnet) + devils(haiku) + scribe(sonnet) 4명에 분산되어 있었다. 사용자의 의도는 (a) 외부 LLM 활용 폭 확대, (b) 퀄리티·정확도 유지, (c) Claude 토큰 절감 — 그리고 후속 요구로 (d) 토론은 외부 LLM + sonnet 이하, 감사는 opus 1명 만장일치 판정 이라는 Debate/Audit 분리 구조였다.

v0.8.0 은 이 두 축을 동시에 반영해:

1. **Transport Fallback Chain Protocol (§8.8)** 을 일반화해 어떤 Performer 도 외부 LLM → Ollama → Claude 체인을 선언할 수 있게 함
2. **developer 의 opt-in 외부 체인** 을 준비 (기본값은 Claude sonnet 유지 — 금지선)
3. **planner 를 opus → sonnet 강등** 해 토론에서 opus 완전 제거
4. **`final-auditor` 신규 Performer** 를 Phase 3 전용 opus 감사자로 배치
5. **만장일치(unanimous) 조작적 정의** = Phase 1 합의율 ≥ 70% AND final-auditor pass

## 2. 변경 범위

14개 파일 수정 + 1개 신규 (총 +469 / -97 라인):

| 영역 | 파일 | 변경 |
|---|---|---|
| MCP server | `mcp-servers/gemini-architect/server.py` | 2개 tool (`architect_deliberate` + 신규 `developer_deliberate`) 노출, 버전 0.8.0, 단일 서버 프로세스 재사용 |
| 플러그인 매니페스트 | `.claude-plugin/plugin.json` | version 0.8.0, `userConfig.developer_transport` opt-in 필드 추가 |
| 마켓플레이스 | `.claude-plugin/marketplace.json` | version 0.8.0 |
| 설정 스키마 | `schemas/config.json` | `transport_chain`, `transportStep`, `external_first`, `mcp_tool_name` 필드 추가 |
| 계약 문서 | `CONTRACT.md` | §8.8 Transport Fallback Chain Protocol 신설, §11.1 Performer 풀 Debate/Audit 분리 재정리, §11.2 프리셋 매트릭스 갱신, §11.3 Final Audit & Unanimous Consensus 신설 |
| 스킬 | `skills/run/SKILL.md` | Phase 3 2단계 감사 프로토콜 재서술, 배지 규약 (Phase 3 배지 추가), 출력 포맷 `unanimous` 필드 추가 |
| 에이전트 | `agents/planner.md` | opus → sonnet 강등, Phase 3 감사 제외 |
| 에이전트 | `agents/developer.md` | Transport 섹션 신설 (기본 sonnet + opt-in 외부 체인) |
| 에이전트 | `agents/orchestrator.md` | Performer 풀 3군 분리 (토론/감사/문서화), 배지 예시 갱신, 책임 9~11항 갱신 |
| 에이전트 (신규) | `agents/final-auditor.md` | **NEW**. Claude opus 전용, Phase 3 전용, 만장일치 판정자. Rework 상한 1회 |
| 프리셋 | `presets/feature.yaml` | `audit.auditors` 에 `final-auditor` 자동 마지막 배치, planner 감사 제외 |
| 프리셋 | `presets/refactor.yaml` | `audit.auditors` 에 `final-auditor` 추가 |
| 프리셋 | `presets/bugfix.yaml` | `audit.auditors` 에 `final-auditor` 추가 |
| README | `README.md` | version 0.8.0 배지, Performer 표 Debate/Audit split, 프리셋 매트릭스 |
| CHANGELOG | `CHANGELOG.md` | `[0.8.0]` 엔트리 (Added/Changed/Security/Migration/Design rationale) |

건드리지 않은 파일: `agents/security.md`, `agents/qa.md`, `agents/devils-advocate.md`, `agents/scribe.md`, `agents/architect.md`, `presets/security-audit.yaml`, `presets/source-analysis.yaml` — 전부 기본 동작이 v0.8.0 원칙과 일치.

## 3. 의사결정 로그

### D1. planner 를 외부 LLM 으로 이관할 것인가 (Q6)
- 선택: **Claude sonnet 강등 (금지선 유지)**
- 근거: 요구사항 해석은 Claude 계열 강점, 외부 LLM 이관 시 뉘앙스·한국어 해석 리스크. opus → sonnet 으로 충분히 토큰 절감 목표 달성.

### D2. final-auditor 의 감사 범위 (Q7)
- 선택: **전문 감사자 + final-auditor 2단계**
- 근거: 전문 감사자가 세부를 잡고 opus 1명이 큰 그림 만장일치 판정. 단층 구조(final-auditor 만)는 전문성 손실, opus 단독 과부하.

### D3. 만장일치 정의 (Q8)
- 선택: **합의율 ≥ 70% AND final-auditor pass (실질 만장일치)**
- 근거: "100% agree" 는 실행 불가능 — Rework 루프 폭발. 70% + opus 종합 판단이 조작적 정의로 타당.

### D4. Final Audit Rework 상한 (Q9)
- 선택: **1회**
- 근거: opus 호출 비용 제어. 전문 감사자 2회 + final-auditor 1회 = 최대 3회 Rework 사이클로 파이프라인 상한 명확화.

### D5. devils-advocate 유지 여부 (Q10)
- 선택: **haiku 유지**
- 근거: haiku 는 opus 계열 아니므로 "토론에 opus 금지" 원칙 무관. 빠른 반응성·YAGNI 철학 계속 유효.

### D6. developer 외부 이관 (원 Q2)
- 선택: **opt-in (config.developer_transport)**
- 근거: Phase 2 실행자(Claude Code 본체 sonnet 계열) 와 모델 계열 일치 유지 필요. 외부 이관은 사용자가 명시 선택 시만.

### D7. MCP server 파일 구조 (원 Q4)
- 선택: **단일 `server.py` 파라미터화**
- 근거: architect + developer 도구가 90% 동일 코드 (call_gemini 공유). 파일 중복 방지 (Reuse-First).

### D8. Transport 프로토콜 신설 (원 Q5)
- 선택: **CONTRACT §8.8 신설**
- 근거: 향후 Performer 이관 시 역할별 특수 분기 제거 → 단일 공통 루프.

## 4. 재사용 기회 평가 (Synthesis 최상단 재현)

**결과: Reuse / Extend 우선, 신규 추상화 0건**

| 항목 | 위치 | 활용 방식 |
|---|---|---|
| MCP transport 자동 등록 | `.claude-plugin/plugin.json.mcpServers` | 추가 tool 은 동일 서버 프로세스에 병합 (새 server.py 0개) |
| Gemini REST 래퍼 (`call_gemini`) | `mcp-servers/gemini-architect/server.py` | 2개 tool 이 공유 |
| 3단 폴백 체인 | v0.7.0 architect 전용 | §8.8 일반화로 모든 Performer 활용 가능 |
| Keychain resolver (macOS/Linux/Windows) | `server.py v0.7.2` | 그대로 재사용, 수정 0 |
| `transport: "mcp"` enum + `performerConfig` | `schemas/config.json v0.7.0` | `transport_chain` 은 기존 필드의 배열 확장 |
| 배지 규약 (`§8.6`) | v0.7.0 신설 | Phase 3 배지 추가만, 규약 자체는 재사용 |

## 5. 만장일치 판정 (v0.8.0 정의)

본 리팩토링은 **도입 자체** 이므로 그 정의가 아직 파이프라인에 살아있지 않다. 다음 refactor·feature 실행부터 `final-auditor` 가 활성화되어 만장일치 판정을 수행한다.

- 본 세션 자가감사: Conductor 단독 PASS (전 Plan 결정이 diff 에 누락 없이 반영)
- 다음 실행 시 `unanimous: true` 가 시스템 레벨에서 확인되면 v0.8.0 이 실제로 살아있다는 신호

## 6. 남은 작업

- [ ] `/reload-plugins` — v0.8.0 매니페스트 + 신규 `final-auditor` agent 등록
- [ ] `/plugin → ensembra → Configure options` 에서 `developer_transport` 를 `external` 로 설정하려면 opt-in
- [ ] 다음 refactor 실행에서 final-auditor 실제 호출 + unanimous 판정 E2E 검증
- [ ] `docs/design/transport-and-audit.md` (함께 생성) 에서 상세 설계 확인

## 7. 참고 문서

- [CONTRACT.md §8.8](../../../CONTRACT.md) Transport Fallback Chain Protocol
- [CONTRACT.md §11.3](../../../CONTRACT.md) Final Audit & Unanimous Consensus
- [CHANGELOG.md `[0.8.0]`](../../../CHANGELOG.md)
- [docs/design/transport-and-audit.md](../../design/transport-and-audit.md) (본 실행 생성)
- [docs/requests/2026-04-17-external-llm-max-refactor.md](../../requests/2026-04-17-external-llm-max-refactor.md) (본 실행 생성)
