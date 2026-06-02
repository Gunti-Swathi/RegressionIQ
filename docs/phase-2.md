# Phase 2 Implementation Notes

## Responsibility

Phase 2 adds graph-based impact analysis and repository-aware context retrieval. It still does not generate tests or call an LLM.

## Main Command

```bash
regressioniq impact --old OLD_COMMIT --new NEW_COMMIT --repo /path/to/repo
```

## What It Builds

- Python module/import graph
- Function-level call graph
- Reverse caller lookup for changed functions
- Source-to-test mapping by naming and references
- Context snippets for changed functions, impacted callers, related tests, and fixtures

## Sample Fixture

`examples/sample_project/` is a tiny pytest project used to validate impact analysis. It contains:

- `src/payments.py::validate_payment`
- `src/checkout.py::checkout` calling `validate_payment`
- `src/invoices.py::create_invoice`
- related pytest files and a `conftest.py` fixture

When `validate_payment` changes, Phase 2 should identify `checkout` as impacted and retrieve both direct and downstream tests.
