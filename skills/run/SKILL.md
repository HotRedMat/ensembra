---
description: Ensembra 파이프라인의 메인 진입점. 프리셋과 요청을 받아 Phase 0~4 를 순차 실행한다. 사용법 "/ensembra:run <preset> <요청>" 예 "/ensembra:run feature 결제에 쿠폰 할인 추가". 프리셋 feature/bugfix/refactor/security-audit/source-analysis 중 선택.
disable-model-invocation: false
---

# Ensembra Run

너(Claude Code)는 이 스킬이 호출되면 **Conductor** 역할을 맡아 Ensembra 파이프라인을 실행한다.

## 인자 파싱
사용자 입력 `$ARGUMENTS` 를 다음 형식으로 파싱:
```
<preset> <요청 문자열>
```
- `<preset>`: `feature` / `bugfix` / `refactor` / `security-audit` / `source-analysis` 중 하나
- `<요청>`: 자연어 문자열

프리셋이 없거나 불명확하면 사용자에게 되묻는다.

## 파이프라인 실행 순서

### Phase 0 — Gather (Deep Scan)
`presets/{preset}.yaml` 의 `deep_scan` 설정을 읽고, 다음을 **병렬 tool call** 로 수행:

1. **강제 6항목** (끌 수 없음):
   - 구조 파악: `Glob "**/*"` 상위 디렉토리 + 진입점 파일(`main.*`, `index.*`, `app.*`) 식별
   - 키워드 역추적: 요청 문자열에서 심볼 추출 후 `Grep` 전 레포 역참조
   - 호출 그래프: 대상 함수 정의 + 호출 지점 + import 관계
   - 데이터 흐름: 대상 데이터의 생성→변형→소비 경로
   - 공통 모듈 인벤토리: `Glob` 으로 `commons/`, `shared/`, `lib/`, `utils/`, `helpers/`, `framework/`, `core/` 전수 + `Read` 로 공개 심볼 나열
   - 프로젝트 문서 인벤토리: `Glob` 으로 `docs/`, `spec/`, `requirements/`, `design/`, `adr/` 전수

2. **선택 4항목** (`~/.claude/config/ensembra/config.json` 의 Deep Scan 토글 확인):
   - 테스트 맵: `Glob` 으로 `tests/`, `__tests__/`, `spec/`
   - git 히스토리: `git log -p --all -n 5 <대상 파일>` (Bash)
   - 의존성: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` Read
   - 설정: `.env.example`, `config/*` Read

3. 수집 결과를 단일 **Context Snapshot** (Markdown) 으로 압축. 각 Performer 입력 `constraints.context_snapshot` 에 첨부.

### Phase 1 — Deliberate

1. **R1 독립 분석**: `presets/{preset}.yaml` 의 `performers` 목록의 각 Performer 를 순차 호출 (subagent 또는 외부 Transport). 각자에게 **동일한** `problem` + `context_snapshot` 전달. 서로의 답을 보지 못함.

2. **R2 반론** (조건부): `rounds` 설정에 따라. `presets/{preset}.yaml` 의 `rounds: [R1, R2, synthesis]` 면 실행. 각 Performer 에게 **이전 라운드 전체 출력** 을 `prior_outputs` 로 전달. R2 출력엔 `peer_signatures` 필수.

3. **합의율 계산**:
   - Peer Signature 매트릭스에서 agree 비율 계산
   - ≥ 70% → Plan 확정, Phase 2 진행
   - 40~70% → R3 또는 사용자 수동 판정
   - < 40% → 파이프라인 중단, 쟁점 목록 사용자 반환

4. **Synthesis**: Conductor(또는 지정된 synthesizer Performer) 가 최종 Plan 합성. 최상단에 **"⚠ 재사용 기회 평가"** 섹션 강제 배치 (`CONTRACT.md` §16.4).

### Transport 호출 규약 (architect = Gemini 경우)

Phase 1 R1 에서 architect Performer 를 호출할 때, Gemini Transport 라면 **키 조회 체인** 을 거쳐 curl 실행:

```bash
# Step 1: Claude Code userConfig env var (미래 호환)
GEMINI_KEY="$CLAUDE_PLUGIN_OPTION_GEMINI_API_KEY"

# Step 2: fallback 으로 ~/.config/ensembra/env 파일
if [ -z "$GEMINI_KEY" ] && [ -f ~/.config/ensembra/env ]; then
  source ~/.config/ensembra/env
  GEMINI_KEY="$GEMINI_API_KEY"
fi

# Step 3: 키 없음 → Claude 서브에이전트 폴백
if [ -z "$GEMINI_KEY" ]; then
  echo "⚠ architect: gemini → claude-sonnet (fallback, no Gemini key)"
  # 아래 curl 생략, 대신 Task 툴로 Claude architect 서브에이전트 호출
  exit 0
fi

# 정상 경로 — Gemini API 호출
curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$GEMINI_KEY" \
  -H 'Content-Type: application/json' \
  -d "$payload"
unset GEMINI_KEY GEMINI_API_KEY  # 쉘 변수 즉시 정리
```

**주의**:
- 키 값은 로그·Task Report·에이전트 출력 어디에도 노출 금지
- 호출 종료 직후 `unset` 으로 프로세스 환경에서 제거
- 폴백 발생 시 Conductor 출력 상단에 배지 표시 (`⚠ architect: gemini → claude-sonnet`)

### Phase 2 — Execute

Conductor(= 현재 Claude Code 세션) 가 **본인** 도구(`Edit`, `Write`, `Bash`) 로 Plan 을 실행. 외부 Performer 는 이 단계에 관여하지 않는다.

Plan 의 각 파일 변경 항목에 대해:
- `create`: `Write` 로 신규 파일 생성
- `modify`: `Read` 후 `Edit` 로 수정
- `delete`: `Bash rm` (신중하게)

실행 중 오류 발생 시 즉시 중단하고 사용자에게 보고.

### Phase 3 — Audit

`presets/{preset}.yaml` 의 `audit.auditors` 목록에 있는 Performer 들을 순차 호출. 각자에게 Plan + Phase 2 diff 전달.

감사자 출력 스키마:
```json
{
  "phase": "audit",
  "verdict": "pass|fail|rework",
  "issues": [{"severity": "high|medium|low", "file": "...", "line": N, "message": "..."}]
}
```

판정:
- 한 명이라도 `verdict: "fail"` → Rework 트리거
- 2명 이상 `rework` → Rework 트리거
- 모두 `pass` → Phase 4 진행

Rework 시 Phase 1 복귀, **Plan diff 만** 전달. Rework 상한 2회 (config 조정 가능).

### Phase 4 — Document

`audit.phase4` 설정에 따라 scribe 호출. 생성할 문서 유형은 프리셋별:
- `feature`/`refactor`: Task Report + Design Doc + Request Spec
- 그 외: Task Report 만

scribe 는 Phase 0~3 기록 전체를 입력으로 받고, 템플릿 슬롯을 채운다. 완료 후 파일 저장 경로를 사용자에게 보고.

## 출력 포맷
최종 사용자 응답은 다음 구조:
```
## Ensembra Run — {preset}

**결과**: Pass (Audit 통과)
**합의율**: 84%
**Rework 횟수**: 0

### 변경 파일
- src/payment/checkout.ts (+24 -3)
- tests/payment/coupon.test.ts (+52)

### 생성된 문서
- docs/reports/tasks/2026-04-15-add-coupon.md
- docs/design/payment.md (append)
- docs/requests/2026-04-15-add-coupon.md

### 재사용 기회 평가
(Synthesis 최상단 섹션 복사)
```

## 보안
- 시크릿 파일(`.env`, `*.key`)은 Phase 0 에서 경로만 수집, 내용 전달 금지
- 로그·보고서에 마스킹 키 적용 (`SECURITY.md`)
- Phase 2 의 비가역 동작(`git push`, `rm -rf` 등)은 사용자 확인 후에만

## 금지
- Phase 0 Deep Scan 강제 6항목 미수행 시 Phase 1 진입 금지
- 외부 Performer(Ollama/Gemini) 에게 파일 쓰기 권한 위임 금지
- Plan 외 파일 수정 금지 (Phase 2)
