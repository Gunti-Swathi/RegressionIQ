from __future__ import annotations

from regressioniq.models import ChangeClassification, ClassificationResult, DecisionResult, RecommendedAction, RiskResult


def decide(classification: ClassificationResult, risk: RiskResult) -> DecisionResult:
    kind = classification.classification

    if kind in {ChangeClassification.DOCS_CHANGE, ChangeClassification.FORMATTING_CHANGE}:
        return DecisionResult(
            generate_tests=False,
            action=RecommendedAction.SKIP,
            reason="No semantic behavior change detected.",
        )
    if kind in {ChangeClassification.IMPORT_CHANGE, ChangeClassification.REFACTOR}:
        return DecisionResult(
            generate_tests=False,
            action=RecommendedAction.MINIMAL_VALIDATION,
            reason="Change appears low-risk; run existing validation only.",
        )
    if kind is ChangeClassification.SECURITY_CHANGE:
        return DecisionResult(
            generate_tests=True,
            action=RecommendedAction.GENERATE_SECURITY_EDGE,
            reason="Security-sensitive semantic change detected.",
        )
    if kind is ChangeClassification.API_CHANGE:
        return DecisionResult(
            generate_tests=True,
            action=RecommendedAction.GENERATE_INTEGRATION,
            reason="API contract change detected.",
        )
    if kind is ChangeClassification.LOGIC_CHANGE:
        return DecisionResult(
            generate_tests=True,
            action=RecommendedAction.GENERATE_UNIT_REGRESSION,
            reason="Behavior-affecting logic change detected.",
        )

    return DecisionResult(
        generate_tests=risk.score >= 35,
        action=RecommendedAction.HUMAN_REVIEW,
        reason="Classification confidence is limited; human review recommended.",
    )

