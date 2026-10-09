# CLAUDE.md

Guidance for any coding agent working in this repository.

## What this is

`annals` is the workspace work-record generator: it walks every repo under
`~/.gitrepos/`, reads each owned repo's `patchnotes.md` and git history, and
renders two files: `ANNALS.md` at this repo's root (the canonical projection)
and the site copy at `~/.gitrepos/VirInvictus.github.io/patchnotes.md` (the
same record wrapped in Jekyll front matter and a Liquid raw block, published
at `/patchnotes/`). `scripts/publish-site` is the daily pipeline: regenerate,
commit locally, commit and push the site copy when it changed, verify the
Pages build, revert on failure. Python 3.14, standard library only, no
network (the publish script's git/gh calls are its only outbound surface).

## Load-bearing distinction

`patchnotes.md` in THIS repo is annals' own release log (house convention).
The generated record is `ANNALS.md`, never hand-edited: every byte of it is
reproducible with `uv run annals`, and `annals --check` exits 1 when the file
on disk is stale. The site copy in the VirInvictus repo is generated the same
way and equally never hand-edited; the daily automation owns both. Do not
rename any of the three files.

## Read-only guarantee

The tool only ever reads member repos (`patchnotes.md`, `git log`,
`git for-each-ref`). It writes exactly one file: `ANNALS.md` in this repo.
It never commits, never pushes, and never writes under the workspace root.
Any change that breaks this guarantee is a spec violation, not a refactor.

## Commands

- `uv run annals`: regenerate `ANNALS.md`, print a summary and coverage report.
- `uv run annals --stdout`: print to stdout, write nothing.
- `uv run annals --check`: exit 1 when `ANNALS.md` is stale (automation hook).
- `uv run pytest`: test suite.
- `uv run ruff check src tests` and `uv run ruff format --check src tests`.

## Version carriers

Three files carry the version and must move together on a bump: `VERSION`,
`pyproject.toml`, and `src/annals/__init__.py` (`__version__`, which stamps
the ANNALS.md masthead). `uv.lock` regenerates itself.

## Config

`annals.toml` at the repo root: workspace root, the exclusion list (reference
clones plus the two local-only audit repos), the stats-only includes (owned
repos without a `patchnotes.md`), and the output path. A new owned repo
without a `patchnotes.md` means a new `stats_only` entry; the run summary
surfaces ignored directories so nothing owned is silently missed.

## Parser contract

The entry-shape table and the date-resolution order are the contract in
`spec.md` (Semantics). The heading zoo was verified against every
release-cutting repo in the workspace on 2026-10-09. When a new heading
shape appears in the wild, add a fixture to `tests/test_parse.py` first,
then touch `parse.py`.

`logo.svg` is a placeholder, flagged as such in a comment inside the file.
