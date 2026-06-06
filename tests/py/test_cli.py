"""Unit tests for the traceability engine CLI entry point."""
from traceability.cli import main


def test_main_forwards_help_flag(capsys):
    #R001-T01: --help is forwarded to the verifier and returns success.
    rc = main(["--help"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Usage:" in out


def test_repo_root_is_cwd(tmp_path, monkeypatch, capsys):
    #R005-T01: an empty cwd yields no requirements docs (repo root is cwd).
    monkeypatch.chdir(tmp_path)
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "no requirements files" in out


def test_exit_status_propagates(tmp_path, monkeypatch):
    #R010-T01: success returns 0 and failure returns 1.
    assert main(["--help"]) == 0
    monkeypatch.chdir(tmp_path)
    assert main([]) == 1
