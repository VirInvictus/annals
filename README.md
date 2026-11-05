# annals

One generated file that walks a directory of git repos, reads each repo's
`patchnotes.md` release log and git history, and renders the whole thing
into a single dashboard-plus-timeline, so the volume and shape of the work
is visible in one place.

## What it does

- Parses every tracked repo's `patchnotes.md`, tolerating the heading shapes
  changelogs actually use (paren dates, separator dates, colon headlines,
  component-prefixed tool versions, date-led batch entries, bare versions).
- Resolves each entry's date from the heading first, then the repo's release
  tags; entries with neither are listed per repo under Undated records in
  their true file order rather than scattered across guessed months.
- Counts commits, first/last activity, and monthly totals per repo
  (read-only; member repos are never touched), and measures the language
  distribution by code lines with `tokei` (fork checkouts excludable per
  config; the section degrades gracefully when tokei is absent).
- Renders `ANNALS.md`: totals, a per-repo table, monthly activity bars, a
  stacked language-distribution bar plus ranked table, a newest-first
  timeline of every release grouped by month, and a coverage appendix
  reporting exactly how each date was resolved, plus release-shaped git
  tags that match no entry (the audit for tagged-but-never-logged work).
- Optionally writes three site artifacts beside the record: a Jekyll-ready
  page copy, a stat-line include, and an Atom feed of the newest releases.

The per-repo `patchnotes.md` files remain canonical. annals only reads them;
`ANNALS.md` is a projection, always reproducible with one command.

## Install

Requires Python 3.14+. Standard library only; `tokei` is the one optional
external tool (it powers the language-distribution section, which renders a
note instead of failing when tokei is missing).

```sh
uv tool install annals
# or: pipx install annals
```

## Quickstart

```sh
cd ~/my-projects          # any directory containing your git repos
annals init               # asks a few questions, writes annals.toml
annals                    # writes ANNALS.md
```

## Configuration

Settings live in `annals.toml`; `annals init` writes a commented starter.
Resolution order: an explicit `--config PATH`, else `./annals.toml` in the
current directory, else the root of a source checkout, else
`~/.config/annals/annals.toml`. No config anywhere is an error that points
at `annals init`, never a silent default.

| Section | Key | Meaning |
|---|---|---|
| `[workspace]` | `root` (required) | The directory containing your repos |
| `[workspace]` | `exclude` | Directory names never read (reference clones, forks) |
| `[workspace]` | `stats_only` | Owned repos without a `patchnotes.md`: commits count, no releases |
| `[run]` | `output` | Record path; relative resolves against the config file's directory |
| `[run]` | `intro` | Masthead paragraph, verbatim; `{generator}` becomes the version string |
| `[stats]` | `authors` | git `--author` patterns (OR); empty counts every commit |
| `[stats]` | `authors_display` | The attribution line the record prints |
| `[languages]` | `exclude` | Repos omitted from the language distribution only |
| `[descriptions]` | per repo | One-line dashboard descriptions |
| `[links]` | per repo | Public repos only: the dashboard links these names |
| `[site]` | `path`, `front_matter` | Page copy: the record wrapped in your front matter and a Liquid raw block |
| `[ledger]` | `path`, `link_url` | One stat paragraph include; `link_url` is the "the patchnotes" link target |
| `[feed]` | `path`, `site_url`, `limit` | Atom feed: newest `limit` entries; links derive from `site_url` |
| `[feed]` | `title`, `subtitle`, `page_url`, `id` | Optional overrides; defaults derive from `site_url` and the newest activity year |

## Usage

```sh
annals                   # regenerate ANNALS.md (plus configured site artifacts)
annals --stdout          # print the record instead of writing anything
annals --check           # exit 1 when the record on disk is stale
annals --config PATH     # use an alternate configuration file
annals init [PATH]       # write a starter annals.toml (default: ./annals.toml)
```

Exit codes: 0 success, 1 a stale or missing record under `--check`, 2 a
configuration problem.

## The site artifacts

The three artifacts are optional; configure the sections you want and drop
the rest:

- `[site]`: the same record as a publishable page (front matter plus a
  `{% raw %}` wrapper, so no headline can break a Jekyll build).
- `[ledger]`: a single totals paragraph, written for an include (the link
  target can be a template snippet; it is copied verbatim).
- `[feed]`: an Atom 1.0 document whose `updated` anchors to the newest
  activity date, so a quiet workspace regenerates byte-identical XML. Pin
  `id` once published: feed readers treat a changed id as a new feed.

## Development

```sh
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
```

Python 3.14, standard library only. The parser contract lives in
`spec.md`; new heading shapes get a fixture in `tests/test_parse.py`
first.

## License

MIT. See `LICENSE`.
