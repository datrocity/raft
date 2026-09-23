# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Changed

- **Renamed the project from `box` to `raft`**, ahead of the first PyPI
  release (the name `box` was already taken). The import package, CLI
  command, and GitHub repository are now all `raft`; the PyPI
  distribution is `data-raft`. Entries below this point describe
  releases made under the old `box` name.

### Added

## [0.2.0] - 2026-09-01

### Added

- Manifests now record `activity`: the script, notebook, or process name
  that produced the data. Auto-detected where possible (the running
  script's filename, or a notebook's name via `JPY_SESSION_NAME` on
  JupyterLab/Notebook 7+); pass `activity=` to `box.init`/`Project`/
  `box.experiment` to set it explicitly, or `author=` to override the
  auto-detected OS username. Both are recorded in every manifest's
  `provenance` section and in the embedded business card, where the
  artifact format supports it.

### Changed

- Metadata files (`params.yaml`/`manifest.yml`/`v{N}.manifest.yml`) are
  now written as `params.json`/`manifest.json`/`v{N}.manifest.json`.
  **Breaking:** catalogs created before this change are not read back —
  `proj.runs()` silently skips experiment folders that only have
  `params.yaml`, and loading an artifact with only the old `.yml` manifest
  raises `ValueError: no artifact class registered for extension 'yml'`.
  If you have an existing catalog in the old format, re-run the code that
  produced it to regenerate it in JSON.
- Build tooling switched from Hatch to a plain `venv` + `pip`
  (`setuptools` backend, via `python -m venv .venv`). `make setup` creates
  `.venv/` directly; no separate package manager is required.
