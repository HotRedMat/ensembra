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
Ensembra 설정
──────────────────
1) Performers         — 역할별 모델 및 활성화 (7명)
2) Presets            — 프리셋별 구성 (6종)
3) Rounds             — 합의 임계값, Rework 상한
4) Deep Scan          — 체크리스트 10항목 (강제 6 + 선택 4)
5) Transports         — Ollama endpoint, Gemini API 키
6) Timeouts           — transport 별 타임아웃
7) Logging            — 마스킹 키, 로그 레벨
8) Reports            — Phase 4 문서별 on/off, 경로, 언어
9) Reuse-First Policy — 4개 장치 Quick Select 또는 Custom
10) Reset             — 기본값으로 복원
0) 저장 후 종료

번호를 입력하세요:
```

사용자 입력을 받으면 해당 서브메뉴로 전이. 각 서브메뉴도 동일 패턴.

## 서브메뉴 (간략)

### (1) Performers
역할 7개 나열 → 선택 → 모델 picker (Live 조회):
- Ollama: `Bash curl -s http://localhost:11434/api/tags` → `.models[].name`
- Gemini: `Bash curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY}"` → `.models[]` (filter: `generateContent` in `supportedGenerationMethods`). 키가 비어있으면 Gemini 섹션 생략하고 "키 미설정 — plugin disable/enable 로 재설정 가능" 안내
- Claude: 정적 목록 (opus/sonnet/haiku + 현재 세션 ID)
숫자 입력으로 선택.

### (2) Presets
프리셋 6개 (feature/bugfix/refactor/security-audit/source-analysis/transfer) 선택 후:
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
- a) Ollama endpoint (기본 `http://localhost:11434`, 플러그인 userConfig.ollama_endpoint 와 연동)
- b) Ollama health check → `curl -s /api/tags`
- c) Gemini API 키 상태 표시
  - `$CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY` 환경변수가 비어있지 않으면 `✓ set (OS keychain)` 표시, 값은 절대 출력 금지
  - 비어있으면 `✗ not set` + "키 재설정은 `claude plugin disable ensembra && claude plugin enable ensembra` 로 수행 (userConfig 프롬프트 재출현)" 안내
  - 이 스킬은 키를 직접 저장하지 않음 — Claude Code 의 OS 키체인 네이티브 메커니즘에 위임
- d) Gemini health check → `curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY}"` 응답 200 / 에러 표시
- e) Claude 폴백 모델 선택

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

### (10) Reset
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

## 보안
- Gemini API 키는 **OS 키체인** 에 저장됨 (Claude Code `userConfig.gemini_api_key` + `sensitive: true`). 평문 파일 저장 없음.
- 이 스킬은 키 값을 화면에 **절대 출력하지 않음** — 설정 여부만 `✓ set / ✗ not set` 로 표시
- `config.json` 에는 시크릿 포함 금지 (키는 OS 키체인에 격리)
- `SECURITY.md` 마스킹 규칙 준수 — 로그·보고서에서 `x-goog-api-key`, `key=`, `GEMINI_API_KEY`, `CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY` 모두 `[REDACTED]`
