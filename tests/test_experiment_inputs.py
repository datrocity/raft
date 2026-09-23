"""Tests for cumulative input tracking on save.

Design under test:

- Each ``exp.load(name)`` records the artifact's URI in a per-experiment
  loaded-inputs set (deduped, order-preserved).
- Every ``exp.save(...)`` embeds the *current* set as ``inputs:`` in the
  new artifact's manifest. The set is NOT cleared between saves --
  reason: notebooks load once and reuse in Python memory across many plots.
- ``proj.load(name)`` records into every currently-active experiment
  (tracked via ``weakref.WeakSet`` on the project). Experiments that go
  out of Python scope drop out automatically.
- ``exp.save(..., inputs=[...])`` overrides the auto-set for that one save.
  Entries may be short artifact names (resolved to the latest version in
  this experiment) or full ``raft://`` URIs.
"""

import gc
import json

import pytest

from raft import init
from raft.errors import ArtifactNotFound


def _experiment_folder(tmp_path):
    walker = tmp_path / "walker"
    return next(p for p in walker.iterdir() if p.name != "global")


def _read_inputs(exp_folder, artifact_name, version=1):
    manifest_path = exp_folder / artifact_name / f"v{version}.manifest.json"
    return json.loads(manifest_path.read_text()).get("inputs", [])


def test_experiment_scope_load_is_recorded_in_next_save(tmp_path):
    # Given: an experiment with a preprocessed artifact
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"pre": True}, "preprocessed")

    # When: we load it, then save a new artifact
    exp.load("preprocessed")
    exp.save({"out": 1}, "result")

    # Then: the new artifact records the loaded one as an input
    inputs = _read_inputs(_experiment_folder(tmp_path), "result")
    assert inputs == ["raft://walker/baseline/preprocessed/v1"]


def test_project_scope_load_is_recorded_in_experiment_save(tmp_path):
    # Given: a project-scope artifact and an active experiment
    proj = init("walker", datastore=str(tmp_path))
    proj.save({"raw": True}, "processed_input")
    exp = proj.experiment("baseline", lr=0.01)

    # When: the experiment loads the project artifact, then saves
    proj.load("processed_input")
    exp.save({"out": 1}, "result")

    # Then: the URI (with global scope) is in the new artifact's inputs
    inputs = _read_inputs(_experiment_folder(tmp_path), "result")
    assert inputs == ["raft://walker/global/processed_input/v1"]


def test_loaded_inputs_persist_across_saves(tmp_path):
    # Given: `results` loaded once, used by two consecutive saves
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"r": 1}, "results")

    # When: load results once, then save two plots
    exp.load("results")
    exp.save({"plot": "a"}, "plot_a")
    exp.save({"plot": "b"}, "plot_b")

    # Then: BOTH plot manifests reference results
    folder = _experiment_folder(tmp_path)
    expected = ["raft://walker/baseline/results/v1"]
    assert _read_inputs(folder, "plot_a") == expected
    assert _read_inputs(folder, "plot_b") == expected


def test_repeated_loads_are_deduped(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"r": 1}, "results")

    exp.load("results")
    exp.load("results")
    exp.load("results")
    exp.save({"plot": True}, "plot_a")

    inputs = _read_inputs(_experiment_folder(tmp_path), "plot_a")
    assert inputs == ["raft://walker/baseline/results/v1"]


def test_multiple_loads_are_recorded_in_insertion_order(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"a": 1}, "art_a")
    exp.save({"b": 2}, "art_b")

    exp.load("art_b")
    exp.load("art_a")
    exp.save({"c": 3}, "art_c")

    inputs = _read_inputs(_experiment_folder(tmp_path), "art_c")
    assert inputs == [
        "raft://walker/baseline/art_b/v1",
        "raft://walker/baseline/art_a/v1",
    ]


def test_explicit_inputs_kwarg_overrides_auto_set(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"a": 1}, "art_a")
    exp.save({"b": 2}, "art_b")
    exp.load("art_a")
    exp.load("art_b")

    exp.save({"c": 3}, "art_c", inputs=["art_a"])

    inputs = _read_inputs(_experiment_folder(tmp_path), "art_c")
    assert inputs == ["raft://walker/baseline/art_a/v1"]


def test_explicit_inputs_accepts_full_uris(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"a": 1}, "art_a")

    uri = "raft://walker/global/some_shared/v7"
    exp.save({"c": 3}, "art_c", inputs=[uri])

    inputs = _read_inputs(_experiment_folder(tmp_path), "art_c")
    assert inputs == [uri]


def test_explicit_inputs_unknown_short_name_raises(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    with pytest.raises(ArtifactNotFound):
        exp.save({"c": 3}, "art_c", inputs=["never_saved"])


def test_two_active_experiments_both_record_project_load(tmp_path):
    # Given: a project-scope artifact and two active experiments
    proj = init("walker", datastore=str(tmp_path))
    proj.save({"raw": True}, "shared")
    exp_a = proj.experiment("A", lr=0.01)
    exp_b = proj.experiment("B", lr=0.02)

    # When: proj.load happens while both are alive
    proj.load("shared")
    exp_a.save({"out": "a"}, "result")
    exp_b.save({"out": "b"}, "result")

    walker = tmp_path / "walker"
    a_folder = next(p for p in walker.iterdir() if "__A__" in p.name)
    b_folder = next(p for p in walker.iterdir() if "__B__" in p.name)
    expected = ["raft://walker/global/shared/v1"]
    assert _read_inputs(a_folder, "result") == expected
    assert _read_inputs(b_folder, "result") == expected


def test_grid_loop_pattern_records_only_current_iteration(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    proj.save({"raw": True}, "shared")

    for lr in [0.01, 0.02]:
        exp = proj.experiment(f"sweep_{lr}", lr=lr)
        proj.load("shared")
        exp.save({"out": lr}, "result")
        gc.collect()

    walker = tmp_path / "walker"
    for lr in [0.01, 0.02]:
        folder = next(p for p in walker.iterdir() if f"__sweep_{lr}__" in p.name)
        assert _read_inputs(folder, "result") == [
            "raft://walker/global/shared/v1"
        ]


def test_close_stops_project_load_recording(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    proj.save({"raw": True}, "shared")
    exp_a = proj.experiment("A", lr=0.01)
    exp_b = proj.experiment("B", lr=0.02)
    exp_a.close()

    proj.load("shared")
    exp_a.save({"out": "a"}, "result")
    exp_b.save({"out": "b"}, "result")

    walker = tmp_path / "walker"
    a_folder = next(p for p in walker.iterdir() if "__A__" in p.name)
    b_folder = next(p for p in walker.iterdir() if "__B__" in p.name)
    assert _read_inputs(a_folder, "result") == []
    assert _read_inputs(b_folder, "result") == ["raft://walker/global/shared/v1"]


def test_context_manager_auto_closes(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    proj.save({"raw": True}, "shared")

    with proj.experiment("A", lr=0.01) as exp_a:
        exp_a.save({"out": "a"}, "result")
    assert exp_a not in proj._active_experiments

    exp_b = proj.experiment("B", lr=0.02)
    proj.load("shared")
    exp_b.save({"out": "b"}, "result")

    walker = tmp_path / "walker"
    a_folder = next(p for p in walker.iterdir() if "__A__" in p.name)
    b_folder = next(p for p in walker.iterdir() if "__B__" in p.name)
    assert _read_inputs(a_folder, "result") == []
    assert _read_inputs(b_folder, "result") == ["raft://walker/global/shared/v1"]
