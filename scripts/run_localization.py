#!/usr/bin/env python
"""RQ1 / RQ3 / RQ4 harness: root-cause localization on the 235-trajectory
evaluation set (CodeTraceBench verified split).

    python scripts/run_localization.py [--methods cf,b2,b1,b3] [--limit 20]

Methods
    cf   CauseFlow (full pipeline: compress -> attribute -> rank)
    b2   DeepSeek-V4 direct reading of the full trajectory
    b1   GPT-4o direct reading
    b3   Random / Majority sanity check
    noattr  the RQ3 "w/o Attribution paths" control (same reasoner,
            compressed trajectory, no attribution paths)

Live runs read the shipped per-trajectory archives
(data/codetracebench/artifacts/*.tar.zst) and — for the non-mock path — a
GPU analyzer and an LLM endpoint.  With the default mock analyzer/reasoner
the harness still runs end to end (archives where available, manifest stubs
otherwise) so the protocol wiring is testable; scores in mock mode are NOT
the paper's numbers (those live in evaluation/exp_data.py and are verified
by evaluation/verify_stats.py).
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "evaluation"))

import pandas as pd                                             # noqa: E402

from causeflow.config import CauseFlowConfig                    # noqa: E402
from causeflow.pipeline import CauseFlow                        # noqa: E402
from causeflow.baselines import (DirectReadingBaseline,         # noqa: E402
                                 NoAttributionControl, RandomMajority)
from causeflow.stage3_repair import build_reasoner
from evaluation.metrics import localization_report              # noqa: E402


def stub_trajectory(row):
    """Manifest stub when the shipped archive is missing or unparseable.

    Builds a minimal Trajectory whose step count matches the manifest, with
    a system prompt / instruction stub as editable inputs.  Only for wiring
    tests — the paper's runs consume the real artifacts.
    """
    from causeflow.schema import EditableInput, EditableKind, Step, Trajectory
    n = int(row["step_count"])
    steps = [Step(index=i + 1,
                  input_text="",
                  output_text=f"step {i+1} output",
                  observation="ok") for i in range(n)]
    steps[-1].observation = "task failed"
    editable = [
        EditableInput(EditableKind.SYSTEM_PROMPT,
                      "You are a software-engineering agent.", "system prompt"),
        EditableInput(EditableKind.TASK_INSTRUCTION,
                      str(row["task_name"]), "task instruction"),
    ]
    return Trajectory(traj_id=row["traj_id"], steps=steps,
                      editable_inputs=editable, verdict="fail")


def load_trajectory(row, artifacts_dir):
    """Load the real trajectory from the shipped tar.zst archive.

    224 of the 235 archives parse directly (mini-swe-agent traj.json,
    openhands session events / per-call JSONs, swe-agent .traj /
    checkpoints, terminus2 episodes); 2 are absent upstream (404) and 9
    ship without a trajectory file — those fall back to the manifest stub.
    """
    archive = os.path.join(artifacts_dir, f"{row['traj_id']}.tar.zst")
    if os.path.exists(archive):
        try:
            from causeflow.io_loaders import load_codetracebench_archive
            t = load_codetracebench_archive(archive,
                                            traj_id=row["traj_id"])
            if t.n_steps > 0:
                return t
        except Exception:
            pass
    return stub_trajectory(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", default="cf,b2,b1,b3")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    split = pd.read_parquet(os.path.join(
        ROOT, "data", "codetracebench", "eval_split_235.parquet"))
    if args.limit:
        split = split.head(args.limit)
    artifacts_dir = os.path.join(ROOT, "data", "codetracebench", "artifacts")

    cfg = CauseFlowConfig(seed=args.seed)
    cf = CauseFlow(cfg)
    reasoner = build_reasoner(cfg)
    methods = {
        "cf": lambda t: [c.step for c in cf.diagnose(t).candidates],
        "b2": lambda t: [c.step for c in DirectReadingBaseline(
            reasoner=None, name="b2").localize(t)],
        "b1": lambda t: [c.step for c in DirectReadingBaseline(
            reasoner=None, name="b1").localize(t)],
        "b3": lambda t: [c.step for c in RandomMajority(
            "random", seed=args.seed).localize(t)],
        "noattr": lambda t: [c.step for c in NoAttributionControl(
            reasoner).localize(t)],
    }

    golds = []
    preds = {m: [] for m in args.methods.split(",")}
    for _, row in split.iterrows():
        traj = load_trajectory(row, artifacts_dir)
        golds.append(int(row["i_star"]))
        for m in preds:
            cand = methods[m](traj)
            cand = [c for c in cand if c and 1 <= c <= traj.n_steps]
            preds[m].append(cand[:3])

    for m, p in preds.items():
        rep = localization_report(p, golds)
        print(f"{m:8s} N={rep['N']:4d}  top-1 {rep['top1']*100:6.2f}  "
              f"top-3 {rep['top3']*100:6.2f}")


if __name__ == "__main__":
    main()
