# Design — Live LLM Call Indicators (3 Layers)

**Status**: Accepted (v0.8.1, 2026-04-17)
**Scope**: `CONTRACT.md §8.6` 확장 — 3 레이어 배지 규약
**Related**: v0.8.0 `§8.8 Transport Fallback Chain Protocol`, `§11.3 Final Audit`

## 1. 문제

v0.8.0 은 외부 LLM 활용을 구조적으로 확대 (Transport Fallback Chain 일반화, developer opt-in 외부 체인 등). 그러나 **사용자 시각에서 외부 호출 진행이 불가시**:

- Phase 1 시작 1회 배지 후 정적 구간 (수 초 ~ 수십 초)
- 그동안 MCP/Ollama 가 정말 호출되는지, 실패해서 Claude 로 조용히 폴백되는지 알 수 없음
- 사용자 명시 피드백: "외부 LLM 사용하는 부분 화면 표시 좀 해줬으면 좋겠어"

## 2. 설계

### 2.1 3 레이어 구조

기존 `§8.6` 의 "Phase 시작 배지 + 폴백 경고" 2 요소를 **3 레이어 관측 계층** 으로 재구조화:

```
Layer 1: Phase 시작 현황판 (v0.7.0+)
  📡 Phase N — Transport 현황:
    [Gemini] role → model @ endpoint
    ...
    
Layer 2: 개별 호출 실시간 배지 (v0.8.1 신규)
  ▶ [Gemini] role — 호출 시작 (model @ endpoint)
  ◀ [Gemini] role — 응답 수신 (Xms, YKB)
  ⚠ [Gemini] role — <reason> → Ollama 폴백
  ✗ [Gemini] role — transport-chain-exhausted
  
Layer 3: Phase 종료 집계 (v0.8.1 신규)
  📊 Phase N 외부 LLM 호출 집계:
    MCP(Gemini)   X회 / Y 성공 / Z 폴백
    Ollama        X회 / Y 성공 / Z 폴백
    Claude 폴백   X회
    외부 LLM 활용률: A/B (C%)
```

### 2.2 심볼 규약

| 이벤트 | 심볼 | 의미 |
|---|---|---|
| 호출 시작 | `▶` | transport_chain 단계 호출 개시 직전 |
| 호출 완료 | `◀` | 응답 수신 성공 (`===ENSEMBRA-OUTPUT===` 블록 파싱 성공) |
| 폴백 | `⚠` | 현 단계 실패 → 다음 transport 시도 |
| 최종 실패 | `✗` | transport_chain 전 단계 소진, Performer.status = error |
| 현황판 | `📡` | Phase 시작 헤더 |
| 집계 | `📊` | Phase 종료 집계 헤더 |

심볼 대안 기각 이유:
- `🟢🔴🟡`: 폰트 렌더링에 따라 너비 가변 → 모노스페이스 정렬 깨짐
- `[OK][FAIL]`: 시각 식별 느림. 긴 로그에서 스캔 불리
- `>`/`<`/`!`: ASCII 만으로는 긴급도 구분 어려움

### 2.3 `외부 LLM 활용률` 산식

```
활용률 = (MCP 성공 + Ollama 성공) / (Performer 호출 총 수) × 100
```

정의 기준:

- **분모 "호출 총 수"**: 실제 호출된 Performer 수. R2 에서 skip 된 Performer 는 제외 (pro tier 의 합의율 85% 자동 스킵 등)
- **분자 "외부 성공"**: transport_chain 의 외부(MCP/Ollama) 단계 중 어느 하나가 성공적으로 응답 반환한 Performer 수. 한 Performer 가 재시도해 성공한 경우에도 1 카운트
- 폴백 결과 Claude 가 처리한 건은 **분자 제외** (활용률의 의미: 외부가 실질 처리한 비율)

### 2.4 해석 가이드

활용률 수치 해석:

| 범위 | 상태 | Conductor 액션 |
|---|---|---|
| ≥ 70% | 정상 (외부 우선 정책 작동) | 추가 액션 없음 |
| 40~70% | 주의 (Transport 일부 불안정) | 집계 배지에 노란색 뉘앙스 표기 |
| < 40% | 경고 (구조적 문제 가능성) | 집계 배지 + 사용자에게 점검 권고 메시지 1회 |

40% 미만일 때 점검 대상:
- `GEMINI_API_KEY` 유효성 (Keychain, `/plugin → Configure options`)
- Ollama 프로세스 기동 여부 (`http://localhost:11434/api/tags`)
- 네트워크 방화벽 (Gemini API, generativelanguage.googleapis.com)

### 2.5 단일 토글 원칙

`logging.show_transport_badge: false` 설정 시 **3 레이어 전부** 억제. 세분 토글(`show_layer_2` 등) 은 제공하지 않는다.

근거: 사용자가 "배지 끄기" 의도일 때 일관된 UX. 부분 토글은 config 복잡도를 증가시키고 실익이 적음 (한 레이어만 보이는 상황의 실용성 낮음).

## 3. 보안 불변식 (§8.6.4 전 레이어 공통 금지선)

v0.8.1 의 신규 실시간 배지는 더 많은 이벤트를 노출하므로 **보안 불변식도 명시적으로 강화**:

1. **API 키 · Authorization 헤더 · 토큰 출력 금지**
   - `GEMINI_API_KEY`, `user_config.gemini_api_key`, `Authorization`, `x-goog-api-key`, `Bearer ...` 등 차단어 목록 Conductor 가 렌더링 직전 마스킹
2. **프롬프트 본문 · 응답 본문 출력 금지**
   - `§8.6.2` 실시간 배지는 bytes/ms/상태 메타데이터만 허용
   - Performer 입력의 `context_snapshot` 내용, 응답의 `===ENSEMBRA-OUTPUT===` 원문 출력 금지
3. **실패 `<reason>` 에서 민감 정보 마스킹**
   - HTTP 상태코드 (`HTTP 429`), 타임아웃 (`timeout 60s`), 스키마 위반 (`missing required field: summary`) 같은 짧은 요약만
   - 원 exception 메시지에 URL·쿼리스트링·헤더가 포함되면 Conductor 가 차단어 검사 후 [REDACTED] 치환
4. **단일 토글 원칙 하에서도 금지선은 유지**
   - `show_transport_badge: true` 에서도 위 4개는 무조건 적용. config 로 해제 불가 (금지선)

## 4. 성능 영향

- wall-clock timestamp: 호출 시작·완료 2회 측정 (`time.monotonic()` 동급) — 마이크로초
- 배지 라인 렌더링: 라인당 80~120 바이트 텍스트 — 전체 토큰 예산에 무시할 수준
- 레이어 2 라인 수: Performer 수 × 2 (정상) ~ × 4 (모두 폴백) = 최대 수십 라인
- 레이어 3: Phase 당 6행 고정

총 오버헤드: 파이프라인 실제 소요시간 대비 0.1% 미만 (MCP 호출의 수백~수천 ms 가 지배).

## 5. 대안 및 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 레이어 2 를 기본 off, 레이어 1/3 만 기본 on | 사용자 요구 "화면 표시" 의 핵심이 레이어 2. 기본 on 이 UX 에 부합 |
| 각 레이어 독립 config 키 | 복잡도 증가, 실익 적음. 단일 토글이 Claude Code `/config` 스타일과 정합 |
| 활용률 분자에 Claude 폴백 포함 | 활용률의 의미가 훼손됨 — 100% 고정 지표가 됨 |
| 프롬프트 본문 일부 (처음 200자) 출력 | 보안 리스크 큼 (시크릿 포함 가능). 메타데이터만으로 디버깅 충분 |
| JSON 라인 포맷 (`{"event":"start","role":"architect"}`) | 사용자가 터미널에서 눈으로 읽기 어려움. 시각 심볼 + 한국어 자연어가 적합 |
| 성능 경고 임계값을 활용률 외 추가 도입 (예: ms 임계) | YAGNI. 활용률 하나로 구조적 문제 감지 충분 |

## 6. 영향 범위

### 6.1 사용자 마이그레이션

- v0.8.0 → v0.8.1: 설정 파일 수동 편집 불필요
- `/reload-plugins` 후 다음 `/ensembra:run` 부터 자동 적용
- 기존 `logging.show_transport_badge` 값 그대로 유지 (false 였으면 3 레이어 모두 억제)

### 6.2 내부 영향

- Conductor 의 `transport_chain` 실행 루프 (§8.8.2) 각 단계 전후에 배지 훅 삽입
- Phase 1·3 종료 직전에 집계 배지 호출
- 통계 수집을 위한 카운터 (per-Performer: attempts, successes by transport, fallbacks, total_ms)

### 6.3 호환성

- v0.7.0 의 기존 `§8.6` 배지 포맷 → `§8.6.1` 로 흡수. 기존 포맷 그대로 동작
- v0.7.0 폴백 경고 배지 → `§8.6.2` 의 `⚠` 레이어 2 배지로 일반화. 메시지 문자열은 동일

## 7. 확장 여지 (Gate4 이월)

- 프로젝트 레벨 누적 활용률 (`docs/reports/daily|weekly` 에 합산)
- JSON 로그 출력 모드 (CI 파싱용): `logging.transport_badge_format: "human|json"`
- 실시간 배지 색상 (ANSI escape) — 터미널 감지 시 자동 활성
- 퍼센트가 역치 미만일 때 Conductor 가 자동 점검 배시 스크립트 제시

## 8. 참고

- [CONTRACT.md §8.6 LLM 호출 배지 규약](../../CONTRACT.md)
- [CONTRACT.md §8.8 Transport Fallback Chain Protocol](../../CONTRACT.md)
- [Task Report](../reports/tasks/2026-04-17-live-llm-badge-layers.md)
- [Request Spec](../requests/2026-04-17-live-llm-badge-layers.md)
