"""`annals init`: a short prompt sequence that writes a starter annals.toml."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

Prompt = Callable[[str], str]

# Written through _toml_line, so the \n sequences below stay escape
# sequences in the file and TOML turns them into real newlines.
_FRONT_MATTER_SAMPLE = "---\\nlayout: default\\ntitle: Patchnotes\\n---"


def _toml_str(value: str) -> str:
    """A path-like value: fully escaped basic string."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _toml_line(value: str) -> str:
    """A value whose backslash sequences are meant for TOML to process
    (front matter newlines); only quotes are escaped."""
    return '"' + value.replace('"', '\\"') + '"'


def _template(
    root: str,
    authors: list[str],
    display: str,
    output: str,
    site: dict[str, str] | None,
) -> str:
    lines = [
        "# annals configuration, written by `annals init`.",
        "#",
        "# Discovery: every directory under [workspace] root that carries a",
        "# patchnotes.md is a release repo. Directories in stats_only are owned",
        "# repos without a patchnotes.md: tracked for commit activity only.",
        "# Everything in exclude is never touched. Anything else shows up in the",
        "# run summary as ignored, so a new repo is never silently missed.",
        "",
        "[workspace]",
        f"root = {_toml_str(root)}",
        "",
        "[run]",
        "# Where the generated record lands; relative paths resolve against",
        "# this file's directory.",
        f"output = {_toml_str(output)}",
        "",
        "[stats]",
        "# Commit statistics count work authored by these identities (git",
        "# --author patterns, OR). Empty the list to count every commit on HEAD.",
        f"authors = [{', '.join(_toml_str(a) for a in authors)}]",
        "# The attribution line the record prints (masthead and dashboard).",
        f"authors_display = {_toml_str(display)}",
        "",
        "# One-line description per tracked repo, shown in the dashboard table.",
        "# New repos surface in the run summary as a reminder to add theirs.",
        "# [descriptions]",
        '# "repo-name" = "What it is"',
        "",
        "# Public repos only: the dashboard links these names. Private repos",
        "# stay plain text.",
        "# [links]",
        '# "repo-name" = "https://github.com/you/repo-name"',
    ]
    if site is None:
        return "\n".join(lines) + "\n"
    lines += [
        "",
        "[site]",
        "# The published copy: the same record wrapped in your front matter and",
        "# a Liquid raw block. Remove this section to generate ANNALS.md only.",
        f"path = {_toml_str(site['site_path'])}",
        f"front_matter = {_toml_line(site['front_matter'])}",
        "",
        "[ledger]",
        "# One stat paragraph written beside the site (a Jekyll include, for",
        "# example). Remove this section to skip the write.",
        f"path = {_toml_str(site['ledger_path'])}",
        "",
        "[feed]",
        "# The Atom artifact: the newest entries, newest first. site_url must",
        "# be absolute (feed links derive from it). Remove this section to",
        "# skip the write.",
        f"path = {_toml_str(site['feed_path'])}",
        f"site_url = {_toml_str(site['site_url'])}",
    ]
    return "\n".join(lines) + "\n"


def _git_config(key: str) -> str:
    try:
        result = subprocess.run(
            ("git", "config", "--get", key),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return ""
    return result.stdout.strip()


def run_init(path: str | None = None, prompt: Prompt | None = None) -> int:
    """Ask for the machine-specific settings and write annals.toml.

    Returns 0 on success, 1 on cancellation, refusal, or abort; every
    prompt answer is a line of stdin (EOF aborts cleanly).
    """
    if prompt is None:
        prompt = input

    def ask(label: str, default: str = "") -> str:
        suffix = f" [{default}]" if default else ""
        answer = prompt(f"{label}{suffix}: ").strip()
        return answer or default

    def ask_yes(label: str) -> bool:
        answer = prompt(f"{label} [y/N]: ").strip().lower()
        return answer in ("y", "yes")

    target = Path(path) if path else Path.cwd() / "annals.toml"

    try:
        if target.is_file() and not ask_yes(f"{target} already exists; overwrite?"):
            print("annals: init cancelled", file=sys.stderr)
            return 1
        while True:
            root = ask(
                "Workspace root (the directory containing your repos)",
                str(Path.cwd()),
            )
            if Path(root).expanduser().is_dir():
                break
            print(f"annals: no such directory: {root}", file=sys.stderr)
        author_text = ask(
            "Git author identities to count, comma-separated (- = every commit)",
            _git_config("user.email"),
        )
        if author_text in ("-", "none"):
            authors = []
        else:
            authors = [a.strip() for a in author_text.split(",") if a.strip()]
        display = ask("Name shown as the author", _git_config("user.name"))
        output = ask("Output file", "ANNALS.md")
        site = None
        if ask_yes("Also configure site artifacts ([site]/[ledger]/[feed])?"):
            site_path = ask("Site copy target path", "site/patchnotes.md")
            front_matter = ask(
                "Jekyll front matter (a \\n sequence becomes a newline)",
                _FRONT_MATTER_SAMPLE,
            )
            ledger_path = ask("Ledger include target path", "site/_includes/ledger.md")
            feed_path = ask("Atom feed target path", "site/feed.xml")
            site_url = ""
            while not site_url:
                site_url = ask("Site URL for the feed (absolute; required)")
            site = {
                "site_path": site_path,
                "front_matter": front_matter,
                "ledger_path": ledger_path,
                "feed_path": feed_path,
                "site_url": site_url,
            }
    except EOFError:
        print("annals: init aborted (input ended)", file=sys.stderr)
        return 1

    text = _template(root, authors, display, output, site)
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        print(
            f"annals: generated config does not parse ({exc}); nothing was written",
            file=sys.stderr,
        )
        return 1
    target.write_text(text, encoding="utf-8")
    print(f"annals: wrote {target}")
    print(
        "annals: run `annals` from this directory (or pass --config) to generate"
        " the record"
    )
    return 0
