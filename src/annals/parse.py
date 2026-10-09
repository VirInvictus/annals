"""Patchnotes entry parsing: the heading zoo from spec.md (Semantics)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Version-led heading. The component word needs two or more characters
# starting with a letter so a leading "v" is never eaten as one; the version
# is dotted digits with an optional pre-release suffix (v0.1.0-alpha).
_VERSION_LED = re.compile(
    r"^#{1,3}\s+"
    r"(?:(?P<component>[A-Za-z][A-Za-z0-9_-]+)\s+)?"
    r"v?(?P<version>\d+(?:\.\d+)+(?:-[0-9A-Za-z.]+)?)"
    r"(?P<rest>.*)$"
)
_PAREN_DATE = re.compile(r"\((?P<date>\d{4}-\d{2}-\d{2})\)")
_TRAIL_DATE = re.compile(r"[—–-]\s*(?P<date>\d{4}-\d{2}-\d{2})\s*$")
_RANGE = re.compile(r"(?:→|->)\s*v?(?P<second>\d+(?:\.\d+)+(?:-[0-9A-Za-z.]+)?)")
_DASH_SPLIT = re.compile(r"[—–]")
# Date-led heading: batch entries (opends waves, no-bump notes). A trailing
# /NN on the date is a day range; the lead date anchors the entry.
_DATE_LED = re.compile(
    r"^#{1,3}\s+(?P<date>\d{4}-\d{2}-\d{2})(?:/\d{1,2})?\s*[:—–-]?\s*(?P<rest>.*)$"
)
# Prose-led heading ending in a parenthesized date, optionally followed by a
# version: the Carrel-calibre-web fork shape
# ("## The sealing lane (2026-10-07, 0.6.44)").
_PROSE_PAREN = re.compile(
    r"^#{1,3}\s+(?P<title>.+?)\s*\((?P<date>\d{4}-\d{2}-\d{2})(?P<tail>[^)]*)\)\s*$"
)
_VERSION_IN_TAIL = re.compile(r"v?\d+(?:\.\d+)+(?:-[0-9A-Za-z.]+)?")
_SUBTITLE = re.compile(r"^###\s+(?P<text>\S.*)$")
# A h1/h2 line always ends a subtitle scan (next title or entry); a line that
# itself parses as an entry does too, whatever its heading level.
_HEADING = re.compile(r"^#{1,2}(?:\s|$)")


@dataclass
class Entry:
    repo: str
    kind: str  # "release" or "batch"
    version: str | None = None  # dotted version, no "v" prefix
    component: str | None = None  # e.g. the opends tool name
    label: str | None = None  # display version; ranges keep "a → b"
    headline: str = ""
    date: str | None = None  # ISO date carried by the heading itself
    resolved: str | None = None  # final date after resolution
    approx: bool = False  # resolved by neighbor or first-commit
    source: str = ""  # inline | tag | neighbor | first-commit
    index: int = 0  # position in the file (newest-first)


def parse_patchnotes(repo: str, text: str) -> tuple[list[Entry], int]:
    """Parse patchnotes text into entries (newest-first) and a duplicate count.

    Within one repo the key (component, version) is unique: the first
    occurrence wins because files are newest-first, later ones count as
    duplicates. Batch entries are never deduplicated.
    """
    lines = text.splitlines()
    entries: list[Entry] = []
    dupes = 0
    seen: set[tuple[str | None, str]] = set()
    for i, line in enumerate(lines):
        entry = (
            _match_version_led(line)
            or _match_date_led(line)
            or _match_prose_paren(line)
        )
        if entry is None:
            continue
        if entry.headline == "":
            entry.headline = _subtitle_after(lines, i)
        if entry.kind == "release":
            key = (entry.component, entry.version or "")
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
        entry.repo = repo
        entry.index = len(entries)
        entries.append(entry)
    return entries, dupes


def resolve_dates(
    entries: list[Entry], tags: dict[str, str], first_commit: str | None
) -> None:
    """Assign resolved/source/approx for every entry, in place.

    Order per spec: inline date, then the repo's tags (exact, not
    approximate), then the nearest dated entry below in the file (files are
    newest-first, so that is the nearest older neighbor), then the repo's
    first commit as the bottom anchor.
    """
    carry: str | None = None
    for entry in reversed(entries):  # oldest first
        if entry.date is not None:
            entry.resolved, entry.source, entry.approx = entry.date, "inline", False
        elif entry.kind == "release":
            tag_date = _tag_lookup(entry, tags)
            if tag_date is not None:
                entry.resolved, entry.source, entry.approx = tag_date, "tag", False
            elif carry is not None:
                entry.resolved, entry.source, entry.approx = carry, "neighbor", True
        if entry.resolved is not None:
            carry = entry.resolved
    for entry in entries:
        if entry.resolved is None:
            entry.resolved = first_commit
            entry.source, entry.approx = "first-commit", True


def _match_version_led(line: str) -> Entry | None:
    m = _VERSION_LED.match(line)
    if m is None:
        return None
    version = m["version"]
    rest = m["rest"]
    date: str | None = None
    pm = _PAREN_DATE.search(rest)
    if pm is not None:
        date = pm["date"]
        rest = rest[: pm.start()] + rest[pm.end() :]
    else:
        tm = _TRAIL_DATE.search(rest)
        if tm is not None:
            date = tm["date"]
            rest = rest[: tm.start()]
    headline = _clean(rest)
    label: str | None = None
    rm = _RANGE.search(rest)
    if rm is not None:
        label = f"{version} → {rm['second']}"
        parts = _DASH_SPLIT.split(rest)
        headline = _clean(parts[-1]) if len(parts) > 1 else ""
    return Entry(
        repo="",
        kind="release",
        version=version,
        component=m["component"],
        label=label,
        headline=headline,
        date=date,
    )


def _match_date_led(line: str) -> Entry | None:
    m = _DATE_LED.match(line)
    if m is None:
        return None
    return Entry(repo="", kind="batch", date=m["date"], headline=_clean(m["rest"]))


def _match_prose_paren(line: str) -> Entry | None:
    m = _PROSE_PAREN.match(line)
    if m is None:
        return None
    vm = _VERSION_IN_TAIL.search(m["tail"])
    version = vm.group(0).lstrip("v") if vm is not None else None
    return Entry(
        repo="",
        kind="release" if version else "batch",
        version=version,
        headline=_clean(m["title"]),
        date=m["date"],
    )


def _clean(text: str) -> str:
    return text.strip(" \t:—–-").strip("()").strip()


def _subtitle_after(lines: list[str], start: int) -> str:
    """The first ### line before the next entry heading, when an entry's own
    heading carries no headline (the cquarry shape)."""
    for line in lines[start + 1 :]:
        if _HEADING.match(line):
            return ""
        if _match_version_led(line) is not None or _match_date_led(line) is not None:
            return ""
        if _match_prose_paren(line) is not None:
            return ""
        sm = _SUBTITLE.match(line)
        if sm is not None:
            return sm["text"].strip()
    return ""


def _tag_lookup(entry: Entry, tags: dict[str, str]) -> str | None:
    if entry.version is None:
        return None
    v = entry.version
    candidates = [f"v{v}", v]
    if entry.component:
        candidates += [f"{entry.component}-v{v}", f"{entry.component}-{v}"]
    for candidate in candidates:
        if candidate in tags:
            return tags[candidate]
    return None
