import json

import pytest

from raft import init
from raft.errors import ArtifactNotFound


def _exp_folder(tmp_path):
    return tmp_path / "walker" / next(
        p.name for p in (tmp_path / "walker").iterdir() if p.name != "global"
    )


def test_identical_save_does_not_create_new_version(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"k": 1}, "cfg")
    exp.save({"k": 1}, "cfg")

    files = sorted((_exp_folder(tmp_path) / "cfg").iterdir())
    data_files = [
        f for f in files
        if f.name.endswith(".json") and not f.name.endswith(".manifest.json")
    ]
    assert len(data_files) == 1
    assert data_files[0].name == "v1.json"


def test_identical_save_appends_run_record(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"k": 1}, "cfg")
    exp.save({"k": 1}, "cfg")

    manifest = json.loads(
        (_exp_folder(tmp_path) / "cfg" / "v1.manifest.json").read_text()
    )
    assert len(manifest["runs"]) == 2


def test_different_save_creates_new_version(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"k": 1}, "cfg")
    exp.save({"k": 2}, "cfg")

    versions = sorted(
        f.name
        for f in (_exp_folder(tmp_path) / "cfg").iterdir()
        if f.name.endswith(".json") and not f.name.endswith(".manifest.json")
    )
    assert versions == ["v1.json", "v2.json"]


def test_load_specific_older_version(tmp_path):
    """Reproduce-a-plot use case: load an older version by explicit number."""
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"k": 1}, "cfg")
    exp.save({"k": 2}, "cfg")
    exp.save({"k": 3}, "cfg")

    assert exp.load("cfg") == {"k": 3}
    assert exp.load("cfg", version=1) == {"k": 1}
    assert exp.load("cfg", version=2) == {"k": 2}


def test_load_missing_version_raises(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"k": 1}, "cfg")
    with pytest.raises(ArtifactNotFound):
        exp.load("cfg", version=42)
