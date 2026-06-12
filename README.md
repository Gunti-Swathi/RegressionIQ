# RegressionIQ

RegressionIQ is a regression test planning tool that analyzes code changes before test generation happens. The goal is to avoid generating tests for every Git diff and instead focus on changes that can actually affect behavior.

Right now, the project supports Python repositories that use pytest. It compares two commits, understands the semantic change, classifies the risk, traces affected code, retrieves related test context, and can draft pytest regression tests through Gemini for human review. It does not approve, execute, repair, or commit generated tests automatically.

## Problem Statement

In most projects, every pull request contains a mix of changes. Some changes are important, and some are not.

For example, these changes usually do not need new regression tests:

- comments
- whitespace
- formatting
- import reordering
- safe local variable renaming

But these changes can affect behavior and should be reviewed more carefully:

- changed conditions
- changed return values
- changed function signatures
- new or removed branches
- changed function calls
- changed validation rules
- API behavior changes
- security-sensitive changes

A normal Git diff only shows text differences. It does not tell us whether the logic of the program changed. Because of that, a test generation system based only on raw diff can easily become noisy and generate low-value tests.

RegressionIQ tries to solve this by looking at code structure first.

## Goal

The goal of RegressionIQ is to build the analysis layer for an AI-powered regression test generation system.

Before any test is generated, the system should answer:

```text
What changed?
Did behavior change?
What type of change is it?
How risky is it?
Which functions or modules are affected?
Which existing tests and fixtures are useful context?
```

This makes the later test generation step more focused and easier to review.

## Approach

RegressionIQ follows this pipeline:

```text
Old/New Git commits
    -> changed Python files
    -> full old/new file loading
    -> AST-based semantic parsing
    -> semantic diff signals
    -> change classification
    -> deterministic risk scoring
    -> test-generation decision
    -> impact analysis
    -> related test/context retrieval
    -> Gemini pytest draft generation
    -> human review and approval
```

The important design choice is that the tool does not rely only on raw Git diff text. It loads the old and new versions of each changed Python file, parses them, and compares their code structure.

## Phase 1: Semantic Change Analysis

Phase 1 focuses on understanding whether a code change is meaningful.

### What Phase 1 Does

1. **Compares two commits**

   ```bash
   git diff OLD_COMMIT NEW_COMMIT
   ```

2. **Finds changed Python files**

   It detects added, modified, and deleted Python files.

3. **Loads old and new file versions**

   ```bash
   git show OLD_COMMIT:path/to/file.py
   git show NEW_COMMIT:path/to/file.py
   ```

4. **Parses code using AST**

   This helps ignore comments and formatting because they do not change the parsed structure.

5. **Extracts semantic signals**

   The parser extracts functions, classes, imports, function signatures, return statements, conditions, and function calls.

6. **Classifies the change**

   Current classifications include:

   - `formatting_change`
   - `import_change`
   - `refactor`
   - `logic_change`
   - `api_change`
   - `security_change`
   - `unknown_change`

7. **Scores risk**

   Risk scoring is deterministic and rule-based. For example, API changes, condition changes, return changes, and security-sensitive paths increase the risk score.

8. **Decides whether future tests are needed**

   Phase 1 does not generate tests. It only decides whether test generation would be useful later.

### Phase 1 Example

Using the sample project, the old commit allows any positive payment amount. The new commit changes `validate_payment()` so the amount must be at least `10`.

Phase 1 detects this as a behavior change in `src/payments.py`:

```json
{
  "path": "src/payments.py",
  "status": "modified",
  "changed_functions": [
    "validate_payment"
  ],
  "classification": "logic_change",
  "confidence": 0.86,
  "risk_score": 83,
  "risk_band": "high",
  "generate_tests": true,
  "recommended_action": "generate_unit_regression_tests",
  "reason": "Behavior-affecting logic change detected.",
  "evidence": [
    "validate_payment: condition_changed, body_changed",
    "High-risk path fragment: payment",
    "Classification risk: logic_change",
    "condition_changed: +10",
    "body_changed: +8"
  ]
}
```

### Phase 1 Evaluation

The evaluation dataset includes common edge cases:

- comment-only changes
- formatting-only changes
- safe local variable renames
- return value changes
- condition changes
- API signature changes
- security-sensitive changes

Current evaluation result:

```text
Cases: 7
Classification accuracy: 100.0%
Test trigger accuracy: 100.0%
Risk band accuracy: 100.0%
Changed function accuracy: 100.0%
```

## Phase 2: Impact Analysis And Context Retrieval

Phase 2 builds on Phase 1.

Phase 1 tells us what changed. Phase 2 tells us what else is affected by that change.

For example, if `validate_payment()` changes, the tool should also identify that `checkout()` may be affected if it calls `validate_payment()`.

### What Phase 2 Adds

1. **Repository graph**

   The tool scans Python files and builds module/function representations.

2. **Function-level call graph**

   It tracks function relationships such as:

   ```text
   checkout() -> validate_payment()
   checkout() -> create_invoice()
   ```

3. **Downstream impact tracing**

   If a changed function is called by another function, the caller is marked as impacted.

4. **Related test mapping**

   The tool finds pytest files related to the changed or impacted code using file names and code references.

5. **Context retrieval**

   It retrieves useful context for future test generation:

   - changed function body
   - impacted caller function body
   - related pytest files
   - `conftest.py` fixtures

### Phase 2 Example

In the sample project, `checkout()` calls `validate_payment()`.

When `src.payments.validate_payment` changes, RegressionIQ returns:

```text
src/payments.py
  changed_symbols: src.payments.validate_payment
  impacted_functions: src.checkout.checkout
  impacted_modules: src.checkout
  related_tests: tests/conftest.py, tests/test_checkout.py, tests/test_payments.py
  context:
    - changed_function: src/payments.py::src.payments.validate_payment
    - impacted_function: src/checkout.py::src.checkout.checkout
    - fixture: tests/conftest.py
    - related_test: tests/test_checkout.py
    - related_test: tests/test_payments.py
```

This is useful because future test generation should not only look at the edited file. It should also look at the code that depends on it and the tests that already cover that area.

## Phase 3: Gemini Test Generation And Human Review

Phase 3 turns the Phase 2 context into pytest regression test drafts.

The tool sends changed functions, impacted callers, related tests, and fixtures to Gemini, then saves the generated pytest code into a review area instead of directly adding it to the main test suite.

### What Phase 3 Adds

1. **Gemini-backed generation**

   Live generation uses `GEMINI_API_KEY` or `GOOGLE_API_KEY` and the optional Google Gen AI SDK.

2. **pytest-only output**

   Prompts instruct Gemini to return focused pytest code that follows the repository context.

3. **Review queue**

   Generated tests are stored under:

   ```text
   .regressioniq/reviews/
   ```

4. **Human approval states**

   Review items can be:

   - `generated`
   - `approved`
   - `rejected`
   - `repair_needed`

5. **Approval command**

   Approved drafts are copied into:

   ```text
   tests/generated/
   ```

### Phase 3 Example

```bash
python3 -m regressioniq.main generate-tests \
  --old OLD_COMMIT \
  --new NEW_COMMIT \
  --repo /path/to/repo \
  --model gemini-2.5-flash
```

For local demos without using Gemini credits:

```bash
python3 -m regressioniq.main generate-tests \
  --old OLD_COMMIT \
  --new NEW_COMMIT \
  --repo /path/to/repo \
  --dry-run
```

Review and approve:

```bash
python3 -m regressioniq.main review-tests --repo /path/to/repo
python3 -m regressioniq.main approve GENERATED_TEST_ID --repo /path/to/repo
```

## Example Terminal Output

![RegressionIQ terminal output](docs/assets/output.jpeg)

## Current Scope

RegressionIQ currently supports:

- Python repositories
- pytest-based projects
- local Git repositories
- single-repository analysis
- AST-based semantic comparison
- deterministic risk scoring
- CLI and JSON output
- graph-based impact analysis
- related test/context retrieval
- Gemini-backed pytest draft generation
- human approval workflow

## Installation

```bash
python3 -m pip install -e ".[dev]"
```

For live Gemini generation:

```bash
python3 -m pip install -e ".[dev,llm]"
export GEMINI_API_KEY="your-api-key"
```

You can also put the key in a `.env` file in the RegressionIQ project root or the repository being analyzed:

```text
GEMINI_API_KEY=your-api-key
```

You can also run the tool directly with:

```bash
python3 -m regressioniq.main COMMAND
```

## Commands

Analyze semantic changes:

```bash
python3 -m regressioniq.main analyze \
  --old OLD_COMMIT \
  --new NEW_COMMIT \
  --repo /path/to/repo
```

Analyze impact and retrieve context:

```bash
python3 -m regressioniq.main impact \
  --old OLD_COMMIT \
  --new NEW_COMMIT \
  --repo /path/to/repo
```

Generate pytest regression drafts:

```bash
python3 -m regressioniq.main generate-tests \
  --old OLD_COMMIT \
  --new NEW_COMMIT \
  --repo /path/to/repo
```

Review generated drafts:

```bash
python3 -m regressioniq.main review-tests --repo /path/to/repo
```

Approve a generated draft:

```bash
python3 -m regressioniq.main approve GENERATED_TEST_ID --repo /path/to/repo
```

Run evaluation:

```bash
python3 -m regressioniq.main eval
```

Run tests:

```bash
python3 -m pytest
```

## Sample Project

A small pytest project is included under:

```text
examples/sample_project/
```

It contains:

- `src/payments.py`
- `src/checkout.py`
- `src/invoices.py`
- `tests/test_payments.py`
- `tests/test_checkout.py`
- `tests/conftest.py`

This sample project is used to check whether Phase 2 correctly detects downstream impact and retrieves related tests.

## Project Structure

```text
regressioniq/
├── git/              # Git commit and file loading
├── parsing/          # Python AST parsing
├── semantic_diff/    # Semantic comparison
├── classifier/       # Change classification
├── risk/             # Rule-based risk scoring
├── decision/         # Test-generation decision logic
├── impact/           # Impact graph and dependency tracing
├── retrieval/        # Context retrieval
├── generation/       # Gemini pytest generation and review storage
├── reporting/        # Text and JSON reports
└── evaluation/       # Evaluation runner
```

## Conclusion

So far, RegressionIQ can identify whether a code change is meaningful, classify the type of change, estimate risk, find affected downstream functions, retrieve related tests and fixtures, and generate pytest drafts for developer review. This creates a selective test generation workflow that is easier to inspect before adoption.

## Next Steps

The next step is to add test execution, feedback-based repair, coverage awareness, and GitHub Actions support.
