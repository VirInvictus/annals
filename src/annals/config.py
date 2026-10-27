"""Configuration loading for annals."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# Fallbacks when no annals.toml exists. The exclusion list mirrors the
# workspace catalog: reference clones by policy, the two local-only audit
# repos, and the retired community-bot repo. stats_only is the owned set
# without a patchnotes.md.
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
        "meoweconomy",
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

# The published variant defaults: Jekyll front matter for the VirInvictus
# site, then the record inside a Liquid raw block (see render_site).
DEFAULT_SITE_PATH = "~/.gitrepos/VirInvictus.github.io/patchnotes.md"
DEFAULT_SITE_FRONT_MATTER = (
    "---\nlayout: default\ntitle: Patchnotes\npermalink: /patchnotes/\n---"
)

# The front-page ledger line: a generator-owned include the site README
# renders with a Liquid include tag. Same sanctioned write family as the
# site copy; no [ledger] section means no write.
DEFAULT_LEDGER_PATH = "~/.gitrepos/VirInvictus.github.io/_includes/ledger.md"


@dataclass(frozen=True)
class SiteTarget:
    path: Path
    front_matter: str


@dataclass(frozen=True)
class LedgerTarget:
    path: Path


@dataclass(frozen=True)
class Config:
    workspace: Path
    output: Path
    exclude: frozenset[str]
    stats_only: frozenset[str]
    authors: tuple[str, ...] = DEFAULT_AUTHORS
    authors_display: str = ""
    site: SiteTarget | None = None
    ledger: LedgerTarget | None = None
    language_exclude: frozenset[str] = frozenset()
    descriptions: dict[str, str] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)


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
    site = data.get("site", {})
    ledger = data.get("ledger")
    if ledger is not None and not isinstance(ledger, dict):
        raise ValueError(
            f"[ledger] must be a table, got {type(ledger).__name__}; check annals.toml"
        )
    langs = data.get("languages", {})
    out = Path(run.get("output", "ANNALS.md"))
    site_path = site.get("path", DEFAULT_SITE_PATH) if site else None
    return Config(
        workspace=Path(ws.get("root", "~/.gitrepos")).expanduser(),
        output=out if out.is_absolute() else resolved.parent / out,
        exclude=frozenset(ws.get("exclude", DEFAULT_EXCLUDE)),
        stats_only=frozenset(ws.get("stats_only", DEFAULT_STATS_ONLY)),
        authors=tuple(stats.get("authors", DEFAULT_AUTHORS)),
        authors_display=stats.get("authors_display", ""),
        site=SiteTarget(
            path=Path(site_path).expanduser(),
            front_matter=site.get("front_matter", DEFAULT_SITE_FRONT_MATTER),
        )
        if site_path
        else None,
        ledger=(
            LedgerTarget(
                path=Path(ledger.get("path", DEFAULT_LEDGER_PATH)).expanduser()
            )
            if ledger is not None
            else None
        ),
        language_exclude=frozenset(langs.get("exclude", ())),
        descriptions=dict(data.get("descriptions", {})),
        links=dict(data.get("links", {})),
    )
