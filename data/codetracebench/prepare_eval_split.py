#!/usr/bin/env python
"""Derive the 235-trajectory evaluation set from the CodeTraceBench manifest.

The verified split manifest (1,000 rows) is the only input.  The evaluation
set of RQ1 / RQ3 / RQ4 is the set of failed trajectories (verdict != solved,
null verdicts included) that carry a non-empty step-level incorrect-step
annotation: 69 SWE-bench + 166 Terminal-Bench = 235 trajectories, each with
i* = the earliest annotated incorrect step.

Verified counts (printed and asserted below):
    1,000 total = 504 solved + 496 non-solved (468 explicit fail + 28 null)
    235 failed-and-annotated  (69 SWE-bench, 166 Terminal-Bench)
    backbones: Claude-Sonnet-4 104 / GPT-5 69 / DeepSeek-V4 62
    agents:    OpenHands 102 / mini-SWE-agent 61 / Terminus2 57 / SWE-agent 15
    1,048 annotated incorrect steps in total
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, os.pardir))

from causeflow.io_loaders import build_eval_split, load_manifest   # noqa: E402


def main():
    manifest_path = os.path.join(HERE, "manifest_verified.parquet")
    out_path = os.path.join(HERE, "eval_split_235.parquet")

    df = load_manifest(manifest_path)
    n_total = len(df)
    n_solved = int((df["solved"] == True).sum())            # noqa: E712
    n_fail_explicit = int((df["solved"] == False).sum())    # noqa: E712
    n_null = int(df["solved"].isna().sum())

    split = build_eval_split(df)
    print(f"manifest: {n_total} rows = {n_solved} solved "
          f"+ {n_fail_explicit} explicit fail + {n_null} null verdict")
    print(f"evaluation set: {len(split)} failed-and-annotated trajectories")
    print(f"  by benchmark : {split['src_bench'].value_counts().to_dict()}")
    print(f"  by backbone  : {split['model'].value_counts().to_dict()}")
    print(f"  by agent     : {split['agent'].value_counts().to_dict()}")
    print(f"  by difficulty: {split['difficulty'].value_counts().to_dict()}")

    assert len(split) == 235, "expected the 235-trajectory evaluation set"
    assert split["src_bench"].value_counts().to_dict() == \
        {"Terminal-Bench": 166, "SWE-bench": 69}
    assert n_total == 1000 and n_solved == 504

    split.to_parquet(out_path, index=False)
    print(f"\nwrote {out_path}  (i* column: 'i_star'; "
          f"stratification: src_bench / model / agent / length_band)")


if __name__ == "__main__":
    main()
