import subprocess
from pathlib import Path

from regressioniq.impact.analyzer import analyze_impact
from regressioniq.impact.graph_builder import build_repository_graph


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "sample_project"


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
        if (
            ".git" in rel.parts
            or ".regressioniq" in rel.parts
            or "__pycache__" in rel.parts
            or rel.name == ".phase2-demo-commits"
            or rel.suffix == ".pyc"
        ):
            continue
        if source.is_file():
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def test_graph_builder_detects_call_relationships():
    graph = build_repository_graph(str(SAMPLE))

    checkout_symbol = "src.checkout.checkout"
    validate_symbol = "src.payments.validate_payment"
    invoice_symbol = "src.invoices.create_invoice"

    assert checkout_symbol in graph.functions
    assert validate_symbol in graph.functions[checkout_symbol].calls
    assert invoice_symbol in graph.functions[checkout_symbol].calls
    assert checkout_symbol in graph.reverse_calls[validate_symbol]


def test_impact_analysis_finds_callers_related_tests_and_context(tmp_path):
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

    report = analyze_impact(old_commit, new_commit, repo_path=str(repo))
    result = report.files[0]

    assert result.changed_file == "src/payments.py"
    assert result.directly_changed_symbols == ["src.payments.validate_payment"]
    assert result.impacted_functions == ["src.checkout.checkout"]
    assert "src.checkout" in result.impacted_modules
    assert not any(symbol.startswith("tests.") for symbol in result.impacted_functions)
    assert "tests/test_payments.py" in result.related_tests
    assert "tests/test_checkout.py" in result.related_tests
    assert "tests/conftest.py" in result.related_tests
    kinds = {snippet.kind for snippet in result.context}
    assert {"changed_function", "impacted_function", "related_test", "fixture"}.issubset(kinds)
