from __future__ import annotations

import json

from regressioniq.models import AnalysisReport


def report_to_json(report: AnalysisReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2)


def report_to_text(report: AnalysisReport) -> str:
    lines = [
        "RegressionIQ Phase 1 Analysis",
        "",
        f"Old commit: {report.old_commit}",
        f"New commit: {report.new_commit}",
        f"Changed files analyzed: {len(report.files)}",
        f"Files requiring generated tests: {report.summary.get('files_requiring_tests', 0)}",
        "",
    ]
    for file in report.files:
        lines.extend(
            [
                file.path,
                f"  status: {file.status.value}",
                f"  classification: {file.classification.value}",
                f"  confidence: {file.confidence:.2f}",
                f"  risk: {file.risk_score} ({file.risk_band})",
                f"  generate_tests: {str(file.generate_tests).lower()}",
                f"  action: {file.recommended_action.value}",
                f"  reason: {file.reason}",
            ]
        )
        if file.changed_functions:
            lines.append(f"  changed_functions: {', '.join(file.changed_functions)}")
        if file.evidence:
            lines.append("  evidence:")
            lines.extend(f"    - {item}" for item in file.evidence[:5])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

