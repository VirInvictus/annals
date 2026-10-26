"""Config + CLI end-to-end tests over a synthetic fixture workspace."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from annals.cli import main
from annals.config import load_config


def _git(path: Path, *args: str, env: dict | None = None) -> None:
    subprocess.run(
        ("git", "-C", str(path), *args),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")


def _commit(
    path: Path,
    message: str,
    when: str,
    name: str = "Test",
    email: str = "test@example.com",
) -> None:
    env = os.environ | {
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }
    (path / "f.txt").write_text(message + "\n")
    _git(path, "add", "-A")
    subprocess.run(
        ("git", "-C", str(path), "commit", "-m", message),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    release = ws / "repo-a"
    _init_repo(release)
    (release / "patchnotes.md").write_text(
        "## v1.1.0 (2026-03-05)\n\n### Two\n\n## v1.0.0 (2026-01-01)\n\n### One\n",
        encoding="utf-8",
    )
    _commit(release, "work", "2026-01-01T00:00:00")
    _commit(
        release,
        "upstream history",
        "2026-03-01T00:00:00",
        name="Upstream",
        email="jan@example.com",
    )

    stats_repo = ws / "sb"
    _init_repo(stats_repo)
    _commit(stats_repo, "work", "2026-02-01T00:00:00")

    excluded = ws / "calibre"
    _init_repo(excluded)
    (excluded / "patchnotes.md").write_text(
        "## v9.9.9 (2026-01-01)\n", encoding="utf-8"
    )
    _commit(excluded, "work", "2026-01-01T00:00:00")

    stray = ws / "stray"
    _init_repo(stray)
    _commit(stray, "work", "2026-01-01T00:00:00")
    return ws


def make_config(ws: Path, output: Path) -> Path:
    cfg = ws.parent / "annals.toml"
    site_out = ws.parent / "site" / "patchnotes.md"
    cfg.write_text(
        "[workspace]\n"
        f'root = "{ws}"\n'
        'exclude = ["calibre"]\n'
        'stats_only = ["sb"]\n'
        "\n[run]\n"
        f'output = "{output}"\n'
        "\n[stats]\n"
        'authors = ["test@example.com"]\n'
        'authors_display = "Test Author"\n'
        "\n[descriptions]\n"
        '"repo-a" = "The first repo"\n'
        "\n[links]\n"
        '"repo-a" = "https://example.com/repo-a"\n'
        "\n[site]\n"
        f'path = "{site_out}"\n'
        'front_matter = "---\\nlayout: default\\npermalink: /patchnotes/\\n---"\n',
        encoding="utf-8",
    )
    return cfg


def test_config_load_and_output_resolution(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    output = tmp_path / "out" / "RECORD.md"
    cfg = make_config(ws, output)
    config = load_config(cfg)
    assert config.workspace == ws
    assert config.output == output
    assert config.exclude == {"calibre"}
    assert config.stats_only == {"sb"}
    assert config.authors == ("test@example.com",)
    assert config.authors_display == "Test Author"
    assert config.descriptions == {"repo-a": "The first repo"}
    assert config.links == {"repo-a": "https://example.com/repo-a"}
    assert config.language_exclude == frozenset()
    assert config.site is not None
    assert config.site.path == tmp_path / "site" / "patchnotes.md"
    assert config.site.front_matter.startswith("---\n")


def test_config_without_site_section(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    cfg = ws.parent / "plain.toml"
    cfg.write_text(f'[workspace]\nroot = "{ws}"\n', encoding="utf-8")
    config = load_config(cfg)
    assert config.site is None


def test_defaults_when_config_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.toml")
    assert config.workspace.name == ".gitrepos"
    assert "calibre" in config.exclude
    assert "meoweconomy" in config.exclude
    assert "Coffer" in config.stats_only
    assert config.authors == ("larocque.brandon@gmail.com",)
    assert config.authors_display == ""
    assert config.site is None


def test_cli_stdout_end_to_end(tmp_path: Path, capsys) -> None:
    ws = make_workspace(tmp_path)
    output = tmp_path / "RECORD.md"
    cfg = make_config(ws, output)

    assert main(["--config", str(cfg), "--stdout"]) == 0
    captured = capsys.readouterr()
    text, summary = captured.out, captured.err

    assert "# The Annals" in text
    assert (
        "| [repo-a](https://example.com/repo-a) | The first repo | 2 | 1.1.0"
        " | 2026-03-05 | 1 | 2026-01-01 |" in text
    )
    assert "authored by Test Author" in text
    assert "larocque.brandon@gmail.com" not in text
    assert "test@example.com" not in text
    assert "- **03-05 · repo-a 1.1.0** · Two" in text
    assert "- **01-01 · repo-a 1.0.0** · One" in text
    assert "calibre" not in text
    assert "| sb | 0 |" in text
    assert "stray" in summary
    assert not output.exists()
    assert not (tmp_path / "site" / "patchnotes.md").exists()


def test_cli_write_then_check(tmp_path: Path, capsys) -> None:
    ws = make_workspace(tmp_path)
    output = tmp_path / "RECORD.md"
    cfg = make_config(ws, output)

    assert main(["--config", str(cfg)]) == 0
    assert output.exists()
    site_out = tmp_path / "site" / "patchnotes.md"
    site_text = site_out.read_text(encoding="utf-8")
    assert site_text.startswith("---\nlayout: default\npermalink: /patchnotes/\n---\n")
    assert "{% raw %}" in site_text and "{% endraw %}" in site_text
    assert "# The Annals" in site_text
    capsys.readouterr()

    assert main(["--config", str(cfg), "--check"]) == 0
    capsys.readouterr()

    output.write_text(
        output.read_text(encoding="utf-8") + "\nstray edit\n", encoding="utf-8"
    )
    assert main(["--config", str(cfg), "--check"]) == 1

    output.unlink()
    assert main(["--config", str(cfg), "--check"]) == 1
