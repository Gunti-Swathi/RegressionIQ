import subprocess
from pathlib import Path

from regressioniq.analyzer import analyze_commits
from regressioniq.models import ChangeClassification


def run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def commit_all(repo: Path, message: str) -> str:
    run(["git", "add", "."], repo)
    run(["git", "-c", "user.name=RegressionIQ", "-c", "user.email=test@example.com", "commit", "-m", message], repo)
    return run(["git", "rev-parse", "HEAD"], repo)


def test_analyze_commits_loads_old_and_new_file_versions(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], repo)
    src = repo / "payment.py"
    src.write_text("def validate_payment(amount):\n    return amount > 0\n", encoding="utf-8")
    old_commit = commit_all(repo, "initial")

    src.write_text("def validate_payment(amount):\n    return amount >= 10\n", encoding="utf-8")
    new_commit = commit_all(repo, "change payment rule")

    report = analyze_commits(old_commit, new_commit, repo_path=str(repo))

    assert len(report.files) == 1
    assert report.files[0].path == "payment.py"
    assert report.files[0].classification == ChangeClassification.LOGIC_CHANGE
    assert report.files[0].generate_tests is True
    assert report.files[0].risk_band == "high"
    assert report.files[0].changed_functions == ["validate_payment"]
