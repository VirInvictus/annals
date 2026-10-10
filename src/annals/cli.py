"""annals command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from . import __version__
from .config import Config, load_config
from .discover import discover
from .gitstats import repo_stats, tag_dates
from .languages import repo_languages
from .parse import Entry, parse_patchnotes, resolve_dates
from .render import Record, RepoRecord, render, render_site


def build(config: Config) -> Record:
    repos, ignored = discover(config)
    records: list[RepoRecord] = []
    for repo in repos:
        stats = repo_stats(repo.path, config.authors)
        entries: list[Entry] = []
        dupes = 0
        if repo.has_patchnotes:
            text = (repo.path / "patchnotes.md").read_text(encoding="utf-8")
            entries, dupes = parse_patchnotes(repo.name, text)
            resolve_dates(entries, tag_dates(repo.path), stats.first if stats else None)
        languages = (
            None if repo.name in config.language_exclude else repo_languages(repo.path)
        )
        records.append(
            RepoRecord(
                name=repo.name,
                entries=entries,
                dupes=dupes,
                stats=stats,
                languages=languages,
            )
        )
    anchored = [e.resolved for rec in records for e in rec.entries if e.resolved]
    activity = [r.stats.last for r in records if r.stats and r.stats.last]
    latest = max(activity + anchored) if activity + anchored else _today()
    return Record(
        repos=records,
        ignored=ignored,
        generator=f"annals {__version__}",
        authors=config.authors,
        latest=latest,
    )


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="annals",
        description="Render the Vir Invictus workspace work record (ANNALS.md).",
    )
    parser.add_argument(
        "--config", type=Path, default=None, help="alternate annals.toml path"
    )
    parser.add_argument(
        "--stdout", action="store_true", help="print the record instead of writing it"
    )
    parser.add_argument(
        "--check", action="store_true", help="exit 1 when ANNALS.md is stale"
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    record = build(config)
    text = render(record)

    if args.check:
        return _check(config, text)
    if args.stdout:
        sys.stdout.write(text)
        _summarize(record, sys.stderr)
        return 0
    config.output.write_text(text, encoding="utf-8")
    print(f"annals: wrote {config.output}")
    if config.site is not None:
        site_text = render_site(record, config.site.front_matter)
        config.site.path.parent.mkdir(parents=True, exist_ok=True)
        config.site.path.write_text(site_text, encoding="utf-8")
        print(f"annals: wrote {config.site.path}")
    _summarize(record, sys.stdout)
    return 0


def _check(config: Config, text: str) -> int:
    try:
        current = config.output.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(
            f"annals: {config.output} does not exist; run `annals` to generate it",
            file=sys.stderr,
        )
        return 1
    if current == text:
        print("annals: ANNALS.md is current")
        return 0
    print(
        "annals: ANNALS.md is stale; regenerate with `uv run annals`", file=sys.stderr
    )
    return 1


def _summarize(record: Record, file: TextIO) -> None:
    total = sum(len(r.entries) for r in record.repos)
    dupes = sum(r.dupes for r in record.repos)
    approx = sum(1 for r in record.repos for e in r.entries if e.approx)
    print(
        f"annals: {len(record.repos)} repos · {total} entries · "
        f"{dupes} duplicates collapsed · {approx} approximate dates",
        file=file,
    )
    if record.ignored:
        print(
            f"annals: ignored (no patchnotes.md, not in stats_only): {', '.join(record.ignored)}",
            file=file,
        )


if __name__ == "__main__":
    raise SystemExit(main())
