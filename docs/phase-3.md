# Phase 3 Implementation Notes

## Responsibility

Phase 3 generates pytest regression test drafts from Phase 2 impact context and keeps them in a human review workflow.

It does not:

- auto-commit generated tests
- silently modify production code
- approve tests without a developer action
- execute or repair generated tests

## Gemini Configuration

Live generation uses Gemini through the optional Google SDK.

```bash
python3 -m pip install -e ".[llm]"
export GEMINI_API_KEY="your-api-key"
```

You can also create a local `.env` file in the RegressionIQ project root or analyzed repository:

```text
GEMINI_API_KEY=your-api-key
```

The default model is configurable and currently set by the CLI default:

```bash
regressioniq generate-tests --model gemini-2.5-flash
```

`GOOGLE_API_KEY` is also supported.

## Main Commands

Generate test drafts:

```bash
regressioniq generate-tests --old OLD_COMMIT --new NEW_COMMIT --repo /path/to/repo
```

Create local placeholder drafts without calling Gemini:

```bash
regressioniq generate-tests --old OLD_COMMIT --new NEW_COMMIT --repo /path/to/repo --dry-run
```

List review items:

```bash
regressioniq review-tests --repo /path/to/repo
```

Approve a generated test:

```bash
regressioniq approve GENERATED_TEST_ID --repo /path/to/repo
```

Reject or mark for repair:

```bash
regressioniq reject GENERATED_TEST_ID --repo /path/to/repo
regressioniq repair-needed GENERATED_TEST_ID --repo /path/to/repo
```

## Review Layout

Generated drafts are saved under:

```text
.regressioniq/reviews/
  tests/
  metadata/
```

Approved tests are copied into:

```text
tests/generated/
```

Each metadata file stores:

- review state
- changed file
- target test path
- Gemini model
- prompt
- generated pytest code
- related tests
- impacted functions

## Review States

- `generated`
- `approved`
- `rejected`
- `repair_needed`
