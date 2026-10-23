"""Stage 2, panel A: trajectory segmentation and the source-target setting.

§3.3.1: the compressed trajectory is split into steps; for step i the source
tokens collect (a) the input of step i — system prompt segments, the task
instruction, tool descriptions, retrieved RAG chunks — and (b) the output of
step i-1 (LLM output, action, environment feedback); the target tokens are
the output of step i.  An output token of step i-1 appears as a source in the
step-i analysis and as a target in the step-(i-1) analysis, which is what
chains per-step records into cross-step causal paths.

A source prefilter of mu = 32 candidates per target (§3.4) keeps the
O(|S| x |Y|) blow-up tractable before the signals are computed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..config import CauseFlowConfig
from ..schema import CompressedTrajectory, EditableInput, Trajectory, TokenCoord


@dataclass
class StepPair:
    """One step-wise analysis window: sources (S_i) and targets (Y_i)."""
    step: int                       # the step being analyzed (targets = y_i)
    sources: List[TokenCoord]       # editable inputs + static context + y_{i-1}
    targets: List[TokenCoord]       # y_i tokens


def segment(traj: Trajectory, compressed: CompressedTrajectory,
            cfg: CauseFlowConfig) -> List[StepPair]:
    """Build the step-wise source-target pairs over the compressed trajectory.

    Coordinates reuse Stage 1's TokenCoord so that every scored token maps
    back to the original trajectory through the position map M.
    """
    kept = compressed.kept
    # editable tokens (step == 0) act as sources for every step
    editable = [c for c in kept if c.step == 0]
    by_step: Dict[int, List[TokenCoord]] = {}
    for c in kept:
        if c.step > 0:
            by_step.setdefault(c.step, []).append(c)

    pairs: List[StepPair] = []
    steps = sorted(by_step.keys())
    for idx, step in enumerate(steps):
        tokens = by_step[step]
        targets = [c for c in tokens if c.origin == "action"]
        if not targets:
            continue
        prev_out: List[TokenCoord] = []
        if idx > 0:
            prev = steps[idx - 1]
            prev_out = [c for c in by_step[prev] if c.origin in ("action", "observation")]
        sources = editable + prev_out
        if not sources:
            # degenerate one-step case: static context only
            sources = list(editable)
        pairs.append(StepPair(step=step, sources=sources, targets=targets))
    return pairs


def prefilter(pair: StepPair, analyzer, cfg: CauseFlowConfig) -> StepPair:
    """Keep the top-mu source candidates per window (cheap salience first).

    The cheap score is the embedding cosine between each source token and
    its best-matching target token; computed as one matrix product over
    cached embeddings.  Ties broken deterministically by (step, index).
    """
    mu = cfg.source_prefilter
    if len(pair.sources) <= mu:
        return pair
    import numpy as np
    S = np.stack([analyzer.embed(s.text) for s in pair.sources])
    T = np.stack([analyzer.embed(t.text) for t in pair.targets])
    best = (S @ T.T).max(axis=1)                     # (n_src,)
    order = sorted(range(len(pair.sources)),
                   key=lambda i: (-best[i], pair.sources[i].step,
                                  pair.sources[i].token_index))
    return StepPair(step=pair.step,
                    sources=[pair.sources[i] for i in order[:mu]],
                    targets=pair.targets)


def cap_targets(pair: StepPair, cfg: CauseFlowConfig) -> StepPair:
    """Cap the number of target tokens per step window.

    Reference-implementation tractability cap: real trajectories carry
    hundreds of output tokens per step, and the O(n^2) attention rollout
    over the window grows quadratically with them.  The cap keeps the
    window small; set it to 0 to disable (full-fidelity GPU runs).
    """
    cap = getattr(cfg, "max_targets_per_step", 0)
    if not cap or len(pair.targets) <= cap:
        return pair
    return StepPair(step=pair.step, sources=pair.sources,
                    targets=pair.targets[:cap])
