# Patchnotes

## v0.1.1 (2026-10-09)

The site edition: the record gains a published twin and loses its last
nondeterminism.

- **Site copy**: with a `[site]` target configured, `annals` also writes the
  record wrapped in Jekyll front matter and a Liquid `{% raw %}` block, for
  the VirInvictus site page at `/patchnotes/`. The wrapper guarantees no
  future headline can break the site build; the body is identical to
  `ANNALS.md`.
- **Byte-stable regeneration**: the masthead drops the generation date, and
  the span and current month anchor to the newest activity date instead of
  today. A quiet workspace now regenerates byte-identical output, so
  `--check` compares the whole file with no stamp exceptions, and the daily
  publish commits only on real change.
- **`scripts/publish-site`**: the daily pipeline the automation calls:
  regenerate, commit the local record, pull the site repo (ff-only), commit
  and push the site copy when its content changed, watch the Pages build for
  the pushed SHA, and revert the site commit if the build fails. Timed-out
  builds are reported, never reverted blind.

41 repos, 1,467 entries, 4 duplicates collapsed; 43 tests green, ruff clean.

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
