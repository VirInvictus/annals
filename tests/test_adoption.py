"""Adoption tests: window math, cache loading, response parsing, config,
and the render section."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from annals.adoption import (
    AdoptionData,
    Row,
    _crates_windows,
    _pypi_windows,
    append_snapshot,
    load_adoption,
    merge_pypi_days,
    parse_crates,
    parse_pypistats,
)
from annals.config import load_config
from annals.render import Record, RepoRecord, render


def test_parse_pypistats_splits_bases() -> None:
    reply = {
        "package": "example-package",
        "type": "overall_downloads",
        "data": [
            {"category": "with_mirrors", "date": "2026-11-17", "downloads": 3779},
            {"category": "without_mirrors", "date": "2026-11-17", "downloads": 611},
            {"category": "without_mirrors", "date": "2026-11-16", "downloads": 590},
            {"category": "some_new_basis", "date": "2026-11-17", "downloads": 1},
        ],
    }
    parsed = parse_pypistats(json.dumps(reply))
    assert parsed["without_mirrors"] == {"2026-11-17": 611, "2026-11-16": 590}
    assert parsed["with_mirrors"] == {"2026-11-17": 3779}


def test_parse_crates_total() -> None:
    reply = {"crate": {"name": "example-crate", "downloads": 1234}}
    assert parse_crates(json.dumps(reply)) == 1234


def test_merge_pypi_days_fresh_values_win_and_stay_sorted() -> None:
    cached = {"without_mirrors": {"2026-11-16": 590}, "with_mirrors": {}}
    fresh = {
        "without_mirrors": {"2026-11-16": 601, "2026-11-17": 611},
        "with_mirrors": {"2026-11-17": 3779},
    }
    merged = merge_pypi_days(cached, fresh)
    assert merged["without_mirrors"] == {"2026-11-16": 601, "2026-11-17": 611}
    assert merged["with_mirrors"] == {"2026-11-17": 3779}
    assert list(merged["without_mirrors"]) == sorted(merged["without_mirrors"])


def test_append_snapshot_replaces_same_day_and_prunes() -> None:
    snaps = {f"2026-11-{day:02d}": day for day in range(1, 11)}
    merged = append_snapshot(snaps, "2026-11-10", 99, keep=5)
    assert merged == {
        "2026-11-06": 6,
        "2026-11-07": 7,
        "2026-11-08": 8,
        "2026-11-09": 9,
        "2026-11-10": 99,
    }


def test_windows_on_empty_series() -> None:
    assert _pypi_windows({}) == ((None, None, None), None)
    assert _crates_windows({}) == ((None, None, None), None)


def test_pypi_windows_boundaries_and_missing_days() -> None:
    # Newest day 2026-11-17: the 7-day window starts at 11-11 inclusive,
    # so the 11-10 sample falls outside 7 days but inside 30; absent days
    # count zero.
    series = {"2026-11-17": 5, "2026-11-11": 7, "2026-11-10": 3}
    windows, lifetime = _pypi_windows(series)
    assert windows == (12, 15, 15)
    assert lifetime == 15


def test_crates_windows_warm_up_then_appear() -> None:
    four_days = {
        "2026-11-14": 100,
        "2026-11-15": 110,
        "2026-11-16": 120,
        "2026-11-17": 130,
    }
    windows, lifetime = _crates_windows(four_days)
    assert windows == (None, None, None)
    assert lifetime == 130
    # The 7-day cutoff is exactly 11-10; that snapshot now qualifies. The
    # 30-day cutoff is 10-18, still older than every sample, so only the
    # 7-day column appears.
    with_history = dict(four_days, **{"2026-11-10": 80})
    windows, lifetime = _crates_windows(with_history)
    assert windows == (50, None, None)
    assert lifetime == 130


def test_load_adoption_missing_or_malformed_degrades(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"version": 1}), encoding="utf-8")
    for path in (tmp_path / "gone.json", bad, wrong):
        data = load_adoption(path, ("example-package",), ("example-crate",), False)
        assert data is not None
        assert data.has_data() is False
        assert data.as_of == ""
        assert [row.lifetime for row in data.rows] == [None, None]


def test_load_adoption_rows_asof_and_uncached_package(tmp_path: Path) -> None:
    cache = {
        "version": 1,
        "fetched_at": "2026-11-18T03:00:00+00:00",
        "packages": {
            "pypi:example-package": {
                "days": {
                    "without_mirrors": {"2026-11-17": 611, "2026-11-16": 590},
                    "with_mirrors": {"2026-11-17": 3779},
                }
            },
            "crates:example-crate": {"snapshots": {"2026-11-17": 1234}},
        },
    }
    path = tmp_path / "adoption.json"
    path.write_text(json.dumps(cache), encoding="utf-8")
    data = load_adoption(
        path,
        ("example-package", "lonely-package"),
        ("example-crate",),
        False,
    )
    assert data is not None
    assert data.as_of == "2026-11-17"
    assert data.has_data() is True
    assert [r.name for r in data.rows] == [
        "example-package",
        "lonely-package",
        "example-crate",
    ]
    pypi_row, lonely, crate_row = data.rows
    assert pypi_row.registry == "PyPI"
    assert pypi_row.lifetime == 1201
    # Both days sit inside the 7-day window ending at 11-17.
    assert pypi_row.windows == (1201, 1201, 1201)
    assert lonely.lifetime is None
    assert lonely.windows == (None, None, None)
    assert crate_row.registry == "crates.io"
    assert crate_row.lifetime == 1234


def test_load_adoption_mirror_toggle_picks_basis(tmp_path: Path) -> None:
    cache = {
        "packages": {
            "pypi:example-package": {
                "days": {
                    "without_mirrors": {"2026-11-17": 611},
                    "with_mirrors": {"2026-11-17": 3779},
                }
            }
        }
    }
    path = tmp_path / "adoption.json"
    path.write_text(json.dumps(cache), encoding="utf-8")
    plain = load_adoption(path, ("example-package",), (), False)
    assert plain is not None
    assert plain.mirrors is False
    assert plain.rows[0].lifetime == 611
    mirrored = load_adoption(path, ("example-package",), (), True)
    assert mirrored is not None
    assert mirrored.mirrors is True
    assert mirrored.rows[0].lifetime == 3779


def _record(adoption: AdoptionData | None) -> Record:
    return Record(
        repos=[RepoRecord(name="repo", entries=[])],
        latest="2026-11-18",
        generator="annals 0.7.0",
        adoption=adoption,
    )


def _sample_data(mirrors: bool = False) -> AdoptionData:
    rows = (
        Row(
            "example-package",
            "PyPI",
            "https://pypi.org/project/example-package/",
            (611, 1201, 1201),
            1201,
        ),
        Row(
            "example-crate",
            "crates.io",
            "https://crates.io/crates/example-crate/",
            (None, None, None),
            1234,
        ),
    )
    return AdoptionData(mirrors=mirrors, as_of="2026-11-17", rows=rows)


def test_adoption_section_table_links_and_placement() -> None:
    text = render(_record(_sample_data()))
    assert "## Adoption" in text
    assert "| Package | Registry | 7 days | 30 days | 3 months | Lifetime |" in text
    assert (
        "| [example-package](https://pypi.org/project/example-package/)"
        " | PyPI | 611 | 1,201 | 1,201 | 1,201 |" in text
    )
    assert (
        "| [example-crate](https://crates.io/crates/example-crate/)"
        " | crates.io | - | - | - | 1,234 |" in text
    )
    assert "as of 2026-11-17" in text
    assert "without mirrors" in text
    assert "accrue from daily samples" in text
    lines = text.splitlines()
    assert (
        lines.index("## The languages")
        < lines.index("## Adoption")
        < lines.index("## The record")
    )


def test_adoption_section_mirror_toggle_reads_both_ways() -> None:
    assert "with mirrors" in render(_record(_sample_data(mirrors=True)))
    assert "without mirrors" in render(_record(_sample_data(mirrors=False)))


def test_adoption_section_absent_and_degraded() -> None:
    text = render(_record(None))
    assert "## Adoption" not in text
    degraded = render(_record(AdoptionData(mirrors=False, as_of="", rows=())))
    assert "Adoption data unavailable" in degraded
    assert "| Package |" not in degraded


def _config(tmp_path: Path, body: str) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    cfg = tmp_path / "annals.toml"
    # The body comes before [workspace] so bare top-level keys (the
    # non-table rejection test) are not swallowed into it.
    cfg.write_text(body + f'[workspace]\nroot = "{ws}"\n', encoding="utf-8")
    return cfg


def test_config_adoption_target(tmp_path: Path) -> None:
    cfg = _config(
        tmp_path,
        "\n[adoption]\nmirrors = true\n"
        'pypi = ["example-package"]\n'
        'crates = ["example-crate"]\n'
        'cache = "stats.json"\n',
    )
    config = load_config(cfg)
    assert config.adoption is not None
    assert config.adoption.pypi == ("example-package",)
    assert config.adoption.crates == ("example-crate",)
    assert config.adoption.mirrors is True
    assert config.adoption.cache == tmp_path / "stats.json"


def test_config_adoption_defaults_and_absence(tmp_path: Path) -> None:
    cfg = _config(tmp_path, '\n[adoption]\npypi = ["example-package"]\n')
    config = load_config(cfg)
    assert config.adoption is not None
    assert config.adoption.cache == tmp_path / "adoption.json"
    assert config.adoption.mirrors is False
    assert config.adoption.crates == ()
    empty = _config(tmp_path, "\n[adoption]\npypi = []\ncrates = []\n")
    assert load_config(empty).adoption is None
    plain = _config(tmp_path, "")
    assert load_config(plain).adoption is None


def test_config_rejects_non_table_adoption(tmp_path: Path) -> None:
    cfg = _config(tmp_path, "\nadoption = true\n")
    with pytest.raises(ValueError, match="adoption"):
        load_config(cfg)
