"""Adoption: registry download totals, rendered from the stats cache.

The generator is network-free: `scripts/fetch-adoption` (run by the nightly
publish pipeline) fills the JSON cache, and this module only reads it. A
missing, malformed, or empty cache degrades the section to a note instead of
failing the run, like tokei's absence.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

# The rendered columns and their day lengths (3 months = 90 days).
WINDOWS: tuple[tuple[str, int], ...] = (
    ("7 days", 7),
    ("30 days", 30),
    ("3 months", 90),
)

# pypistats reports every day twice; both bases are cached, so the mirror
# toggle in [adoption] flips at render time without refetching.
MIRROR_BASES = ("without_mirrors", "with_mirrors")

PYPI_URL = "https://pypi.org/project/{name}/"
CRATES_URL = "https://crates.io/crates/{name}/"

# Cumulative crates.io samples kept per crate, one per nightly fetch; the
# widest window needs about 90 of them.
SNAPSHOT_KEEP = 400


@dataclass(frozen=True)
class Row:
    name: str
    registry: str
    url: str
    # One cell per WINDOWS entry; None renders as "-" until data exists
    # (a crates window whose sample history is still warming up).
    windows: tuple[int | None, ...]
    lifetime: int | None


@dataclass(frozen=True)
class AdoptionData:
    mirrors: bool
    as_of: str  # newest data day across the rendered rows; "" when none
    rows: tuple[Row, ...]

    def has_data(self) -> bool:
        return bool(self.as_of) and any(row.lifetime is not None for row in self.rows)


def parse_pypistats(text: str) -> dict[str, dict[str, int]]:
    """Daily downloads per mirror basis from one pypistats /overall reply.

    The reply interleaves every basis by date and the endpoint has no
    per-basis URL variant (verified 2026-11-18), so the split happens here.
    Unknown categories are dropped.
    """
    rows = json.loads(text)["data"]
    out: dict[str, dict[str, int]] = {basis: {} for basis in MIRROR_BASES}
    for row in rows:
        basis = row.get("category")
        if basis in out:
            out[basis][row["date"]] = int(row["downloads"])
    return out


def parse_crates(text: str) -> int:
    """A crate's cumulative download total from a crates.io reply."""
    return int(json.loads(text)["crate"]["downloads"])


def merge_pypi_days(
    days: dict[str, dict[str, int]], fresh: dict[str, dict[str, int]]
) -> dict[str, dict[str, int]]:
    """Fold a fresh pypistats history into the cached one, date-sorted.

    Fresh values win: pypistats revises recent days as its own pipeline
    catches up, and the cache should carry the corrected series.
    """
    return {
        basis: dict(sorted({**days.get(basis, {}), **fresh.get(basis, {})}.items()))
        for basis in MIRROR_BASES
    }


def append_snapshot(
    snapshots: dict[str, int], day: str, total: int, keep: int = SNAPSHOT_KEEP
) -> dict[str, int]:
    """One cumulative sample per fetch: same-day refetches replace, the
    oldest samples prune once `keep` have accrued."""
    merged = dict(snapshots)
    merged[day] = total
    return dict(sorted(merged.items())[-keep:])


def _pypi_windows(
    series: dict[str, int],
) -> tuple[tuple[int | None, ...], int | None]:
    """The window sums and the lifetime total for one PyPI package.

    Windows end at the newest data day; a day missing from the series
    counts zero, and a package younger than a window simply sums what
    exists (its whole history is within the window).
    """
    if not series:
        return tuple(None for _ in WINDOWS), None
    newest = max(series)
    windows = []
    for _, length in WINDOWS:
        cutoff = (date.fromisoformat(newest) - timedelta(days=length - 1)).isoformat()
        windows.append(sum(n for day, n in series.items() if day >= cutoff))
    return tuple(windows), sum(series.values())


def _crates_windows(
    snapshots: dict[str, int],
) -> tuple[tuple[int | None, ...], int | None]:
    """The window sums and the lifetime total for one crates.io crate.

    A window is the newest snapshot minus the newest one at or before the
    window's start (crates.io publishes no time series, so windows are
    sample arithmetic); with no sample that far back the window reads
    None until history accrues.
    """
    if not snapshots:
        return tuple(None for _ in WINDOWS), None
    items = sorted(snapshots.items())
    newest_day, newest_total = items[-1]
    windows = []
    for _, length in WINDOWS:
        cutoff = (date.fromisoformat(newest_day) - timedelta(days=length)).isoformat()
        earlier = [total for day, total in items if day <= cutoff]
        windows.append(newest_total - earlier[-1] if earlier else None)
    return tuple(windows), newest_total


def load_cache(path: Path) -> dict | None:
    """The parsed cache, or None when the file is missing or unreadable."""
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if not isinstance(cache, dict) or not isinstance(cache.get("packages"), dict):
        return None
    return cache


def _empty_row(name: str, registry: str, url: str) -> Row:
    return Row(
        name=name,
        registry=registry,
        url=url,
        windows=tuple(None for _ in WINDOWS),
        lifetime=None,
    )


def load_adoption(
    cache_path: Path,
    pypi: Sequence[str],
    crates: Sequence[str],
    mirrors: bool = False,
) -> AdoptionData:
    """The section's data for the configured packages.

    A missing, malformed, or damaged cache yields empty rows (the render
    degrades to a note), which is what separates configured from
    unconfigured for the renderer: None means no [adoption] section at
    all. Packages absent from the cache still get a row, with empty cells
    until the fetch covers them.
    """
    cache = load_cache(cache_path)
    basis = "with_mirrors" if mirrors else "without_mirrors"
    rows: list[Row] = []
    newest = ""
    try:
        packages = cache["packages"] if cache is not None else {}
        for name in pypi:
            entry = packages.get(f"pypi:{name}")
            entry = entry if isinstance(entry, dict) else {}
            days = entry.get("days")
            series = days.get(basis, {}) if isinstance(days, dict) else {}
            series = series if isinstance(series, dict) else {}
            windows, lifetime = _pypi_windows(series)
            if series:
                newest = max(newest, max(series))
            rows.append(
                Row(
                    name=name,
                    registry="PyPI",
                    url=PYPI_URL.format(name=name),
                    windows=windows,
                    lifetime=lifetime,
                )
            )
        for name in crates:
            entry = packages.get(f"crates:{name}")
            entry = entry if isinstance(entry, dict) else {}
            snaps = entry.get("snapshots")
            snaps = snaps if isinstance(snaps, dict) else {}
            windows, lifetime = _crates_windows(snaps)
            if snaps:
                newest = max(newest, max(snaps))
            rows.append(
                Row(
                    name=name,
                    registry="crates.io",
                    url=CRATES_URL.format(name=name),
                    windows=windows,
                    lifetime=lifetime,
                )
            )
    except TypeError, ValueError, KeyError, AttributeError:
        rows = [
            _empty_row(name, "PyPI", PYPI_URL.format(name=name)) for name in pypi
        ] + [
            _empty_row(name, "crates.io", CRATES_URL.format(name=name))
            for name in crates
        ]
        newest = ""
    return AdoptionData(mirrors=mirrors, as_of=newest, rows=tuple(rows))
