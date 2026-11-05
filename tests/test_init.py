"""`annals init` tests: the prompt sequence over injected answers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from annals.cli import main
from annals.config import load_config
from annals.init import run_init


class Answers:
    """A prompt function fed from a fixed list; exhausted list = EOF, like
    a closed stdin."""

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)

    def __call__(self, _text: str) -> str:
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


def minimal_answers(ws: Path) -> list[str]:
    # Root, authors, display, output (default), site artifacts declined.
    return [str(ws), "test@example.com", "Test Author", "", "n"]


def site_answers(ws: Path) -> list[str]:
    return minimal_answers(ws)[:-1] + [
        "y",  # configure site artifacts
        "",  # site copy path (default)
        "",  # front matter (default sample)
        "",  # ledger path (default)
        "",  # feed path (default)
        "https://example.org",  # site_url (required, no default)
    ]


def test_minimal_init_writes_parseable_config(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    target = tmp_path / "annals.toml"
    assert run_init(str(target), prompt=Answers(*minimal_answers(ws))) == 0
    config = load_config(target)
    assert config.workspace == ws
    assert config.authors == ("test@example.com",)
    assert config.authors_display == "Test Author"
    assert config.output == tmp_path / "ANNALS.md"
    assert config.site is None
    assert config.ledger is None
    assert config.feed is None


def test_init_dash_authors_count_every_commit(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    target = tmp_path / "annals.toml"
    answers = [str(ws), "-", "", "", "n"]
    assert run_init(str(target), prompt=Answers(*answers)) == 0
    assert load_config(target).authors == ()


def test_template_empty_authors(tmp_path: Path) -> None:
    from annals.init import _template

    text = _template(str(tmp_path), [], "Nobody", "ANNALS.md", None)
    assert "authors = []" in text


def test_init_site_artifacts(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    target = tmp_path / "annals.toml"
    assert run_init(str(target), prompt=Answers(*site_answers(ws))) == 0
    config = load_config(target)
    assert config.site is not None
    # Artifact paths stay as configured (resolved against the working
    # directory at write time); only [run] output resolves against the
    # config file's directory.
    assert config.site.path == Path("site/patchnotes.md")
    # The default sample is a single line with \n sequences, which TOML
    # turns into real newlines.
    assert config.site.front_matter == ("---\nlayout: default\ntitle: Patchnotes\n---")
    assert config.ledger is not None
    assert config.ledger.path == Path("site/_includes/ledger.md")
    assert config.feed is not None
    assert config.feed.path == Path("site/feed.xml")
    assert config.feed.site_url == "https://example.org"


def test_init_refuses_overwrite(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    target = tmp_path / "annals.toml"
    target.write_text("# keep me\n", encoding="utf-8")
    assert run_init(str(target), prompt=Answers("n")) == 1
    assert target.read_text(encoding="utf-8") == "# keep me\n"


def test_init_overwrite_confirmed(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    target = tmp_path / "annals.toml"
    target.write_text("# old\n", encoding="utf-8")
    answers = ["y", *minimal_answers(ws)]
    assert run_init(str(target), prompt=Answers(*answers)) == 0
    assert "root" in target.read_text(encoding="utf-8")


def test_init_eof_aborts_without_writing(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    target = tmp_path / "annals.toml"
    prompt: Callable[[str], str] = Answers()
    assert run_init(str(target), prompt=prompt) == 1
    assert not target.exists()


def test_init_bad_root_repeats_the_prompt(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    target = tmp_path / "annals.toml"
    answers = [str(tmp_path / "gone"), *minimal_answers(ws)]
    assert run_init(str(target), prompt=Answers(*answers)) == 0
    assert load_config(target).workspace == ws


def test_init_survives_quote_characters(tmp_path: Path) -> None:
    ws = tmp_path / 'we"ird'
    ws.mkdir()
    target = tmp_path / "annals.toml"
    assert run_init(str(target), prompt=Answers(*minimal_answers(ws))) == 0
    assert load_config(target).workspace == ws


def test_cli_init_command(tmp_path: Path, monkeypatch) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    answers = minimal_answers(ws)
    monkeypatch.setattr("builtins.input", lambda _text: answers.pop(0))
    target = tmp_path / "annals.toml"
    assert main(["init", str(target)]) == 0
    assert target.is_file()
    assert load_config(target).workspace == ws
