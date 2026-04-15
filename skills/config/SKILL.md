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
- a) Ollama endpoint (기본 `http://localhost:11434`)
- b) Ollama health check → `curl -s /api/tags`
- c) **Gemini API key — 인터랙티브 설정 플로우** (v0.3.0+)
- d) Gemini health check
- e) Claude 폴백 모델 선택

#### (5)c Gemini API key 인터랙티브 플로우

Claude Code 2.1.109 의 plugin install 이 sensitive userConfig 프롬프트를 띄우지 못하는 버그를 우회하기 위해, 이 스킬이 직접 키 설정 플로우를 제공한다.

**1. 현재 상태 조회** — 다음 순서로 키 존재 확인:

```bash
# Step 1: Claude Code userConfig 환경변수 (미래 호환)
if [ -n "$CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY" ]; then
  echo "SOURCE=env_var LEN=${#CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY}"
fi

# Step 2: ~/.config/ensembra/env 파일 (현재 워크어라운드)
if [ -f ~/.config/ensembra/env ] && grep -q '^GEMINI_API_KEY=' ~/.config/ensembra/env; then
  echo "SOURCE=env_file"
fi
```

**2. 상태 표시** (값 절대 출력 금지):

```
Gemini API key lookup chain:
  1. $CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY  : ✗ not set
  2. ~/.config/ensembra/env                : ✗ not set
  → architect will fall back to Claude sub-agent

Set up Gemini now? (y/n)
```

또는 설정됐으면:

```
Gemini API key lookup chain:
  1. $CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY  : ✗ not set
  2. ~/.config/ensembra/env                : ✓ set (length=39)
  → architect will use Gemini (gemini-2.5-flash)

Actions:
  r) Replace key
  d) Delete key (disable Gemini)
  t) Test API call (health check)
  0) Back
```

**3. 사용자가 `y` (설정) 또는 `r` (교체) 선택 시**:

보안 경고 출력:
```
⚠ 보안 안내:
다음 메시지에 Gemini API key 를 붙여넣으면 ~/.claude/history.jsonl
대화 히스토리에 기록됩니다. 테스트 완료 후 키를 로테이션
하는 것을 강력히 권장합니다.

무료 키 발급: https://aistudio.google.com/app/apikey

계속하시겠습니까? (y/n)
```

`y` 확인 시:
```
다음 메시지에 Gemini API key 만 붙여넣으세요 (예: AIza... 로 시작):
```

**4. 사용자가 다음 메시지에 키 제출 → Conductor 가 즉시 수행**:

```bash
# 디렉토리 보장
mkdir -p ~/.config/ensembra

# 파일 작성 (Write 툴 사용, 키 값은 여기서 절대 로그에 쓰지 마라)
cat > ~/.config/ensembra/env <<ENV_FILE
GEMINI_API_KEY=<사용자가_제출한_키>
ENV_FILE

# 권한 강제
chmod 600 ~/.config/ensembra/env

# 검증 — curl 호출로 실제 응답 확인 (키 값은 출력 금지)
source ~/.config/ensembra/env
response=$(curl -s -m 10 "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY")
if echo "$response" | jq -e '.models' > /dev/null; then
  echo "✓ Gemini API key saved and verified"
  echo "  file: ~/.config/ensembra/env (chmod 600)"
  echo "  models accessible: $(echo "$response" | jq '.models | length')"
else
  echo "✗ Gemini API error:"
  echo "$response" | jq -r '.error.message' | head -3
  echo "  (파일은 저장되었지만 키가 유효하지 않을 수 있습니다)"
fi
```

**5. 절대 규칙**:
- 키 값을 화면 출력에 포함 금지 (길이·프리뷰 해시만 허용)
- 저장 후 즉시 `chmod 600` 강제
- 검증 실패 시에도 파일은 그대로 두되, 사용자에게 "키 확인 필요" 만 안내
- 에이전트는 자신의 출력에 키를 포함해 저장하지 않음 — Task Report, 인수인계서, 로그 모두

**6. Claude Code userConfig 가 미래 버전에서 고쳐진 경우**:
- `$CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY` 가 주입되면 그게 자동으로 우선 (조회 체인 step 1)
- env 파일은 두 번째 우선순위로 폴백
- 사용자는 아무 조치 없이도 자동 마이그레이션됨 (env 파일을 지울지 말지 선택)

#### (5)d Gemini health check
사용자 선택 시 현재 조회 체인으로 로드한 키로 실제 API 호출. 응답 200 + 모델 목록 표시, 또는 에러 메시지.

#### (5)e Claude 폴백 모델
Gemini/Ollama 불가 시 architect/security/qa 가 사용할 Claude 모델 선택 (opus/sonnet/haiku).

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
- Gemini API 키 조회 체인 (v0.3.0+):
  1. `$CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY` (Claude Code `userConfig` + OS 키체인, 미래 호환)
  2. `~/.config/ensembra/env` 파일 (Claude Code 2.x userConfig 버그 워크어라운드, `chmod 600` 강제)
- **이상적 경로**: OS 키체인 (Claude Code 가 제대로 작동할 때)
- **현실적 경로**: `chmod 600` 파일 (현재 Claude Code 2.1.109 기준)
- 이 스킬은 키 값을 화면에 **절대 출력하지 않음** — 존재 여부와 길이만 표시
- `config.json` 에는 시크릿 포함 금지 (키는 env 파일 또는 키체인에 격리)
- `SECURITY.md` 마스킹 규칙 준수 — 로그·보고서에서 `x-goog-api-key`, `key=`, `GEMINI_API_KEY`, `CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY` 모두 `[REDACTED]`
- 사용자가 키를 대화에 붙여넣은 경우 즉시 경고: "대화 히스토리에 기록되므로 테스트 후 로테이션 권장"
