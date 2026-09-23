---
name: importing-into-raft
description: Use when a user asks to import an existing folder of scattered research outputs (CSVs, plots, notebooks, configs) into a raft catalog. The AI scans the folder, proposes an import plan grouping files by likely experiment, and only executes after the user confirms.
---

# Importing messy research data into raft

You are helping a researcher bring years of accumulated files into a raft catalog. Assume the layout is inconsistent. Do NOT execute any import until the user has approved a written plan.

## Workflow

1. **Inventory.** Recursively list the folder. Note filenames, extensions, directory structure. Do not read binary contents yet.

2. **Detect signals of experiment identity**, in this order of trust:
   - External config files (`config.yaml`, `params.json`, `inputs.json`) — most trustworthy
   - README.md or notebook markdown cells describing the run
   - Filename patterns (`sim_lr0.01_prior_uniform.parquet`) — parse conservatively
   - Directory naming conventions (`22_08_30_experiment/`, `run_baseline/`)
   - Git history near each file (rarely useful, don't over-rely)

3. **Cluster files into candidate experiments.** A cluster is "these files were produced by one run." Heuristics: shared parent directory, shared filename prefix, shared config file reference. When unsure, keep clusters small — you can merge later; splitting later is harder.

4. **Extract params per cluster.** If a config file is present, use it verbatim. If only filenames are available, parse but flag anything ambiguous. Never invent params.

5. **Draft an import plan.** Write `import_plan.md` in the source folder. For each cluster, show:
   - Proposed experiment name
   - Proposed params (annotated with source: "from config.yaml" / "parsed from filename")
   - Files to import, and their proposed artifact names
   - Files to SKIP (junk, duplicates, uncertain)

6. **Show the plan to the user and wait for approval.** Ask them to confirm or edit clusters, names, and params. Be explicit about ambiguities — list any files you were unsure about.

7. **Execute only after approval.** For each cluster:
   ```python
   exp = proj.experiment(name, **params)
   for src_path, artifact_name in cluster:
       data = load_by_extension(src_path)
       exp.save(data, artifact_name)
   ```

8. **Report.** Print a summary: N experiments created, M artifacts imported, K files skipped and why.

## Rules

- Never delete or move the original files. Import is a copy-in; the source folder is untouched.
- Never invent params. If you can't find one, ask.
- Never merge two candidate experiments unless the evidence is overwhelming.
- If the folder has 100+ candidate clusters, split the work: show the plan for the first 10, get user feedback on the heuristics, then continue.
- If any extraction step fails silently (missing key, unparseable filename), STOP and ask.

## Loading heuristics by extension

- `.csv`, `.tsv` → `pandas.read_csv`
- `.parquet` → `pandas.read_parquet`
- `.npy` → `numpy.load`
- `.npz` → `numpy.load` (yields a dict; ask user how to split)
- `.png`, `.jpg`, `.jpeg` → `PIL.Image.open`
- `.json` → `json.load` — save as dict artifact
- `.yaml`, `.yml` → `yaml.safe_load` — save as dict artifact (`pyyaml` is not a `raft` dependency; `pip install pyyaml` if missing)
- Unknown → skip and report

## Anti-patterns

- Do NOT overwrite existing raft experiments during import.
- Do NOT chain `proj.experiment()` calls without capturing the handle — you'll lose track.
- Do NOT strip whitespace or normalize case in extracted param values; keep them exactly as found.

## Example `import_plan.md` fragment

    ## Cluster 1
    - Proposed experiment name: `baseline`
    - Proposed params: `{lr: 0.01, prior: uniform}` (from `configs/baseline.yaml`)
    - Import:
      - `results/baseline_run1.csv` → artifact `result`
      - `plots/baseline_loss.png` → artifact `loss_curve`
    - Skip:
      - `results/baseline_run1.csv.backup` — appears to be a duplicate
      - `notes.txt` — free-form text, no clear artifact type
