from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from regressioniq.config import AppConfig
from regressioniq.generation.client import GeminiClient, TestGenerationClient
from regressioniq.generation.models import GeneratedTest, GenerationReport
from regressioniq.generation.prompt import build_generation_prompt, extract_python_code
from regressioniq.generation.storage import ReviewStore
from regressioniq.impact.analyzer import analyze_impact
from regressioniq.impact.models import ImpactFileResult


def _slug(path: str) -> str:
    name = Path(path).stem.replace("-", "_")
    return "".join(char if char.isalnum() or char == "_" else "_" for char in name).strip("_") or "regression"


def _proposal_id(file: ImpactFileResult, prompt: str) -> str:
    digest = hashlib.sha1(f"{file.changed_file}\n{prompt}".encode("utf-8")).hexdigest()[:10]
    return f"{_slug(file.changed_file)}_{digest}"


def _target_path(file: ImpactFileResult, proposal_id: str) -> str:
    return f"tests/generated/test_regression_{proposal_id}.py"


def _dry_run_code(file: ImpactFileResult) -> str:
    changed = ", ".join(file.changed_functions) or file.changed_file
    related = ", ".join(file.related_tests) or "no related tests found"
    return (
        '"""Generated regression test draft.\n\n'
        f"Changed area: {changed}\n"
        f"Related context: {related}\n"
        'Replace this scaffold with Gemini output before approval.\n'
        '"""\n\n'
        "def test_regression_placeholder():\n"
        "    assert True\n"
    )


def _should_generate(file: ImpactFileResult) -> bool:
    return bool(file.changed_functions or file.directly_changed_symbols or file.impacted_functions)


def generate_tests(
    old_commit: str,
    new_commit: str,
    repo_path: str = ".",
    config: AppConfig | None = None,
    model: str = "gemini-2.5-flash",
    review_dir: str = ".regressioniq/reviews",
    client: TestGenerationClient | None = None,
    dry_run: bool = False,
) -> GenerationReport:
    config = config or AppConfig()
    impact = analyze_impact(old_commit, new_commit, repo_path, config)
    store = ReviewStore(repo_path, review_dir)
    env_paths = [Path.cwd() / ".env", Path(repo_path) / ".env"]
    llm = client if client is not None else None if dry_run else GeminiClient(model=model, env_paths=env_paths)

    generated: list[GeneratedTest] = []
    for file in impact.files:
        if not _should_generate(file):
            continue

        prompt = build_generation_prompt(file)
        proposal_id = _proposal_id(file, prompt)
        test_code = _dry_run_code(file) if dry_run else extract_python_code(llm.generate(prompt))  # type: ignore[union-attr]
        target_path = _target_path(file, proposal_id)
        review_file = f"{review_dir}/tests/{Path(target_path).name}"
        metadata_file = f"{review_dir}/metadata/{proposal_id}.json"
        proposal = GeneratedTest(
            id=proposal_id,
            changed_file=file.changed_file,
            target_path=target_path,
            review_file=review_file,
            metadata_file=metadata_file,
            model=model if not dry_run else "dry-run",
            prompt=prompt,
            test_code=test_code,
            rationale="Generated from Phase 2 impact context and related pytest examples.",
            related_tests=file.related_tests,
            impacted_functions=file.impacted_functions,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        generated.append(store.save(proposal))

    return GenerationReport(
        old_commit=old_commit,
        new_commit=new_commit,
        model=model if not dry_run else "dry-run",
        review_dir=review_dir,
        generated=generated,
        summary={
            "files_considered": len(impact.files),
            "tests_generated": len(generated),
            "review_items": len(store.list()),
        },
    )
