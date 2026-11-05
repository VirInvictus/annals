"""ANNALS.md rendering: masthead, dashboard, timeline, coverage."""

from __future__ import annotations

import hashlib
import textwrap
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlparse
from xml.sax.saxutils import escape as _xml_escape

from .config import FeedTarget, LedgerTarget
from .gitstats import RepoStats
from .parse import Entry, unlogged_tags

_MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
_BAR_WIDTH = 28
# The stacked language bar: one shade per top language, interpuncts for the
# tail, so segments stay distinguishable in monospace.
_STACK_CHARS = ("█", "▓", "▒", "░")
_STACK_TAIL = "·"
_STACK_WIDTH = 40
_LANG_TABLE_WIDTH = 22
_LANG_TABLE_ROWS = 12


@dataclass
class RepoRecord:
    name: str
    entries: list[Entry]
    dupes: int = 0
    stats: RepoStats | None = None
    languages: dict[str, int] | None = None
    tags: dict[str, str] = field(default_factory=dict)  # name -> creatordate
    has_patchnotes: bool = True  # stats-only repos audit no tags


def _anchored(entries: list[Entry]) -> list[Entry]:
    """Entries the sources vouch for by exact date: inline or tag. Anything
    approximate (neighbor or first-commit) stays out of the timeline; a long
    dateless run collapsed onto one guessed day is noise, not record."""
    return [e for e in entries if e.resolved and e.source in ("inline", "tag")]


@dataclass
class Record:
    repos: list[RepoRecord]
    ignored: list[str] = field(default_factory=list)
    generator: str = ""
    authors: tuple[str, ...] = ()
    authors_display: str = ""  # the attribution line; raw emails stay machine-side
    latest: str = ""  # newest activity date; anchors the span and "this month"
    # None -> the generic masthead paragraph; otherwise verbatim, with
    # "{generator}" replaced by the generator string.
    intro: str | None = None
    descriptions: dict[str, str] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)

    def attribution(self) -> str:
        return (
            f", authored by {self.attribution_name()}"
            if self.attribution_name()
            else ""
        )

    def attribution_name(self) -> str:
        return self.authors_display or ", ".join(self.authors)

    def repo_cell(self, name: str) -> str:
        """The dashboard's first cell: a linked name when the repo is
        public, the bare name otherwise."""
        url = self.links.get(name)
        return f"[{name}]({url})" if url else name


def render(record: Record) -> str:
    parts = [
        _masthead(record),
        _dashboard(record),
        _languages(record),
        _timeline(record),
        _coverage(record),
    ]
    return "\n".join("\n".join(part) for part in parts).rstrip() + "\n"


def render_site(record: Record, front_matter: str) -> str:
    """The published variant: Jekyll front matter, then the record inside a
    Liquid raw block, so no future headline can break the site build."""
    return f"{front_matter}\n\n{{% raw %}}\n{render(record)}{{% endraw %}}\n"


def render_feed(record: Record, feed: FeedTarget) -> str:
    """The Atom artifact: the newest exactly-dated entries, published
    alongside the site copy. `updated` anchors to the newest activity date
    like the rest of the record, never the generation time, so a quiet
    workspace regenerates byte-identical XML."""
    base = (feed.page_url or feed.site_url).rstrip("/")
    page = f"{base}/"
    feed_url = f"{page}feed.xml"
    host = urlparse(feed.site_url or feed.page_url).netloc or base
    feed_id = feed.id or (
        f"tag:{host},{record.latest[:4]}:{urlparse(page).path or '/'}"
    )
    name = record.attribution_name()
    subtitle = feed.subtitle or (
        f"Every release entry from {name}'s patchnotes, newest first."
        if name
        else "Every release entry from this workspace's patchnotes, newest first."
    )
    out = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"  <title>{_xml_text(feed.title)}</title>",
        f"  <subtitle>{_xml_text(subtitle)}</subtitle>",
        f"  <id>{_xml_text(feed_id)}</id>",
        f"  <updated>{record.latest}T00:00:00Z</updated>",
        f'  <link rel="alternate" href="{_xml_text(page)}"/>',
        f'  <link rel="self" href="{_xml_text(feed_url)}"/>',
        f"  <generator>{_xml_text(record.generator)}</generator>",
    ]
    dated = _timeline_order([e for r in record.repos for e in _anchored(r.entries)])
    for e in dated[: feed.limit]:
        name = _entry_name(e)
        title = f"{name}: {e.headline}" if e.headline else name
        key = (
            e.version
            or hashlib.sha1((e.headline or str(e.index)).encode("utf-8")).hexdigest()[
                :12
            ]
        )
        ident = f"tag:{host},{e.resolved[:4]}:{e.resolved}/{e.repo}/{key}"
        out += [
            "  <entry>",
            f"    <id>{_xml_text(ident)}</id>",
            f"    <title>{_xml_text(title)}</title>",
            f"    <updated>{e.resolved}T00:00:00Z</updated>",
            f'    <link rel="alternate" href="{_xml_text(page)}"/>',
            "  </entry>",
        ]
    out.append("</feed>")
    return "\n".join(out) + "\n"


def _xml_text(text: str) -> str:
    """XML element/attribute text: & < > and the attribute quote."""
    return _xml_escape(text, {'"': "&quot;"})


def _count(n: int, singular: str, plural: str) -> str:
    return f"{n:,} {singular if n == 1 else plural}"


def _timeline_order(dated: list[Entry]) -> list[Entry]:
    """The record's ordering: newest first, same-day entries in their
    patchnotes file order (stable sorts). Shared by the timeline, the feed,
    and the ledger's newest-entry line so they can never diverge."""
    ordered = list(dated)
    ordered.sort(key=lambda e: (e.repo, e.index))
    ordered.sort(key=lambda e: e.resolved, reverse=True)
    return ordered


def _entry_name(e: Entry) -> str:
    who = e.repo + (f" {e.component}" if e.component else "")
    what = e.label or e.version or ""
    return f"{who} {what}".strip()


def render_ledger(record: Record, ledger: LedgerTarget) -> str:
    """The front-page stat line: the dashboard totals as one paragraph,
    written to the configured include. Anchored to the newest activity
    date like the rest of the record, so a quiet workspace regenerates
    byte-identical prose. Generator-authored, so no em-dashes."""
    dated = [e for r in record.repos for e in _anchored(r.entries)]
    total_entries = sum(len(r.entries) for r in record.repos)
    commits = sum(r.stats.commits for r in record.repos if r.stats)
    month = record.latest[:7]
    month_entries = [e for e in dated if e.resolved[:7] == month]
    month_repos = len({e.repo for e in month_entries})
    month_name = (
        f"{_MONTH_NAMES[int(month[5:7])]} {month[:4]}" if len(month) == 7 else month
    )
    repos_part = _count(len(record.repos), "repository", "repositories")
    releases_part = _count(total_entries, "release", "releases")
    commits_part = _count(commits, "commit", "commits")
    month_part = _count(len(month_entries), "release", "releases")
    newest = _timeline_order(dated)[0] if dated else None
    newest_part = (
        f" The newest entry is **{_entry_name(newest)}** ({newest.resolved[5:]})."
        if newest is not None
        else ""
    )
    link = (
        f"[the patchnotes]({ledger.link_url})" if ledger.link_url else "the patchnotes"
    )
    return (
        f"As of {record.latest} the ledger reads **{repos_part} · "
        f"{releases_part} · {commits_part}**; {month_name} added {month_part}"
        f" across {month_repos} of them.{newest_part} The whole record lands in"
        f" {link}, regenerated nightly from each repo's own log.\n"
    )


def _masthead(record: Record) -> list[str]:
    heading = ["# The Annals", ""]
    if record.intro is not None:
        return heading + [record.intro.replace("{generator}", record.generator), ""]
    who = (
        f" of {record.attribution_name()}'s workspace"
        if record.attribution_name()
        else " of this workspace"
    )
    paragraph = (
        f"The work record{who}: every release entry from the tracked repos' "
        "`patchnotes.md` files, plus each repo's git activity, in one place. "
        f"Generated by {record.generator}. The per-repo patchnotes remain "
        "canonical; this file is a projection, reproducible with `annals`."
    )
    return heading + [textwrap.fill(paragraph, width=76), ""]


def _dashboard(record: Record) -> list[str]:
    dated = [e for r in record.repos for e in _anchored(r.entries)]
    total_entries = sum(len(r.entries) for r in record.repos)
    commits = sum(r.stats.commits for r in record.repos if r.stats)
    spans = [r.stats.first for r in record.repos if r.stats and r.stats.first]
    span_start = min(spans) if spans else record.latest
    month = record.latest[:7]
    month_entries = [e for e in dated if e.resolved[:7] == month]
    month_repos = len({e.repo for e in month_entries})
    month_commits = sum(r.stats.monthly.get(month, 0) for r in record.repos if r.stats)

    attribution = record.attribution()
    out = [
        "## The shape of the work",
        "",
        f"- **{len(record.repos)} repositories tracked · {total_entries:,} releases"
        f" recorded · {commits:,} commits{attribution}**",
        f"- Span: {span_start} to {record.latest}",
        f"- This month ({month}): {len(month_entries):,} releases across"
        f" {month_repos} repos · {month_commits:,} commits",
        "",
        "| Repository | What it is | Releases | Latest | Last release | Commits | Active since |",
        "|---|---|---:|---|---|---:|---|",
    ]
    for r in sorted(record.repos, key=lambda r: (-len(r.entries), r.name)):
        latest, last_date = "-", "-"
        if r.entries:
            first = r.entries[0]
            what = first.label or first.version or "-"
            latest = f"{first.component} {what}" if first.component else what
            last_date = first.resolved or "-"
            if first.resolved and first.approx:
                last_date = f"≈{last_date}"
        commits_cell = f"{r.stats.commits:,}" if r.stats else "-"
        since = r.stats.first if r.stats and r.stats.first else "-"
        description = record.descriptions.get(r.name, "")
        out.append(
            f"| {record.repo_cell(r.name)} | {description} | {len(r.entries)}"
            f" | {latest} | {last_date} | {commits_cell} | {since} |"
        )

    rel: Counter[str] = Counter(e.resolved[:7] for e in dated)
    com: Counter[str] = Counter()
    for r in record.repos:
        if r.stats:
            com.update(r.stats.monthly)
    months = sorted(set(rel) | set(com))
    out += [
        "",
        "### Activity by month",
        "",
        "| Month | Releases | Commits |",
        "|---|---|---|",
    ]
    for m in months:
        out.append(
            f"| {m} | {_bar(rel.get(m, 0), max(rel.values(), default=0))} | {_bar(com.get(m, 0), max(com.values(), default=0))} |"
        )
    out.append("")
    return out


def _bar(count: int, maximum: int, width: int = _BAR_WIDTH) -> str:
    if count == 0:
        return "·"
    scaled = max(1, round(count / maximum * width))
    return f"{'▇' * scaled} {count:,}"


def _bare_bar(count: int, maximum: int, width: int = _BAR_WIDTH) -> str:
    """A proportion bar without the embedded count, for cells whose number
    has a column of its own."""
    if count == 0:
        return "·"
    return "▇" * max(1, round(count / maximum * width))


def _languages(record: Record) -> list[str]:
    merged: dict[str, int] = {}
    repos_by_lang: Counter[str] = Counter()
    measured = False
    for r in record.repos:
        if r.languages is None:
            continue
        measured = True
        for lang, lines in r.languages.items():
            merged[lang] = merged.get(lang, 0) + lines
            repos_by_lang[lang] += 1
    out = ["## The languages", ""]
    if not measured:
        return out + [
            "_(Language distribution unavailable: `tokei` is not installed.)_",
            "",
        ]
    if not merged:
        return out + ["_No code measured in the tracked repos._", ""]
    ranked = sorted(merged.items(), key=lambda kv: (-kv[1], kv[0]))
    total = sum(merged.values())
    repo_count = sum(1 for r in record.repos if r.languages is not None)
    out.append(
        f"{total:,} lines of code · {len(ranked)} languages · {repo_count} repos"
    )
    out += [
        "",
        "Code lines measured by `tokei` over each tracked repo's tree:"
        " reference clones and fork checkouts (the `[languages]` exclude)"
        " never count, and neither do lockfiles or data formats. A snapshot"
        " of the trees as they stand, not a measure of authorship pace.",
        "",
        *_stacked_bar(ranked, total),
        "",
    ]
    out += ["| Language | Share | Code lines | Repos |", "|---|---|---:|---:|"]
    shown, rest = ranked[:_LANG_TABLE_ROWS], ranked[_LANG_TABLE_ROWS:]
    for lang, lines in shown:
        out.append(
            f"| {lang} | {_bare_bar(lines, ranked[0][1], _LANG_TABLE_WIDTH)}"
            f" {lines / total * 100:.1f}% | {lines:,} | {repos_by_lang[lang]} |"
        )
    if rest:
        rest_lines = sum(lines for _, lines in rest)
        out.append(
            f"| other | {_bare_bar(rest_lines, ranked[0][1], _LANG_TABLE_WIDTH)}"
            f" {rest_lines / total * 100:.1f}% | {rest_lines:,} | - |"
        )
    out.append("")
    return out


def _stacked_bar(ranked: list[tuple[str, int]], total: int) -> list[str]:
    """One monospace bar: a distinct shade per top language, an interpunct
    tail for the rest. Rendered as a fenced code block: the shade characters
    only align in monospace, and the site's prose font is proportional."""
    head = ranked[: len(_STACK_CHARS)]
    weights = [lines for _, lines in head]
    tail = total - sum(weights)
    chars = list(_STACK_CHARS[: len(head)])
    if tail > 0:
        weights.append(tail)
        chars.append(_STACK_TAIL)
    counts = _largest_remainder(weights, _STACK_WIDTH)
    bar = "".join(char * n for char, n in zip(chars, counts, strict=True))
    head_chars = chars[: len(head)]
    legend = [
        f"{char} {lang} {lines / total * 100:.0f}%"
        for (lang, lines), char in zip(head, head_chars, strict=True)
    ]
    if tail > 0:
        legend.append(f"{_STACK_TAIL} other {tail / total * 100:.0f}%")
    return ["```", bar, "  ".join(legend), "```"]


def _largest_remainder(weights: list[int], width: int) -> list[int]:
    """Split `width` cells across weights; leftover cells go to the largest
    fractional remainders, so segments always sum to exactly the width."""
    total = sum(weights)
    exact = [w * width / total for w in weights]
    counts = [int(e) for e in exact]
    order = sorted(
        range(len(weights)), key=lambda i: exact[i] - counts[i], reverse=True
    )
    for i in range(width - sum(counts)):
        counts[order[i % len(order)]] += 1
    return counts


def _timeline(record: Record) -> list[str]:
    dated = _timeline_order([e for r in record.repos for e in _anchored(r.entries)])

    out = ["## The record", ""]
    if not dated:
        out += ["_Nothing dated to record yet._", ""]
        return out
    by_year: dict[str, dict[str, list[Entry]]] = {}
    for e in dated:
        by_year.setdefault(e.resolved[:4], {}).setdefault(e.resolved[5:7], []).append(e)
    for year in sorted(by_year, reverse=True):
        out += [f"### {year}", ""]
        for month in sorted(by_year[year], reverse=True):
            label = f"{_MONTH_NAMES[int(month)]} {year}"
            out += [f"#### {label}", ""]
            out += [_timeline_line(e) for e in by_year[year][month]]
            out.append("")
    return out


def _timeline_line(e: Entry) -> str:
    name = _entry_name(e)
    head = f" · {e.headline}" if e.headline else ""
    return f"- **{e.resolved[5:]} · {name}**{head}"


def _coverage(record: Record) -> list[str]:
    out = [
        "## Coverage",
        "",
        "Date sources per entry: **inline** (heading carried the date), **tag**",
        "(resolved from the release tag), **neighbor** (approximated from the next",
        "older entry, marked ≈), and **first-commit** (approximated from the",
        "repo's first commit, marked ≈). **Unlogged** counts release-shaped",
        "tags, audited from the repo's first workspace-authored commit onward,",
        "that match no entry in this file; versions named inside batch entries",
        "count as logged.",
        "",
    ]
    if record.authors:
        out += [
            "Commit counts include only commits authored by"
            f" {record.attribution_name()}: fork histories carry upstream",
            "commits that are not this workspace's work.",
            "",
        ]
    out += [
        "| Repository | Entries | Inline | Tag | Neighbor | First commit | Duplicates | Unlogged |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    unlogged_by_repo: dict[str, list[str]] = {}
    for r in sorted(record.repos, key=lambda r: r.name):
        counts = Counter(e.source for e in r.entries)
        cutoff = r.stats.first if r.stats else None
        unlogged = unlogged_tags(r.entries, r.tags, cutoff) if r.has_patchnotes else []
        if unlogged:
            unlogged_by_repo[r.name] = unlogged
        cell = "-" if not r.has_patchnotes else str(len(unlogged))
        out.append(
            f"| {r.name} | {len(r.entries)} | {counts.get('inline', 0)}"
            f" | {counts.get('tag', 0)} | {counts.get('neighbor', 0)}"
            f" | {counts.get('first-commit', 0)} | {r.dupes} | {cell} |"
        )
    out.append("")

    undated = [
        (r, [e for e in r.entries if e.resolved and e.source not in ("inline", "tag")])
        for r in record.repos
    ]
    undated = [(r, entries) for r, entries in undated if entries]
    if undated:
        out += [
            "### Undated records",
            "",
            "These entries carry no heading date and matched no release tag; their",
            "dates could only be guessed from neighbors or a repo's first commit.",
            "They are listed per repo in file order (newest first) instead of",
            "scattered across guessed months.",
            "",
        ]
        for r, entries in undated:
            out += [f"#### {r.name}", ""]
            for e in entries:
                what = e.label or e.version or ""
                head = f" · {e.headline}" if e.headline else ""
                out.append(f"- {what}{head}".rstrip())
            out.append("")

    if unlogged_by_repo:
        out += [
            "### Tags without entries",
            "",
            "Release-shaped tags whose version matches no entry above: a release",
            "was tagged but never logged, or the entry's version and the tag",
            "disagree.",
            "",
        ]
        for r in sorted(record.repos, key=lambda r: r.name):
            names = unlogged_by_repo.get(r.name)
            if not names:
                continue
            out += [f"#### {r.name}", ""]
            out += [f"- {name} ({r.tags[name]})" for name in names]
            out.append("")

    if record.ignored:
        out += [
            "### Ignored directories",
            "",
            "No `patchnotes.md`, not in `stats_only`, not excluded by name:",
            "",
            ", ".join(f"`{n}`" for n in record.ignored),
            "",
            "Owned ones belong in `stats_only`; everything else in `exclude`.",
            "",
        ]
    return out
