# `raft` keeps you afloat on the data lake

Experiment-first research catalog for scientists. Give research results a persistent, queryable identity tied to the parameters and code that produced them.

`raft` is a small Python library introducing a small number of commands to save, load, and query the artifacts that your research creates: data, tables, plots, anything! Lineage, versioning, smart caching, and meta-analysis fall out of a handful of calls in the flow of normal research scripts and notebooks.

`raft` is not an organizing tool that forces you to join a new tidiness cult.

**NEW** `raft` now ships with an AI skill to help you import your messy research files into `raft`, using your favorite AI assistant!!

## Installation with `pip`

The PyPI distribution is `data-raft` (`raft` was already taken); everything else — the import (`import raft`), the CLI (`raft ...`), the repo — is just `raft`.

    pip install data-raft


## 1. Why raft?

Every research project rediscovers the same problem: after enough experiments, `results/` turns into `run3_final.csv`, `run3_final_FIXED.csv`, `sweep_lr0.01/`, and a git history that no longer matches what actually produced any of them. Six months later, nobody — including you — can answer "which parameters made this plot?" or "what code produced this array?"

`raft` answers that by giving every saved result an explicit identity: which **project** it belongs to, which **experiment** (a name plus the exact parameters) produced it, which git commit, who's the author, and when it was created. That identity travels with the file rather than living in a database you might lose. A compact "business card" of it (project, experiment, parameters, git commit, author, timestamp) is embedded directly in the data file itself whenever the format allows (parquet metadata, PNG text chunks, CSV comment lines), and the full record always lives in a small JSON file (`manifest.json`) saved right next to it. You don't need anything special to access your data, `ls` the folder, `cat` the manifest, copy your data around anywhere.

**Lineage** falls out for free: `raft` keeps track of the data you `load()` when doing an experiment, and records it in the metadata of your results when you `save()`. Given a final analysis plot, you can always reconstruct the full graph of data that led to it.

On disk, it looks like this:

    catalog/walker/                                    <- project
      global/                                          <- project-scope shared artifacts
        processed_input/
          v1.parquet
          v1.manifest.json
      2026-08-15__baseline__a3f18d02/                  <- experiment folder
        params.json
        manifest.json
        result/
          v1.parquet
          v1.manifest.json

Every experiment folder is self-contained: `params.json` reconstructs the parameters, and every artifact carries its own manifest, so a folder survives being copied or moved.

## 2. Projects, experiments, parameters, save/load

There's only five things you need to learn to understand `raft`:

- An **artifact** is anything you want to save (a DataFrame, an array, an image, a dictionary, ...).
- Each artifact is saved with a **version**. By default, `raft` saves you from overwriting an existing experimental file, and instead creates a set of versions as `v1`, `v2`, etc. so you can always reproduce a plot, even if it's based on old data. `raft` is also clever in that it always `load()`s the latest version of an artifact unless you ask for a specific version, and if `save()` data that is identical to the previous version, it doesn't create a new file, it just appends a record to the metadata.
- An **experiment** contains all of the artifacts created by one **run** of your analyses and simulations. When your code runs on a grid of parameters, `raft` creates a folder for each (experiment, parameter) instance. `raft` also provides some utilities to later load the results for the set of all parameters, or query a subset of them (as in, `.where(param1=0.3, param2="gaussian")`.
- A **project** is the root folder for a larger research effort. It contains a set of experiments, and any global artifacts that are shared between them (e.g., some preprocessed input data, or the stimuli to use in an experiment).

A quick example of a typical `raft` session:

```python
import raft

# Create or load the "walker" project
project = raft.init("walker", datastore="./catalog")
# An experiment is defined with a name ("baseline") and, optionally, a set of parameters (lr=0.01, prior="uniform")
exp = project.experiment("baseline", lr=0.01, prior="uniform")

# The parameters are saved in the experiment object, if you need to look them up
result = simulate(lr=exp.lr, prior=exp.prior)

# Here we save the simulation results as an artifact in project "walker" under the experiment "baseline" with parameters lr=0.01, prior="uniform".
# `raft` will take care of saving metadata information: the author, date, git commit, the name of this script, etc.
exp.save(result, "result")

# ... later, even in a different session ...
exp.load("result")               # load the latest version of "results"
exp.load("result", version=1)    # a specific one, e.g. to reproduce an old plot
```

You can also save/load at **project-scope** (`project.save(...)` / `project.load(...)`) for things shared across every experiment.

The metadata of each artifact also records who and what produced it: the OS username, and the running script or notebook name (`activity`), auto-detected where possible. Override either at init time if the auto-detected values aren't what you want:

```python
project = raft.init("walker", datastore="./catalog", activity="train.py", author="jane")
```

`activity` is just a string, it could also be "manual fix", "lambda function on AWS", or "interactive section with python".

`raft` picks a storage format from the data's type:

| Python type | On-disk format | Notes |
|---|---|---|
| `pandas.DataFrame` | `.parquet` | default; preserves dtypes exactly |
| `pandas.DataFrame` | `.csv` | opt-in via `format="csv"`, human-readable |
| `numpy.ndarray` | `.npy` | |
| `dict` | `.json` | |
| `PIL.Image.Image` | `.png` | |

More types will be added over time. If you need one that isn't here, [open a GitHub issue](https://github.com/datrocity/raft/issues).

See `notebook/01_walkthrough.ipynb` for a full walkthrough.

## 3. RunSets: meta-analysis across experiments

Once you've run a grid of experiments, `project.runs()` gives you way to iterate over them or collect the one you're interested in (e.g., all runs with a specific parameter).


```python
runs = project.runs()
hits = runs.where(lr=0.01, prior="uniform")

summary = hits.summarize(
    final_loss=lambda r: r.load("result")["loss"].iloc[-1],
)

# same experiment name, different parameters (the common grid pattern) --
# load_all returns pairs, so same-name runs never collide
for run, result in hits.load_all("result"):
    plot(result, label=f"lr={run.params['lr']}")
```

`where()` filters by exact parameter match; pass `name=` to filter by experiment name instead, or combine both (e.g. `runs.where(name="baseline", lr=0.01)`). `frame()` / `summarize()` return a DataFrame with one row per run.

## 4. Caching with `@compute_or_load`

Sometimes you have a notebook that starts by preprocessing a big set of raw data that is used in the rest of the script. Every time you run the analysis, the same preprocessing happens and it's really boring.

In `raft`, you could do something like this to do that step only the first time, and then loading it from your catalog:

```python
if not project.has("my_processed_input"):
    data = expensive_preprocessing()
    project.save(data, "my_processed_input")
else:
    data = project.load("my_processed_input")
```

Alternatively, `raft` provides a `compute_or_load` decorator. The first call to the function computes and saves, and every later call (in this run or a future one) just loads:

```python
@project.compute_or_load("processed_input")    # project scope: shared across all experiments
def preprocess():
    return expensive_preprocessing()

data = preprocess()   # computed once, then just loaded from disk

@exp.compute_or_load("preprocessed")         # experiment scope: local to this one run
def local_step():
    ...
```

## 5. AI assistant support

`raft` ships two AI skills (`raft/skills/*.md`) that teach an AI coding assistant (Claude Code, Cursor, etc.) to use the library correctly:

- **Writing `raft` code**: it tells your AI how to use the `raft` API, so it can use it appropriately
- **Importing messy data**: A guided workflow for turning a folder of years-old, inconsistently named CSVs, plots, and config files into a proper raft catalog. The assistant inventories the folder, proposes a plan grouping files into candidate experiments, and only imports after you approve it.

Install them after `pip install data-raft`:

    raft install-skills                        # copies to ~/.claude/skills/raft/
    raft install-skills --dest ~/.some/place   # or a custom directory

For non-Claude tools, point the assistant at `AGENTS.md` in the source repo, or `python -c "import raft; print(raft.skills_path())"` if you'd rather symlink.

## Development

    make setup        # create local .venv and install
    make test          # run tests
    make lint          # ruff
    make format        # ruff format

## Requirements

Python 3.11+. Depends on numpy, pandas, pillow, pyarrow, joblib.

## License

BSD 3-Clause.
