"""gitstats tests against real temporary git repos with pinned dates."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from annals.gitstats import repo_stats, tag_dates


def _git(path: Path, *args: str, env: dict | None = None) -> None:
    subprocess.run(
        ("git", "-C", str(path), *args),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")


def _commit(
    path: Path,
    message: str,
    when: str,
    name: str = "Test",
    email: str = "test@example.com",
) -> None:
    env = os.environ | {
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }
    (path / "f.txt").write_text(message + "\n")
    _git(path, "add", "-A")
    subprocess.run(
        ("git", "-C", str(path), "commit", "-m", message),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def test_repo_stats_author_filter(tmp_path: Path) -> None:
    repo = tmp_path / "forked"
    _init_repo(repo)
    _commit(repo, "mine", "2026-05-01T12:00:00")
    _commit(
        repo,
        "upstream",
        "2026-06-01T12:00:00",
        name="Upstream",
        email="jan@example.com",
    )
    _commit(repo, "mine again", "2026-07-01T12:00:00")

    filtered = repo_stats(repo, ("test@example.com",))
    assert filtered is not None
    assert filtered.commits == 2
    assert filtered.first == "2026-05-01"
    assert filtered.last == "2026-07-01"
    assert filtered.monthly == {"2026-05": 1, "2026-07": 1}

    everything = repo_stats(repo)
    assert everything is not None
    assert everything.commits == 3


def test_repo_stats_counts_and_months(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(repo, "first", "2026-05-01T12:00:00")
    _commit(repo, "second", "2026-06-15T09:00:00")
    _commit(repo, "third", "2026-06-20T09:00:00")

    stats = repo_stats(repo)
    assert stats is not None
    assert stats.commits == 3
    assert stats.first == "2026-05-01"
    assert stats.last == "2026-06-20"
    assert stats.monthly == {"2026-05": 1, "2026-06": 2}


def test_repo_stats_none_for_plain_directory(tmp_path: Path) -> None:
    assert repo_stats(tmp_path / "not-a-repo") is None


def test_repo_stats_none_for_empty_repo(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    _init_repo(repo)
    assert repo_stats(repo) is None


def test_tag_dates_maps_creatordate(tmp_path: Path) -> None:
    repo = tmp_path / "tagged"
    _init_repo(repo)
    _commit(repo, "first", "2026-05-01T12:00:00")
    env = os.environ | {
        "GIT_COMMITTER_DATE": "2026-05-02T08:00:00",
        "GIT_AUTHOR_DATE": "2026-05-02T08:00:00",
    }
    subprocess.run(
        ("git", "-C", str(repo), "tag", "-a", "v1.0.0", "-m", "one"),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert tag_dates(repo) == {"v1.0.0": "2026-05-02"}


def test_tag_dates_empty_for_untagged_repo(tmp_path: Path) -> None:
    repo = tmp_path / "plain"
    _init_repo(repo)
    _commit(repo, "first", "2026-05-01T12:00:00")
    assert tag_dates(repo) == {}
