from __future__ import annotations

import argparse
import json
import sys

from regressioniq.analyzer import analyze_commits
from regressioniq.config import load_config
from regressioniq.evaluation.runner import evaluation_to_text, run_evaluation
from regressioniq.impact.analyzer import analyze_impact
from regressioniq.git.collector import GitError
from regressioniq.reporting.reporter import impact_report_to_json, impact_report_to_text, report_to_json, report_to_text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="regressioniq", description="Semantic regression impact analysis.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze semantic changes between two commits.")
    analyze.add_argument("--old", required=True, help="Old/base commit SHA or ref.")
    analyze.add_argument("--new", required=True, help="New/head commit SHA or ref.")
    analyze.add_argument("--repo", default=".", help="Path to the local Git repository.")
    analyze.add_argument("--config", default=None, help="Optional JSON config path.")
    analyze.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    analyze.add_argument("--output", default=None, help="Optional path to write JSON report.")

    impact = subparsers.add_parser("impact", help="Analyze downstream impact and retrieve repository context.")
    impact.add_argument("--old", required=True, help="Old/base commit SHA or ref.")
    impact.add_argument("--new", required=True, help="New/head commit SHA or ref.")
    impact.add_argument("--repo", default=".", help="Path to the local Git repository.")
    impact.add_argument("--config", default=None, help="Optional JSON config path.")
    impact.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    impact.add_argument("--output", default=None, help="Optional path to write JSON report.")

    evaluate = subparsers.add_parser("eval", help="Run the Phase 1 evaluation benchmark.")
    evaluate.add_argument("--cases", default="eval_cases", help="Directory containing JSON eval cases.")
    evaluate.add_argument("--config", default=None, help="Optional JSON config path.")
    evaluate.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.command == "analyze":
            report = analyze_commits(args.old, args.new, args.repo, config)
            output = report_to_json(report)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as handle:
                    handle.write(output + "\n")
            print(output if args.json else report_to_text(report), end="")
            return 1 if any(file.generate_tests and file.confidence < 0.5 for file in report.files) else 0

        if args.command == "impact":
            report = analyze_impact(args.old, args.new, args.repo, config)
            output = impact_report_to_json(report)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as handle:
                    handle.write(output + "\n")
            print(output if args.json else impact_report_to_text(report), end="")
            return 0

        if args.command == "eval":
            metrics = run_evaluation(args.cases, config)
            print(json.dumps(metrics, indent=2) if args.json else evaluation_to_text(metrics), end="")
            return 0

    except GitError as exc:
        print(f"Git error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"RegressionIQ error: {exc}", file=sys.stderr)
        return 3

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

