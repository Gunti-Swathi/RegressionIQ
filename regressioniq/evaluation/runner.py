from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from pydantic import BaseModel, Field

from regressioniq.analyzer import analyze_changed_files
from regressioniq.config import AppConfig
from regressioniq.models import ChangedFile, FileStatus


class EvalExpected(BaseModel):
    classification: str
    changed_functions: list[str] = Field(default_factory=list)
    generate_tests: bool
    risk_band: str | None = None


class EvalCase(BaseModel):
    name: str
    path: str = "example.py"
    status: FileStatus = FileStatus.MODIFIED
    old_content: str | None = None
    new_content: str | None = None
    expected: EvalExpected


def _load_cases(cases_dir: str) -> list[EvalCase]:
    root = Path(cases_dir)
    cases = []
    for path in sorted(root.glob("*.json")):
        cases.append(EvalCase.model_validate_json(path.read_text(encoding="utf-8")))
    return cases


def run_evaluation(cases_dir: str = "eval_cases", config: AppConfig | None = None) -> dict[str, Any]:
    config = config or AppConfig()
    cases = _load_cases(cases_dir)
    results: list[dict[str, Any]] = []

    for case in cases:
        report = analyze_changed_files(
            [
                ChangedFile(
                    path=case.path,
                    status=case.status,
                    old_content=case.old_content,
                    new_content=case.new_content,
                )
            ],
            old_commit=f"eval:{case.name}:old",
            new_commit=f"eval:{case.name}:new",
            config=config,
        )
        actual = report.files[0]
        expected_functions = set(case.expected.changed_functions)
        actual_functions = set(actual.changed_functions)
        result = {
            "name": case.name,
            "classification_ok": actual.classification.value == case.expected.classification,
            "trigger_ok": actual.generate_tests == case.expected.generate_tests,
            "risk_band_ok": case.expected.risk_band is None or actual.risk_band == case.expected.risk_band,
            "changed_functions_ok": expected_functions.issubset(actual_functions),
            "expected": case.expected.model_dump(),
            "actual": actual.model_dump(mode="json"),
        }
        results.append(result)

    def pct(key: str) -> float:
        if not results:
            return 0.0
        return round(mean(1.0 if item[key] else 0.0 for item in results) * 100, 2)

    return {
        "cases": len(results),
        "classification_accuracy": pct("classification_ok"),
        "test_trigger_accuracy": pct("trigger_ok"),
        "risk_band_accuracy": pct("risk_band_ok"),
        "changed_function_accuracy": pct("changed_functions_ok"),
        "results": results,
    }


def evaluation_to_text(metrics: dict[str, Any]) -> str:
    lines = [
        "RegressionIQ Phase 1 Evaluation",
        "",
        f"Cases: {metrics['cases']}",
        f"Classification accuracy: {metrics['classification_accuracy']}%",
        f"Test trigger accuracy: {metrics['test_trigger_accuracy']}%",
        f"Risk band accuracy: {metrics['risk_band_accuracy']}%",
        f"Changed function accuracy: {metrics['changed_function_accuracy']}%",
    ]
    failures = [
        item
        for item in metrics["results"]
        if not all(
            [
                item["classification_ok"],
                item["trigger_ok"],
                item["risk_band_ok"],
                item["changed_functions_ok"],
            ]
        )
    ]
    if failures:
        lines.extend(["", "Failures:"])
        for item in failures:
            lines.append(
                f"- {item['name']}: expected {json.dumps(item['expected'])}, "
                f"got classification={item['actual']['classification']}, "
                f"generate_tests={item['actual']['generate_tests']}, "
                f"risk_band={item['actual']['risk_band']}"
            )
    return "\n".join(lines) + "\n"

