from __future__ import annotations

from regressioniq.config import AppConfig
from regressioniq.models import ChangeClassification, ClassificationResult, RiskResult, SemanticFileChange


def _band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def score_risk(
    change: SemanticFileChange,
    classification: ClassificationResult,
    config: AppConfig | None = None,
) -> RiskResult:
    config = config or AppConfig()
    score = 0
    reasons: list[str] = []
    path_lower = change.path.lower()

    for fragment in config.risk.high_risk_paths:
        if fragment.lower() in path_lower:
            score += 30
            reasons.append(f"High-risk path fragment: {fragment}")
            break

    class_scores = {
        ChangeClassification.DOCS_CHANGE: 0,
        ChangeClassification.FORMATTING_CHANGE: 0,
        ChangeClassification.IMPORT_CHANGE: 8,
        ChangeClassification.REFACTOR: 12,
        ChangeClassification.LOGIC_CHANGE: 35,
        ChangeClassification.API_CHANGE: 45,
        ChangeClassification.SECURITY_CHANGE: 55,
        ChangeClassification.UNKNOWN_CHANGE: 25,
    }
    class_score = class_scores[classification.classification]
    score += class_score
    if class_score:
        reasons.append(f"Classification risk: {classification.classification.value}")

    signal_scores = {
        "condition_changed": 10,
        "return_changed": 10,
        "call_changed": 8,
        "body_changed": 8,
        "signature_changed": 20,
        "function_added": 10,
        "function_deleted": 15,
        "file_added": 10,
        "file_deleted": 20,
    }
    for signal, points in signal_scores.items():
        if signal in change.signals:
            score += points
            reasons.append(f"{signal}: +{points}")

    if len(change.changed_functions) > 3:
        score += 10
        reasons.append("Multiple changed functions.")

    final = min(score, 100)
    return RiskResult(score=final, band=_band(final), reasons=reasons)

