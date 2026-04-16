---
description: Ensembra 파이프라인의 메인 진입점. 프리셋과 요청을 받아 Phase 0~4 를 순차 실행한다. 사용법 "/ensembra:run <preset> <요청>" 예 "/ensembra:run feature 결제에 쿠폰 할인 추가". 프리셋 feature/bugfix/refactor/security-audit/source-analysis 중 선택.
disable-model-invocation: false
---

# Ensembra Run

너(Claude Code)는 이 스킬이 호출되면 **Conductor** 역할을 맡아 Ensembra 파이프라인을 실행한다.

## 인자 파싱
사용자 입력 `$ARGUMENTS` 를 다음 형식으로 파싱:
```
<preset> [--tier=pro|max] <요청 문자열>
```
- `<preset>`: `feature` / `bugfix` / `refactor` / `security-audit` / `source-analysis` 중 하나
- `--tier=` (선택): 본 실행에 한해 Plan Tier 강제. 생략 시 config → 기본값 `pro` 순으로 해석
- `<요청>`: 자연어 문자열

프리셋이 없거나 불명확하면 사용자에게 되묻는다. `--tier` 값이 `pro|max` 외이면 오류로 중단.

## Plan Tier Resolution

Phase 0 진입 **직전** 에 tier 를 확정한다. 우선순위:

1. `--tier=` 인자 (본 실행 한정)
2. `~/.claude/config/ensembra/config.json` 의 `plan_tier` 필드
3. 기본값 `"pro"`

확정된 tier 는 Phase 0~4 전 과정에 동일하게 적용된다. Conductor 는 **Phase 0 시작 전** 한 줄 배지로 반드시 알린다:

```
🎚 plan_tier: pro (Deep Scan 3/10, Context=symbols, R2=diff-only, Audit=1명)
🎚 plan_tier: max (Deep Scan preset 원본, Context=full, R2=full, Audit=preset 전원)
```

### Tier 프로파일 (고정값)

| 축 | **pro** (기본) | **max** |
|---|---|---|
| Deep Scan 강제 6항목 | 1·2·9 는 전문 수행, 3·4 는 압축(핵심 심볼만), 10 은 상위 디렉토리 목록만 | 현행 전부 수행 |
| Deep Scan 선택 4항목 | preset `deep_scan.optional` 지시 **무시**, 전부 off | preset `deep_scan.optional` 지시 따름 |
| Context Snapshot | 심볼 목록·경로 인벤토리만 (파일 본문 생략) | 현행 (본문 발췌 포함) |
| Phase 1 R2 전달 | 이전 라운드 출력의 **diff 요약** (신규 쟁점·변경 위치만) | 이전 라운드 **전체 출력** |
| Phase 1 R2 스킵 | R1 Peer Signature 합의율 ≥ 85% 면 R2 자동 스킵 (rounds yaml 무시) | preset `rounds` 그대로 |
| Phase 3 Audit 감사자 | preset `audit.auditors` 의 **첫 1명** 만 호출 | preset `audit.auditors` 전원 |
| Phase 4 scribe 입력 | Phase 0~3 기록의 **요약본** (각 Phase 당 500자 이내) | Phase 0~3 **원본 기록** |

### 금지선 (pro 에서도 절대 양보 불가)

- feature preset 의 `security` / `qa` Performer 는 pro 에서도 참여 유지
- 합의율 임계값 (`rounds.*_consensus`) 은 tier 와 무관 — config 값 그대로 사용
- Reuse-First 장치 4개 (config `reuse_first.device_*`) 는 tier 로 토글 금지
- Deep Scan 강제 6항목은 "압축"·"범위 축소" 는 허용하되 "미수행" 은 불가 (§ 금지 참조)

### 합의율 저하 시 Auto-Escalation

pro 로 실행 중 R1 합의율이 40~70% 구간에 진입하면 Conductor 는 사용자에게 제안:
```
⚠ R1 합의율 62% — pro tier 에서 R2 전체 전달로 임시 상향 조정하시겠습니까? (y/n)
```
`y` → 해당 실행 한정으로 R2 는 max 방식으로 전환. `n` → pro R2 diff 방식 유지 또는 중단.

## 파이프라인 실행 순서

### Phase 0 — Gather (Deep Scan)
`presets/{preset}.yaml` 의 `deep_scan` 설정을 읽되, **Plan Tier Resolution** 결과를 겹쳐 적용한다. `tier=pro` 면 optional 4항목은 모두 off, forced 6항목 중 3·4·10 은 압축 모드. `tier=max` 면 preset 지시 그대로. 확정된 체크리스트로 다음을 **병렬 tool call** 로 수행:

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
   - `tier=pro`: 심볼 목록·경로 인벤토리만 포함. 파일 본문 발췌 금지.
   - `tier=max`: 현행 — 핵심 파일 본문 발췌 포함.

### Phase 1 — Deliberate

1. **R1 독립 분석**: `presets/{preset}.yaml` 의 `performers` 목록의 각 Performer 를 순차 호출 (subagent 또는 외부 Transport). 각자에게 **동일한** `problem` + `context_snapshot` 전달. 서로의 답을 보지 못함.

2. **R2 반론** (조건부): `rounds` 설정 + **Plan Tier** 에 따라.
   - `tier=max`: preset `rounds: [R1, R2, synthesis]` 이면 항상 실행. `prior_outputs` 는 이전 라운드 **전체 출력**.
   - `tier=pro`: R1 Peer Signature 합의율 ≥ 85% 면 R2 **자동 스킵**. 85% 미만이면 실행하되 `prior_outputs` 는 **diff 요약** (신규 쟁점, 반대 지점, 변경 제안 위치만 — 각 Performer 당 400자 이내).
   - 합의율 40~70% 구간 진입 시 §Plan Tier Resolution 의 Auto-Escalation 규칙 적용.

   R2 출력엔 `peer_signatures` 필수.

3. **합의율 계산**:
   - Peer Signature 매트릭스에서 agree 비율 계산
   - ≥ 70% → Plan 확정, Phase 2 진행
   - 40~70% → R3 또는 사용자 수동 판정
   - < 40% → 파이프라인 중단, 쟁점 목록 사용자 반환

4. **Synthesis**: Conductor(또는 지정된 synthesizer Performer) 가 최종 Plan 합성. 최상단에 **"⚠ 재사용 기회 평가"** 섹션 강제 배치 (`CONTRACT.md` §16.4).

### Transport 호출 규약 (architect = MCP → Ollama → Claude, v0.7.0+)

Phase 1 R1 에서 architect Performer 를 호출할 때 **3단 폴백 체인**을 따른다.

**1단: MCP server (gemini-architect)**

`settings.local.json` 에 `mcpServers.gemini-architect` 가 등록되어 있고, `GEMINI_API_KEY` 가 설정된 경우. Conductor 는 MCP tool-use 로 `architect_deliberate` tool 을 호출한다. API 키는 MCP server 프로세스 환경변수에만 존재하며 skill/agent content 에는 절대 노출되지 않는다.

**2단: Ollama (폴백)**

MCP 가용 실패 시 (MCP server 미등록, GEMINI_API_KEY 미설정, Gemini API 오류). `userConfig.ollama_endpoint` (비시크릿) 치환으로 엔드포인트를 얻는다:

```bash
curl -s -X POST "${user_config.ollama_endpoint}/api/generate" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"qwen2.5:14b\",\"prompt\":\"$prompt\",\"stream\":false}"
```

**3단: Claude 서브에이전트 (최종 폴백)**

Ollama 도 실패 시 Claude `sonnet` 서브에이전트로 폴백. 항상 가용.

**폴백 시 배지 표시**:
```
⚠ architect: gemini-2.5-flash (MCP) 실패 → ollama/qwen2.5:14b (fallback)
⚠ architect: ollama 실패 → claude-sonnet (fallback)
```

### LLM 호출 배지 (v0.7.0+)

`config.json logging.show_transport_badge: true` (기본) 일 때, Phase 1 R1 시작 직전에 전체 Performer 의 Transport/Model 현황을 출력한다:

```
📡 Phase 1 R1 — Transport 현황:
  [Gemini  ] architect  → gemini-2.5-flash  @ MCP(gemini-architect)
  [Ollama  ] security   → qwen2.5:14b       @ localhost:11434
  [Ollama  ] qa         → llama3.1:8b        @ localhost:11434
  [Claude  ] planner    → opus              @ subagent
  [Claude  ] developer  → sonnet            @ subagent
  [Claude  ] devils-adv → haiku             @ subagent
```

배지에 API 키·인증 토큰은 절대 포함하지 않는다. 상세 규약은 `CONTRACT.md §8.6` 참조.

### Phase 2 — Execute

Conductor(= 현재 Claude Code 세션) 가 **본인** 도구(`Edit`, `Write`, `Bash`) 로 Plan 을 실행. 외부 Performer 는 이 단계에 관여하지 않는다.

Plan 의 각 파일 변경 항목에 대해:
- `create`: `Write` 로 신규 파일 생성
- `modify`: `Read` 후 `Edit` 로 수정
- `delete`: `Bash rm` (신중하게)

실행 중 오류 발생 시 즉시 중단하고 사용자에게 보고.

### Phase 3 — Audit

`presets/{preset}.yaml` 의 `audit.auditors` 목록을 **Plan Tier** 로 필터링 후 순차 호출. `tier=pro` 면 목록의 **첫 1명** 만, `tier=max` 면 전원. 각자에게 Plan + Phase 2 diff 전달.

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

scribe 의 입력은 **Plan Tier** 로 결정:
- `tier=pro`: Phase 0~3 기록의 **요약본** (각 Phase 당 500자 이내, Conductor 가 사전 압축)
- `tier=max`: Phase 0~3 **원본 기록** 전체

scribe 는 받은 입력으로 템플릿 슬롯을 채운다. 완료 후 파일 저장 경로를 사용자에게 보고.

## 출력 포맷
최종 사용자 응답은 다음 구조:
```
## Ensembra Run — {preset}

🎚 **plan_tier**: pro    (또는 max)
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
