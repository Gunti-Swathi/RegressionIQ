from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class RiskConfig(BaseModel):
    high_risk_paths: list[str] = Field(
        default_factory=lambda: [
            "auth",
            "authentication",
            "permission",
            "access",
            "payment",
            "billing",
            "security",
            "api",
            "db",
            "database",
        ]
    )
    security_keywords: list[str] = Field(
        default_factory=lambda: [
            "token",
            "password",
            "secret",
            "permission",
            "role",
            "auth",
            "jwt",
            "csrf",
            "access",
        ]
    )
    ignored_path_fragments: list[str] = Field(
        default_factory=lambda: [
            ".venv/",
            "venv/",
            "__pycache__/",
            ".regressioniq/",
            ".git/",
            "node_modules/",
            "dist/",
            "build/",
            ".pytest_cache/",
        ]
    )
    ignored_suffixes: list[str] = Field(
        default_factory=lambda: [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".lock",
            ".pyc",
            ".so",
            ".zip",
        ]
    )


class AppConfig(BaseModel):
    language: str = "python"
    test_framework: str = "pytest"
    risk: RiskConfig = Field(default_factory=RiskConfig)


def load_config(path: str | None = None) -> AppConfig:
    if path is None:
        default = Path("regressioniq.json")
        if not default.exists():
            return AppConfig()
        path = str(default)

    config_path = Path(path)
    if not config_path.exists():
        return AppConfig()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)
