# annals

The work record of the Vir Invictus workspace: one generated file that walks
every project in `~/.gitrepos/`, reads each owned repo's `patchnotes.md` and
git history, and renders the whole thing into a single dashboard-plus-timeline,
so the volume and shape of the work is visible in one place.

## What it does

- Parses every owned repo's `patchnotes.md`, tolerating the heading shapes the
  workspace actually uses (paren dates, separator dates, colon headlines,
  component-prefixed tool versions, date-led batch entries, bare versions).
- Resolves each entry's date from the heading first, then the repo's release
  tags; entries with neither are listed per repo under Undated records in
  their true file order rather than scattered across guessed months.
- Counts commits, first/last activity, and monthly totals per repo (read-only;
  member repos are never touched), and measures the workspace's language
  distribution by code lines with `tokei` (fork checkouts excludable per
  config; the section degrades gracefully when tokei is absent).
- Renders `ANNALS.md`: totals, a per-repo table, monthly activity bars, a
  stacked language-distribution bar plus ranked table, a newest-first
  timeline of every release grouped by month, and a coverage appendix
  reporting exactly how each date was resolved, plus release-shaped git
  tags that match no entry (the audit for tagged-but-never-logged work).

The per-repo `patchnotes.md` files remain canonical. annals only reads them;
`ANNALS.md` is a projection, always reproducible with one command. With a
`[site]` target configured, the same record is also written as a Jekyll page
for publication (the Vir Invictus site serves it at `/patchnotes/`), beside
two smaller generator-owned artifacts: the front-page ledger include and an
Atom feed of the newest releases at `/patchnotes/feed.xml`.

## Usage

```sh
uv run annals             # regenerate ANNALS.md in this repo
uv run annals --stdout    # print the record instead of writing it
uv run annals --check     # exit 1 when ANNALS.md is stale
```

Configuration lives in `annals.toml` (workspace root, the exclusion list for
reference clones, and the stats-only list for owned repos without releases).
Python 3.14, standard library only. Tests: `uv run pytest`.

## License

MIT. See `LICENSE`.
