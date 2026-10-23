"""Baselines: direct reading (B1 / B2) and the sanity check (B3), §4.1.2.

Both direct-reading baselines receive the *full, uncompressed* failed
trajectory and the same goal instruction — output the root-cause step — and
represent the ceiling of strong models reading the trajectory directly.
B3 (Random / Majority) is a sanity check.  The same-reasoner, no-attribution
control (the "w/o Attribution paths" variant of RQ3) is the same reasoner as
CauseFlow's Stage 3 reading the *compressed* trajectory without the
attribution paths.
"""
from __future__ import annotations

import random
from collections import Counter
from typing import List, Optional

from .config import CauseFlowConfig
from .schema import Candidate, Trajectory
from .stage1_compression import compress, error_signal_steps
from .stage3_repair import EvidenceBundle


class DirectReadingBaseline:
    """B1 (GPT-4o) / B2 (DeepSeek-V4): a reasoner reads the full trajectory.

    With an LLM reasoner this is the paper's B1/B2; with the MockReasoner it
    emulates the documented failure mode of direct reading — the visible-
    suspect (scapegoat) bias: the most recent step carrying an error signal
    is ranked first, which the motivating example shows to be misled
    remediation rather than the root cause.
    """

    def __init__(self, reasoner=None, cfg: Optional[CauseFlowConfig] = None,
                 name: str = "direct-reading"):
        self.reasoner = reasoner
        self.cfg = cfg or CauseFlowConfig()
        self.name = name

    def localize(self, traj: Trajectory) -> List[Candidate]:
        if self.reasoner is not None:
            evidence = EvidenceBundle.build(traj, compress(traj, self.cfg), [])
            return self.reasoner.rank(evidence, self.cfg)
        # mock: visible-suspect bias (recency-ranked error steps)
        err = sorted(error_signal_steps(traj), reverse=True)
        steps = err or [traj.failure_step]
        out = []
        for i, s in enumerate(steps[: self.cfg.top_k]):
            out.append(Candidate(
                step=s, region="", strength=1.0 - 0.1 * i,
                confidence=0.9 - 0.1 * i, type=None,
                rationale="most recent error-signal step (visible suspect)"))
        return out


class NoAttributionControl:
    """The RQ3 'w/o Attribution paths' variant: the same reasoner as
    Stage 3 reading the compressed trajectory, with no attribution paths."""

    def __init__(self, reasoner, cfg: Optional[CauseFlowConfig] = None):
        self.reasoner = reasoner
        self.cfg = cfg or CauseFlowConfig()

    def localize(self, traj: Trajectory) -> List[Candidate]:
        evidence = EvidenceBundle.build(traj, compress(traj, self.cfg), [])
        return self.reasoner.rank(evidence, self.cfg)


class RandomMajority:
    """B3 sanity check: Random picks a step uniformly; Majority picks the
    modal annotated step seen on the evaluation set (default prior: the
    final step)."""

    def __init__(self, mode: str = "random", seed: int = 0,
                 majority_step: Optional[int] = None):
        assert mode in ("random", "majority")
        self.mode = mode
        self.rng = random.Random(seed)
        self.majority_step = majority_step

    def localize(self, traj: Trajectory) -> List[Candidate]:
        n = traj.n_steps
        if self.mode == "majority":
            pick = self.majority_step or n
            return [Candidate(step=pick, region="", confidence=0.5)
                    for _ in range(3)]
        picks = self.rng.sample(range(1, n + 1), k=min(3, n))
        return [Candidate(step=p, region="", confidence=1 / (i + 1))
                for i, p in enumerate(picks)]
