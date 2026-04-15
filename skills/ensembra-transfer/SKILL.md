---
description: Ensembra 인수인계서 생성 스킬. 프로젝트를 다른 담당자에게 넘기기 위한 독립 문서를 만든다. 사용법 "/ensembra:transfer" (전체) 또는 "/ensembra:transfer <경로 또는 자연어>". 세션 중단용 handoff 와 다르며 handoff 는 외부 플러그인(d2-ops-handoff) 담당.
disable-model-invocation: false
---

# Ensembra Transfer

너(Claude Code)는 이 스킬이 호출되면 **`transfer` 프리셋**을 특수 파이프라인으로 실행한다.

## 중요 구분
- **Handoff** (세션 중단·재개 노트) 는 Ensembra 범위 밖. `d2-ops-handoff` 등 외부 플러그인이 담당
- **Transfer** (인수인계서) 는 프로젝트를 다른 담당자에게 넘기기 위한 독립 문서. Ensembra 담당

## 인자 파싱
`$ARGUMENTS` 를 scope 로 해석:
- **인자 없음**: 프로젝트 전체 → 파일명 `docs/transfer/{YYYY-MM-DD}-project.md`
- **경로** (`/` 포함): 해당 디렉토리 → 파일명 `docs/transfer/{YYYY-MM-DD}-{path-slug}.md`
- **자연어** (예: "결제 모듈"): planner 가 파일 집합 추론 → 파일명 `docs/transfer/{YYYY-MM-DD}-{slug}.md`

## 파이프라인

### Phase 0 — Wide Scan
일반 Deep Scan 대신 **전 레포** 범위 스캔:

1. **강제 10항목 전부 수행** (1~4, 9, 10 + 5~8):
   - 구조 파악: 전 레포 트리
   - 키워드 역추적: scope 관련 심볼
   - 호출 그래프: scope 파일 + 외부 호출 지점
   - 데이터 흐름: scope 전반
   - 테스트 맵: 전체 `tests/` 구조
   - git 히스토리: `git log -p --all --since="30 days ago"` (Bash)
   - 의존성: 전체 `package.json`/`pyproject.toml`/`Cargo.toml`
   - 설정: `.env.example`, `config/*`, `docker-compose.yml` 등
   - 공통 모듈 인벤토리: 전수
   - 프로젝트 문서 인벤토리: `docs/reports/tasks/` + `docs/reports/weekly/` + `docs/design/` 전수

2. TODO/FIXME/XXX 주석 전수 집계 (`Grep` 여러 패턴)

3. 결과를 Wide Context Snapshot 으로 압축

### Phase 1 — R1 only (섹션 분담)

**토론·반론·서명 없음**. 6 Performer 를 **병렬** 호출, 각자 담당 섹션만 작성:

| Performer | 섹션 |
|---|---|
| planner | 프로젝트 목적·목표, 마일스톤, 열린 요구사항 |
| architect | 아키텍처 개요, 모듈 경계, 설계 결정 이력 |
| developer | 빌드·실행·테스트·개발환경, 스타일, 기술 부채 |
| security | 시크릿 **경로만**, 외부 계정 소유권, 보안 이슈 |
| qa | 테스트 커버리지, 신뢰/불안정 영역, 플래키 테스트 |
| devils-advocate | **⚠ 주의할 함정**, 과거 시행착오, 반직관 지점, "고치지 마라" 영역 |

각 Performer 호출 시 Wide Context Snapshot 전달. Peer Signature 불필요.

### Phase 2, 3 — 건너뜀
파일 수정 없음 (읽기 전용). 감사 불필요.

### Phase 4 — scribe 특수 모드

scribe 가 6 섹션 결과를 받아 **표준 10섹션 템플릿**에 배치:

```markdown
# 프로젝트 인수인계서 — {scope}

**작성일**: {date}
**인계 범위**: {scope}
**작성 도구**: Ensembra transfer preset
**Ensembra 버전**: 0.1.0

## 0. 요약 (scribe, 3~5줄)
## 1. 프로젝트 목적·목표 (planner)
## 2. 아키텍처 (architect)
## 3. 빌드·실행·개발환경 (developer)
## 4. 보안·시크릿·계정 (security)
## 5. 테스트 현황 (qa)
## 6. ⚠ 주의할 함정 (devils-advocate)
## 7. 최근 변경 이력 (scribe, git log + Task Report 집계)
## 8. 열린 이슈·다음 단계 (scribe, TODO/FIXME 집계)
## 9. 참고 문서 (scribe)
## 10. 부록: 의존성 스냅샷 (scribe)
```

scribe 는:
- 섹션 간 **용어 일관화** (planner 가 "사용자", security 가 "client" 이면 통일)
- 목차 자동 생성
- 0번 요약 섹션 작성 (1분 안에 읽는 용도)
- 7, 8, 9, 10 번 부록을 Wide Scan 결과로 자동 집계

## 저장
- 파일 경로: `docs/transfer/{YYYY-MM-DD}-{scope}.md`
- 디렉토리 없으면 `mkdir -p`
- `Write` 로 저장

## 초기 프로젝트 대응
devils-advocate 섹션이 빈약할 수 있음 (과거 기록 부족). 이 경우:
> "해당 없음 — Task Report 누적 후 풍부해짐"

으로 자동 마크하고 경고 배지 출력.

## 진행률 표시
Wide Scan 이 길어질 수 있으므로 단계별 진행률 출력:
```
Phase 0 Wide Scan ... (1/3 완료)
Phase 1 섹션 작성 ... 2/6 Performer 완료
Phase 4 scribe 취합 ...
✅ docs/transfer/2026-04-15-project.md 생성 완료
```

## 보안
- 시크릿 **값** 절대 포함 금지. 경로만 기록
- `SECURITY.md` 마스킹 키 적용
- `.env`, `*.key`, `id_rsa*` 파일은 Wide Scan 에서 경로만 수집, `Read` 금지

## 금지
- 파일 수정 금지 (읽기 전용 작업)
- Phase 1 에서 토론·반론 시도 금지 (R1 only)
- scribe 가 섹션 내용 창작 금지 — 각 Performer 가 낸 내용만 취합
