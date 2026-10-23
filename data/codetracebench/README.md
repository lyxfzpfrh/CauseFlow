# CodeTraceBench (verified split)

* `manifest_verified.parquet` — the 1,000-row verified-split manifest from
  the HuggingFace dataset `NJU-LINK/CodeTraceBench` (κ = 0.73). Columns:
  `traj_id, agent, model, task_name, task_slug, difficulty, category, tags,
  solved, step_count, stages, stage_count, incorrect_error_stage_count,
  trial_name, source_relpath, annotation_relpath, incorrect_stages,
  generated_at, artifact_path`.
* `prepare_eval_split.py` — derives the evaluation set from the manifest
  (failed trajectories with a non-empty incorrect-step annotation; `i_star`
  = earliest annotated incorrect step). Prints and asserts the paper's
  counts: 235 = 69 SWE-bench + 166 Terminal-Bench.
* `eval_split_235.parquet` — the derived evaluation set (RQ1/RQ3/RQ4), with
  stratification columns `src_bench / model / agent / length_band`.
* `artifacts/` — the raw per-trajectory runs of the evaluation set as
  `<traj_id>.tar.zst` archives, read by
  `causeflow.io_loaders.load_codetracebench_archive` (224 of 235 parse;
  2 absent upstream, 9 ship without a trajectory file — see the loader
  docstring for the supported layouts).

`solved` takes values True / False / null; the 28 null-verdict rows are
counted as failed, giving 504 solved / 496 failed.
