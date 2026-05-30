from __future__ import annotations

import ast
from dataclasses import dataclass

from regressioniq.models import FunctionInfo, ModuleInfo


class _LocalNameNormalizer(ast.NodeTransformer):
    def __init__(self) -> None:
        self._names: dict[str, str] = {}

    def _mapped(self, name: str) -> str:
        if name not in self._names:
            self._names[name] = f"local_{len(self._names)}"
        return self._names[name]

    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(ast.Name(id=self._mapped(node.id), ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = self._mapped(node.arg)
        return node


@dataclass(frozen=True)
class ParsedFunction:
    qualname: str
    node: ast.FunctionDef | ast.AsyncFunctionDef


def _normalize_node(node: ast.AST, rename_locals: bool = False) -> str:
    cloned = ast.fix_missing_locations(ast.parse(ast.unparse(node)))
    target: ast.AST = cloned.body[0] if cloned.body else node
    if isinstance(target, (ast.FunctionDef, ast.AsyncFunctionDef)):
        target.decorator_list = []
        target.returns = None
        target.body = [
            statement
            for statement in target.body
            if not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
        ]
    if rename_locals:
        target = _LocalNameNormalizer().visit(target)
        ast.fix_missing_locations(target)
    return ast.dump(target, include_attributes=False)


def _expr_dump(node: ast.AST) -> str:
    return ast.dump(node, include_attributes=False)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ast.unparse(node)


def _function_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = [arg.arg for arg in node.args.posonlyargs + node.args.args]
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")
    args.extend(arg.arg for arg in node.args.kwonlyargs)
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")
    return args


def _function_info(qualname: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
    returns: list[str] = []
    conditions: list[str] = []
    calls: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Return) and child.value is not None:
            returns.append(_expr_dump(child.value))
        elif isinstance(child, (ast.If, ast.IfExp, ast.While)):
            conditions.append(_expr_dump(child.test))
        elif isinstance(child, ast.Call):
            calls.append(_call_name(child.func))

    return FunctionInfo(
        name=node.name,
        qualname=qualname,
        lineno=node.lineno,
        end_lineno=getattr(node, "end_lineno", node.lineno),
        args=_function_args(node),
        normalized_body=_normalize_node(node),
        normalized_body_renamed=_normalize_node(node, rename_locals=True),
        returns=returns,
        conditions=conditions,
        calls=calls,
    )


def _collect_functions(tree: ast.Module) -> dict[str, FunctionInfo]:
    functions: dict[str, FunctionInfo] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = _function_info(node.name, node)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qualname = f"{node.name}.{child.name}"
                    functions[qualname] = _function_info(qualname, child)
    return functions


def _collect_imports(tree: ast.Module) -> list[str]:
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.extend(f"{module}.{alias.name}" for alias in node.names)
    return sorted(imports)


def parse_python_module(path: str, content: str | None) -> ModuleInfo:
    if content is None:
        return ModuleInfo(path=path)
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return ModuleInfo(path=path, syntax_error=str(exc))

    return ModuleInfo(
        path=path,
        imports=_collect_imports(tree),
        functions=_collect_functions(tree),
        classes=[node.name for node in tree.body if isinstance(node, ast.ClassDef)],
    )

