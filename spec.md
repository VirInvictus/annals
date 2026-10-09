# annals specification

## Purpose

annals answers one question: how much work does the Vir Invictus workspace
represent, and what is its shape over time? It renders a single record,
`ANNALS.md`, from sources that already exist and stay canonical:

- each owned repo's `patchnotes.md` (the release log),
- each repo's git history (commits, tags).

annals is read-only against the workspace. Its only write is `ANNALS.md`
inside its own repo.

## Semantics

### Discovery

Walk the `[workspace]` root one level deep. A directory carrying a
`patchnotes.md` is a **release repo**. A directory named in `stats_only` is
tracked for commit statistics only. A directory in `exclude` is never read.
Anything else is reported in the run summary as ignored, never silently
dropped.

### Entry shapes

The parser reads headings of level 1-3 in `patchnotes.md`. A line is an entry
when it matches one of these shapes (all verified against every
release-cutting repo in the workspace on 2026-10-09):

1. **Version-led**: optional component word, optional `v`, dotted version with
   optional pre-release suffix. The component must be two or more characters
   starting with a letter, so a leading `v` is never consumed as one. After
   the version, in any order: a parenthesized ISO date, a trailing separator
   date (`—`, `–`, or `-` before `YYYY-MM-DD`), and/or a headline after `:`,
   a dash separator, or a range arrow (`→`, `->`).
   Examples: `## v1.26.2 (2026-10-09)`, `# 3.61.0 (2026-10-09)`,
   `## 0.9.10 (2026-09-15)`, `## darkfix-ds1 v0.1.3 (2026-10-07)`,
   `## v0.1.4 — 2026-08-09`, `## v3.2.1: headline`,
   `## v1.0.0 (Stable Release)`, `## v0.1.10 → v0.1.16 — headline`.
2. **Date-led**: a leading ISO date (optionally a `/NN` day range), optional
   separator, then prose. These are batch entries (`kind = batch`) and carry
   no version. Examples: `## 2026-09-06 hardening batch: ...`,
   `## 2026-09-17 (no version bump: ...)`.
3. **Prose-paren**: prose title ending in a parenthesized ISO date, with an
   optional version inside the paren after the date; with a version it is a
   release, without one a batch. The Carrel-calibre-web fork shape:
   `## The sealing lane (2026-10-07, 0.6.44)`.

Anything else is not an entry (title lines, prose headlines). A version-led
entry whose heading carries no headline takes the first `### ` line before
the next entry heading as its headline.

Parenthesized text that is not an ISO date is headline text, never a date.

### Date resolution

Each entry resolves to one date, in this order, with its source recorded:

1. **inline**: the heading carried the date. Exact.
2. **tag**: the repo's git tags, checked as `v<version>`, `<version>`,
   `<component>-v<version>`, `<component>-<version>`. Exact: a tag date is
   the release day.
3. **neighbor**: the nearest dated entry below it in the file (files are
   newest-first, so that is the nearest older anchor). Approximate, marked.
4. **first-commit**: the repo's first commit date, when no dated anchor
   exists below. Approximate, marked.

Only exactly dated entries (inline, tag) enter the timeline. Approximate
entries (neighbor, first-commit) never receive a fabricated position in the
month grid: a long dateless run collapsed onto one guessed day is noise, not
record. They are listed per repo under Undated records, in file order, which
is their true relative order.

### Duplicates

Within one repo, the key `(component, version)` must be unique. The first
occurrence wins (files are newest-first); later occurrences are counted as
duplicates in the coverage appendix and dropped. Batch entries are never
deduplicated.

### Statistics

Per repo, from `git`: total commits on `HEAD`, author dates of the first and
last commit, and a per-month commit histogram (author date, `%as`). Commit
counts are filtered to the configured author identities (`[stats] authors`,
git `--author` patterns, OR) so fork histories count only this workspace's
work; an empty list counts every commit. A repo with no matching commits
contributes nothing.

### Output contract

`ANNALS.md` contains, in order:

1. Masthead: what the file is, the generator version and generation date,
   and the canonical-source note.
2. Dashboard: totals (repos, releases, commits, span), this-month numbers,
   a per-repo table (releases, latest version, last release, commits, active
   since) sorted by release count, and a month-by-month table with inline
   bar charts for releases and commits. The last-release cell carries `≈`
   when even the repo's newest entry is approximate.
3. The record: newest-first timeline of exactly dated entries grouped by
   year then month; one line per entry: date, repo, component and/or
   version, headline verbatim from the source.
4. Coverage appendix: per-repo date-source counts (inline, tag, neighbor,
   first-commit, duplicates), the Undated records (approximate entries in
   file order), and the ignored directories.

Headlines are quoted verbatim from member patchnotes and may contain
anything, including em-dashes. Prose the generator itself authors contains
none.

The generation stamp line is excluded from `--check` staleness comparison,
so a same-data regeneration on a later day is still "current".

## CLI

- `annals` (default): regenerate `ANNALS.md`, write it, print a summary
  (repos tracked, entries, duplicates collapsed, approximations, ignored
  directories).
- `annals --stdout`: print the record to stdout; write nothing.
- `annals --check`: regenerate in memory and compare (stamp line excluded);
  exit 0 when `ANNALS.md` is current, exit 1 when stale or missing.
- `annals --config PATH`: use an alternate configuration file. Default:
  `annals.toml` in the current directory, else the one at the repo root.

The tool never commits, never pushes, and never writes outside its own repo.

## Non-goals

- No network access. Everything is local files and local git.
- No third-party dependencies; Python 3.14 standard library only.
- No scheduling. Automation (cron, ZCode idle tasks) wraps the CLI; it is
  not part of annals.
- No hand editing of `ANNALS.md`; every byte is reproducible. Corrections
  belong in the member repos' own patchnotes, then a regeneration.
