from __future__ import annotations

from regressioniq.impact.models import ImpactFileResult


MAX_SNIPPET_CHARS = 1800


def _clip(value: str, limit: int = MAX_SNIPPET_CHARS) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n# ... clipped for prompt size ..."


def build_generation_prompt(file: ImpactFileResult) -> str:
    context_blocks: list[str] = []
    for index, snippet in enumerate(file.context, start=1):
        symbol = f" symbol={snippet.symbol}" if snippet.symbol else ""
        context_blocks.append(
            "\n".join(
                [
                    f"### Context {index}: {snippet.kind} path={snippet.path}{symbol}",
                    f"Reason: {snippet.reason}",
                    "```python",
                    _clip(snippet.content),
                    "```",
                ]
            )
        )

    changed_functions = ", ".join(file.changed_functions) or "unknown"
    impacted = ", ".join(file.impacted_functions) or "none"
    related_tests = ", ".join(file.related_tests) or "none"

    return "\n\n".join(
        [
            "You are RegressionIQ, generating focused pytest regression tests for a Python repository.",
            "Return only valid pytest code. Do not include markdown fences or commentary.",
            "Prefer small, deterministic tests that reuse existing fixtures and style from the context.",
            "Do not modify production code. Do not invent external services or dependencies.",
            "Cover the behavior change and any impacted caller behavior when context supports it.",
            f"Changed file: {file.changed_file}",
            f"Changed functions: {changed_functions}",
            f"Impacted functions: {impacted}",
            f"Related tests: {related_tests}",
            *context_blocks,
        ]
    )


def extract_python_code(response: str) -> str:
    stripped = response.strip()
    if "```" not in stripped:
        return stripped + "\n"

    parts = stripped.split("```")
    for index, part in enumerate(parts):
        block = part.strip()
        if index % 2 == 1:
            if block.startswith("python"):
                block = block.removeprefix("python").strip()
            return block.rstrip() + "\n"
    return stripped + "\n"
