"""Stage 2, panel C: the attribution matrix and backward tracing (§3.3.4).

Over all step-wise attribution records, the binary attribution matrix
A in {0,1}^{|S| x |Y|} has an edge s -> t iff the record's final_score > theta.
The edges induce a token-level directed graph G_tau in which an output token
of step i-1 appears both as a source (step-i analysis) and as a target
(step-(i-1) analysis), forming the cross-step linkage.

Backward tracing starts from the failure manifestation F(tau) and walks the
high-score edges upwards; a candidate root cause is a source node with *no
high-scoring incoming edge* that can reach F(tau) — the editable-input end of
a traced candidate path — with the geometric mean of final scores along the
path as its initial evidence strength.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from ..config import CauseFlowConfig
from ..schema import (AttributionRecord, CandidatePath, CompressedTrajectory,
                      Trajectory)
from .analyzer import Analyzer
from .segmentation import StepPair, cap_targets, prefilter, segment
from . import signals


@dataclass
class AttributionResult:
    records: List[AttributionRecord]
    paths: List[CandidatePath]
    step_scores: Dict[Tuple[int, int], float]   # (source_step, target_step) -> mass


def _window(pair: StepPair) -> List[str]:
    """Tokens of the analysis window in causal order, sources before targets."""
    return ([c.text for c in pair.sources] + [c.text for c in pair.targets])


def attribute(traj: Trajectory, compressed: CompressedTrajectory,
              analyzer: Analyzer, cfg: CauseFlowConfig) -> AttributionResult:
    """Compute all attribution records, fuse, threshold, and trace backwards.

    One teacher-forced pass per step window, one occluded pass per (window,
    source) — the occlusion batch of §3.4 — then all SF / HS / KI values are
    read off the cached passes.
    """
    pairs = [prefilter(cap_targets(p, cfg), analyzer, cfg)
             for p in segment(traj, compressed, cfg)]

    records: List[AttributionRecord] = []
    for pair in pairs:
        n_src = len(pair.sources)
        window = _window(pair)
        fp = analyzer.forced_pass(window)
        rollout = signals.attention_rollout(fp.attn_layers)
        n_win = len(fp.tokens)
        # occlusion passes: one per source, batched (§3.4: batches of 64)
        occl = {si: analyzer.occluded_pass(window, si)
                for si in range(min(n_src, n_win))}
        for ti, tgt in enumerate(pair.targets):
            tgt_idx = n_src + ti
            if tgt_idx >= n_win:
                continue
            for si, src in enumerate(pair.sources):
                if si >= n_win:
                    break
                sf = signals.semantic_flow_cached(si, tgt_idx, fp, rollout, cfg)
                hs = signals.hessian_sensitivity(si, tgt_idx, fp, analyzer, cfg)
                ki = signals.kl_impact_cached(fp, occl[si], tgt_idx, si) \
                    if si in occl else 0.0
                records.append(AttributionRecord(
                    source_step=src.step, source_index=src.token_index,
                    source_token=src.text,
                    target_step=tgt.step, target_index=tgt.token_index,
                    target_token=tgt.text,
                    semantic_flow=sf, hessian_sensitivity=hs, kl_impact=ki))

    # ---- fusion (Eq. 7) ----
    if records:
        sf_arr = np.array([r.semantic_flow for r in records])
        hs_arr = np.array([r.hessian_sensitivity for r in records])
        ki_arr = np.array([r.kl_impact for r in records])
        fused = signals.fuse(sf_arr, hs_arr, ki_arr, cfg)
        for r, f in zip(records, fused):
            r.final_score = float(f)

    paths = trace_backward(records, traj, cfg)

    # step-level aggregated causal mass (source_step -> target_step)
    step_scores: Dict[Tuple[int, int], float] = defaultdict(float)
    for r in records:
        if r.final_score > cfg.edge_threshold and r.source_step > 0:
            step_scores[(r.source_step, r.target_step)] += r.final_score
    return AttributionResult(records=records, paths=paths,
                             step_scores=dict(step_scores))


# --------------------------------------------------------------------------
# Backward tracing
# --------------------------------------------------------------------------
def _key(r: AttributionRecord, side: str) -> Tuple[int, str, int]:
    if side == "s":
        return (r.source_step, r.source_token, r.source_index)
    return (r.target_step, r.target_token, r.target_index)


def trace_backward(records: List[AttributionRecord], traj: Trajectory,
                   cfg: CauseFlowConfig) -> List[CandidatePath]:
    """Trace candidate paths from F(tau) up the high-score edges of G_tau.

    A path is a list of attribution records ordered from the failure
    manifestation backwards; the *current node* while walking is the source
    of the most recently appended edge.  A node is a relay when some
    high-scoring edge points into it (it appears as the target of a record,
    i.e. it was itself generated); a terminal — a candidate root cause — is a
    node with no high-scoring incoming edge, most notably every editable
    input token, which by construction is never generated.
    """
    edges = [r for r in records if r.final_score > cfg.edge_threshold]
    if not edges:
        return []

    # nodes that some high-scoring edge points *into* (relays)
    has_incoming = {_key(r, "t") for r in edges}
    # edges into a node, grouped
    into: Dict[Tuple, List[AttributionRecord]] = defaultdict(list)
    for r in edges:
        into[_key(r, "t")].append(r)

    failure = traj.failure_step
    # seed from the failure manifestation: the highest-scoring edges whose
    # target is a token generated at the final step.  Seeds are taken by
    # rank (at least `top_k` of them) even when they sit below theta — the
    # threshold governs which edges the walk follows, not where it starts;
    # otherwise a trajectory whose failure step attracts only weak edges
    # would have nothing to trace.
    failure_edges = sorted(
        (r for r in records if r.target_step == failure),
        key=lambda r: -r.final_score)
    frontier: List[Tuple[List[AttributionRecord], Tuple]] = []
    for r in failure_edges[: max(cfg.top_k, 3)]:
        frontier.append(([r], _key(r, "s")))

    paths: List[CandidatePath] = []
    while frontier:
        path, node = frontier.pop()

        # terminal: no high-scoring edge points into this node
        if node not in has_incoming:
            strength = math.exp(sum(math.log(max(r.final_score, 1e-12))
                                    for r in path) / len(path))
            paths.append(CandidatePath(
                records=path, terminal_step=node[0],
                terminal_token=node[1], strength=strength))
            continue

        # relay node: extend through the high-score edges that point into it
        extended = False
        for e in into.get(node, []):
            if len(path) >= 64:            # trace-depth guard
                break
            nxt = _key(e, "s")
            if any(_key(p, "s") == nxt for p in path):
                continue                    # no cycles
            frontier.append((path + [e], nxt))
            extended = True
        if not extended:
            strength = math.exp(sum(math.log(max(r.final_score, 1e-12))
                                    for r in path) / len(path))
            paths.append(CandidatePath(
                records=path, terminal_step=node[0], terminal_token=node[1],
                strength=strength))

    paths.sort(key=lambda p: -p.strength)
    return paths[: cfg.top_k * 4]        # keep a margin for Stage-3 ranking
