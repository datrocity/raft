import json

import pandas as pd
import pandas.testing as pdt
import pytest

from raft.errors import ArtifactNotFound
from raft.project import Project


def _read_manifest(path):
    return json.loads(path.read_text())


def test_project_creates_datastore_root(tmp_path):
    Project("walker", datastore=str(tmp_path / "catalog"))
    assert (tmp_path / "catalog" / "walker").is_dir()


def test_project_save_and_load(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    df = pd.DataFrame({"a": [1, 2, 3]})
    proj.save(df, "processed_input")

    back = proj.load("processed_input")
    pdt.assert_frame_equal(back, df)


def test_project_save_writes_to_global_folder(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    proj.save({"k": "v"}, "config")
    assert (tmp_path / "catalog" / "walker" / "global" / "config" / "v1.json").is_file()
    assert (
        tmp_path / "catalog" / "walker" / "global" / "config" / "v1.manifest.json"
    ).is_file()


def test_project_has_returns_bool(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    assert proj.has("nope") is False
    proj.save({"k": 1}, "nope")
    assert proj.has("nope") is True


def test_project_load_missing_raises(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    with pytest.raises(ArtifactNotFound):
        proj.load("nope")


def test_project_load_returns_latest_version(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    proj.save({"v": 1}, "config")
    proj.save({"v": 2}, "config")
    assert proj.load("config") == {"v": 2}


def test_project_load_specific_version(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    proj.save({"v": 1}, "config")
    proj.save({"v": 2}, "config")
    proj.save({"v": 3}, "config")

    assert proj.load("config") == {"v": 3}
    assert proj.load("config", version=1) == {"v": 1}
    assert proj.load("config", version=2) == {"v": 2}


def test_project_load_missing_version_raises(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    proj.save({"v": 1}, "config")
    with pytest.raises(ArtifactNotFound):
        proj.load("config", version=42)


def test_project_init_helper_returns_project(tmp_path):
    from raft import init

    proj = init("walker", datastore=str(tmp_path / "catalog"))
    assert isinstance(proj, Project)
    assert proj.name == "walker"


def test_project_write_on_change_no_new_file_for_identical_data(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    proj.save({"k": 1}, "cfg")
    proj.save({"k": 1}, "cfg")

    files = sorted(
        (tmp_path / "catalog" / "walker" / "global" / "cfg").iterdir()
    )
    data_files = [
        f for f in files
        if f.name.endswith(".json") and not f.name.endswith(".manifest.json")
    ]
    assert len(data_files) == 1
    assert data_files[0].name == "v1.json"


def test_project_records_activity_and_author_override(tmp_path):
    proj = Project(
        "walker",
        datastore=str(tmp_path / "catalog"),
        activity="pipeline.py",
        author="alice",
    )
    assert proj.activity == "pipeline.py"
    assert proj.author == "alice"

    proj.save({"k": 1}, "cfg")
    manifest = _read_manifest(
        tmp_path / "catalog" / "walker" / "global" / "cfg" / "v1.manifest.json"
    )
    assert manifest["provenance"]["activity"] == "pipeline.py"
    assert manifest["provenance"]["author"] == "alice"


def test_project_auto_detects_author_when_not_given(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    assert isinstance(proj.author, str)
    assert proj.author

    proj.save({"k": 1}, "cfg")
    manifest = _read_manifest(
        tmp_path / "catalog" / "walker" / "global" / "cfg" / "v1.manifest.json"
    )
    assert manifest["provenance"]["author"] == proj.author


def test_project_run_record_carries_activity_and_author(tmp_path):
    proj = Project(
        "walker",
        datastore=str(tmp_path / "catalog"),
        activity="pipeline.py",
        author="alice",
    )
    proj.save({"k": 1}, "cfg")
    proj.save({"k": 1}, "cfg")  # identical -> appends a run record

    manifest = _read_manifest(
        tmp_path / "catalog" / "walker" / "global" / "cfg" / "v1.manifest.json"
    )
    assert len(manifest["runs"]) == 2
    for run in manifest["runs"]:
        assert run["activity"] == "pipeline.py"
        assert run["author"] == "alice"


def test_project_business_card_includes_activity_when_set(tmp_path):
    proj = Project(
        "walker", datastore=str(tmp_path / "catalog"), activity="pipeline.py"
    )
    card = proj._business_card("cfg", 1)
    assert card["activity"] == "pipeline.py"


def test_project_business_card_omits_activity_when_none(tmp_path):
    proj = Project("walker", datastore=str(tmp_path / "catalog"))
    proj.activity = None
    card = proj._business_card("cfg", 1)
    assert "activity" not in card
