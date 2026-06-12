from __future__ import annotations

import json

from regressioniq.generation.models import GenerationReport, GeneratedTest
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



def impact_report_to_json(report) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2)


def impact_report_to_text(report) -> str:
    lines = [
        "RegressionIQ Phase 2 Impact Analysis",
        "",
        f"Old commit: {report.old_commit}",
        f"New commit: {report.new_commit}",
        f"Changed files analyzed: {report.summary.get('files_analyzed', 0)}",
        f"Impacted functions found: {report.summary.get('impacted_functions', 0)}",
        f"Related tests found: {report.summary.get('related_tests', 0)}",
        f"Context snippets retrieved: {report.summary.get('context_snippets', 0)}",
        "",
    ]
    for file in report.files:
        lines.append(file.changed_file)
        if file.directly_changed_symbols:
            lines.append(f"  changed_symbols: {', '.join(file.directly_changed_symbols)}")
        if file.impacted_functions:
            lines.append(f"  impacted_functions: {', '.join(file.impacted_functions)}")
        if file.impacted_modules:
            lines.append(f"  impacted_modules: {', '.join(file.impacted_modules)}")
        if file.related_tests:
            lines.append(f"  related_tests: {', '.join(file.related_tests)}")
        if file.context:
            lines.append("  context:")
            for snippet in file.context[:6]:
                symbol = f"::{snippet.symbol}" if snippet.symbol else ""
                lines.append(f"    - {snippet.kind}: {snippet.path}{symbol}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generation_report_to_json(report: GenerationReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2)


def generation_report_to_text(report: GenerationReport) -> str:
    lines = [
        "RegressionIQ Phase 3 Test Generation",
        "",
        f"Old commit: {report.old_commit}",
        f"New commit: {report.new_commit}",
        f"Model: {report.model}",
        f"Review dir: {report.review_dir}",
        f"Generated tests: {report.summary.get('tests_generated', 0)}",
        "",
    ]
    for item in report.generated:
        lines.extend(_generated_test_lines(item))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def review_items_to_text(items: list[GeneratedTest]) -> str:
    lines = ["RegressionIQ Phase 3 Review Queue", ""]
    if not items:
        lines.append("No generated tests are waiting for review.")
        return "\n".join(lines).rstrip() + "\n"
    for item in items:
        lines.extend(_generated_test_lines(item))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _generated_test_lines(item: GeneratedTest) -> list[str]:
    lines = [
        item.id,
        f"  state: {item.state.value}",
        f"  changed_file: {item.changed_file}",
        f"  review_file: {item.review_file}",
        f"  target_path: {item.target_path}",
        f"  model: {item.model}",
    ]
    if item.impacted_functions:
        lines.append(f"  impacted_functions: {', '.join(item.impacted_functions)}")
    if item.related_tests:
        lines.append(f"  related_tests: {', '.join(item.related_tests)}")
    return lines
