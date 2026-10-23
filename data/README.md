# Data

Two public benchmarks are used; provenance and derivation are documented per
subdirectory.

## CodeTraceBench (`codetracebench/`) — RQ1 / RQ3 / RQ4

* **Source**: HuggingFace dataset `NJU-LINK/CodeTraceBench`, verified split
  (bench manifest, inter-annotator agreement κ = 0.73).
* **`manifest_verified.parquet`** (shipped): 1,000 rows, one per trajectory,
  with agent / backbone / task / difficulty / stage annotations.
* **`eval_split_235.parquet`** (derived by `prepare_eval_split.py`): the
  evaluation set — failed trajectories (verdict ≠ solved, null verdicts
  included) carrying a non-empty step-level incorrect-step annotation:

  | property | count |
  |---|---|
  | total / solved / failed | 1,000 / 504 / 496 |
  | by benchmark (of the 1,000) | SWE-bench 489 + Terminal-Bench 511 |
  | failed-and-annotated (evaluation set) | **235** |
  | by benchmark (of the 235) | SWE-bench 69 + Terminal-Bench 166 |
  | by backbone | Claude-Sonnet-4 104 / GPT-5 69 / DeepSeek-V4 62 |
  | by agent | OpenHands 102 / mini-SWE-agent 61 / Terminus2 57 / SWE-agent 15 |
  | by difficulty | hard 103 / medium 102 / easy 30 |
  | annotated incorrect steps | 1,048 |
  | inter-annotator agreement | κ = 0.73 |

  `i_star` = earliest annotated incorrect step of the trajectory (the
  root-cause step under the identification argued in §4.1.1 of the paper).
  Stratification columns `src_bench` / `model` / `agent` / `length_band`
  support the RQ4 breakdowns.
* **`artifacts/`** (shipped): the raw per-trajectory runs as
  `<traj_id>.tar.zst` (37 MB total), read directly by
  `causeflow.io_loaders.load_codetracebench_archive`.  Supported layouts:
  mini-swe-agent `traj.json`, openhands session events / per-call JSONs,
  swe-agent `.traj` / `checkpoints.jsonl`, terminus2 episode logs.
  Coverage: 224 of 235 parse; 2 trajectories are absent from the upstream
  dataset (404) and 9 archives ship without a trajectory file (shell-level
  logs only) — the localization harness falls back to a manifest stub for
  those 11.

`solved` takes values True / False / null; the 28 null-verdict rows are
counted as failed, giving 504 solved / 496 failed.

## ITBench (`itbench/`) — RQ2

* **Source**: HuggingFace dataset `ibm-research/ITBench-Trajectories`.
* **`ReAct-Agent-Trajectories/`** (shipped): 35 SRE scenarios × 3 runs of
  the official ITBench-SRE-Agent (ReAct-style) on the single open-weight
  backbone **GPT-OSS-120B** = 105 trajectories.  Every scenario contains
  exactly one successful run among its three repeated runs, so the dataset
  holds **35 successful and 70 failed**; the 70 failed form the RQ2 repair
  evaluation set, and the motivating trajectory of the paper comes from
  this set.  Each run directory holds `session.jsonl` (agent trace),
  `agent_output.json` (final diagnosis) and, where judged,
  `judge_output.json` (graded metrics).
* **`label_runs.py`** derives **`itbench_runs_manifest.parquet`**: one row
  per run with the judge scores (root-cause entity P/R/F1, propagation
  chain, ...) for per-run diagnostics; upstream judge coverage is partial
  (90 of 105 runs carry `judge_output.json`).
* Repair validation (re-execution) additionally requires the ITBench gym.

## Attribution convention

CodeTraceBench annotations ground only the **step** component of the
localization output (top-1/top-3/F1 are step-level); no public benchmark
annotates token regions, which is why token-granularity claims are assessed
through the consistency checks of §4.2.3 rather than scored directly.
