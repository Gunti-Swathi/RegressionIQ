from regressioniq.analyzer import analyze_changed_files
from regressioniq.models import ChangeClassification, ChangedFile, FileStatus


def analyze(old: str, new: str, path: str = "src/example.py"):
    report = analyze_changed_files(
        [ChangedFile(path=path, status=FileStatus.MODIFIED, old_content=old, new_content=new)],
        old_commit="old",
        new_commit="new",
    )
    return report.files[0]


def test_comment_only_change_is_skipped():
    result = analyze(
        "def total(price):\n    return price + 1\n",
        "# New explanation.\ndef total(price):\n    return price + 1\n",
    )

    assert result.classification == ChangeClassification.FORMATTING_CHANGE
    assert result.generate_tests is False


def test_return_value_change_generates_tests():
    result = analyze(
        "def total(price):\n    return price + 1\n",
        "def total(price):\n    return price + 2\n",
    )

    assert result.classification == ChangeClassification.LOGIC_CHANGE
    assert result.generate_tests is True
    assert result.changed_functions == ["total"]


def test_condition_change_generates_tests():
    result = analyze(
        "def allowed(user):\n    if user.active:\n        return True\n    return False\n",
        "def allowed(user):\n    if user.active and user.verified:\n        return True\n    return False\n",
    )

    assert result.classification == ChangeClassification.LOGIC_CHANGE
    assert result.generate_tests is True


def test_api_signature_change_is_api_change():
    result = analyze(
        "def get_user(user_id):\n    return user_id\n",
        "def get_user(user_id, include_roles=False):\n    return user_id\n",
        path="src/api/users.py",
    )

    assert result.classification == ChangeClassification.API_CHANGE
    assert result.generate_tests is True
    assert result.risk_band == "high"


def test_safe_local_variable_rename_is_refactor():
    result = analyze(
        "def total(price):\n    tax = price * 0.1\n    return price + tax\n",
        "def total(price):\n    fee = price * 0.1\n    return price + fee\n",
    )

    assert result.classification == ChangeClassification.REFACTOR
    assert result.generate_tests is False

