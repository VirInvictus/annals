# Patchnotes

## v0.4.0 (2026-10-29)

The audited record and the feed: the record now checks its own completeness
against git, publishes as Atom, and its headlines stopped quoting whole
paragraphs.

- **Headline cap**: a harvested headline is verbatim while it is
  headline-sized (250 characters or fewer); a longer plain paragraph or
  bold/italic run is body prose, not a summary, and cuts at its first
  sentence end. crash-course's entries were rendering at up to 2,154
  characters, several ending in the literal `VERSION -> x.y.z.` stamp, and
  69 of ~1,160 timeline entries ran over 300 characters. Short summaries
  (the saforums and Colophon shapes) are byte-identical.
- **Tag reconciliation**: the coverage table gains an Unlogged column and a
  "Tags without entries" section: release-shaped tags that match no parsed
  entry, per repo, dated. The record's completeness claim is now checked
  against `git for-each-ref`, not asserted. The audit runs from each repo's
  first workspace-authored commit onward (a fork checkout's inherited
  upstream tags are not this workspace's unlogged releases), and versions
  named inside batch entries count as logged, including an a.b.c-d.e.f
  patch run (the opends wave shape). Stats-only repos show a dash: no log
  to audit.
- **The feed**: a third generator-owned site artifact, `patchnotes/feed.xml`:
  the newest 50 exactly-dated entries as Atom, anchored to the newest
  activity date like the record, byte-stable on quiet days. publish-site
  stages it with the other two; entry ids are `tag:` URIs keyed on date,
  repo, and version, and titles are XML-escaped timeline lines.
- **Ledger**: the front-page line names the newest entry ("The newest entry
  is **bindery-cli 0.59.0** (10-28)." as of this writing), from the same
  ordering helper the timeline and feed share, so the three can never
  disagree about what is newest.
- **Display**: masthead and month counts carry thousands separators like
  every other number in the record ("1,535 releases", not "1535" beside
  "5,048 commits").

86 tests green (up from 70), ruff clean.

## v0.3.0 (2026-10-27)

The front-page ledger: the workspace totals now surface on the site's
front door, one paragraph above the fold, not only on the patchnotes page.

- **Ledger line**: a new `[ledger]` target. Each run writes one
  generator-authored paragraph (the totals, the month's shape, the
  patchnotes link) to the site's `_includes/ledger.md`, which the site
  README renders with a Liquid include tag. The file is generator-owned
  like the site copy: created when missing, overwritten every run, so a
  quiet workspace stays byte-identical and hand-authored pages are never
  touched. The paragraph anchors to the newest activity date like the
  rest of the record, and carries no em-dashes, like all
  generator-authored prose.
- **publish-site**: stages the include alongside patchnotes.md, so a
  ledger change ships in the same daily commit. Both staged files are
  generator-owned; blind staging can never sweep hand edits into a daily
  refresh.
- **Config**: a non-table `[ledger]` value is a loud error instead of a
  silent skip, and singular counts pluralize correctly on the front
  page ("1 repository", not "1 repositories").

## v0.2.0 (2026-10-26)

The parser repair and the public-page grounding: every entry now carries
its source's headline, the dashboard says what each repo is, and the page
stops handing scrapers the raw email.

- **Parser**: entries start at heading levels 1-2 only (re-verified against
  the corpus 2026-10-25; the old level-3 rule minted phantom releases:
  "bindery-cli The 0.41.0" was live on the public page, Hermitage's six
  "cquarry x.y" subtitles were entries, and a python fence in meoweconomy
  produced a "through 6.10"). The headline harvest extends past the `###`
  subtitle: bold and italic lead runs (the Hearth, Hearthfall, and
  Framework shapes), colon-label runs extended to their sentence end (the
  lattice shape), plain summary paragraphs (the saforums, Colophon, and
  lattice shapes), keep-a-changelog category labels and bare acronym
  section labels looking through as structure, thematic breaks transparent,
  fenced code blocks never contributing, and a first-bullet fallback
  (approved 2026-10-25) that headlines bullet-led sources at their
  sentence boundary. 643 of 1,660 entries rendered bare before; zero do
  now. Two source typos the repair surfaced went back to their repos:
  CalibreQuarry's v3.75.0 entry was dated one day after its own tag, and
  lattice-music's v6.4.0 heading carried its date twice.
- **Dashboard grounding**: a "What it is" column carries a one-line
  description per repo from the new `[descriptions]` config table (43
  entries), and public repos' names link to GitHub through the `[links]`
  table (31 of the 42 repos with remotes; private repos stay plain text).
- **Attribution**: `[stats] authors_display` puts "Brandon LaRocque" on
  the masthead and the Coverage footnote; the raw git filter email stays
  machine-side, off the published page.
- **Languages**: one method line under the section states what tokei
  counts (tracked trees, forks and reference clones excluded, no
  lockfiles, a snapshot rather than a pace claim), so the total is not
  misread as a velocity number.
- **Config**: meoweconomy moves to `exclude` (retired from the portfolio
  record on 2026-08-08; its remote is not VirInvictus), dropping its 118
  entries and ~45k Python lines from the public counts.

First run at 0.2.0: 43 repos, 1,531 entries, 3 duplicates collapsed,
every entry carrying a headline; 67 tests green, ruff clean.

## v0.1.3 (2026-10-09)

The stacked language bar moves into a fenced code block: display fix, no
data changes. The shade characters only align in monospace, and the site's
prose font is proportional serif, so on /patchnotes/ the bar rendered as
fallback glyphs with segments of drifting width and a legend that
soft-wrapped into the bar. In a code block both lines render in IBM Plex
Mono on the site and stay identical everywhere else.

## v0.1.2 (2026-10-09)

The languages: a new section between the dashboard and the record.

- **Measurement**: code lines per language from the installed `tokei`
  (one JSON call per repo). Data formats and prose in tokei's output are
  dropped, so the distribution counts programming and build/scripting
  languages only. A missing tokei degrades the section to a note, never a
  failure.
- **Fork exclusion**: `[languages]` exclude drops repos from this section
  only; Carrel-calibre-web's checkout carries upstream calibre-web's
  131k lines of JavaScript, which said nothing about this workspace's
  languages. Commits and releases still count it exactly as before.
- **Display**: a stacked proportion bar with a distinct shade character per
  top language (█ ▓ ▒ ░, interpunct tail) and largest-remainder rounding so
  segments sum exactly to the width, then a ranked table of the top twelve
  languages plus `other`, each with share, code lines, and repo count.

420,286 lines of code across 27 languages in the first rendering:
Rust 39%, Python 35%, GDScript 12%, C 6%. 51 tests green, ruff clean.

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
