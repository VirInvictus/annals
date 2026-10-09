"""Configuration loading for annals."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

# Fallbacks when no annals.toml exists. The exclusion list mirrors the
# workspace catalog: reference clones by policy, plus the two local-only
# audit repos. stats_only is the owned set without a patchnotes.md.
DEFAULT_EXCLUDE = frozenset(
    {
        "annas-archive-outter",
        "Apostrophe",
        "Awful.app",
        "blightmud",
        "calibre",
        "deadbeef",
        "DeDRM_tools",
        "developer-site",
        "ebook-fonts",
        "godot-simplified-flightsim",
        "gtksourceview",
        "hyprland-wiki",
        "jellyfin-tizen",
        "jellyfin-web",
        "kalker",
        "koreader",
        "llama.cpp",
        "notecalc3",
        "numbat",
        "quickshell-refs",
        "quickshell-web",
        "SpookiUI",
        "zelda3",
        "audit",
        "audit-final",
    }
)
DEFAULT_STATS_ONLY = frozenset(
    {
        "1-timezone",
        "dead-reckoning-bookend-preset",
        "VirInvictus",
        "VirInvictus.github.io",
        "Coffer",
        "project-void",
        "project-yeschef",
    }
)

# Commit statistics count work authored by these identities (git --author
# patterns). Fork repos carry upstream history that would otherwise land in
# the totals; empty the list to count every commit on HEAD.
DEFAULT_AUTHORS: tuple[str, ...] = ("larocque.brandon@gmail.com",)


@dataclass(frozen=True)
class Config:
    workspace: Path
    output: Path
    exclude: frozenset[str]
    stats_only: frozenset[str]
    authors: tuple[str, ...] = DEFAULT_AUTHORS


def repo_root() -> Path:
    """This repo's root, derived from the package location (src/annals/)."""
    return Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> Config:
    """Load annals.toml, falling back to built-in defaults when absent.

    Resolution order: an explicit --config path, else annals.toml in the
    current directory, else the one at this repo's root.
    """
    resolved = path or (
        Path.cwd() / "annals.toml"
        if (Path.cwd() / "annals.toml").is_file()
        else repo_root() / "annals.toml"
    )
    data: dict = {}
    if resolved.is_file():
        data = tomllib.loads(resolved.read_text(encoding="utf-8"))
    ws = data.get("workspace", {})
    run = data.get("run", {})
    stats = data.get("stats", {})
    out = Path(run.get("output", "ANNALS.md"))
    return Config(
        workspace=Path(ws.get("root", "~/.gitrepos")).expanduser(),
        output=out if out.is_absolute() else resolved.parent / out,
        exclude=frozenset(ws.get("exclude", DEFAULT_EXCLUDE)),
        stats_only=frozenset(ws.get("stats_only", DEFAULT_STATS_ONLY)),
        authors=tuple(stats.get("authors", DEFAULT_AUTHORS)),
    )
