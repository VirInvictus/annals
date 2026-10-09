"""Workspace discovery: classify directories under the workspace root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config


@dataclass(frozen=True)
class Repo:
    name: str
    path: Path
    has_patchnotes: bool
    stats_only: bool


def discover(config: Config) -> tuple[list[Repo], list[str]]:
    """Return (tracked repos sorted by name, ignored directory names).

    A directory with a patchnotes.md is a release repo; a stats_only name is
    tracked for commit activity alone; an excluded name is never read;
    anything else is reported as ignored so an owned repo is never silently
    missed.
    """
    repos: list[Repo] = []
    ignored: list[str] = []
    for child in sorted(config.workspace.iterdir(), key=lambda p: p.name):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in config.exclude:
            continue
        if child.name in config.stats_only:
            repos.append(Repo(child.name, child, has_patchnotes=False, stats_only=True))
        elif (child / "patchnotes.md").is_file():
            repos.append(Repo(child.name, child, has_patchnotes=True, stats_only=False))
        else:
            ignored.append(child.name)
    return repos, ignored
