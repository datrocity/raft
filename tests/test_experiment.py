import datetime as dt
import json

import pandas as pd
import pandas.testing as pdt

from raft import init


def _today():
    return dt.date.today().isoformat()


def test_experiment_creates_dated_folder(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    proj.experiment("baseline", lr=0.01, prior="uniform")

    walker = tmp_path / "walker"
    subs = [p.name for p in walker.iterdir() if p.name != "global"]
    assert len(subs) == 1
    folder = subs[0]
    assert folder.startswith(_today() + "__baseline__")


def test_experiment_writes_params_json(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    proj.experiment("baseline", lr=0.01, prior="uniform")
    walker = tmp_path / "walker"
    exp_folder = next(p for p in walker.iterdir() if p.name != "global")
    params = json.loads((exp_folder / "params.json").read_text())
    assert params == {"lr": 0.01, "prior": "uniform"}


def test_experiment_params_are_attribute_accessible(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01, prior="uniform")
    assert exp.lr == 0.01
    assert exp.prior == "uniform"
    assert exp.params == {"lr": 0.01, "prior": "uniform"}


def test_experiment_save_and_load_dataframe(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    df = pd.DataFrame({"a": [1, 2, 3]})
    exp.save(df, "result")
    pdt.assert_frame_equal(exp.load("result"), df)


def test_experiment_reopens_by_identity(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp1 = proj.experiment("baseline", lr=0.01)
    exp1.save({"k": 1}, "cfg")

    exp2 = proj.experiment("baseline", lr=0.01)  # same identity
    assert exp2.load("cfg") == {"k": 1}


def test_experiment_different_params_makes_different_folder(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    proj.experiment("baseline", lr=0.01)
    proj.experiment("baseline", lr=0.02)
    walker = tmp_path / "walker"
    exp_folders = [p.name for p in walker.iterdir() if p.name != "global"]
    assert len(exp_folders) == 2


def test_experiment_short_form_via_module(tmp_path):
    import raft

    exp = raft.experiment(
        "walker", "baseline", datastore=str(tmp_path), lr=0.01
    )
    exp.save({"k": 1}, "cfg")
    assert exp.load("cfg") == {"k": 1}


def test_experiment_manifest_records_activity_and_author_override(tmp_path):
    proj = init(
        "walker", datastore=str(tmp_path), activity="pipeline.py", author="alice"
    )
    proj.experiment("baseline", lr=0.01)
    walker = tmp_path / "walker"
    exp_folder = next(p for p in walker.iterdir() if p.name != "global")
    manifest = json.loads((exp_folder / "manifest.json").read_text())
    assert manifest["provenance"]["activity"] == "pipeline.py"
    assert manifest["provenance"]["author"] == "alice"


def test_experiment_artifact_manifest_inherits_activity_and_author(tmp_path):
    proj = init(
        "walker", datastore=str(tmp_path), activity="pipeline.py", author="alice"
    )
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"k": 1}, "cfg")

    walker = tmp_path / "walker"
    exp_folder = next(p for p in walker.iterdir() if p.name != "global")
    manifest = json.loads((exp_folder / "cfg" / "v1.manifest.json").read_text())
    assert manifest["provenance"]["activity"] == "pipeline.py"
    assert manifest["provenance"]["author"] == "alice"


def test_experiment_auto_detects_author_when_not_given(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    proj.experiment("baseline", lr=0.01)
    walker = tmp_path / "walker"
    exp_folder = next(p for p in walker.iterdir() if p.name != "global")
    manifest = json.loads((exp_folder / "manifest.json").read_text())
    assert manifest["provenance"]["author"] == proj.author


def test_experiment_business_card_includes_activity_when_set(tmp_path):
    proj = init("walker", datastore=str(tmp_path), activity="pipeline.py")
    exp = proj.experiment("baseline", lr=0.01)
    card = exp._business_card("result", 1)
    assert card["activity"] == "pipeline.py"


def test_experiment_business_card_omits_activity_when_none(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    proj.activity = None
    exp = proj.experiment("baseline", lr=0.01)
    card = exp._business_card("result", 1)
    assert "activity" not in card
