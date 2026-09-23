"""End-to-end smoke test: cache, save, load, meta-analyze, version pinning."""

import pandas as pd

import raft


def test_full_flow(tmp_path):
    proj = raft.init("walker", datastore=str(tmp_path))

    calls = {"pre": 0}

    @proj.compute_or_load("processed_input")
    def preprocess():
        calls["pre"] += 1
        return pd.DataFrame({"x": range(10)})

    # Grid: same experiment name, different params
    for lr in (0.01, 0.02, 0.05):
        exp = proj.experiment("baseline", lr=lr, prior="uniform")
        _ = preprocess()  # cached after first
        exp.save(
            pd.DataFrame({"loss": [1.0 / (1 + i * lr) for i in range(5)]}),
            "result",
        )

    assert calls["pre"] == 1  # only computed once, reused across the grid

    runs = proj.runs()
    assert len(runs) == 3

    summary = runs.summarize(
        final_loss=lambda r: r.load("result")["loss"].iloc[-1],
    )
    assert set(summary.columns) >= {"name", "lr", "prior", "final_loss"}
    assert len(summary) == 3

    # load_all returns pairs; grid-safe with same-name-different-params
    pairs = runs.load_all("result")
    assert len(pairs) == 3
    lrs = sorted(r.params["lr"] for r, _ in pairs)
    assert lrs == [0.01, 0.02, 0.05]


def test_reproduce_older_version(tmp_path):
    """Save twice, then verify we can load the earlier version."""
    proj = raft.init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"n": 1}, "cfg")
    exp.save({"n": 2}, "cfg")

    assert exp.load("cfg") == {"n": 2}
    assert exp.load("cfg", version=1) == {"n": 1}
