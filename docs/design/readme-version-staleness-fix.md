# Design — README version staleness fix

**Status**: Accepted (2026-04-17, applied)
**Scope**: Documentation-only, no code or architecture change

## 1. 문제

README.md 의 `## Verification status` 섹션 첫 줄은:
```
`v0.1.0` is fully verified at the structural and behavioral level:
```
v0.2.x ~ v0.8.0 릴리스를 거치는 동안 이 문장의 버전 식별자가 갱신되지 않아 "현재 릴리스는 검증되지 않은 것처럼" 보이는 문서 staleness 가 발생.

## 2. 설계 결정

단일 문자열 교체:

```diff
- `v0.1.0` is fully verified at the structural and behavioral level:
+ `v0.8.0` is fully verified at the structural and behavioral level:
```

### 대안 및 기각

| 대안 | 기각 사유 |
|---|---|
| 섹션 전체 재작성 (v0.8.0 기준 검증 항목 갱신) | 사용자 요청 "오타 1개 수정" 스코프 초과. 별도 run 으로 분리 |
| 버전 문자열을 CHANGELOG 최상단에서 자동 주입하는 메커니즘 도입 | 과잉 설계. 릴리스마다 수동 1라인 갱신이 현실적 |
| 섹션 삭제 | 검증 이력 정보 손실. 가치 있는 bullet 포함 (rework loop, halt-on-low-consensus 등) |

## 3. 영향 범위

- 사용자: 0 (외부 동작 변화 없음)
- CI/빌드: 0
- 문서 일관성: +1 (현 릴리스 태그와 정합화)

## 4. 본 설계서의 존재 이유

`refactor` preset 은 `design_doc: true` 이므로 문서 갱신도 refactor 로 분류되면 Design Doc 이 강제된다. 스코프가 작은 refactor 는 이처럼 **간결한 Design Doc** 을 남기는 것이 CONTRACT §15.2 의 의도.

## 5. 참고

- [Task Report](../reports/tasks/2026-04-17-readme-version-staleness-fix.md)
- [Request Spec](../requests/2026-04-17-readme-version-staleness-fix.md)
