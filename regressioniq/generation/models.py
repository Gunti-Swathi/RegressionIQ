from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReviewState(str, Enum):
    GENERATED = "generated"
    APPROVED = "approved"
    REJECTED = "rejected"
    REPAIR_NEEDED = "repair_needed"


class GeneratedTest(BaseModel):
    id: str
    changed_file: str
    target_path: str
    review_file: str
    metadata_file: str
    state: ReviewState = ReviewState.GENERATED
    model: str
    prompt: str
    test_code: str
    rationale: str
    related_tests: list[str] = Field(default_factory=list)
    impacted_functions: list[str] = Field(default_factory=list)
    created_at: str


class GenerationReport(BaseModel):
    old_commit: str
    new_commit: str
    model: str
    review_dir: str
    generated: list[GeneratedTest] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
