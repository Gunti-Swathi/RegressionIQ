from __future__ import annotations

import ast
from pathlib import Path

from regressioniq.config import AppConfig
from regressioniq.impact.models import FunctionNode, ModuleNode, RepositoryGraph


def _skip_path(path: Path, root: Path, config: AppConfig) -> bool:
    rel = path.relative_to(root).as_posix()
    if not rel.endswith('.py'):
        return True
    return any(fragment in rel for fragment in config.risk.ignored_path_fragments)


def module_name(path: str) -> str:
    without_suffix = path[:-3] if path.endswith('.py') else path
    parts = [part for part in without_suffix.replace('\\', '/').split('/') if part]
    if parts and parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f'{parent}.{node.attr}' if parent else node.attr
    return None


class _FunctionVisitor(ast.NodeVisitor):
    def __init__(self, imported_names: dict[str, str], current_module: str) -> None:
        self.imported_names = imported_names
        self.current_module = current_module
        self.calls: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        raw = _call_name(node.func)
        if raw:
            self.calls.append(self._resolve(raw))
        self.generic_visit(node)

    def _resolve(self, raw: str) -> str:
        head = raw.split('.', 1)[0]
        if raw in self.imported_names:
            return self.imported_names[raw]
        if head in self.imported_names:
            tail = raw.split('.', 1)[1] if '.' in raw else ''
            return f'{self.imported_names[head]}.{tail}' if tail else self.imported_names[head]
        return f'{self.current_module}.{raw}' if '.' not in raw else raw


def _imports(tree: ast.Module) -> tuple[list[str], dict[str, str]]:
    imports: list[str] = []
    imported_names: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                imported_names[alias.asname or alias.name.split('.')[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            imports.append(module)
            for alias in node.names:
                if alias.name == '*':
                    continue
                imported_names[alias.asname or alias.name] = f'{module}.{alias.name}'
    return sorted(set(imports)), imported_names


def _iter_functions(tree: ast.Module):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield f'{node.name}.{child.name}', child


def build_repository_graph(repo_path: str, config: AppConfig | None = None) -> RepositoryGraph:
    config = config or AppConfig()
    root = Path(repo_path).resolve()
    graph = RepositoryGraph(root=str(root))

    for path in sorted(root.rglob('*.py')):
        if _skip_path(path, root, config):
            continue
        rel = path.relative_to(root).as_posix()
        content = path.read_text(encoding='utf-8')
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        module = module_name(rel)
        imports, imported_names = _imports(tree)
        module_node = ModuleNode(module=module, path=rel, imports=imports)
        graph.import_graph[module] = imports

        for qualname, node in _iter_functions(tree):
            visitor = _FunctionVisitor(imported_names, module)
            visitor.visit(node)
            source = ast.get_source_segment(content, node) or ''
            symbol = f'{module}.{qualname}'
            fn = FunctionNode(
                symbol=symbol,
                module=module,
                qualname=qualname,
                path=rel,
                lineno=node.lineno,
                end_lineno=getattr(node, 'end_lineno', node.lineno),
                source=source,
                calls=sorted(set(visitor.calls)),
            )
            module_node.functions[qualname] = fn
            graph.functions[symbol] = fn

        graph.modules[module] = module_node

    reverse: dict[str, set[str]] = {}
    for caller_symbol, fn in graph.functions.items():
        for callee in fn.calls:
            reverse.setdefault(callee, set()).add(caller_symbol)
    graph.reverse_calls = {key: sorted(value) for key, value in reverse.items()}
    return graph
