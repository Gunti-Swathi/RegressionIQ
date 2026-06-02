from __future__ import annotations

from regressioniq.analyzer import analyze_commits
from regressioniq.config import AppConfig
from regressioniq.impact.graph_builder import build_repository_graph, module_name
from regressioniq.impact.models import ImpactFileResult, ImpactReport
from regressioniq.impact.test_mapper import find_related_tests
from regressioniq.retrieval.context_retriever import retrieve_context


def _symbol_for(path: str, qualname: str) -> str:
    return f'{module_name(path)}.{qualname}'


def _walk_callers(graph, changed_symbols: list[str], max_depth: int = 2) -> list[str]:
    seen = set(changed_symbols)
    frontier = list(changed_symbols)
    impacted: list[str] = []
    for _ in range(max_depth):
        next_frontier: list[str] = []
        for symbol in frontier:
            for caller in graph.reverse_calls.get(symbol, []):
                if caller in seen:
                    continue
                seen.add(caller)
                caller_node = graph.functions.get(caller)
                if caller_node and caller_node.path.startswith('tests/'):
                    continue
                impacted.append(caller)
                next_frontier.append(caller)
        frontier = next_frontier
    return impacted


def analyze_impact(
    old_commit: str,
    new_commit: str,
    repo_path: str = '.',
    config: AppConfig | None = None,
) -> ImpactReport:
    config = config or AppConfig()
    phase1 = analyze_commits(old_commit, new_commit, repo_path, config)
    graph = build_repository_graph(repo_path, config)
    files: list[ImpactFileResult] = []

    for file in phase1.files:
        changed_symbols = [_symbol_for(file.path, name) for name in file.changed_functions]
        changed_symbols = [symbol for symbol in changed_symbols if symbol in graph.functions]
        impacted = _walk_callers(graph, changed_symbols)
        impacted_modules = sorted({graph.functions[symbol].module for symbol in impacted if symbol in graph.functions})
        changed_modules = sorted({module_name(file.path)})
        related_tests = find_related_tests(repo_path, graph, [*changed_symbols, *impacted], [*changed_modules, *impacted_modules])
        context = retrieve_context(repo_path, graph, changed_symbols, impacted, related_tests)

        files.append(
            ImpactFileResult(
                changed_file=file.path,
                changed_functions=file.changed_functions,
                directly_changed_symbols=changed_symbols,
                impacted_functions=impacted,
                impacted_modules=impacted_modules,
                related_tests=related_tests,
                context=context,
            )
        )

    return ImpactReport(
        old_commit=old_commit,
        new_commit=new_commit,
        files=files,
        summary={
            'files_analyzed': len(files),
            'changed_symbols': sum(len(item.directly_changed_symbols) for item in files),
            'impacted_functions': sum(len(item.impacted_functions) for item in files),
            'related_tests': len({test for item in files for test in item.related_tests}),
            'context_snippets': sum(len(item.context) for item in files),
        },
    )
