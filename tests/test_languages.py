"""Language-distribution tests: tokei JSON parsing and the render section."""

from __future__ import annotations

import json
from pathlib import Path

from annals.languages import parse_tokei, repo_languages
from annals.render import Record, RepoRecord, render


def test_parse_tokei_drops_total_data_and_zero_code() -> None:
    text = json.dumps(
        {
            "Rust": {"code": 100, "lines": 150, "children": [{"Markdown": {}}]},
            "Markdown": {"code": 5},
            "JSON": {"code": 50},
            "TOML": {"code": 30},
            "Lua": {"code": 0},
            "Total": {"code": 185},
        }
    )
    assert parse_tokei(text) == {"Rust": 100}


def test_repo_languages_none_on_missing_path(tmp_path: Path) -> None:
    assert repo_languages(tmp_path / "does-not-exist") is None


def test_repo_languages_empty_on_prose_only_repo(tmp_path: Path) -> None:
    d = tmp_path / "prose"
    d.mkdir()
    (d / "notes.txt").write_text("just prose\nnothing else\n")
    (d / "README.md").write_text("# Notes\n\nWords.\n")
    assert repo_languages(d) == {}


def test_repo_languages_counts_code(tmp_path: Path) -> None:
    d = tmp_path / "code"
    d.mkdir()
    (d / "main.py").write_text("x = 1\ny = 2\n")
    langs = repo_languages(d)
    assert langs is not None
    assert langs.get("Python") == 2


def _record(languages: dict[str, int] | None) -> Record:
    repo = RepoRecord(name="repo", entries=[], languages=languages)
    return Record(repos=[repo], latest="2026-10-09", generator="annals 0.1.0")


def test_languages_section_bar_table_and_totals() -> None:
    text = render(_record({"Python": 600, "Rust": 400}))
    assert "## The languages" in text
    assert "1,000 lines of code · 2 languages · 1 repos" in text

    bar = next(line for line in text.splitlines() if line.startswith("█"))
    assert len(bar) == 40
    assert bar.count("█") == 24 and bar.count("▓") == 16
    assert "█ Python 60%" in text
    assert "▓ Rust 40%" in text

    # the bar lives in a fenced code block: shade characters only align in
    # monospace, and the site's prose font is proportional
    lines = text.splitlines()
    idx = lines.index(bar)
    assert lines[idx - 1] == "```" and lines[idx + 2] == "```"

    assert "| Python |" in text
    assert "60.0%" in text
    assert "| Rust |" in text
    assert "40.0%" in text


def test_languages_section_tail_and_other_row() -> None:
    languages = {"A": 700, "B": 200, "C": 60, "D": 30, "E": 10}
    text = render(_record(languages))
    bar = next(line for line in text.splitlines() if line.startswith("█"))
    # 4 shade chars for the top four, interpunct tail for the fifth
    assert (
        bar.count("█")
        + bar.count("▓")
        + bar.count("▒")
        + bar.count("░")
        + bar.count("·")
        == 40
    )
    assert "· other 1%" in text
    # the table shows every language, none fell to an "other" row
    assert "| other |" not in text


def test_languages_section_many_languages_other_row() -> None:
    languages = {f"Lang{i}": 100 - i for i in range(16)}
    text = render(_record(languages))
    assert "| other |" in text
    # top 12 named rows (Lang0..Lang11); Lang12 falls to the other row
    assert "| Lang11 |" in text
    assert "| Lang12 |" not in text


def test_languages_section_unavailable_note() -> None:
    text = render(_record(None))
    assert "Language distribution unavailable" in text
    assert "| Language |" not in text
