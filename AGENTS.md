# AGENTS.md

Guidance for AI assistants and human contributors working on the `raft`
source tree. End-user assistant guidance is in `raft/skills/*.md`.

## Project shape

`raft` is a small library that gives research results a persistent,
queryable identity. Four nouns:

- **Project** — named workspace (`walker`), rooted at `{datastore}/{project}/`.
- **Experiment** — one named run with frozen params; identity is
  `(project, name, params)`; folder is `{date}__{name}__{hash8}`.
- **Artifact** — a named saved thing (DataFrame, ndarray, image, dict).
- **Version** — automatic; identical `data_hash` reuses the same version
  and appends a run record to the manifest.

Every manifest's `provenance` section also records `author` (OS username)
and `activity` (the running script/notebook name), both auto-detected where
possible and overridable via `Project(..., activity=..., author=...)` /
`raft.init(..., activity=..., author=...)`. See `raft/manifest/lineage.py`.

## Development commands

    make setup        # create local .venv and install
    make test         # run all tests
    make cov          # coverage report
    make lint         # ruff check
    make format       # ruff format
    make watch        # rerun tests on file change

## Code conventions

- Python 3.11+.
- **No type annotations by default.** Numpy-style docstrings carry types.
- Ruff enforces docstring style (D rule set, numpy convention).
- Public API lives in `raft/__init__.py`; internal helpers stay module-private
  (leading underscore).
- Immutability preferred for value objects (`Manifest`, `Version`).
- Errors inherit from `RaftError` so users catch everything with one `except`.
- Line length 88.

## Adding a new artifact type

1. Create `raft/artifact/<mytype>.py`.
2. Subclass `Artifact`, set `handles_type` and `extension` class attributes.
3. Implement `write_bytes(data, metadata=None)` and `read_bytes(blob)`.
   If the on-disk format can embed metadata (PNG tEXt, parquet schema, etc.),
   encode `metadata` inline. Otherwise accept and ignore the kwarg.
4. Call `register_artifact(YourArtifactClass)` at the module bottom.
   For an opt-in alternative format (like the CSV alternative to parquet),
   pass `format="csv"`.
5. Add to the late-import list in `raft/artifact/__init__.py`.
6. Add a test file `tests/artifact/test_<mytype>.py` covering: registration,
   extension, round-trip, and metadata embed (if applicable).

## Extending an existing experiment

Experiment identity is `(project, name, params)`. To try a variant, create
a new experiment with different params — never mutate an existing one.

```python
proj.experiment("baseline", lr=0.01)   # existing folder
proj.experiment("baseline", lr=0.05)   # new folder, different hash
```

## What raft does NOT do

- Sweep execution — write the loop yourself.
- Workflow orchestration or DAG scheduling.
- Config-file DSL — params are Python kwargs.
- Auto-instrumentation of notebook cells.
- Cross-project queries — `RunSet` is scoped to one project.

## Committing

Commit style: conventional (`feat(scope): ...`, `fix(scope): ...`,
`docs: ...`, `chore: ...`). Every commit should leave main lint-clean and
tests-green.
