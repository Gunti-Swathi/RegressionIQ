# RegressionIQ

RegressionIQ is a regression test planning tool that analyzes code changes before any test generation happens. The idea is simple: not every Git diff needs new tests. Some commits only change comments or formatting, while others change logic, API behavior, or security-sensitive code.

The current version focuses on understanding those differences. It compares two commits, classifies the kind of change, estimates risk, traces affected code, and retrieves related test context. It does **not** generate tests yet, call an LLM, modify source code, or commit files automatically.

## Why This Project?

Raw Git diff is useful, but it only shows text changes. That is not always enough to decide whether behavior changed.

For example, these changes should usually not trigger new regression tests:

- comments
- whitespace
- formatting
- import reordering
- safe local variable renaming

But these changes usually should trigger deeper analysis:

- modified conditions
- changed return values
- function signature changes
- branch additions or removals
- changed function calls
- validation rule changes
- API behavior changes
- security-sensitive logic changes

RegressionIQ uses semantic analysis to separate noisy edits from behavior changes. After that, it traces what code may be affected and collects the test context that would be useful later.

## Methodology

RegressionIQ follows a staged analysis pipeline:

```text
Old/New Git commits
    -> changed Python files
    -> AST-based semantic parsing
    -> semantic diff signals
    -> change classification
    -> deterministic risk scoring
    -> test-generation decision
    -> impact graph analysis
    -> related test/context retrieval
```

This keeps the analysis explainable instead of sending a raw diff directly to a model.

## Phase 1: Semantic Change Analysis

Phase 1 answers:

```text
Did the code behavior actually change?
If yes, what kind of change is it?
How risky is it?
Should future regression tests be generated?
```

### Step-By-Step

1. **Compare two commits**

   RegressionIQ compares an old commit and a new commit:

   ```bash
   git diff OLD_COMMIT NEW_COMMIT
   ```

2. **Collect changed Python files**

   It identifies added, modified, and deleted Python files while ignoring irrelevant files such as caches, virtual environments, generated files, lock files, and binary assets.

3. **Load full old/new file contents**

   Instead of relying only on raw diff text, it loads both versions of each changed file:

   ```bash
   git show OLD_COMMIT:path/to/file.py
   git show NEW_COMMIT:path/to/file.py
   ```

4. **Parse code semantically**

   The code is parsed into AST structures so comments and formatting do not affect the semantic comparison.

5. **Extract semantic signals**

   The parser extracts functions, classes, imports, function signatures, return statements, conditions, and function calls.

6. **Classify the change**

   Rule-based classification identifies categories such as:

   - `formatting_change`
   - `import_change`
   - `refactor`
   - `logic_change`
   - `api_change`
   - `security_change`

7. **Score risk deterministically**

   Risk scoring is rule-based and explainable. For example, API changes, condition changes, return changes, and security-sensitive paths increase the risk score.

8. **Decide whether tests are needed**

   The decision engine returns whether future test generation should happen and what kind of validation is recommended.

## Phase 2: Impact Analysis And Context Retrieval

Phase 2 builds on Phase 1.

Phase 1 tells us **what changed**. Phase 2 tells us **what else is affected** and **which files are useful context**.

### Step-By-Step

1. **Build a repository graph**

   RegressionIQ scans Python files and builds module/function representations for the repository.

2. **Build a function-level call graph**

   It detects function calls such as:

   ```text
   checkout() -> validate_payment()
   checkout() -> create_invoice()
   ```

3. **Trace downstream impact**

   If `validate_payment()` changes, RegressionIQ finds functions that call it, such as `checkout()`.

4. **Map source code to related tests**

   It finds pytest files related to the changed or impacted code using naming conventions and code references.

5. **Retrieve repository context**

   It retrieves focused snippets such as:

   - changed function body
   - impacted caller function body
   - related pytest files
   - `conftest.py` fixtures

6. **Return a structured impact report**

   The output includes changed symbols, impacted functions/modules, related tests, and context snippets.

## Example Phase 2 Result

For the sample project, changing `src.payments.validate_payment` produces this impact result:

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

This is the main Phase 2 behavior: the tool does not stop at the edited file. It sees that `checkout()` depends on `validate_payment()` and pulls in the checkout/payment tests as useful context.

## Current Scope

RegressionIQ currently supports:

- Python repositories
- pytest-based projects
- local Git repositories
- single-repository analysis
- AST-based semantic comparison
- deterministic risk scoring
- CLI and JSON reports
- graph-based impact analysis
- repository-aware context retrieval
- local evaluation fixtures

## Installation

```bash
python3 -m pip install -e ".[dev]"
```

You can also run commands directly with:

```bash
python3 -m regressioniq.main COMMAND
```

## Analyze Semantic Changes

```bash
python3 -m regressioniq.main analyze \
  --old OLD_COMMIT \
  --new NEW_COMMIT \
  --repo /path/to/repo
```

JSON output:

```bash
python3 -m regressioniq.main analyze \
  --old OLD_COMMIT \
  --new NEW_COMMIT \
  --repo /path/to/repo \
  --json
```

## Analyze Impact

```bash
python3 -m regressioniq.main impact \
  --old OLD_COMMIT \
  --new NEW_COMMIT \
  --repo /path/to/repo
```

## Example Terminal Output

![RegressionIQ terminal output](docs/assets/output.jpeg)

## Machine-Readable Output

RegressionIQ also supports JSON output for CI/CD and future orchestration:

```json
{
  "path": "src/auth/tokens.py",
  "classification": "security_change",
  "confidence": 0.82,
  "risk_score": 100,
  "risk_band": "high",
  "generate_tests": true,
  "recommended_action": "generate_security_edge_case_tests"
}
```

## Evaluation

The Phase 1 evaluation dataset covers representative semantic-diff edge cases:

- comment-only changes
- formatting-only changes
- safe local variable renames
- return value changes
- condition changes
- API signature changes
- security-sensitive changes

Run evaluation:

```bash
python3 -m regressioniq.main eval
```

Current benchmark result:

```text
Cases: 7
Classification accuracy: 100.0%
Test trigger accuracy: 100.0%
Risk band accuracy: 100.0%
Changed function accuracy: 100.0%
```

Phase 2 is covered by tests that verify call graph construction, impacted function detection, related test mapping, and context retrieval.

Run all tests:

```bash
python3 -m pytest
```

## Sample Project

A small pytest project is included under:

```text
examples/sample_project/
```

It is used to validate Phase 2 impact analysis. The sample project contains payments, checkout, invoices, related tests, and fixtures. When payment validation changes, RegressionIQ should identify checkout as impacted and retrieve both payment and checkout tests.

## Project Structure

```text
regressioniq/
├── git/              # Git commit/file loading
├── parsing/          # Python AST parsing
├── semantic_diff/    # Semantic comparison engine
├── classifier/       # Change classification
├── risk/             # Rule-based risk scoring
├── decision/         # Test-generation decision logic
├── impact/           # Phase 2 graph and impact analysis
├── retrieval/        # Context retrieval
├── reporting/        # Text and JSON reports
└── evaluation/       # Evaluation runner
```

## Next Steps

Next, RegressionIQ will use this retrieved context to draft regression test suggestions for developer review. After that, the plan is to add test execution, repair feedback, coverage awareness, and GitHub Actions support.
