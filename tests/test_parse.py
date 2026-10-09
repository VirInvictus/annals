"""Parser tests: every heading shape observed in the wild on 2026-10-09."""

from __future__ import annotations

from annals.parse import parse_patchnotes, resolve_dates


def one(text: str):
    entries, dupes = parse_patchnotes("repo", text)
    assert dupes == 0
    assert len(entries) == 1
    return entries[0]


def test_cquarry_style_paren_date_and_subtitle() -> None:
    entry = one(
        "## v1.26.2 (2026-10-09)\n"
        "\n"
        "### Mirroring Calibre 9.16: the first parity-watch audit lane\n"
        "\n"
        "Body prose.\n"
    )
    assert entry.kind == "release"
    assert entry.version == "1.26.2"
    assert entry.component is None
    assert entry.date == "2026-10-09"
    assert entry.headline == "Mirroring Calibre 9.16: the first parity-watch audit lane"


def test_calibrequarry_h1_no_v() -> None:
    entry = one(
        "# 3.61.0 (2026-10-09)\n\n### The EPUB3 dc:date round-trip fix (issue #4)\n"
    )
    assert entry.version == "3.61.0"
    assert entry.date == "2026-10-09"
    assert entry.headline == "The EPUB3 dc:date round-trip fix (issue #4)"


def test_carrel_no_v_prefix() -> None:
    entry = one("## 0.9.10 (2026-09-15)\n\n### The final-blitz release\n")
    assert entry.version == "0.9.10"
    assert entry.headline == "The final-blitz release"


def test_component_prefix_opends() -> None:
    entry = one("## darkfix-ds1 v0.1.3 (2026-10-07)\n")
    assert entry.component == "darkfix-ds1"
    assert entry.version == "0.1.3"
    assert entry.date == "2026-10-07"
    assert entry.headline == ""


def test_trailing_date_em_dash() -> None:
    entry = one("## v0.1.4 — 2026-08-09\n")
    assert entry.version == "0.1.4"
    assert entry.date == "2026-08-09"


def test_trailing_date_hyphen() -> None:
    entry = one("## v0.18.0 - 2026-10-07\n")
    assert entry.version == "0.18.0"
    assert entry.date == "2026-10-07"


def test_colon_headline_no_date() -> None:
    entry = one("## v3.2.1: viaduct starts without a keyring\n")
    assert entry.version == "3.2.1"
    assert entry.date is None
    assert entry.headline == "viaduct starts without a keyring"


def test_paren_text_is_headline_not_date() -> None:
    entry = one("## v1.0.0 (Stable Release)\n")
    assert entry.version == "1.0.0"
    assert entry.date is None
    assert entry.headline == "Stable Release"


def test_pre_release_suffix() -> None:
    entry = one("## v0.1.0-alpha (Planning Stage)\n")
    assert entry.version == "0.1.0-alpha"
    assert entry.headline == "Planning Stage"


def test_range_heading() -> None:
    entry = one("## v0.1.10 → v0.1.16 — Builder polish + interaction fixes\n")
    assert entry.version == "0.1.10"
    assert entry.label == "0.1.10 → 0.1.16"
    assert entry.date is None
    assert entry.headline == "Builder polish + interaction fixes"


def test_range_without_headline() -> None:
    entry = one("## v0.1.10 → v0.1.16\n")
    assert entry.label == "0.1.10 → 0.1.16"
    assert entry.headline == ""


def test_batch_date_led_opends() -> None:
    entry = one(
        "## 2026-09-06 hardening batch: save-inspect v0.9.6, ovr-map v0.3.1-0.3.3\n"
    )
    assert entry.kind == "batch"
    assert entry.version is None
    assert entry.date == "2026-09-06"
    assert "save-inspect v0.9.6" in entry.headline


def test_batch_date_led_paren_note() -> None:
    entry = one(
        "## 2026-09-17 (no version bump: refactor + tests + a companion script)\n"
    )
    assert entry.kind == "batch"
    assert entry.date == "2026-09-17"
    assert entry.headline == "no version bump: refactor + tests + a companion script"


def test_bare_version_no_date() -> None:
    entry = one("## v0.3.0\n")
    assert entry.version == "0.3.0"
    assert entry.date is None
    assert entry.headline == ""


def test_prose_paren_fork_shape() -> None:
    entry = one(
        "## The sealing lane's tail and the upstream security wave"
        " (2026-10-07, 0.6.44)\n"
    )
    assert entry.kind == "release"
    assert entry.version == "0.6.44"
    assert entry.date == "2026-10-07"
    assert entry.headline == ("The sealing lane's tail and the upstream security wave")


def test_prose_paren_without_version_is_batch() -> None:
    entry = one(
        "## Cross-repo blitz touches (2026-09-15, logged per grant #117; no release)\n"
    )
    assert entry.kind == "batch"
    assert entry.version is None
    assert entry.date == "2026-09-15"
    assert entry.headline == "Cross-repo blitz touches"


def test_title_and_prose_skipped() -> None:
    text = (
        "# Patchnotes\n"
        "\n"
        "Released versions appear here, newest first.\n"
        "\n"
        "### Just a prose headline\n"
        "\n"
        "## v1.0.0 (2026-01-01)\n"
    )
    entries, dupes = parse_patchnotes("repo", text)
    assert dupes == 0
    assert len(entries) == 1
    assert entries[0].version == "1.0.0"


def test_subtitle_scan_stops_at_next_entry() -> None:
    text = "## v2.0.0\n\n## v1.0.0 (2026-01-01)\n\n### Older\n"
    entries, _ = parse_patchnotes("repo", text)
    assert [e.headline for e in entries] == ["", "Older"]


def test_h3_version_heading_is_an_entry() -> None:
    entry = one("### v1.2.3 (2026-02-03)\n")
    assert entry.version == "1.2.3"
    assert entry.date == "2026-02-03"


def test_duplicate_versions_collapse() -> None:
    text = "## v1.0.0: The Wayland Release\n\n## v0.9.0 (2026-01-01)\n\n## v1.0.0: Stable\n"
    entries, dupes = parse_patchnotes("repo", text)
    assert dupes == 1
    assert [e.version for e in entries] == ["1.0.0", "0.9.0"]
    assert entries[0].headline == "The Wayland Release"


def test_same_version_different_component_kept() -> None:
    text = "## darkfix-ds1 v0.1.3 (2026-10-07)\n\n## darkfix-ds2 v0.1.3 (2026-10-07)\n"
    entries, dupes = parse_patchnotes("repo", text)
    assert dupes == 0
    assert len(entries) == 2


# --- date resolution ---


def _resolve(entries, tags=None, first_commit=None):
    resolve_dates(entries, tags or {}, first_commit)
    return entries


def test_resolve_inline() -> None:
    entry = one("## v1.0.0 (2026-01-01)\n")
    _resolve([entry])
    assert (entry.resolved, entry.source, entry.approx) == (
        "2026-01-01",
        "inline",
        False,
    )


def test_resolve_prefers_inline_over_tag() -> None:
    entry = one("## v1.0.0 (2026-01-01)\n")
    _resolve([entry], tags={"v1.0.0": "2026-02-02"})
    assert (entry.resolved, entry.source, entry.approx) == (
        "2026-01-01",
        "inline",
        False,
    )


def test_resolve_tag_exact() -> None:
    entry = one("## v0.3.0\n")
    _resolve([entry], tags={"v0.3.0": "2026-01-05"})
    assert (entry.resolved, entry.source, entry.approx) == ("2026-01-05", "tag", False)


def test_resolve_tag_bare_name() -> None:
    entry = one("## 0.9.10\n")
    _resolve([entry], tags={"0.9.10": "2026-09-15"})
    assert (entry.resolved, entry.source, entry.approx) == ("2026-09-15", "tag", False)


def test_resolve_component_tag() -> None:
    entry = one("## darkfix-ds1 v0.1.3\n")
    _resolve([entry], tags={"darkfix-ds1-v0.1.3": "2026-10-07"})
    assert (entry.resolved, entry.source, entry.approx) == ("2026-10-07", "tag", False)


def test_resolve_neighbor_marks_approx() -> None:
    text = "## v0.2.0\n\n## v0.1.0 (2026-01-01)\n"
    entries, _ = parse_patchnotes("repo", text)
    _resolve(entries)
    assert (entries[0].resolved, entries[0].source, entries[0].approx) == (
        "2026-01-01",
        "neighbor",
        True,
    )
    assert (entries[1].resolved, entries[1].source, entries[1].approx) == (
        "2026-01-01",
        "inline",
        False,
    )


def test_resolve_chain_falls_to_nearest_older() -> None:
    text = "## v0.3.0\n\n## v0.2.0\n\n## v0.1.0 (2026-01-01)\n"
    entries, _ = parse_patchnotes("repo", text)
    _resolve(entries)
    assert all(e.resolved == "2026-01-01" and e.approx for e in entries[:2])


def test_resolve_first_commit_bottom_anchor() -> None:
    text = "## v0.2.0\n\n## v0.1.0\n"
    entries, _ = parse_patchnotes("repo", text)
    _resolve(entries, first_commit="2025-12-01")
    assert all(
        e.resolved == "2025-12-01" and e.source == "first-commit" for e in entries
    )
