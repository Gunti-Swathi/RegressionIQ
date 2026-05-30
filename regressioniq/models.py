from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FileStatus(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


class ChangeClassification(str, Enum):
    DOCS_CHANGE = "docs_change"
    FORMATTING_CHANGE = "formatting_change"
    IMPORT_CHANGE = "import_change"
    REFACTOR = "refactor"
    LOGIC_CHANGE = "logic_change"
    API_CHANGE = "api_change"
    SECURITY_CHANGE = "security_change"
    UNKNOWN_CHANGE = "unknown_change"


class RecommendedAction(str, Enum):
    SKIP = "skip"
    MINIMAL_VALIDATION = "minimal_validation"
    GENERATE_UNIT_REGRESSION = "generate_unit_regression_tests"
    GENERATE_INTEGRATION = "generate_integration_tests"
    GENERATE_SECURITY_EDGE = "generate_security_edge_case_tests"
    HUMAN_REVIEW = "human_review"


class ChangedFile(BaseModel):
    path: str
    status: FileStatus
    old_content: str | None = None
    new_content: str | None = None


class FunctionInfo(BaseModel):
    name: str
    qualname: str
    lineno: int
    end_lineno: int
    args: list[str] = Field(default_factory=list)
    normalized_body: str
    normalized_body_renamed: str
    returns: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    calls: list[str] = Field(default_factory=list)


class ModuleInfo(BaseModel):
    path: str
    imports: list[str] = Field(default_factory=list)
    functions: dict[str, FunctionInfo] = Field(default_factory=dict)
    classes: list[str] = Field(default_factory=list)
    syntax_error: str | None = None


class SemanticFileChange(BaseModel):
    path: str
    status: FileStatus
    changed_functions: list[str] = Field(default_factory=list)
    added_functions: list[str] = Field(default_factory=list)
    deleted_functions: list[str] = Field(default_factory=list)
    changed_classes: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    old_parse_error: str | None = None
    new_parse_error: str | None = None


class ClassificationResult(BaseModel):
    classification: ChangeClassification
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence: list[str] = Field(default_factory=list)


class RiskResult(BaseModel):
    score: int = Field(ge=0, le=100)
    band: str
    reasons: list[str] = Field(default_factory=list)


class DecisionResult(BaseModel):
    generate_tests: bool
    action: RecommendedAction
    reason: str


class FileAnalysis(BaseModel):
    path: str
    status: FileStatus
    changed_functions: list[str] = Field(default_factory=list)
    classification: ChangeClassification
    confidence: float
    risk_score: int
    risk_band: str
    generate_tests: bool
    recommended_action: RecommendedAction
    reason: str
    evidence: list[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    old_commit: str
    new_commit: str
    files: list[FileAnalysis]
    summary: dict[str, Any] = Field(default_factory=dict)

