import subprocess
import sys
import types

from raft.manifest.lineage import (
    activity_source,
    author_source,
    detect_activity,
    detect_author,
    git_source,
    timestamp_source,
)


def test_timestamp_source_returns_iso8601_utc():
    out = timestamp_source()
    assert "created_at" in out
    ts = out["created_at"]
    assert ts.endswith("Z")
    assert "T" in ts


def test_author_source_wraps_given_author():
    assert author_source("alice") == {"author": "alice"}


def test_detect_author_returns_nonempty_string():
    out = detect_author()
    assert isinstance(out, str)
    assert out


def test_activity_source_wraps_given_activity():
    assert activity_source("pipeline.py") == {"activity": "pipeline.py"}


def test_activity_source_wraps_none():
    assert activity_source(None) == {"activity": None}


def test_detect_activity_uses_jpy_session_name(monkeypatch):
    monkeypatch.setenv("JPY_SESSION_NAME", "/home/user/notebooks/analysis.ipynb")
    assert detect_activity() == "analysis.ipynb"


def test_detect_activity_falls_back_to_main_file(monkeypatch):
    monkeypatch.delenv("JPY_SESSION_NAME", raising=False)
    fake_main = types.SimpleNamespace(__file__="/some/path/myscript.py")
    monkeypatch.setitem(sys.modules, "__main__", fake_main)
    assert detect_activity() == "myscript.py"


def test_detect_activity_returns_none_when_undetectable(monkeypatch):
    monkeypatch.delenv("JPY_SESSION_NAME", raising=False)
    fake_main = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "__main__", fake_main)
    assert detect_activity() is None


def test_detect_activity_prefers_jpy_session_name_over_main_file(monkeypatch):
    monkeypatch.setenv("JPY_SESSION_NAME", "/home/user/nb.ipynb")
    fake_main = types.SimpleNamespace(__file__="/some/path/myscript.py")
    monkeypatch.setitem(sys.modules, "__main__", fake_main)
    assert detect_activity() == "nb.ipynb"


def test_git_source_outside_repo_returns_empty(tmp_path):
    assert git_source(cwd=tmp_path) == {}


def test_git_source_inside_repo_has_sha(tmp_path):
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-m",
            "init",
        ],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    out = git_source(cwd=tmp_path)
    assert "code" in out
    code = out["code"]
    assert "git_sha" in code
    assert len(code["git_sha"]) == 40
    assert code["dirty"] is False
    assert code["git_remote"] is None


def test_git_source_dirty_flag(tmp_path):
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-m",
            "init",
        ],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    (tmp_path / "new.txt").write_text("hi")

    out = git_source(cwd=tmp_path)
    assert out["code"]["dirty"] is True
