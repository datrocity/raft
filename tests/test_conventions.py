import datetime as dt

from raft.conventions import (
    WriteMode,
    canonicalize_params,
    experiment_folder_name,
    params_hash,
)


def test_write_mode_members():
    # v1 ships a single mode; other modes may be added later.
    assert WriteMode.WRITE_ON_CHANGE.name == "WRITE_ON_CHANGE"


def test_canonicalize_params_orders_keys():
    a = canonicalize_params({"b": 2, "a": 1})
    b = canonicalize_params({"a": 1, "b": 2})
    assert a == b == '{"a": 1, "b": 2}'


def test_canonicalize_params_handles_nested():
    out = canonicalize_params({"nested": {"y": 2, "x": 1}, "top": 3})
    assert out == '{"nested": {"x": 1, "y": 2}, "top": 3}'


def test_params_hash_is_stable_and_short():
    h1 = params_hash({"lr": 0.01, "prior": "uniform"})
    h2 = params_hash({"prior": "uniform", "lr": 0.01})
    assert h1 == h2
    assert len(h1) == 8
    assert all(c in "0123456789abcdef" for c in h1)


def test_params_hash_differs_for_different_params():
    assert params_hash({"lr": 0.01}) != params_hash({"lr": 0.02})


def test_experiment_folder_name_format():
    date = dt.date(2026, 8, 15)
    name = experiment_folder_name(date, "baseline", {"lr": 0.01})
    assert name.startswith("2026-08-15__baseline__")
    assert name.count("__") == 2
    _, _, h = name.split("__")
    assert h == params_hash({"lr": 0.01})
