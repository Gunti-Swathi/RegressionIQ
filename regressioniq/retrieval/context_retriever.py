from __future__ import annotations

from pathlib import Path

from regressioniq.impact.models import ContextSnippet, RepositoryGraph


def _read(repo_path: str, rel_path: str) -> str:
    return (Path(repo_path) / rel_path).read_text(encoding='utf-8')


def retrieve_context(
    repo_path: str,
    graph: RepositoryGraph,
    changed_symbols: list[str],
    impacted_symbols: list[str],
    related_tests: list[str],
    max_snippets: int = 12,
) -> list[ContextSnippet]:
    snippets: list[ContextSnippet] = []

    for symbol in changed_symbols:
        fn = graph.functions.get(symbol)
        if fn:
            snippets.append(
                ContextSnippet(
                    kind='changed_function',
                    path=fn.path,
                    symbol=symbol,
                    reason='Directly changed function from semantic diff.',
                    content=fn.source,
                )
            )

    for symbol in impacted_symbols:
        fn = graph.functions.get(symbol)
        if fn:
            snippets.append(
                ContextSnippet(
                    kind='impacted_function',
                    path=fn.path,
                    symbol=symbol,
                    reason='Function calls changed code and may need regression coverage.',
                    content=fn.source,
                )
            )

    for rel_path in related_tests:
        kind = 'fixture' if rel_path.endswith('conftest.py') else 'related_test'
        snippets.append(
            ContextSnippet(
                kind=kind,
                path=rel_path,
                symbol=None,
                reason='Existing pytest context related to changed or impacted code.',
                content=_read(repo_path, rel_path),
            )
        )

    return snippets[:max_snippets]
