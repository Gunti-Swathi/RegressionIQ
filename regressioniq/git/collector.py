from __future__ import annotations

import subprocess
from pathlib import Path

from regressioniq.config import AppConfig
from regressioniq.models import ChangedFile, FileStatus


class GitError(RuntimeError):
    pass


def _run_git(args: list[str], repo_path: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def _show_file(commit: str, path: str, repo_path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo_path,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _is_ignored(path: str, config: AppConfig) -> bool:
    normalized = path.replace("\\", "/")
    if not normalized.endswith(".py"):
        return True
    if any(fragment in normalized for fragment in config.risk.ignored_path_fragments):
        return True
    return any(normalized.endswith(suffix) for suffix in config.risk.ignored_suffixes)


def collect_changed_files(
    old_commit: str,
    new_commit: str,
    repo_path: str = ".",
    config: AppConfig | None = None,
) -> list[ChangedFile]:
    config = config or AppConfig()
    repo = str(Path(repo_path).resolve())
    diff = _run_git(["diff", "--name-status", old_commit, new_commit], repo)

    files: list[ChangedFile] = []
    for line in diff.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        raw_status = parts[0]
        path = parts[-1]
        if _is_ignored(path, config):
            continue

        status_code = raw_status[0]
        if status_code == "A":
            status = FileStatus.ADDED
        elif status_code == "D":
            status = FileStatus.DELETED
        else:
            status = FileStatus.MODIFIED

        files.append(
            ChangedFile(
                path=path,
                status=status,
                old_content=None if status is FileStatus.ADDED else _show_file(old_commit, path, repo),
                new_content=None if status is FileStatus.DELETED else _show_file(new_commit, path, repo),
            )
        )
    return files

