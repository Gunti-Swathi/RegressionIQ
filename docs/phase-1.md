# Phase 1 Implementation Notes

## Responsibility

Phase 1 only understands semantic code changes, classifies them, estimates risk, and decides whether regression test generation is needed later.

It never:

- generates tests
- calls LLMs
- modifies source code
- commits files

## Main Command

```bash
regressioniq analyze --old OLD_COMMIT --new NEW_COMMIT
```

## Semantic Strategy

The analyzer loads full file contents from each commit with `git show`, parses both versions, and compares extracted semantic structures.

Comments and formatting disappear during AST normalization, so harmless text-only edits are skipped.

## Evaluation

The benchmark in `eval_cases/` checks:

- formatting-only changes
- comment changes
- safe local variable renames
- return value changes
- condition changes
- API signature changes
- security-sensitive logic changes

