# Patchnotes

## v0.1.0 (2026-10-09)

The first cut: the whole generator in one release.

- **Parser**: three entry shapes covering every heading convention in the
  workspace (version-led with paren, separator, or colon dates and optional
  component words and range arrows; date-led batch entries; prose-paren fork
  entries), subtitle pickup for headline-less entries, and per-repo
  duplicate collapsing keyed on (component, version).
- **Date resolution**: inline heading date first, then the repo's release
  tags, then neighbor and first-commit guesses, which are computed and
  counted but never enter the timeline; approximate entries land in the
  Undated records section in true file order instead of piling onto guessed
  months.
- **Statistics**: per-repo commit counts, first/last activity, and monthly
  histograms, read-only, filtered to the configured author identities so
  fork histories never count upstream commits.
- **Renderer**: masthead, dashboard (totals, per-repo table, monthly
  activity bars), year-month timeline of exactly dated entries, and a
  coverage appendix reporting how every date was resolved.
- **CLI**: `annals` writes `ANNALS.md` and prints a coverage summary;
  `--stdout` prints without writing; `--check` exits 1 when the file is
  stale (the generation stamp line is excluded from the comparison).

First full run: 41 repositories tracked, 1,467 entries, 4 duplicates
collapsed, 41 tests green, ruff clean.
