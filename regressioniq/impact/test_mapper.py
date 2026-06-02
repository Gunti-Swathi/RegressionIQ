from __future__ import annotations

from pathlib import Path

from regressioniq.impact.models import FunctionNode, RepositoryGraph


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return ''


def find_related_tests(repo_path: str, graph: RepositoryGraph, symbols: list[str], modules: list[str]) -> list[str]:
    root = Path(repo_path).resolve()
    tests_root = root / 'tests'
    if not tests_root.exists():
        return []

    function_names = {symbol.rsplit('.', 1)[-1] for symbol in symbols}
    module_leafs = {module.rsplit('.', 1)[-1] for module in modules if module}
    source_paths = set()
    for symbol in symbols:
        fn = graph.functions.get(symbol)
        if fn:
            source_paths.add(Path(fn.path).stem)

    related: set[str] = set()
    for test_file in sorted(tests_root.rglob('test_*.py')):
        rel = test_file.relative_to(root).as_posix()
        stem = test_file.stem.removeprefix('test_')
        content = _read(test_file)
        if stem in module_leafs or stem in source_paths:
            related.add(rel)
            continue
        if any(name in content for name in function_names):
            related.add(rel)
            continue
        if any(module in content for module in modules):
            related.add(rel)
            continue

    conftest = tests_root / 'conftest.py'
    if conftest.exists() and related:
        related.add(conftest.relative_to(root).as_posix())
    return sorted(related)
