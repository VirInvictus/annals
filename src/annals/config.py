"""Configuration loading for annals."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(ValueError):
    """A configuration problem the user can fix: a missing file, a missing
    required key, a key of the wrong type."""


@dataclass(frozen=True)
class SiteTarget:
    path: Path
    front_matter: str


@dataclass(frozen=True)
class LedgerTarget:
    path: Path
    # Markdown link target for "the patchnotes" (absent: plain text, no link).
    link_url: str | None = None


@dataclass(frozen=True)
class FeedTarget:
    path: Path
    site_url: str
    limit: int
    title: str = "The Annals"
    # None -> a generic subtitle built at render time.
    subtitle: str | None = None
    # None -> the site_url root itself.
    page_url: str | None = None
    # None -> a tag: URI derived from the page URL and the newest activity
    # year. Pin it once published: readers treat an id change as a new feed.
    id: str | None = None


@dataclass(frozen=True)
class Config:
    workspace: Path
    output: Path
    exclude: frozenset[str] = frozenset()
    stats_only: frozenset[str] = frozenset()
    authors: tuple[str, ...] = ()
    authors_display: str = ""
    # None -> the generic masthead paragraph built at render time.
    # "{generator}" in the text becomes the generator string ("annals X.Y.Z"),
    # so a hand-written intro keeps the live version stamp.
    intro: str | None = None
    site: SiteTarget | None = None
    ledger: LedgerTarget | None = None
    feed: FeedTarget | None = None
    language_exclude: frozenset[str] = frozenset()
    descriptions: dict[str, str] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)


def repo_root() -> Path:
    """This checkout's root, derived from the package location (src/annals/)."""
    return Path(__file__).resolve().parents[2]


def xdg_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "annals" / "annals.toml"


def _resolve_config_path(path: Path | None) -> Path:
    """Where annals.toml lives: an explicit --config path (which must
    exist), else the current directory, else this checkout's root, else the
    XDG config directory. No file anywhere is a setup error, not a default.
    """
    if path is not None:
        if not path.is_file():
            raise ConfigError(f"config file not found: {path}")
        return path
    candidates = (
        Path.cwd() / "annals.toml",
        repo_root() / "annals.toml",
        xdg_config_path(),
    )
    found = next((candidate for candidate in candidates if candidate.is_file()), None)
    if found is None:
        raise ConfigError(
            "no annals.toml found (looked in the current directory, this"
            " checkout's root, and the XDG config directory); run `annals"
            " init` to create one"
        )
    return found


def _table(data: dict, key: str) -> dict | None:
    value = data.get(key)
    if value is not None and not isinstance(value, dict):
        raise ConfigError(
            f"[{key}] must be a table, got {type(value).__name__}; check annals.toml"
        )
    return value


def load_config(path: Path | None = None) -> Config:
    """Load annals.toml from the resolution order in _resolve_config_path.

    Everything machine-specific lives in the file; the code carries none of
    it. [workspace] root is the one required key.
    """
    resolved = _resolve_config_path(path)
    data = tomllib.loads(resolved.read_text(encoding="utf-8"))
    ws = _table(data, "workspace") or {}
    run = _table(data, "run") or {}
    stats = _table(data, "stats") or {}
    langs = _table(data, "languages") or {}
    site = _table(data, "site") or {}
    ledger = _table(data, "ledger")
    feed = _table(data, "feed")

    root = ws.get("root")
    if not root:
        raise ConfigError(
            "[workspace] root is required (the directory containing your repos)"
        )
    workspace = Path(root).expanduser()
    if not workspace.is_dir():
        raise ConfigError(f"workspace root does not exist: {workspace}")

    out = Path(run.get("output", "ANNALS.md"))
    site_path = site.get("path")
    feed_target = None
    if feed is not None and feed.get("path"):
        site_url = str(feed.get("site_url", ""))
        page_url = feed.get("page_url")
        if not site_url and not page_url:
            raise ConfigError("[feed] needs site_url or page_url (absolute links)")
        feed_target = FeedTarget(
            path=Path(feed["path"]).expanduser(),
            site_url=site_url,
            limit=int(feed.get("limit", 50)),
            title=str(feed.get("title", "The Annals")),
            subtitle=feed.get("subtitle"),
            page_url=page_url,
            id=feed.get("id"),
        )
    ledger_target = None
    if ledger is not None and ledger.get("path"):
        ledger_target = LedgerTarget(
            path=Path(ledger["path"]).expanduser(),
            link_url=ledger.get("link_url"),
        )
    return Config(
        workspace=workspace,
        output=out if out.is_absolute() else resolved.parent / out,
        exclude=frozenset(ws.get("exclude", ())),
        stats_only=frozenset(ws.get("stats_only", ())),
        authors=tuple(stats.get("authors", ())),
        authors_display=stats.get("authors_display", ""),
        intro=run.get("intro"),
        site=(
            SiteTarget(
                path=Path(site_path).expanduser(),
                front_matter=str(site.get("front_matter", "")),
            )
            if site_path
            else None
        ),
        ledger=ledger_target,
        feed=feed_target,
        language_exclude=frozenset(langs.get("exclude", ())),
        descriptions=dict(data.get("descriptions", {})),
        links=dict(data.get("links", {})),
    )
