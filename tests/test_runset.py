import pandas as pd

from raft import init


def _seed(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    for lr in (0.01, 0.02, 0.05):
        exp = proj.experiment(f"sweep_lr_{lr}", lr=lr, prior="uniform")
        exp.save(pd.DataFrame({"x": [lr, lr]}), "result")
    exp = proj.experiment("with_prior", lr=0.01, prior="gauss")
    exp.save(pd.DataFrame({"x": [999]}), "result")
    return proj


def test_runs_returns_all_experiments(tmp_path):
    proj = _seed(tmp_path)
    runs = proj.runs()
    assert len(list(runs)) == 4


def test_where_filters_by_param(tmp_path):
    proj = _seed(tmp_path)
    runs = proj.runs()
    hits = list(runs.where(lr=0.01))
    assert len(hits) == 2  # sweep_lr_0.01 and with_prior


def test_where_multi_criteria(tmp_path):
    proj = _seed(tmp_path)
    hits = list(proj.runs().where(lr=0.01, prior="gauss"))
    assert len(hits) == 1
    assert hits[0].name == "with_prior"


def test_iter_yields_runs_with_name_params_load(tmp_path):
    proj = _seed(tmp_path)
    for run in proj.runs().where(prior="uniform"):
        assert isinstance(run.name, str)
        assert "lr" in run.params
        df = run.load("result")
        assert isinstance(df, pd.DataFrame)


def test_frame_returns_dataframe_with_params(tmp_path):
    proj = _seed(tmp_path)
    df = proj.runs().frame()
    assert "lr" in df.columns
    assert "prior" in df.columns
    assert "name" in df.columns
    assert len(df) == 4


def test_where_filters_by_name(tmp_path):
    proj = _seed(tmp_path)
    hits = list(proj.runs().where(name="with_prior"))
    assert len(hits) == 1
    assert hits[0].name == "with_prior"


def test_where_by_name_matches_all_params_variants(tmp_path):
    """The grid pattern: one name, several params variants -- where(name=...)
    returns all of them, not just one."""
    proj = init("walker", datastore=str(tmp_path))
    for lr in [0.01, 0.02, 0.05]:
        exp = proj.experiment("baseline", lr=lr)
        exp.save({"lr": lr}, "cfg")

    hits = proj.runs().where(name="baseline")
    lrs = sorted(r.params["lr"] for r in hits)
    assert lrs == [0.01, 0.02, 0.05]


def test_where_combines_name_and_param(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    for lr in [0.01, 0.02, 0.05]:
        exp = proj.experiment("baseline", lr=lr)
        exp.save({"lr": lr}, "cfg")

    hits = list(proj.runs().where(name="baseline", lr=0.02))
    assert len(hits) == 1
    assert hits[0].params["lr"] == 0.02


def test_where_by_name_no_match_returns_empty(tmp_path):
    proj = _seed(tmp_path)
    hits = list(proj.runs().where(name="does_not_exist"))
    assert hits == []


def test_where_missing_param_excludes(tmp_path):
    proj = _seed(tmp_path)
    exp = proj.experiment("no_prior", lr=0.99)
    exp.save({"k": 1}, "cfg")
    hits = list(proj.runs().where(prior="uniform"))
    names = [r.name for r in hits]
    assert "no_prior" not in names


def test_run_load_specific_version(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp = proj.experiment("baseline", lr=0.01)
    exp.save({"v": 1}, "cfg")
    exp.save({"v": 2}, "cfg")

    run = next(iter(proj.runs()))
    assert run.load("cfg") == {"v": 2}
    assert run.load("cfg", version=1) == {"v": 1}


def test_summarize_returns_frame_with_params_and_summaries(tmp_path):
    proj = _seed(tmp_path)
    runs = proj.runs().where(prior="uniform")
    summary = runs.summarize(
        first_x=lambda r: r.load("result")["x"].iloc[0],
        row_count=lambda r: len(r.load("result")),
    )
    assert set(summary.columns) >= {"name", "lr", "prior", "first_x", "row_count"}
    assert len(summary) == 3
    assert summary["row_count"].tolist() == [2, 2, 2]


def test_load_all_returns_run_artifact_pairs(tmp_path):
    proj = _seed(tmp_path)
    hits = proj.runs().where(prior="uniform")
    pairs = hits.load_all("result")

    assert len(pairs) == 3
    for run, art in pairs:
        assert hasattr(run, "params")
        assert isinstance(art, pd.DataFrame)


def test_load_all_supports_same_name_grid(tmp_path):
    """The common grid pattern: same experiment name, different params, one
    entry per variant (no silent dict-key collision)."""
    proj = init("walker", datastore=str(tmp_path))
    for lr in [0.01, 0.02, 0.05]:
        exp = proj.experiment("baseline", lr=lr)
        exp.save(pd.DataFrame({"lr_col": [lr]}), "result")

    pairs = proj.runs().load_all("result")
    lrs = sorted(run.params["lr"] for run, _ in pairs)
    assert lrs == [0.01, 0.02, 0.05]


def test_load_all_skips_runs_missing_the_artifact(tmp_path):
    proj = init("walker", datastore=str(tmp_path))
    exp1 = proj.experiment("has_it", lr=0.01)
    exp1.save({"x": 1}, "result")
    proj.experiment("empty", lr=0.02)

    pairs = proj.runs().load_all("result")
    names = [run.name for run, _ in pairs]
    assert names == ["has_it"]
