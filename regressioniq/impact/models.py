from __future__ import annotations

from pydantic import BaseModel, Field


class FunctionNode(BaseModel):
    symbol: str
    module: str
    qualname: str
    path: str
    lineno: int
    end_lineno: int
    source: str
    calls: list[str] = Field(default_factory=list)


class ModuleNode(BaseModel):
    module: str
    path: str
    imports: list[str] = Field(default_factory=list)
    functions: dict[str, FunctionNode] = Field(default_factory=dict)


class RepositoryGraph(BaseModel):
    root: str
    modules: dict[str, ModuleNode] = Field(default_factory=dict)
    functions: dict[str, FunctionNode] = Field(default_factory=dict)
    reverse_calls: dict[str, list[str]] = Field(default_factory=dict)
    import_graph: dict[str, list[str]] = Field(default_factory=dict)


class ContextSnippet(BaseModel):
    kind: str
    path: str
    symbol: str | None = None
    reason: str
    content: str


class ImpactFileResult(BaseModel):
    changed_file: str
    changed_functions: list[str] = Field(default_factory=list)
    directly_changed_symbols: list[str] = Field(default_factory=list)
    impacted_functions: list[str] = Field(default_factory=list)
    impacted_modules: list[str] = Field(default_factory=list)
    related_tests: list[str] = Field(default_factory=list)
    context: list[ContextSnippet] = Field(default_factory=list)


class ImpactReport(BaseModel):
    old_commit: str
    new_commit: str
    files: list[ImpactFileResult]
    summary: dict[str, int] = Field(default_factory=dict)
