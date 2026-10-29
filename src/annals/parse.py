"""Patchnotes entry parsing: the heading zoo from spec.md (Semantics)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

# Version-led heading. The component word needs two or more characters
# starting with a letter so a leading "v" is never eaten as one; the version
# is dotted digits with an optional pre-release suffix (v0.1.0-alpha).
# Entries start at heading levels 1-2 only: a level-3 version line is a
# subtitle (re-verified against the corpus 2026-10-25; treating ### lines as
# entries minted phantom releases).
_VERSION_LED = re.compile(
    r"^#{1,2}\s+"
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
    r"^#{1,2}\s+(?P<date>\d{4}-\d{2}-\d{2})(?:/\d{1,2})?\s*[:—–-]?\s*(?P<rest>.*)$"
)
# Prose-led heading ending in a parenthesized date, optionally followed by a
# version: the Carrel-calibre-web fork shape
# ("## The sealing lane (2026-10-07, 0.6.44)").
_PROSE_PAREN = re.compile(
    r"^#{1,2}\s+(?P<title>.+?)\s*\((?P<date>\d{4}-\d{2}-\d{2})(?P<tail>[^)]*)\)\s*$"
)
_VERSION_IN_TAIL = re.compile(r"v?\d+(?:\.\d+)+(?:-[0-9A-Za-z.]+)?")
_SUBTITLE = re.compile(r"^###\s+(?P<text>\S.*)$")
# A h1/h2 line always ends a headline scan (next title or entry).
_HEADING = re.compile(r"^#{1,2}(?:\s|$)")
_FENCE = re.compile(r"^```")
# Table rows never carry a summary line (an entry opened by a table stays
# bare); bullets do, through the first-bullet fallback.
_TABLE = re.compile(r"^\|")
# A paragraph that opens with a bold run (possibly spanning soft-wrapped
# lines): the run's inner text is the headline (the Hearth / Hearthfall
# shapes). Plain paragraphs are headlines whole (the saforums shape).
_BOLD_RUN = re.compile(r"^\*\*(.+?)\*\*", re.DOTALL)
# The Framework shape: an italic lead annotation in single asterisks.
_ITALIC_RUN = re.compile(r"^\*([^*]+?)\*(?!\*)", re.DOTALL)
# Thematic breaks bracket sections in the older house shapes
# (CalibreQuarry 2.x, deadbeef-cui); they are transparent to the scan.
_THEMATIC = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$")
# Keep-a-changelog section labels are structure, never headlines; the scan
# looks through them for the prose underneath. The set is corpus-driven:
# the stock categories plus the house dialects observed on 2026-10-25.
_CATEGORIES = frozenset(
    {
        "added",
        "changed",
        "deprecated",
        "removed",
        "fixed",
        "fixes",
        "security",
        "features",
        "new features",
        "bug fixes",
        "performance",
        "breaking",
        "breaking changes",
        "improvements",
        "internal",
        "documentation",
        "structural improvements",
        "dead code removed",
        "new features & improvements",
        "bug fixes & improvements",
        "tests",
        "requirements",
        "repository",
        "tui",
        "cli",
    }
)
# A bullet's text: the marker stripped; soft-wrapped continuation lines join.
_BULLET_START = re.compile(r"^(?:[-*+]|\d+[.)])\s+(?P<text>\S.*)$")
# A release-shaped tag: optional component prefix, optional v, dotted
# version, optional pre-release suffix; the whole name (the reverse check
# for unlogged_tags).
_TAG_VERSION = re.compile(
    r"^(?:(?P<component>[A-Za-z][A-Za-z0-9_-]*?)-)?"
    r"v?(?P<version>\d+(?:\.\d+)+(?:-[0-9A-Za-z.]+)?)$"
)
# A harvested headline quotes its source verbatim only while it is
# headline-sized; a longer plain paragraph or run is body prose, not a
# summary, and cuts at its first sentence end (the crash-course shape,
# 2026-10-29: entries rendering at up to 2,154 characters).
_SUMMARY_CAP = 250


# Bare acronym labels (TUI, CLI) are section structure, not titles.
def _is_category_label(text: str) -> bool:
    return text.lower() in _CATEGORIES or (text.isupper() and len(text) <= 5)


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
    in_fence = False
    for i, line in enumerate(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        entry = (
            _match_version_led(line)
            or _match_date_led(line)
            or _match_prose_paren(line)
        )
        if entry is None:
            continue
        if entry.headline == "":
            entry.headline = _headline_after(lines, i)
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


def _headline_after(lines: list[str], start: int) -> str:
    """An entry's headline when its own heading carries none.

    Order: the first `### ` line before the next entry heading (the cquarry
    shape; keep-a-changelog labels and bare acronyms look through as
    structure), else the first prose paragraph, else the first bullet. A
    paragraph opening with a bold or italic run headlines with the run's
    inner text (the Hearth / Hearthfall / Framework shapes), extended
    through the sentence's end when the run closes on a colon label (the
    lattice shape); a plain paragraph headlines whole while headline-sized,
    soft-wraps joined (the saforums / Colophon shape), and cuts at its first
    sentence end when longer (the crash-course shape). A first bullet
    headlines its sentence under the same run rules (approved 2026-10-25:
    the bullet is body, not an authored summary, but a naked version number
    serves nobody). Thematic breaks and fenced blocks never contribute; a
    table row straight after the heading leaves the entry bare.
    """
    paragraph: list[str] = []
    in_fence = False
    for i, line in enumerate(lines[start + 1 :], start + 1):
        if _FENCE.match(line):
            if paragraph:
                break
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _THEMATIC.match(line):
            continue
        if _HEADING.match(line):
            break
        sm = _SUBTITLE.match(line)
        if sm is not None:
            text = sm["text"].strip()
            if not _is_category_label(text):
                return text
            continue
        if not line.strip():
            if paragraph:
                break
            continue
        if _TABLE.match(line):
            break
        bm = _BULLET_START.match(line)
        if bm is not None:
            if paragraph:
                break
            return _headline_from_text(_bullet_text(lines, i, bm["text"]))
        paragraph.append(line.strip())
    if not paragraph:
        return ""
    return _headline_from_text(" ".join(paragraph), cut_sentence=False)


def _bullet_text(lines: list[str], start: int, first: str) -> str:
    """One bullet's text: its marker-stripped first line plus soft-wrapped
    continuation lines (indented), until a blank or structural line."""
    parts = [first]
    for line in lines[start + 1 :]:
        if not line.strip():
            break
        if _BULLET_START.match(line) or _HEADING.match(line) or _FENCE.match(line):
            break
        if line[0] in " \t":
            parts.append(line.strip())
        else:
            break
    return " ".join(parts)


def _headline_from_text(text: str, cut_sentence: bool = True) -> str:
    """Run-aware headline extraction from one block of prose. Bullets cut at
    the sentence boundary; whole-quote paths (summary paragraphs, bare runs)
    stay verbatim while headline-sized (see _SUMMARY_CAP) and cut at the
    first sentence end when longer."""
    joined = " ".join(text.split())
    run = _BOLD_RUN.match(joined) or _ITALIC_RUN.match(joined)
    if run is None:
        if cut_sentence or len(joined) > _SUMMARY_CAP:
            return _first_sentence(joined)
        return joined
    inner = " ".join(run.group(1).split())
    if not inner.endswith(":"):
        return inner if len(inner) <= _SUMMARY_CAP else _first_sentence(inner)
    rest = joined[run.end() :].strip()
    if not rest:
        return inner
    tail = _first_sentence(rest)
    return " ".join(f"{inner} {tail}".split())


def _first_sentence(text: str) -> str:
    sent = re.search(r"[.!?](?:\s|$)", text)
    return text[: sent.end()].rstrip() if sent else text


def unlogged_tags(
    entries: list[Entry], tags: dict[str, str], cutoff: str | None = None
) -> list[str]:
    """Release-shaped tags that match no parsed entry, newest first.

    The reverse of _tag_lookup: a tag is logged when some release entry's
    (component, version) produces it as a candidate, or when a batch
    entry's headline names the version in prose (the opends wave shape;
    an a.b.c-d.e.f run expands across its patches). A tag predating the
    repo's first workspace-authored commit is inherited history (fork
    checkouts carry upstream tags) and is never audited; with no cutoff,
    everything is.
    """
    candidates: set[str] = set()
    for entry in entries:
        if entry.kind == "release":
            if entry.version is None:
                continue
            v = entry.version
            candidates.update((f"v{v}", v))
            if entry.component:
                candidates.update((f"{entry.component}-v{v}", f"{entry.component}-{v}"))
        else:
            candidates.update(_batch_version_candidates(entry.headline))
    return [
        name
        for date, name in sorted(
            (
                (date, name)
                for name, date in tags.items()
                if _TAG_VERSION.match(name)
                and name not in candidates
                and (cutoff is None or date >= cutoff)
            ),
            reverse=True,
        )
    ]


_BATCH_VERSION = re.compile(
    r"(?:(?P<component>[A-Za-z][A-Za-z0-9_-]*)\s+)?"
    r"v?(?P<first>\d+(?:\.\d+)+)"
    r"(?:-(?P<second>\d+(?:\.\d+)+))?"
)


def _batch_version_candidates(headline: str) -> Iterator[str]:
    """Every tag name a batch headline could be logging: each version token
    (with its preceding component word, when it has one), and both ends of
    an a.b.c-d.e.f patch run."""
    for m in _BATCH_VERSION.finditer(headline):
        component = m["component"]
        for v in _expand_version_range(m["first"], m["second"]):
            yield v
            yield f"v{v}"
            if component:
                yield f"{component}-v{v}"
                yield f"{component}-{v}"


def _expand_version_range(first: str, second: str | None) -> list[str]:
    """A batch wave's version run: 0.3.1-0.3.3 expands to 0.3.1, 0.3.2,
    0.3.3 when the endpoints share major.minor and differ in patch only
    (bounded, so a typo cannot mint thousands); anything else contributes
    its endpoints."""
    if second is None:
        return [first]
    a, b = first.split("."), second.split(".")
    if len(a) == len(b) == 3 and a[:2] == b[:2]:
        lo, hi = int(a[2]), int(b[2])
        if 0 <= hi - lo <= 50:
            return [f"{a[0]}.{a[1]}.{p}" for p in range(lo, hi + 1)]
    return [first, second]


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
