# Example transcript — `/ensembra:run feature` on a calculator sandbox

This is a real (cleaned-up) transcript from an end-to-end pipeline run that added a `multiply` function to a simple calculator module.

## Setup

```bash
mkdir -p /tmp/ensembra-demo/src /tmp/ensembra-demo/tests
cd /tmp/ensembra-demo

cat > src/calculator.js <<'EOF'
function add(a, b) { return a + b; }
function subtract(a, b) { return a - b; }
module.exports = { add, subtract };
EOF

cat > tests/calculator.test.js <<'EOF'
const { add, subtract } = require('../src/calculator');
console.assert(add(2, 3) === 5, 'add failed');
console.assert(subtract(5, 3) === 2, 'subtract failed');
console.log('all tests passed');
EOF
```

## Command

```bash
claude --plugin-dir /path/to/ensembra --permission-mode acceptEdits \
  --print "/ensembra:run feature Add a multiply function to src/calculator.js that multiplies two numbers, and add a test for it. Follow the existing module.exports pattern and console.assert style. Keep the whole change minimal."
```

## Output (abridged)

```
## Ensembra Run — feature

**결과**: Pass (Audit 통과)
**합의율**: 100%
**Rework 횟수**: 0

### 변경 파일
- src/calculator.js (+4 -1) — multiply(a, b) 함수 추가, exports 확장
- tests/calculator.test.js (+2 -1) — import에 multiply 추가, assert 1건 추가

### 재사용 기회 평가
기존 calculator.js의 함수 정의 패턴(function X(a, b) { return a op b; })과
module.exports 객체 리터럴, 테스트의 console.assert 스타일을 100% 재사용.
신규 파일/모듈/의존성 생성 없음.

### 향후 개선 권장 (Audit QA 피드백)
- package.json에 "test": "node tests/calculator.test.js" 추가
- console.assert → node:assert 또는 테스트 프레임워크 전환 검토
```

## Result

**src/calculator.js**
```js
function add(a, b) { return a + b; }
function subtract(a, b) { return a - b; }
function multiply(a, b) { return a * b; }
module.exports = { add, subtract, multiply };
```

**tests/calculator.test.js**
```js
const { add, subtract, multiply } = require('../src/calculator');
console.assert(add(2, 3) === 5, 'add failed');
console.assert(subtract(5, 3) === 2, 'subtract failed');
console.assert(multiply(3, 4) === 12, 'multiply failed');
console.log('all tests passed');
```

## Verification

```bash
node tests/calculator.test.js
# all tests passed
```

## What Ensembra did well in this run

1. **Reuse-First worked**: Synthesis explicitly noted "100% reuse of existing function-definition pattern, module.exports literal, console.assert style. No new files/modules/dependencies."
2. **Audit override correct**: qa raised suggestions about `package.json` test script and `node:assert`, but correctly marked them as non-blocking improvements rather than regressions — pipeline proceeded to Pass.
3. **Phase 4 auto-skipped** for this trivial change — the scribe recognized the minimal scope didn't warrant a full Task Report. (For larger changes, it would have generated one.)

## What to try after this

- Add a divide function with a zero check: `/ensembra:run bugfix ...`
- Extract the inline pattern to a utility: `/ensembra:run refactor ...`
- Generate a handover doc for the sandbox: `/ensembra:transfer`
