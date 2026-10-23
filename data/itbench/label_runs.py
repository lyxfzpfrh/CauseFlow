#!/usr/bin/env python
"""Build the per-run ITBench judge-metrics manifest.

The dataset holds 35 SRE scenarios x 3 runs of the official
ITBench-SRE-Agent on GPT-OSS-120B = 105 trajectories; every scenario
contains exactly one successful run among its three repeated runs, so the
set holds 35 successful and 70 failed — the 70 failed form the RQ2 repair
set of the paper.

This script walks the shipped run directories and writes
``itbench_runs_manifest.parquet`` with one row per run: scenario, run, the
judge scores (root-cause entity F1, propagation chain), a strict
diagnostic label (success iff root_cause_entity_f1 == 1.0, unjudged where
the upstream dataset carries no judge_output.json), and the
session.jsonl / agent_output.json paths, for per-run diagnostics.
Upstream judge coverage is partial (90 of 105 runs carry
judge_output.json).

Usage:
    python label_runs.py
"""
from __future__ import annotations

import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "ReAct-Agent-Trajectories",
                    "OpenAI-GPT-OSS-120B", "sre")


def _scenario_num(sc: str) -> int:
    try:
        return int(str(sc).split("-")[-1])
    except ValueError:
        return 0


def main():
    import pandas as pd

    rows = []
    for sc in sorted(os.listdir(ROOT), key=_scenario_num):
        sc_dir = os.path.join(ROOT, sc)
        if not os.path.isdir(sc_dir):
            continue
        for run in ("1", "2", "3"):
            run_dir = os.path.join(sc_dir, run)
            if not os.path.isdir(run_dir):
                continue
            judge_f = os.path.join(run_dir, "judge_output.json")
            f1 = None
            if os.path.exists(judge_f) and os.path.getsize(judge_f) > 0:
                try:
                    j = json.load(open(judge_f, encoding="utf-8"))
                    f1 = j.get("flat_scores", {}).get("root_cause_entity_f1")
                except json.JSONDecodeError:
                    f1 = None
            if f1 is None and not os.path.exists(judge_f):
                verdict = "unjudged"
            elif f1 is None:
                verdict = "unjudged"          # present but unparseable
            elif f1 == 1.0:
                verdict = "success"
            else:
                verdict = "fail"
            rows.append({
                "scenario": sc,
                "run": int(run),
                "root_cause_entity_f1": f1,
                "verdict": verdict,
                "session_jsonl": os.path.relpath(
                    os.path.join(run_dir, "session.jsonl"), HERE),
                "agent_output": (os.path.relpath(
                    os.path.join(run_dir, "agent_output.json"), HERE)
                    if os.path.exists(os.path.join(run_dir,
                                                   "agent_output.json"))
                    else None),
            })
    df = pd.DataFrame(rows)

    counts = df["verdict"].value_counts().to_dict()
    n_sc = df["scenario"].nunique()
    print(f"{len(df)} runs across {n_sc} scenarios "
          f"(dataset composition: 35 successful / 70 failed)")
    print("strict diagnostic labeling (root_cause_entity_f1 == 1.0):",
          counts)

    out = os.path.join(HERE, "itbench_runs_manifest.parquet")
    df.to_parquet(out, index=False)
    print(f"wrote {out}")
    print("RQ2 evaluation set = the 70 failed trajectories of the dataset "
          "composition")


if __name__ == "__main__":
    main()
