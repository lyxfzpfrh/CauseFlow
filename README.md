# CauseFlow — Artifact

**Tracing LLM Agent Failures to Their Root Causes: Cross-Step Backward
Attribution and Localized Repair.**

CauseFlow is a post-mortem debugging pipeline for failed ReAct-style agent
trajectories:

| Stage | Paper § | What it does |
|---|---|---|
| 1. Trajectory compression | 3.2 | Failure-preserving, offline reduction (waste taxonomy + failure neighborhood + position map *M*) |
| 2. Attribution analysis | 3.3 | Step-wise source–target pairs scored by **SF / HS / KI**, fused (Eq. 7), thresholded into edges, traced backwards |
| 3. Reasoning and repair | 3.4 | Rank top-k causes (6 root-cause types + scapegoat flag), locate the earliest editable input, generate a budgeted localized edit, validate by re-execution |

> **Repository layout**
>
> ```
> causeflow/          the CauseFlow framework (reference implementation)
>   schema.py           data model (Trajectory, AttributionRecord, Candidate, Edit)
>   config.py           every hyperparameter of the paper (§3.4)
>   stage1_compression.py
>   stage2_attribution/ segmentation, signals (SF/HS/KI, Eq. 3-6), analyzer, tracing
>   stage3_repair/      reasoning, edit taxonomy + guardrails, re-execution
>   pipeline.py         the end-to-end CauseFlow class
>   baselines.py        B1 / B2 direct reading, B3 random/majority, no-attribution control
>   io_loaders.py       benchmark data loaders (manifest, tar.zst archives, session logs)
> data/               datasets
>   codetracebench/      manifest + 235-trajectory evaluation set + per-trajectory archives
>   itbench/             105 agent runs (35 SRE scenarios x 3) + run manifest
> evaluation/         paper statistics: exp_data.py (single source of truth),
>                      metrics.py (protocol), verify_stats.py, experiment_data.xlsx
> scripts/            RQ1/RQ2/RQ3 harnesses
> ```

## Quickstart (no GPU, no API keys)

```bash
pip install -r requirements.txt

# 1. derive the 235-trajectory evaluation set from the manifest
python data/codetracebench/prepare_eval_split.py

# 2. label the ITBench runs and build the RQ2 manifest
python data/itbench/label_runs.py

# 3. recompute and verify every headline number of the paper
python evaluation/verify_stats.py
```

`evaluation/exp_data.py` is the **single source of truth** for all reported
statistics. RQ1/RQ3 entries are 5-run integer top-1/top-3 hit counts out of
N (235 / 150); RQ1 F1 follows the official set-level protocol over the 56
distinct annotated incorrect steps (precision over delivered candidates,
recall over the 56 positives); RQ2/RQ4 are deterministic counts. Every
mean, std, P/R/F1, gap, p-value, confidence interval, and effect size in
the paper is recomputable from those records:

```bash
python evaluation/exp_data.py          # full dump, all four RQs
python evaluation/verify_stats.py     # 50 assertion checks vs. paper values
```

Live end-to-end runs (instead of the recorded run counts) require a GPU
analyzer (`CauseFlowConfig(use_mock_analyzer=False)`, defaults to
DeepSeek-V4) and an OpenAI-compatible reasoner endpoint
(`use_mock_reasoner=False`, `reasoner_base_url=...`):

```bash
python scripts/run_localization.py            # RQ1 (+ RQ4 stratification)
python scripts/run_ablation.py                # RQ3
python scripts/run_repair.py                  # RQ2 (needs the ITBench gym)
```

> **Scope note.** The mock analyzer/reasoner make the pipeline machinery
> runnable everywhere; scores obtained in mock mode are **not** the paper's
> numbers. The paper's numbers are the recorded runs in
> `evaluation/exp_data.py`, and the harnesses above re-execute the same
> protocol when real backends are supplied.

## Data

See `data/README.md`. In short:

* **CodeTraceBench verified split** (`data/codetracebench/`): manifest of
  1,000 human-annotated trajectories (489 SWE-bench + 511 Terminal-Bench;
  504 solved / 496 failed); **235 failed-and-annotated** trajectories
  (69 SWE-bench + 166 Terminal-Bench) form the RQ1/RQ3/RQ4 evaluation set,
  with the raw per-trajectory runs shipped as tar.zst archives (224 of 235
  parse with the bundled loaders; 2 are absent upstream and 9 ship without
  a trajectory file — the harness falls back to a manifest stub for those).
* **ITBench** (`data/itbench/`): 35 SRE scenarios × 3 runs of
  GPT-OSS-120B = 105 trajectories; every scenario contains exactly one
  successful run among its three repeated runs, so the dataset holds
  35 successful and 70 failed — the 70 failed form the RQ2 repair set;
  `label_runs.py` additionally derives a per-run judge-metrics manifest
  for diagnostics.
