#!/usr/bin/env python
"""RQ3 harness: component ablation on the 150-trajectory stratified subset.

Variants (paper §4.4):
    w/o Compression     skip Stage 1 (attribute the raw trajectory)
    w/o SF              fusion with w1 = 0, renormalized
    w/o HS              fusion with w2 = 0, renormalized
    w/o KI              fusion with w3 = 0, renormalized
    w/o LLM reasoning   rule-based ranking (the mock reasoner)
    w/o Attribution paths  same reasoner, compressed trajectory, no paths
    CauseFlow (full)

The 150-trajectory stratified subset is sampled from the 235 evaluation set
with the paper's strata (benchmark / backbone / difficulty proportional).
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
from causeflow.schema import (CompressedTrajectory, TokenCoord,  # noqa: E402
                              default_tokenize)
from causeflow.stage1_compression import compress               # noqa: E402
from causeflow.stage2_attribution import attribute              # noqa: E402
from causeflow.stage3_repair import (EvidenceBundle,            # noqa: E402
                                     MockReasoner)
from evaluation.metrics import localization_report              # noqa: E402
from scripts.run_localization import load_trajectory            # noqa: E402


def raw_trajectory_view(traj):
    """A 'compression' that keeps everything (the w/o Compression variant)."""
    kept = [TokenCoord(step=0, token_index=j, text=t, origin="editable")
            for seg in traj.editable_inputs
            for j, t in enumerate(seg.tokens)]
    for s in traj.steps:
        for j, t in enumerate(default_tokenize(s.output_text)):
            kept.append(TokenCoord(step=s.index, token_index=j, text=t,
                                   origin="action"))
        for j, t in enumerate(default_tokenize(s.observation)):
            kept.append(TokenCoord(step=s.index, token_index=j, text=t,
                                   origin="observation"))
    return CompressedTrajectory(traj_id=traj.traj_id, kept=kept)


def ablation_subset(split: pd.DataFrame, n: int = 150, seed: int = 0):
    """Stratified 150-of-235 sample."""
    frac = {("Terminal-Bench", "hard"): 0.0}
    strata = split.groupby(["src_bench", "difficulty"], group_keys=False)
    sampled = strata.apply(
        lambda g: g.sample(frac=min(1.0, n / len(split)),
                           random_state=seed))
    return sampled.head(n).reset_index(drop=True)


def run_variant(name: str, row, artifacts_dir, cfg):
    traj = load_trajectory(row, artifacts_dir)
    cf = CauseFlow(cfg)

    if name == "w/o Compression":
        raw = raw_trajectory_view(traj)
        att = attribute(traj, raw, cf.analyzer, cfg)
        evidence = EvidenceBundle.build(traj, raw, att.paths)
        return [c.step for c in cf.reasoner.rank(evidence, cfg)]

    if name in ("w/o SF", "w/o HS", "w/o KI"):
        w = list(cfg.fusion_weights)
        idx = {"w/o SF": 0, "w/o HS": 1, "w/o KI": 2}[name]
        w[idx] = 0.0
        tot = sum(w)
        cfg2 = CauseFlowConfig(
            fusion_weights=tuple(x / tot for x in w), seed=cfg.seed)
        return [c.step for c in CauseFlow(cfg2).diagnose(traj).candidates]

    if name == "w/o LLM reasoning":
        cfg2 = CauseFlowConfig(seed=cfg.seed)
        cf2 = CauseFlow(cfg2)
        diag = cf2.diagnose(traj)
        mock = MockReasoner()
        ev = EvidenceBundle.build(traj, compress(traj, cfg2), diag.paths)
        return [c.step for c in mock.rank(ev, cfg2)]

    if name == "w/o Attribution paths (same reasoner)":
        cfg2 = CauseFlowConfig(seed=cfg.seed)
        cf2 = CauseFlow(cfg2)
        comp = compress(traj, cfg2)
        ev = EvidenceBundle.build(traj, comp, [])
        return [c.step for c in cf2.reasoner.rank(ev, cfg2)]

    return [c.step for c in cf.diagnose(traj).candidates]


VARIANTS = ["w/o Compression", "w/o SF", "w/o HS", "w/o KI",
            "w/o LLM reasoning",
            "w/o Attribution paths (same reasoner)", "CauseFlow (full)"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    split = pd.read_parquet(os.path.join(
        ROOT, "data", "codetracebench", "eval_split_235.parquet"))
    subset = ablation_subset(split)
    if args.limit:
        subset = subset.head(args.limit)
    artifacts_dir = os.path.join(ROOT, "data", "codetracebench", "artifacts")
    cfg = CauseFlowConfig()

    for name in VARIANTS:
        golds, preds = [], []
        for _, row in subset.iterrows():
            steps = run_variant(name, row, artifacts_dir, cfg)
            n = int(row["step_count"])
            steps = [s for s in steps if s and 1 <= s <= n][:3]
            golds.append(int(row["i_star"]))
            preds.append(steps)
        rep = localization_report(preds, golds)
        print(f"{name:40s} N={rep['N']:4d}  top-1 {rep['top1']*100:6.2f}")


if __name__ == "__main__":
    main()
