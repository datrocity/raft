from raft.manifest.manifest import Manifest


def test_empty_manifest_roundtrip():
    m = Manifest()
    assert Manifest.from_json(m.to_json()).sections == {}


def test_add_and_get_section():
    m = Manifest()
    m.add("params", {"lr": 0.01, "prior": "uniform"})
    assert m.sections["params"] == {"lr": 0.01, "prior": "uniform"}


def test_merge_into_existing_section():
    m = Manifest()
    m.add("code", {"git_sha": "abc"})
    m.merge("code", {"dirty": False})
    assert m.sections["code"] == {"git_sha": "abc", "dirty": False}


def test_merge_creates_missing_section():
    m = Manifest()
    m.merge("author", {"author": "pietro"})
    assert m.sections["author"] == {"author": "pietro"}


def test_append_to_list_section():
    m = Manifest()
    m.append("runs", {"at": "2026-08-15T14:22:03Z"})
    m.append("runs", {"at": "2026-08-15T15:00:00Z"})
    assert m.sections["runs"] == [
        {"at": "2026-08-15T14:22:03Z"},
        {"at": "2026-08-15T15:00:00Z"},
    ]


def test_json_roundtrip_preserves_content():
    m = Manifest()
    m.add("params", {"lr": 0.01})
    m.add("code", {"git_sha": "abc123", "dirty": False})
    m.append("runs", {"at": "2026-08-15T14:22:03Z"})
    round_tripped = Manifest.from_json(m.to_json())
    assert round_tripped.sections == m.sections
