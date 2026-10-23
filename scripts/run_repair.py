#!/usr/bin/env python
"""RQ2 harness: attribution-directed repair on the failed ITBench runs.

    python scripts/run_repair.py [--limit 10]

Uses the shipped ITBench trajectories (data/itbench/ReAct-Agent-Trajectories,
labeled by data/itbench/label_runs.py into itbench_runs_manifest.parquet)
and an LLM reasoner endpoint for live runs (set use_mock_reasoner=False and
configure reasoner_base_url in CauseFlowConfig).  Re-execution uses an
Environment implementation bound to the ITBench gym; without one the harness
reports "not_reexecuted".  The paper's RQ2 numbers live in
evaluation/exp_data.py.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
sys.path.insert(0, ROOT)

from causeflow.config import CauseFlowConfig                    # noqa: E402
from causeflow.pipeline import CauseFlow                        # noqa: E402


class ItbenchGymStub:
    """Placeholder Environment: wire the ITBench gym here.

    execute(traj, edit) must re-run the task under the edited prompt in the
    gym and return the new trajectory with verdict 'success' / 'fail'.
    """

    def execute(self, traj, edit):
        from causeflow.schema import Trajectory
        return Trajectory(traj_id=traj.traj_id + "-replay",
                          steps=traj.steps,
                          editable_inputs=traj.editable_inputs,
                          verdict="fail")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--manifest", default=os.path.join(
        ROOT, "data", "itbench", "itbench_runs_manifest.parquet"))
    args = ap.parse_args()

    import pandas as pd
    if not os.path.exists(args.manifest):
        print(f"manifest not found: {args.manifest} "
              f"(run data/itbench/label_runs.py first)")
        return
    df = pd.read_parquet(args.manifest)
    failed = df[df["verdict"] == "fail"]
    if args.limit:
        failed = failed.head(args.limit)
    if failed.empty:
        print("no failed runs in the manifest")
        return
    print(f"repair harness over the failed ITBench runs "
          f"(manifest diagnostic label 'fail': {len(failed)} of {len(df)} runs; "
          f"the paper's RQ2 set is the 70 failed trajectories of the "
          f"dataset composition)")

    from causeflow.io_loaders import load_itbench_session
    cfg = CauseFlowConfig()
    cf = CauseFlow(cfg)
    gym = ItbenchGymStub()
    n_repaired = n_intent = n_loaded = 0
    for _, row in failed.iterrows():
        sess = os.path.join(ROOT, "data", "itbench", row["session_jsonl"])
        traj = load_itbench_session(
            sess, traj_id=f"{row['scenario']}-run{row['run']}")
        if traj.n_steps == 0:
            print(f"{traj.traj_id:24s} SKIPPED (unparseable session log)")
            continue
        n_loaded += 1
        diag = cf.repair(traj, environment=gym)
        ok = diag.repair and diag.repair.verdict == "success"
        n_repaired += bool(ok)
        n_intent += all(e.within_budget for e in diag.edits)
        print(f"{traj.traj_id:24s} verdict="
              f"{diag.repair.verdict if diag.repair else 'none'}"
              f"  budget_ok={all(e.within_budget for e in diag.edits)}")
    if n_loaded:
        print(f"\nrepair {n_repaired}/{n_loaded} = "
              f"{n_repaired/n_loaded*100:.2f}   "
              f"within-budget {n_intent}/{n_loaded}")


if __name__ == "__main__":
    main()
