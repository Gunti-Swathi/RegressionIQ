from __future__ import annotations

from regressioniq.config import AppConfig
from regressioniq.models import ChangeClassification, ClassificationResult, SemanticFileChange


def _contains_security_signal(change: SemanticFileChange, config: AppConfig) -> bool:
    searchable = " ".join([change.path, *change.signals, *change.evidence]).lower()
    return any(keyword.lower() in searchable for keyword in config.risk.security_keywords)


def classify_change(change: SemanticFileChange, config: AppConfig | None = None) -> ClassificationResult:
    config = config or AppConfig()
    signals = set(change.signals)

    if "syntax_error" in signals:
        return ClassificationResult(
            classification=ChangeClassification.UNKNOWN_CHANGE,
            confidence=0.35,
            reason="Syntax error prevented semantic classification.",
            evidence=change.evidence,
        )

    if _contains_security_signal(change, config) and signals - {"import_changed", "formatting_or_comment_only"}:
        return ClassificationResult(
            classification=ChangeClassification.SECURITY_CHANGE,
            confidence=0.82,
            reason="Security-sensitive path or keyword changed with semantic code impact.",
            evidence=change.evidence,
        )

    if "signature_changed" in signals:
        return ClassificationResult(
            classification=ChangeClassification.API_CHANGE,
            confidence=0.9,
            reason="Function signature changed.",
            evidence=change.evidence,
        )

    logic_signals = {
        "return_changed",
        "condition_changed",
        "call_changed",
        "body_changed",
        "function_added",
        "function_deleted",
        "logic_added",
        "logic_deleted",
        "file_added",
        "file_deleted",
    }
    if signals & logic_signals:
        return ClassificationResult(
            classification=ChangeClassification.LOGIC_CHANGE,
            confidence=0.86,
            reason="Behavior-affecting code structure changed.",
            evidence=change.evidence,
        )

    if signals == {"local_variable_rename"} or "local_variable_rename" in signals:
        return ClassificationResult(
            classification=ChangeClassification.REFACTOR,
            confidence=0.72,
            reason="Only safe local variable renaming was detected.",
            evidence=change.evidence,
        )

    if signals == {"import_changed"}:
        return ClassificationResult(
            classification=ChangeClassification.IMPORT_CHANGE,
            confidence=0.8,
            reason="Only import set changed.",
            evidence=change.evidence,
        )

    if signals == {"formatting_or_comment_only"}:
        return ClassificationResult(
            classification=ChangeClassification.FORMATTING_CHANGE,
            confidence=0.92,
            reason="Only formatting or comments changed.",
            evidence=change.evidence,
        )

    return ClassificationResult(
        classification=ChangeClassification.DOCS_CHANGE if not signals else ChangeClassification.UNKNOWN_CHANGE,
        confidence=0.65 if not signals else 0.45,
        reason="No semantic code changes detected." if not signals else "Unrecognized change pattern.",
        evidence=change.evidence,
    )

