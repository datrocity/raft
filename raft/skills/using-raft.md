---
name: using-raft
description: Use when writing Python code that interacts with a raft research catalog — creating experiments, saving artifacts, or reading past runs for meta-analysis.
---

# Using raft

`raft` is a research-catalog library with four nouns. Learn them and you know the API.

## Four nouns

- **Project** — a named workspace, one per research effort.
- **Experiment** — one named run with frozen params. Identity is `(project, name, params)`.
- **Artifact** — a saved thing (DataFrame, ndarray, image, dict).
- **Version** — automatic. Identical data → no new version (WRITE_ON_CHANGE); different data → next `v{N}`.

## Write

```python
import raft

proj = raft.init("walker", datastore="./catalog")
exp = proj.experiment("baseline", lr=0.01, prior="uniform")

# Params flow from the experiment; do not re-declare them
results = simulate(lr=exp.lr, prior=exp.prior)
exp.save(results, "result")
```

Every manifest records `author` and `activity` (the script/notebook/process
name) automatically where possible. If the user names a specific script,
notebook, or author explicitly, pass them at init instead of guessing:

```python
proj = raft.init("walker", datastore="./catalog", activity="train.py", author="jane")
```

## Cache expensive steps with @compute_or_load

At experiment scope:

```python
@exp.compute_or_load("preprocessed")
def preprocess():
    return expensive_preprocessing(raw_data)

data = preprocess()  # first call: computes and saves. Later: loads.
```

At project scope (shared across all experiments):

```python
@proj.compute_or_load("shared_input")
def make_shared():
    return download_and_clean()

data = make_shared()
```

## Read (meta-analysis)

```python
runs = proj.runs()                       # RunSet over every experiment
hits = runs.where(lr=0.01, prior="uniform")

# Per-run iteration
for run in hits:
    plot(run.load("result"), title=run.name)

# Summary frame — one row per run
summary = hits.summarize(
    final_loss=lambda r: r.load("result")["loss"].iloc[-1],
)

# load_all yields (Run, artifact) pairs — safe with same-name grid patterns
for run, result in hits.load_all("result"):
    plot(result, label=f"lr={run.params['lr']}")
```

## Reading an older version

`load` returns the latest version by default. Pass `version=N` to load an older one (e.g., to reproduce a plot whose manifest recorded `result/v2`):

```python
exp.load("result")              # latest
exp.load("result", version=2)   # specific
```

## Cross-scope input tracking

Loads (both `exp.load` and `proj.load`) are recorded automatically and embedded as `inputs:` in every subsequent artifact manifest. Cumulative — a `results` loaded once is credited as input for every later `save`.

Override with explicit inputs:

```python
exp.save(plot, "plot", inputs=["results"])         # short name
exp.save(plot, "plot", inputs=["raft://foo/global/x/v3"])  # full URI
```

## Extending a previous run

To try a variant of an existing experiment, create a new experiment with different params. Never mutate an existing one:

```python
proj.experiment("baseline", lr=0.01)   # existing
proj.experiment("baseline", lr=0.05)   # new folder, different hash
```

## Format overrides

Pandas default is parquet (dtypes preserved). CSV is opt-in for human-readable output:

```python
exp.save(df, "result")                 # v1.parquet
exp.save(df, "result", format="csv")   # v1.csv, with `# key value` metadata
```

## What raft does NOT do

- No sweep execution — write the loop yourself.
- No workflow orchestration.
- No config-file DSL — params are Python kwargs.
- No auto-instrumentation of cells.
- `@compute_or_load` decorates zero-argument functions only.
