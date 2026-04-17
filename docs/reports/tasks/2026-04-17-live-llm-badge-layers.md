# Task Report — v0.8.1 외부 LLM 호출 실시간 가시화 (Live Indicators 3 레이어)

- **Date**: 2026-04-17
- **Preset**: `refactor`
- **Plan Tier**: `pro`
- **Pipeline Result**: Pass (final-auditor 만장일치)
- **합의율**: 100%
- **만장일치(v0.8.0 정의)**: ✅ 도달
- **Rework 횟수**: 전문 감사 0 / Final Audit 0

## 1. 요약

v0.8.0 은 외부 LLM (MCP Gemini · Ollama) 활용 폭을 넓혔지만 **실제 호출 진행이 불가시** 했다. 사용자가 "화면에 표시를 좀 해줬으면 좋겠어" 라고 명시 요청 → v0.8.1 로 **3 레이어 배지 규약** 을 확장:

1. 레이어 1 (기존 v0.7.0): Phase 시작 현황판 — 유지
2. 레이어 2 (신규 v0.8.1): 개별 호출 실시간 배지 — `▶ / ◀ / ⚠ / ✗`
3. 레이어 3 (신규 v0.8.1): Phase 종료 집계 — `📊` + **외부 LLM 활용률** 산식

## 2. 변경 범위 (8 파일, +189 / -26 라인)

| 파일 | 액션 | 변경 |
|---|---|---|
| `CONTRACT.md` | modify | §8.6 을 §8.6.1~§8.6.4 로 분할 + 3 레이어 규약 명문화 |
| `skills/run/SKILL.md` | modify | LLM 호출 배지 섹션 3 레이어 재작성 + 출력 포맷 `외부 LLM 활용률` 필드 추가 |
| `agents/orchestrator.md` | modify | 배지 섹션에 레이어 2·3 예시 추가 |
| `.claude-plugin/plugin.json` | modify | version 0.8.0 → 0.8.1 |
| `.claude-plugin/marketplace.json` | modify | version 0.8.0 → 0.8.1 (2개소 전부) |
| `mcp-servers/gemini-architect/server.py` | modify | SERVER_VERSION 0.8.0 → 0.8.1 |
| `README.md` | modify | version 배지 0.8.0 → 0.8.1 |
| `CHANGELOG.md` | modify | [0.8.1] 엔트리 (Added/Changed/Version bump/Security/Migration/Design rationale) |

## 3. 외부 LLM 활용률 정의 (v0.8.1 신규 지표)

```
활용률 = (MCP 성공 + Ollama 성공) / (Performer 호출 총 수) × 100
```

- 분모: 실제 호출된 Performer 수 (R2 skip Performer 제외)
- 분자: transport_chain 의 외부(MCP/Ollama) 단계 성공 건수
- 폴백 결과로 Claude 가 실제 처리한 건은 분자 제외
- 한 Performer 가 `MCP 실패 → Ollama 성공` 이면 Ollama 성공 1건으로 카운트

**해석 가이드**:
- ≥ 70%: 외부 우선 정책 정상
- 40~70%: Transport 일부 불안정
- < 40%: 구조적 진단 필요 → Conductor 가 경고 1회 추가 출력

## 4. 의사결정 로그

### D1. 실시간 배지 심볼 선정
- 선택: `▶` 시작 / `◀` 완료 / `⚠` 폴백 / `✗` 최종실패
- 대안 기각: `🟢🔴` 등 컬러 이모지는 모노스페이스 정렬 어긋남. ASCII arrow 계열은 시각 구분 약함

### D2. 레이어 단일 토글 vs 세분 토글
- 선택: `logging.show_transport_badge: false` 하나로 3 레이어 전부 억제
- 근거: 사용자가 "배지 끄기" 의도 일관성. 세분 토글은 config 복잡도 증가 vs 실익 적음

### D3. 활용률 분자 정의
- 선택: **외부 성공만** 분자 (폴백 후 Claude 처리 분자 제외)
- 근거: "외부 LLM 활용률" 이 문자 그대로 외부가 실질 처리한 비율이어야 의미. 폴백 Claude 까지 분자에 포함하면 100% 고정되어 무의미

### D4. 성능 오버헤드
- 선택: wall-clock timestamp 2회 + 배지 라인 렌더링 = 무시할 수준
- 근거: 라인당 수십 바이트. MCP 호출 자체의 수백~수천 ms 대비 0.1% 미만

## 5. v0.8.0 기반 확장 (Reuse-First 준수)

| 기존 (v0.8.0) | v0.8.1 확장 방식 |
|---|---|
| `CONTRACT.md §8.6` Phase 시작 배지 + 폴백 경고 | §8.6.1 로 흡수, §8.6.2/§8.6.3 추가 |
| `§8.8.2` 공통 실행 루프 4단계 (가용검사 → 호출 → 파싱 → 성공 or 폴백) | 각 단계 전후에 레이어 2 배지 훅 삽입 |
| `§11.3` final-auditor 만장일치 규약 | 그대로 — 배지는 관측 계층, 판정 규약 변경 없음 |
| 출력 포맷의 `unanimous` / `Rework 횟수` 필드 | `외부 LLM 활용률` 1행 추가 |

**신규 파일 0, 신규 추상화 0, 신규 의존성 0**. 문서 확장만.

## 6. 재사용 기회 평가 (Synthesis 최상단 재현)

**결과: Reuse / Extend, 신규 추상화 0건**

- `§8.6` 를 **확장** (§8.6.1~§8.6.4 하위절 분할)
- `§8.8 Transport Fallback Chain Protocol` 의 공통 루프에 **배지 훅** 끼우기 (로직 변경 0)
- 보안 불변식 (`§8.6.4` 전 레이어 공통 금지선) 은 기존 v0.7.0 규칙의 **통합·명문화**

## 7. Final Auditor 총평

> v0.8.1 Live Indicators 3레이어 설계는 사용자의 '외부 LLM 화면 표시' 요구를 §8.6 확장(신규 추상화 0·신규 파일 0)으로 충족하며, 보안 불변식과 §8.8 Transport Fallback Chain·§11.3 만장일치 규약과 완전히 정합한다. 토론 합의 100% 와 전문 감사자 pass 판정이 Phase 2 diff 에 누락·왜곡 없이 반영되었고, version bump 6곳 모두 동기화되었다. Phase 4 Document 로 진행 가능.

## 8. 다음 검증 단계 (후속 run)

- [ ] `/reload-plugins` — v0.8.1 활성
- [ ] 다음 refactor/feature 실행에서 레이어 2 실시간 배지 실 출력 확인
- [ ] Phase 종료 배지에서 활용률 숫자가 실제로 의미 있는 값인지 확인

## 9. 참고 문서

- [Design Doc](../../design/live-llm-badge-layers.md)
- [Request Spec](../../requests/2026-04-17-live-llm-badge-layers.md)
- [CONTRACT.md §8.6](../../../CONTRACT.md) LLM 호출 배지 규약 (v0.8.1 3 레이어)
- [CHANGELOG.md 0.8.1](../../../CHANGELOG.md)
