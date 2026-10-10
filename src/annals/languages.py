"""Language distribution: code lines per language, measured by tokei."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

# tokei reports data formats and prose alongside code; only actual
# programming and build/scripting languages belong in the distribution.
NON_LANGUAGES = frozenset(
    {
        "CSV",
        "JSON",
        "Markdown",
        "Org",
        "Plain Text",
        "PO File",
        "reStructuredText",
        "SVG",
        "Text",
        "TOML",
        "XML",
        "YAML",
    }
)


def parse_tokei(text: str) -> dict[str, int]:
    """Code lines per language from tokei's JSON output.

    Top-level entries only: a parent's code excludes its nested children, so
    nothing double-counts. The Total row, languages with no code lines, and
    data formats / prose are dropped.
    """
    data = json.loads(text)
    return {
        lang: stats["code"]
        for lang, stats in data.items()
        if lang != "Total" and lang not in NON_LANGUAGES and stats.get("code")
    }


def repo_languages(path: Path) -> dict[str, int] | None:
    """Code lines per language for one repo, shelling to the installed tokei.

    None when tokei is unavailable or fails (the section degrades to a note
    instead of failing the run); an empty dict when the repo has no code.
    """
    try:
        result = subprocess.run(
            ("tokei", "--output", "json", str(path)),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError, FileNotFoundError:
        return None
    return parse_tokei(result.stdout)
