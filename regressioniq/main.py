from __future__ import annotations

import argparse
import json
import sys

from regressioniq.analyzer import analyze_commits
from regressioniq.config import load_config
from regressioniq.evaluation.runner import evaluation_to_text, run_evaluation
from regressioniq.generation.models import ReviewState
from regressioniq.generation.service import generate_tests
from regressioniq.generation.storage import ReviewStore
from regressioniq.impact.analyzer import analyze_impact
from regressioniq.git.collector import GitError
from regressioniq.reporting.reporter import (
    generation_report_to_json,
    generation_report_to_text,
    impact_report_to_json,
    impact_report_to_text,
    report_to_json,
    report_to_text,
    review_items_to_text,
)


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

    generate = subparsers.add_parser("generate-tests", help="Generate pytest regression test drafts with Gemini.")
    generate.add_argument("--old", required=True, help="Old/base commit SHA or ref.")
    generate.add_argument("--new", required=True, help="New/head commit SHA or ref.")
    generate.add_argument("--repo", default=".", help="Path to the local Git repository.")
    generate.add_argument("--config", default=None, help="Optional JSON config path.")
    generate.add_argument("--model", default="gemini-2.5-flash", help="Gemini model name.")
    generate.add_argument("--review-dir", default=".regressioniq/reviews", help="Directory for generated review drafts.")
    generate.add_argument("--dry-run", action="store_true", help="Create placeholder drafts without calling Gemini.")
    generate.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    generate.add_argument("--output", default=None, help="Optional path to write JSON report.")

    review = subparsers.add_parser("review-tests", help="List generated tests waiting for human review.")
    review.add_argument("--repo", default=".", help="Path to the local Git repository.")
    review.add_argument("--review-dir", default=".regressioniq/reviews", help="Directory containing generated review drafts.")
    review.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    approve = subparsers.add_parser("approve", help="Approve a generated test and copy it into tests/generated.")
    approve.add_argument("id", help="Generated test id.")
    approve.add_argument("--repo", default=".", help="Path to the local Git repository.")
    approve.add_argument("--review-dir", default=".regressioniq/reviews", help="Directory containing generated review drafts.")

    reject = subparsers.add_parser("reject", help="Reject a generated test draft.")
    reject.add_argument("id", help="Generated test id.")
    reject.add_argument("--repo", default=".", help="Path to the local Git repository.")
    reject.add_argument("--review-dir", default=".regressioniq/reviews", help="Directory containing generated review drafts.")

    repair = subparsers.add_parser("repair-needed", help="Mark a generated test draft as needing repair.")
    repair.add_argument("id", help="Generated test id.")
    repair.add_argument("--repo", default=".", help="Path to the local Git repository.")
    repair.add_argument("--review-dir", default=".regressioniq/reviews", help="Directory containing generated review drafts.")

    evaluate = subparsers.add_parser("eval", help="Run the Phase 1 evaluation benchmark.")
    evaluate.add_argument("--cases", default="eval_cases", help="Directory containing JSON eval cases.")
    evaluate.add_argument("--config", default=None, help="Optional JSON config path.")
    evaluate.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(getattr(args, "config", None))
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

        if args.command == "generate-tests":
            report = generate_tests(
                args.old,
                args.new,
                repo_path=args.repo,
                config=config,
                model=args.model,
                review_dir=args.review_dir,
                dry_run=args.dry_run,
            )
            output = generation_report_to_json(report)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as handle:
                    handle.write(output + "\n")
            print(output if args.json else generation_report_to_text(report), end="")
            return 0

        if args.command == "review-tests":
            items = ReviewStore(args.repo, args.review_dir).list()
            print(
                json.dumps([item.model_dump(mode="json") for item in items], indent=2)
                if args.json
                else review_items_to_text(items),
                end="",
            )
            return 0

        if args.command == "approve":
            item = ReviewStore(args.repo, args.review_dir).approve(args.id)
            print(f"Approved {item.id} -> {item.target_path}\n", end="")
            return 0

        if args.command == "reject":
            item = ReviewStore(args.repo, args.review_dir).update_state(args.id, ReviewState.REJECTED)
            print(f"Rejected {item.id}\n", end="")
            return 0

        if args.command == "repair-needed":
            item = ReviewStore(args.repo, args.review_dir).update_state(args.id, ReviewState.REPAIR_NEEDED)
            print(f"Marked {item.id} as repair_needed\n", end="")
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
