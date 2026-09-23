import pandas as pd
import pandas.testing as pdt

from raft import init


def test_compute_or_load_computes_on_first_call(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    calls = {"n": 0}

    @exp.compute_or_load("processed")
    def make_processed():
        calls["n"] += 1
        return pd.DataFrame({"x": [1, 2, 3]})

    df = make_processed()
    assert calls["n"] == 1
    pdt.assert_frame_equal(df, pd.DataFrame({"x": [1, 2, 3]}))


def test_compute_or_load_loads_on_second_call(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    calls = {"n": 0}

    @exp.compute_or_load("processed")
    def make_processed():
        calls["n"] += 1
        return pd.DataFrame({"x": [1, 2, 3]})

    make_processed()
    df = make_processed()
    assert calls["n"] == 1  # not recomputed
    pdt.assert_frame_equal(df, pd.DataFrame({"x": [1, 2, 3]}))


def test_compute_or_load_project_scope(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    calls = {"n": 0}

    @proj.compute_or_load("shared")
    def make_shared():
        calls["n"] += 1
        return {"n": 42}

    make_shared()
    make_shared()
    assert calls["n"] == 1


def test_compute_or_load_across_experiments_uses_project_scope(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    calls = {"n": 0}

    @proj.compute_or_load("shared")
    def make_shared():
        calls["n"] += 1
        return {"n": 42}

    proj.experiment("baseline", lr=0.01)
    make_shared()
    proj.experiment("higher_lr", lr=0.05)
    make_shared()

    assert calls["n"] == 1
