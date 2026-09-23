import pytest

from raft.storage.file_datastore import FileDatastore


def test_write_then_read_roundtrip(tmp_path):
    ds = FileDatastore(tmp_path)
    ds.write("a/b/c.txt", b"hello")
    assert ds.read("a/b/c.txt") == b"hello"


def test_exists(tmp_path):
    ds = FileDatastore(tmp_path)
    assert not ds.exists("nope.txt")
    ds.write("yes.txt", b"x")
    assert ds.exists("yes.txt")


def test_read_missing_raises_key_error(tmp_path):
    ds = FileDatastore(tmp_path)
    with pytest.raises(KeyError):
        ds.read("nope.txt")


def test_list_dir_returns_sorted_names(tmp_path):
    ds = FileDatastore(tmp_path)
    ds.write("d/b.txt", b"")
    ds.write("d/a.txt", b"")
    ds.write("d/c.txt", b"")
    assert ds.list_dir("d") == ["a.txt", "b.txt", "c.txt"]


def test_list_dir_missing_raises_key_error(tmp_path):
    ds = FileDatastore(tmp_path)
    with pytest.raises(KeyError):
        ds.list_dir("no-such-dir")


def test_makedirs_creates_nested(tmp_path):
    ds = FileDatastore(tmp_path)
    ds.makedirs("a/b/c")
    assert (tmp_path / "a" / "b" / "c").is_dir()


def test_delete_removes_file(tmp_path):
    ds = FileDatastore(tmp_path)
    ds.write("x.txt", b"x")
    ds.delete("x.txt")
    assert not ds.exists("x.txt")


def test_delete_missing_raises_key_error(tmp_path):
    ds = FileDatastore(tmp_path)
    with pytest.raises(KeyError):
        ds.delete("nope.txt")


def test_write_overwrites(tmp_path):
    ds = FileDatastore(tmp_path)
    ds.write("f.txt", b"one")
    ds.write("f.txt", b"two")
    assert ds.read("f.txt") == b"two"
