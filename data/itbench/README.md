# ITBench (RQ2 repair set)

* **Source**: HuggingFace dataset `ibm-research/ITBench-Trajectories`
  (ICML 2025 version of ITBench).
* `ReAct-Agent-Trajectories/OpenAI-GPT-OSS-120B/sre/` — 35 SRE scenarios ×
  3 runs of the official ITBench-SRE-Agent (ReAct-style) on the single
  open-weight backbone **GPT-OSS-120B** = 105 trajectories.  Every scenario
  contains exactly one successful run among its three repeated runs, so
  the dataset holds **35 successful and 70 failed trajectories**; the 70
  failed form the RQ2 repair evaluation set, and the motivating trajectory
  of the paper comes from this set.  Each run directory holds
  `session.jsonl` (agent trace), `agent_output.json` (final diagnosis)
  and, where judged, `judge_output.json` (graded metrics).
* `label_runs.py` — derives `itbench_runs_manifest.parquet`: one row per
  run with the judge scores (root-cause entity P/R/F1, propagation chain,
  ...) for per-run diagnostics; upstream judge coverage is partial
  (90 of 105 runs carry `judge_output.json`).
* Repair validation (re-execution) additionally requires the ITBench gym.
