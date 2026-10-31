## annals v0.4.0: the audited record and the feed

Five changes, all reviewed and approved by you: the headline cap fix (sentence cut over a cap), masthead number polish, tag reconciliation audit, Atom feed artifact, and the newest-release line in the ledger. Tests-first for the parser per the repo's contract.

### 1. Headline cap (the crash-course bug)
- `tests/test_parse.py` FIRST: a crash-course-shaped fixture (`## v0.18.0 - 2026-10-07` over a 300+ char single paragraph ending in `VERSION -> 0.18.0.`) asserting the headline cuts at the first sentence end; the saforums short-paragraph shape asserting it stays quoted whole; a boundary pair at exactly 250/251 chars.
- `parse.py`: a `_SUMMARY_CAP = 250`. In `_headline_from_text`, the whole-quote paths (plain paragraph, bold/italic run inner text) return verbatim when at or under the cap; anything longer cuts at its first sentence end. Already sentence-cut paths (bullets, colon tails) untouched. saforums and Colophon are single sentences, so the existing record barely moves: only the 69 oversized entries shrink.
- `spec.md` Semantics: one amended sentence; the plain-paragraph quote gains "when it is headline-sized (250 characters or fewer); a longer one is body prose, not a summary, and cuts at its first sentence end (the crash-course shape)".

### 2. Masthead polish
- `render.py` dashboard bullet: `{total_entries:,}` and `{len(month_entries):,}` so the line reads `1,535 releases` like `5,048 commits` and the ledger already does.

### 3. Tag reconciliation audit
- `cli.py build()`: call `tag_dates()` once per repo, pass to `resolve_dates` and store on `RepoRecord` (new `tags` field, plus `has_patchnotes` so stats-only repos are excluded).
- `parse.py`: `unlogged_tags(entries, tags)`: for each version-shaped tag, reuse the existing `_tag_lookup` candidate logic in reverse (tag matches if any release entry's `(component, version)` produces it). Returns unmatched tag names.
- `render.py _coverage`: an "Unlogged" count column in the table (dash for stats-only repos) and a `### Tags without entries` subsection listing `tag (date)`, newest first, only when any exist. One prose sentence defines the column. This turns the record's completeness claim into something checked against git.

### 4. Atom feed artifact
- `config.py`: `FeedTarget(path, site_url, limit)`; defaults `~/.gitrepos/VirInvictus.github.io/patchnotes/feed.xml`, `https://virinvictus.github.io` (matches the site's `_config.yml` url), limit 50. A non-table `[feed]` is the same loud error as `[ledger]`.
- `render.py`: `render_feed(record, target)`: Atom 1.0, stdlib string assembly with `xml.sax.saxutils.escape`. Exactly-dated entries in the timeline's own ordering (extracted into a shared helper so feed and record can't diverge), first `limit`. Feed `id`/`self` at `{site_url}/patchnotes/feed.xml`, alternate link to `/patchnotes/`, `updated` anchored to `record.latest` at `T00:00:00Z` so a quiet workspace stays byte-identical (same determinism rule as the record). Entry ids are `tag:` URIs keyed on date, repo, and version or a sha1 headline slug; titles are the timeline line without markdown, XML-escaped.
- `cli.py`: write it like the other two targets. `annals.toml` gains the `[feed]` table.
- `scripts/publish-site`: add `patchnotes/feed.xml` to the porcelain check and the `git add` list; Jekyll copies the static file verbatim, so it serves at `/patchnotes/feed.xml`.
- Tests: escaping (`&`/`<` in headlines), limit, ordering, byte-stable regeneration, the config error, the CLI write.

### 5. Newest release in the ledger
- `render_ledger` gains one sentence: `The newest entry is **bindery-cli 0.59.0** (10-28).`, using the shared entry-name helper; omitted when nothing is dated.

### Housekeeping and release
- Spec: new `### The feed` subsection; CLI write list; roadmap gains Phase 9 (ticked); repo `AGENTS.md` "two configured site artifacts" becomes three; README mentions the feed.
- VERSION, `pyproject.toml`, `src/annals/__init__.py` to 0.4.0 together; new patchnotes entry `## v0.4.0 (2026-10-29)`; then `uv run annals` to regenerate all four artifacts.
- Verify: `uv run pytest`, `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run annals --check`, and a second `uv run annals` proving the feed is byte-identical.
- One local commit (repo is local-only, no push): `annals v0.4.0: the audited record and the feed` carrying code, tests, docs, VERSION, patchnotes, and the regenerated artifacts.
- Not in this turn: the annotated `v0.4.0` tag (stays approval-gated; I'll cut it on your go) and the site push (tonight's `publish-site` run publishes the three artifacts on its own).

Proposed patchnotes entry (goes in verbatim):
> ## v0.4.0 (2026-10-29)
>
> The audited record and the feed: the record now checks its own completeness against git, publishes as Atom, and its headlines stopped quoting whole paragraphs.
>
> - **Headline cap**: a harvested headline is verbatim when it is headline-sized (250 characters or fewer); a longer plain paragraph or run is body prose, not a summary, and cuts at its first sentence end. crash-course's 19 entries were rendering at up to 2,154 characters, several ending in the literal `VERSION -> x.y.z.` stamp; 69 of ~1,160 timeline entries ran over 300 characters. Short summaries (the saforums and Colophon shapes) are byte-identical.
> - **Tag reconciliation**: the coverage table gains an Unlogged column and a "Tags without entries" section: release-shaped tags that match no parsed entry, per repo, dated. The record's completeness claim is now checked against `git for-each-ref`, not asserted.
> - **The feed**: a third generator-owned site artifact, `patchnotes/feed.xml`: the newest 50 exactly-dated entries as Atom, anchored to the newest activity date like the record, byte-stable on quiet days. publish-site stages it with the other two.
> - **Ledger**: the front-page line names the newest entry.
> - **Display**: masthead and month counts carry thousands separators like every other number in the record.

70 tests today; expect ~85 after.