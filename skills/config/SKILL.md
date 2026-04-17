---
description: Ensembra 의 모든 설정을 선택형 대화로 관리하는 picker. 모델·프리셋·라운드·Deep Scan·Transport·타임아웃·로깅·Reports·Reuse-First 를 통합 관리한다. 사용법 "/ensembra:config". Claude Code /config 와 유사한 UX.
disable-model-invocation: false
---

# Ensembra Config

너(Claude Code)는 이 스킬이 호출되면 **상태 머신** 형태의 대화형 설정 picker 를 실행한다. Claude Code 에 진정한 TUI 가 없으므로 **메뉴 출력 → 사용자 숫자 입력 → 다음 상태 전이** 패턴으로 구현.

## 저장 경로
`~/.config/ensembra/config.json` (레포 외부). `chmod 600` 권장.

## 초기 진입
1. `~/.config/ensembra/config.json` 존재 여부 확인 (Bash `test -f`)
2. 없으면 기본값으로 메모리 상태 초기화
3. 있으면 `Read` 로 로드
4. 메인 메뉴 출력

## 메인 메뉴

```
Ensembra 설정 (v0.9.0+)
──────────────────
0)  Profile           — 🆕 Claude 요금제 프로파일 (pro-plan/max-plan/custom)
1)  Performers        — 역할별 모델 및 활성화 (8명, v0.9.0 final-auditor 포함)
2)  Presets           — 프리셋별 구성 (8종, v0.9.0+ ops/ops-safe 포함)
3)  Rounds            — 합의 임계값, Rework 상한
4)  Deep Scan         — 체크리스트 10항목 (강제 6 + 선택 4)
5)  Transports        — Ollama endpoint, Gemini API 키
6)  Timeouts          — transport 별 타임아웃
7)  Logging           — 마스킹 키, 로그 레벨
8)  Reports           — Phase 4 문서별 on/off, 경로, 언어
9)  Reuse-First Policy — 4개 장치 Quick Select 또는 Custom
10) Plan Tier         — Claude 플랜 기반 실행 tier (pro/max)
11) Risk Routing      — 🆕 위험 기반 자동 라우팅 (v0.9.0+)
12) Reset             — 기본값으로 복원
q) 저장 후 종료

번호를 입력하세요:
```

**프로파일 우선순위**: 프로파일(0번) 설정 시 해당 YAML 의 `transport_routing`/`rounds_override`/`phase3_override`/`output_limits_multiplier` 등이 기본값으로 로드된다. 개별 항목을 바꾸면 자동으로 `profile=custom` 으로 전환되고 변경 항목만 `profile_overrides` 에 저장된다 (나머지는 원래 프로파일 값 상속).

사용자 입력을 받으면 해당 서브메뉴로 전이. 각 서브메뉴도 동일 패턴.

## 서브메뉴 (간략)

### (1) Performers
역할 7개 나열 → 선택 → 모델 picker (Live 조회):
- Ollama: `Bash curl -s http://localhost:11434/api/tags` → `.models[].name`
- Claude: 정적 목록 (opus/sonnet/haiku + 현재 세션 ID)
- Gemini: **v0.7.0 에서 MCP 기반 재도입**. `settings.local.json` 에 `mcpServers.gemini-ensembra` 등록 여부로 가용성 판단. 키는 `/plugin → ensembra → Configure options` 에서 설정 (sensitive:true, picker 가 직접 접근하지 않음)
숫자 입력으로 선택.

### (2) Presets
프리셋 8개 (feature/bugfix/refactor/**ops**/**ops-safe**/security-audit/source-analysis/transfer) 선택 후 (v0.9.0+ ops/ops-safe 신설):
- a) 참여 Performer 체크박스
- b) 라운드 구성
- c) Phase 2 Execute on/off
- d) Phase 3 Audit on/off + 감사자
- e) Phase 4 Document 문서별 on/off
- f) Deep Scan 선택 항목

### (3) Rounds
- a) R2 자동 트리거 파일 개수 (기본 5)
- b) R2 자동 트리거 합의율 (기본 70)
- c) Synthesis 확정 합의율 (기본 70)
- d) 중단 합의율 (기본 40)
- e) Rework 상한 (기본 2)

### (4) Deep Scan
강제 6개(1,2,3,4,9,10) 은 토글 불가, 선택 4개(5,6,7,8) 만 토글.
1~4, 9, 10 번호 입력 시: "이 항목은 강제 on 입니다" 안내만.

### (5) Transports
- a) Ollama endpoint (기본 `http://localhost:11434`)
- b) Ollama health check → `curl -s /api/tags`
- c) Claude 폴백 모델 선택
- d) Gemini MCP 상태 확인 → `settings.local.json` 에 `mcpServers.gemini-ensembra` 등록 여부 표시 + MCP server health check

#### (5)c Claude 폴백 모델
Ollama 불가 시 architect/security/qa 가 사용할 Claude 모델 선택 (opus/sonnet/haiku).

#### (5)d Gemini MCP 상태 확인 (v0.7.0 복원)

v0.6.0 에서 제거되었던 Gemini 서브메뉴가 v0.7.0 에서 MCP 기반으로 복원됨.

표시 항목:
- `settings.local.json` 에 `mcpServers.gemini-ensembra` 등록 여부 (등록됨/미등록)
- MCP server 프로세스 가동 여부 (가동 중/미가동)
- API 키 설정 여부: **`gemini_api_key` 값 자체를 읽지 않고**, MCP server 에 health check 호출을 보내 간접 확인

**불변식**: picker 는 `gemini_api_key` 를 **절대 읽지·쓰지·길이 측정도 하지 않는다**. 키 설정은 `/plugin → ensembra → Configure options` 에서만 가능.

### (5)e Fallback 승인 프로토콜 (v0.9.3+)

외부 LLM 실패 시 Claude 폴백 사용자 승인 설정.

```
Ensembra > Transports > Fallback (v0.9.3+)
──────────────────────────────
현재: critical_only, batch_by_phase=true, retry=30s

1) 승인 모드:
     a) strict         — 모든 폴백 확인 (외부→Ollama도)
     b) critical_only  — 외부 체인 전부 실패 시만 확인 (권장, 기본)
     c) none           — 자동 폴백 (v0.9.2 동작)

2) Phase 배치 처리: [x] on / [ ] off
     on 시 Phase 시작 직전 1회 Health Check 로 일괄 승인.
     off 시 매 Performer 호출 시점마다 개별 프롬프트 (피로도 높음).

3) Retry 대기 시간:  현재 30초 (5~300초)
     [4] 재시도 선택 시 대기. Gemini rate limit 복구 목적.

9) 저장 후 상위 메뉴
0) 취소
```

**session_auto_approve** 는 실행 중 사용자가 [6] 선택 시 세션 한정 활성화. config 저장 안 함 (다음 세션 초기화).

### (6) Timeouts
Ollama/Gemini/Claude-subagent/Deep-Scan 각각 초 단위.

### (7) Logging
로그 레벨, 추가 마스킹 키, 폴백 배지 on/off.

### (8) Reports
- Task Report: **off 불가** (표시만)
- Design/Request/Daily/Weekly: 각각 on/off
- 보고서 경로 커스텀
- 언어 (원 요청 자동 / 한국어 / English)
- 인수인계서 기본 scope, 템플릿, devils-advocate 섹션 포함

### (9) Reuse-First Policy
메인 화면:
```
Ensembra > Reuse-First Policy
────────────────────────────────────
현재 상태: Maximum (4/4)
  [x] 1) Deep Scan Inventory
  [x] 2) Schema Field
  [x] 3) Auto Disagree
  [x] 4) Synthesis Report

Quick Select:
  1) Maximum    — 1+2+3+4 (기본)
  2) Strong     — 1+2+4
  3) Balanced   — 1+2
  4) Advisory   — 1 only
  5) Off        — 전부 off (비권장)
  0) Custom (체크박스 편집)
  9) 저장 후 상위 메뉴
```

#### Custom 편집 (cascade 자동 처리)
1~4 번호 토글 + `u` undo + `9` 저장 + `0` 취소.

**Cascade 규칙**:
- 장치 2 를 off → 3, 4 자동 off
- 장치 3 또는 4 를 on (2 off 상태) → 2 자동 on
- 자동 처리 후 안내 메시지 표시

무효 상태 도달 불가 (impossible by construction). Grey out 없음.

### (10) Plan Tier

Claude 플랜에 따라 파이프라인 실행 강도를 조절하는 프로파일. `skills/run/SKILL.md` 의 **Plan Tier Resolution** 섹션과 `CONTRACT.md §17` 이 권위 있는 정의.

```
Ensembra > Plan Tier
──────────────────────────────
현재: pro

1) pro  — Claude Pro 사용자 기준 (기본)
         · Deep Scan 3/10 (선택 4항목 off, 강제 6항목 중 3·4·10 압축)
         · Context Snapshot: 심볼·경로만
         · R2: R1 합의율 ≥85% 면 스킵, 아니면 diff 요약 전달
         · Audit: preset 감사자 목록의 첫 1명
         · scribe 입력: Phase 요약본

2) max  — Claude Max 사용자 기준
         · Deep Scan: preset 지시 그대로
         · Context Snapshot: 원문 발췌 포함
         · R2: 전체 출력 전달
         · Audit: preset 전원
         · scribe 입력: 원본 기록

9) 저장 후 상위 메뉴
0) 취소
```

**금지선** (tier 로 토글 불가): security/qa Performer 참여, 합의율 임계값, Reuse-First 장치, Deep Scan 강제 6항목의 "미수행".

**우선순위**: `/ensembra:run --tier=...` 인자 > 본 설정 > 기본값 `pro`

### (0) Profile — v0.9.0+ 신규

Claude 요금제 기반 통합 프로파일. profiles/{name}.yaml 에서 Transport 체인·출력 상한·정책 완화를 일괄 로드.

```
Ensembra > Profile (v0.9.0+)
──────────────────────────────
현재: pro-plan

1) 🪙 pro-plan  — Claude Pro 플랜 사용자 (비용 최소)
                 · 모든 Performer 1순위 Gemini/Ollama
                 · final-auditor: sonnet/Gemini pro 허용 (opus 완화)
                 · planner/scribe 외부 이관 허용
                 · 출력 상한 60% 적용
                 · Phase 3 감사자 2명 (전문 1 + final)
                 · 예상 Claude API 절감: 85~90%
                 · 예상 품질 저하: 10~15% (설계·요구사항 해석)

2) 💎 max-plan  — Claude Max5 플랜 사용자 (품질 우선)
                 · planner/developer/scribe/final-auditor Claude 고정
                 · opus final-auditor 유지
                 · 출력 상한 100% 적용
                 · Phase 3 감사자 preset 전원
                 · 예상 Claude API 절감: 0~10%
                 · 품질 저하 없음

3) custom      — profile_overrides 로 개별 항목 수동 지정

9) 저장 후 상위 메뉴
0) 취소
```

**우선순위**: `/ensembra:run --profile=...` 인자 > 본 설정 > 기본값 `pro-plan`

**프로파일 전환 영향**:
- (1) Performers, (2) Presets 의 Transport 체인이 프로파일 YAML 기본값으로 재설정
- 사용자가 개별 항목을 변경하면 자동으로 `profile=custom` 전환 + `profile_overrides` 에 변경점만 저장
- (10) Plan Tier 의 값이 프로파일 YAML 의 `plan_tier` 로 자동 동기화

### (11) Risk Routing — v0.9.0+ 신규

요청 텍스트 Triage (Stage A) + Phase 0 Deep Scan 재평가 (Stage B) 로 preset·profile 을 자동 결정.

```
Ensembra > Risk Routing (v0.9.0+)
──────────────────────────────
현재: staged 모드, auto_upgrade=10, notify=3, kill_switch=strict

1) 활성화:                  [x] on / [ ] off
2) 모드:
     a) always_ask  — 변동 +3 이상 항상 확인
     b) staged      — 알림 vs 자동 임계값 분리 (권장)
     c) aggressive  — 변동 +3 이상 자동 업그레이드
3) auto_upgrade_threshold   현재 10 (staged 전용)
4) notify_threshold         현재 3
5) kill_switch:
     a) strict  — 치명 신호 감지 시 강제 중단 (기본)
     b) warn    — 경고만 표시하고 계속
     c) off     — 비활성화 (비권장)
6) 위험 키워드 편집 (Critical/High/Paths)
7) 로그 기록 (runs.jsonl):  [x] on / [ ] off

9) 저장 후 상위 메뉴
0) 취소
```

**3단계 적응 권장**:
- 1~2주 (검증기): `always_ask` 모드 — 시스템 판정을 사용자가 검토
- 3~4주 (전환기): `staged` 모드 + `auto_upgrade=15` 로 시작
- 5주 이후 (정상): `staged` 모드 + `auto_upgrade=10` (기본값)

### (12) Reset
"모든 값을 기본값으로 복원하시겠습니까? (y/n)" 확인 후 진행.

## 저장

`0) 저장 후 종료` 선택 시:

1. 최종 상태 요약 표시:
   ```
   다음 설정으로 저장합니다:
     Performers: 6명
     Reuse-First: Maximum
     합의 임계값: 70/40
     Rework 상한: 2
     Deep Scan: 10/10 (강제 6 + 선택 4)
     Reports: 5/5

   y) 저장  n) 편집 계속
   ```

2. `y` 입력 시:
   - `~/.config/ensembra/` 디렉토리 없으면 `mkdir -p` (Bash)
   - `Write` 로 `~/.config/ensembra/config.json` 원자적 저장 (tmp → rename)
   - `Bash chmod 600` 권한 설정
   - 완료 메시지 출력

3. `n` 입력 시: 메인 메뉴로 복귀

## 구현 제약
- Claude Code 슬래시 스킬에 진정한 TUI 없음 → 본 SKILL 본문 자체가 **상태 머신 프롬프트**
- 각 메뉴는 한 메시지에 출력, 사용자 다음 메시지를 숫자로 파싱
- 순수 Markdown + Bash + Read/Write 만 사용. Node/Python 런타임 불필요

## 스키마 참조
`schemas/config.json` 의 JSON Schema 를 준수. 저장 시 스키마 검증 수행.

## 보안 (v0.7.0+)
- **이 스킬은 `gemini_api_key` 를 절대 읽지·쓰지·길이 측정도 하지 않는다** (v0.5.x 의 치환 기반 노출 경로 재현 방지)
- v0.7.0 에서 Gemini 가 MCP server 기반으로 재도입됨 — 키는 MCP server 프로세스 env 로만 전달, skill/agent content 미노출
- `config.json` 에는 시크릿 포함 금지 — 모든 시크릿은 Claude Code `userConfig` + OS 키체인에 위임
- `SECURITY.md` 마스킹 규칙 준수 — 로그·보고서에서 `x-goog-api-key`, `key=`, `GEMINI_API_KEY`, `CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY`, `user_config.gemini_api_key` 모두 `[REDACTED]`
