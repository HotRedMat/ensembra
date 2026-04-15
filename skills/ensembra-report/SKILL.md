---
description: Ensembra 일일/주간 업무 보고서 생성. 사용법 "/ensembra:report daily" 또는 "/ensembra:report weekly". 자동 생성 아님, 사용자 명시 호출만.
disable-model-invocation: false
---

# Ensembra Report

너(Claude Code)는 이 스킬이 호출되면 scribe 를 호출해 **일일 또는 주간 roll-up 보고서**를 생성한다.

## 인자 파싱
`$ARGUMENTS` 의 첫 단어:
- `daily` → 오늘 날짜의 일일 보고서
- `weekly` → 현재 주의 주간 보고서
- 그 외 → 사용법 안내 후 종료

## Daily Report

### 입력 수집
1. 오늘 날짜 획득: `Bash date +%Y-%m-%d`
2. `docs/reports/tasks/{YYYY-MM-DD}-*.md` 파일 목록 수집 (`Glob`)
3. 각 Task Report `Read` 로 파싱:
   - 제목 (프로젝트 slug)
   - 프리셋
   - 상태 (Pass / Fail)
   - 합의율
   - 변경 파일 수
   - 재사용 기회 평가 결과
4. 전일 Daily Report 존재 여부 확인 (중복 생성 방지, `test -f`)
5. 존재하면 사용자에게 "덮어쓸까요?" 확인

### 출력 구조
```markdown
# 일일 업무 보고 — {YYYY-MM-DD}

## 완료 태스크 ({count})
1. [{task-title}](../tasks/{YYYY-MM-DD}-{slug}.md) — {preset} — {status}
2. ...

## 집계
- 전체 합의율 평균: {avg}%
- Reuse-First 재사용 건수: {count}회
- Audit 실패: {count}회
- Fallback 발생: {count}회 ({details})

## 열린 항목
- 각 Task Report 의 "후속 조치" 섹션에서 집계

## 내일 우선순위 (devils-advocate 관점)
- devils-advocate 섹션에서 추출한 권장 사항 최대 3개
```

### 저장
`docs/reports/daily/{YYYY-MM-DD}.md`

## Weekly Report

### 주차 계산
1. `Bash date +%G-W%V` 로 ISO 8601 주차 획득 (예: `2026-W16`)
2. 주의 시작일·종료일 계산 (월요일~일요일)

### 입력 수집
1. 해당 주의 Daily Report 들 `Glob` (`docs/reports/daily/YYYY-MM-DD.md` 최대 7개)
2. 각 Daily `Read` 로 파싱
3. 해당 주의 모든 Task Report 도 직접 수집 (Daily 누락분 대비)

### 출력 구조
```markdown
# 주간 업무 보고 — {YYYY}-W{week} ({start-date} ~ {end-date})

## 요약
- 완료 태스크: {count}개 ({preset breakdown})
- 주요 결정: {top 3}
- Audit 실패: {count}회 ({details})

## 재사용 현황
- 재사용 발생: {count}회
- 무시된 재사용 기회: {count}회

## Performer 사용 통계
- planner 호출: {count}회
- architect 호출: {count}회
- ...
- Gemini fallback: {count}회
- Ollama fallback: {count}회

## 주요 설계 결정 (Design Doc 변경 집계)
- docs/design/{feature}.md 에 추가된 섹션들

## 다음 주 우선순위
- Daily 의 "내일 우선순위" 섹션에서 중복 제거 후 집계
```

### 저장
`docs/reports/weekly/{YYYY}-W{week}.md`

## scribe 호출
실제 보고서 작성은 scribe Performer 에게 위임:
- 입력: 수집된 Task/Daily Report 집계
- 출력: 위 템플릿 슬롯을 채운 최종 Markdown
- 검증: 필수 섹션 누락, 참조 링크 깨짐 확인

scribe 는 **창작 금지**. 입력 데이터에 없는 정보를 지어내지 않음.

## 빈 데이터 대응
해당 날짜·주차에 Task Report 가 **0개** 인 경우:
- 사용자에게 알리고 생성 여부 확인:
  ```
  오늘({date}) 완료된 태스크가 없습니다. 빈 보고서를 생성할까요? (y/n)
  ```
- `y` 이면 "태스크 없음" 만 명시한 최소 보고서 생성
- `n` 이면 종료

## 보안
- 보고서에 시크릿 유입 금지. Task Report 에 시크릿이 있으면 마스킹 처리
- `SECURITY.md` 마스킹 키 적용

## 금지
- Task Report 원본 수정 금지 (집계만)
- 자동 생성 금지 — 사용자 명시 호출만
- scribe 가 의견 추가 금지 — 집계·요약만
