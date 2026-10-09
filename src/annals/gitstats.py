"""Read-only git statistics for member repos."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoStats:
    commits: int
    first: str | None
    last: str | None
    monthly: dict[str, int]


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(path), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def repo_stats(path: Path, authors: tuple[str, ...] = ()) -> RepoStats | None:
    """Commit counts and author-date histogram from git log.

    None when the path is not a git repo or has no matching commits. Author
    date (%as) on purpose: it reflects when the work was written, not when a
    rebase landed it. `authors` is a set of git --author patterns (OR); the
    filter keeps fork histories from counting upstream commits. An empty
    tuple counts every commit on HEAD.
    """
    try:
        args = ["log", "--format=%as"]
        for author in authors:
            args += ["--author", author]
        out = _git(path, *args)
    except subprocess.CalledProcessError, FileNotFoundError:
        return None
    dates = out.split()
    if not dates:
        return None
    monthly: dict[str, int] = {}
    for d in dates:
        month = d[:7]
        monthly[month] = monthly.get(month, 0) + 1
    return RepoStats(
        commits=len(dates), first=dates[-1], last=dates[0], monthly=monthly
    )


def tag_dates(path: Path) -> dict[str, str]:
    """Tag name -> creatordate (ISO short) for every tag; empty when none."""
    try:
        out = _git(
            path,
            "for-each-ref",
            "refs/tags",
            "--format=%(refname:short)|%(creatordate:short)",
        )
    except subprocess.CalledProcessError, FileNotFoundError:
        return {}
    tags: dict[str, str] = {}
    for line in out.splitlines():
        name, sep, date = line.partition("|")
        if sep and date:
            tags[name] = date
    return tags
