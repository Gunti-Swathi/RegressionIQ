import subprocess
from pathlib import Path

from regressioniq.generation.client import load_env_files
from regressioniq.generation.models import ReviewState
from regressioniq.generation.service import generate_tests
from regressioniq.generation.storage import ReviewStore


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "sample_project"


class FakeGeminiClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return (
            "```python\n"
            "def test_validate_payment_regression():\n"
            "    from src.payments import validate_payment\n"
            "    assert validate_payment(10, 'USD') is True\n"
            "    assert validate_payment(9, 'USD') is False\n"
            "```\n"
        )


def run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def commit_all(repo: Path, message: str) -> str:
    run(["git", "add", "."], repo)
    run(["git", "-c", "user.name=RegressionIQ", "-c", "user.email=test@example.com", "commit", "-m", message], repo)
    return run(["git", "rev-parse", "HEAD"], repo)


def copy_sample_project(target: Path) -> None:
    for source in SAMPLE.rglob("*"):
        rel = source.relative_to(SAMPLE)
        if ".git" in rel.parts or "__pycache__" in rel.parts or rel.name == ".phase2-demo-commits" or rel.suffix == ".pyc":
            continue
        if source.is_file():
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def changed_sample_repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "sample"
    repo.mkdir()
    run(["git", "init"], repo)
    copy_sample_project(repo)
    old_commit = commit_all(repo, "initial sample project")

    payments = repo / "src" / "payments.py"
    payments.write_text(
        "def validate_payment(amount: float, currency: str) -> bool:\n"
        "    if amount < 10:\n"
        "        return False\n"
        "    if currency not in {\"USD\", \"EUR\"}:\n"
        "        return False\n"
        "    return True\n",
        encoding="utf-8",
    )
    new_commit = commit_all(repo, "tighten payment minimum")
    return repo, old_commit, new_commit


def test_generate_tests_uses_gemini_client_and_saves_review_item(tmp_path):
    repo, old_commit, new_commit = changed_sample_repo(tmp_path)
    client = FakeGeminiClient()

    report = generate_tests(old_commit, new_commit, repo_path=str(repo), client=client, model="gemini-test")

    assert report.summary["tests_generated"] == 1
    assert len(client.prompts) == 1
    assert "src/payments.py" in client.prompts[0]
    assert "tests/test_payments.py" in client.prompts[0]

    item = report.generated[0]
    assert item.state == ReviewState.GENERATED
    assert item.model == "gemini-test"
    assert "def test_validate_payment_regression" in item.test_code
    assert (repo / item.review_file).exists()
    assert (repo / item.metadata_file).exists()


def test_review_store_approves_generated_test(tmp_path):
    repo, old_commit, new_commit = changed_sample_repo(tmp_path)
    report = generate_tests(old_commit, new_commit, repo_path=str(repo), dry_run=True)
    item = report.generated[0]

    approved = ReviewStore(str(repo)).approve(item.id)

    assert approved.state == ReviewState.APPROVED
    assert (repo / approved.target_path).exists()
    stored = ReviewStore(str(repo)).get(item.id)
    assert stored.state == ReviewState.APPROVED


def test_load_env_files_reads_gemini_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=test-key\n", encoding="utf-8")

    load_env_files([env_file])

    assert __import__("os").environ["GEMINI_API_KEY"] == "test-key"
