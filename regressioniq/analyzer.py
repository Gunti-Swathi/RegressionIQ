from __future__ import annotations

from regressioniq.classifier.change_classifier import classify_change
from regressioniq.config import AppConfig
from regressioniq.decision.engine import decide
from regressioniq.git.collector import collect_changed_files
from regressioniq.models import AnalysisReport, ChangedFile, FileAnalysis
from regressioniq.risk.scorer import score_risk
from regressioniq.semantic_diff.engine import analyze_file_change


def analyze_changed_files(
    files: list[ChangedFile],
    old_commit: str,
    new_commit: str,
    config: AppConfig | None = None,
) -> AnalysisReport:
    config = config or AppConfig()
    analyses: list[FileAnalysis] = []

    for file in files:
        semantic_change = analyze_file_change(file)
        classification = classify_change(semantic_change, config)
        risk = score_risk(semantic_change, classification, config)
        decision = decide(classification, risk)

        analyses.append(
            FileAnalysis(
                path=file.path,
                status=file.status,
                changed_functions=semantic_change.changed_functions,
                classification=classification.classification,
                confidence=classification.confidence,
                risk_score=risk.score,
                risk_band=risk.band,
                generate_tests=decision.generate_tests,
                recommended_action=decision.action,
                reason=decision.reason,
                evidence=[*classification.evidence, *risk.reasons],
            )
        )

    return AnalysisReport(
        old_commit=old_commit,
        new_commit=new_commit,
        files=analyses,
        summary={
            "files_analyzed": len(analyses),
            "files_requiring_tests": sum(1 for item in analyses if item.generate_tests),
            "max_risk_score": max((item.risk_score for item in analyses), default=0),
        },
    )


def analyze_commits(
    old_commit: str,
    new_commit: str,
    repo_path: str = ".",
    config: AppConfig | None = None,
) -> AnalysisReport:
    config = config or AppConfig()
    files = collect_changed_files(old_commit, new_commit, repo_path, config)
    return analyze_changed_files(files, old_commit, new_commit, config)

