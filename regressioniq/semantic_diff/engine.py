from __future__ import annotations

from regressioniq.models import ChangedFile, FileStatus, SemanticFileChange
from regressioniq.parsing.python_ast import parse_python_module


def _append_if(condition: bool, values: list[str], item: str) -> None:
    if condition and item not in values:
        values.append(item)


def analyze_file_change(file: ChangedFile) -> SemanticFileChange:
    old_module = parse_python_module(file.path, file.old_content)
    new_module = parse_python_module(file.path, file.new_content)
    change = SemanticFileChange(
        path=file.path,
        status=file.status,
        old_parse_error=old_module.syntax_error,
        new_parse_error=new_module.syntax_error,
    )

    if old_module.syntax_error or new_module.syntax_error:
        change.signals.append("syntax_error")
        change.evidence.append("Unable to parse one or both file versions.")
        return change

    if file.status is FileStatus.ADDED:
        change.added_functions = sorted(new_module.functions)
        change.changed_functions = sorted(new_module.functions)
        change.signals.extend(["file_added", "logic_added"])
        change.evidence.append("Python file added.")
        return change

    if file.status is FileStatus.DELETED:
        change.deleted_functions = sorted(old_module.functions)
        change.changed_functions = sorted(old_module.functions)
        change.signals.extend(["file_deleted", "logic_deleted"])
        change.evidence.append("Python file deleted.")
        return change

    old_functions = old_module.functions
    new_functions = new_module.functions
    old_names = set(old_functions)
    new_names = set(new_functions)

    added = sorted(new_names - old_names)
    deleted = sorted(old_names - new_names)
    change.added_functions = added
    change.deleted_functions = deleted
    if added:
        change.signals.append("function_added")
        change.evidence.append(f"Added functions: {', '.join(added)}")
    if deleted:
        change.signals.append("function_deleted")
        change.evidence.append(f"Deleted functions: {', '.join(deleted)}")

    if old_module.imports != new_module.imports:
        change.signals.append("import_changed")
        change.evidence.append("Import set changed.")

    for qualname in sorted(old_names & new_names):
        old = old_functions[qualname]
        new = new_functions[qualname]
        function_signals: list[str] = []

        safe_local_rename = (
            old.args == new.args
            and old.calls == new.calls
            and old.normalized_body != new.normalized_body
            and old.normalized_body_renamed == new.normalized_body_renamed
        )
        if safe_local_rename:
            change.changed_functions.append(qualname)
            _append_if(True, change.signals, "local_variable_rename")
            change.evidence.append(f"{qualname}: local_variable_rename")
            continue

        if old.args != new.args:
            function_signals.append("signature_changed")
        if old.returns != new.returns:
            function_signals.append("return_changed")
        if old.conditions != new.conditions:
            function_signals.append("condition_changed")
        if old.calls != new.calls:
            function_signals.append("call_changed")
        if old.normalized_body != new.normalized_body:
            function_signals.append("body_changed")

        if function_signals:
            change.changed_functions.append(qualname)
            for signal in function_signals:
                _append_if(True, change.signals, signal)
            change.evidence.append(f"{qualname}: {', '.join(function_signals)}")

    if not change.signals and file.old_content != file.new_content:
        change.signals.append("formatting_or_comment_only")
        change.evidence.append("File text changed, but parsed semantic structure did not.")

    return change
