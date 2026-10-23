"""Stage 1: Trajectory Compression (paper §3.2).

Failure-preserving, offline reduction built on the AgentDiet core module
(waste taxonomy: useless / redundant / expired), with both mechanisms
re-designed around the failure instead of around cost:

  * Re-set delay  -> the *failure-preserving delay*: content carrying error
    signals (errors, tracebacks, anomalous metrics) and the whole *failure
    neighborhood* are delayed until the final step and never compressed.
  * Re-set window -> the *episode-aligned window*: expiry / redundancy are
    judged within complete problem-solving episodes (default 8 steps).

The failure neighborhood is defined entirely from observables (never from
annotations): the failure manifestation F(tau) with a guard window of 3 steps
on either side, every step whose content carries an error signal with the same
guard window, and the editable input segments, which are never candidates for
removal.

Output: the compressed trajectory tau' plus the position map M from kept
tokens to original (step, token) coordinates.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Set

from .config import CauseFlowConfig
from .schema import (CompressedTrajectory, TokenCoord, Trajectory,
                     default_tokenize)

# Fixed pattern set for error signals: errors, tracebacks, anomalous metrics.
ERROR_PATTERNS = [
    re.compile(r"\btraceback\b", re.I),
    re.compile(r"\berror\b", re.I),
    re.compile(r"\bexception\b", re.I),
    re.compile(r"\bfail(?:ed|ure|ing)?\b", re.I),
    re.compile(r"\bdenied\b", re.I),
    re.compile(r"\btimeout\b", re.I),
    re.compile(r"\brefus(?:ed|al)\b", re.I),
    re.compile(r"\bnot found\b", re.I),
    re.compile(r"\bno\s+\w+\s+found\b", re.I),
    re.compile(r"\bNaN\b"),
    re.compile(r"\bpanic\b", re.I),
    re.compile(r"\bfatal\b", re.I),
    re.compile(r"\bexit code [1-9]\d*", re.I),
    re.compile(r"\b unhealthy\b", re.I),
    re.compile(r"\bcritical\b", re.I),
]


def carries_error_signal(text: str) -> bool:
    """True if the fixed pattern set matches errors/tracebacks/anomalies."""
    return any(p.search(text) for p in ERROR_PATTERNS)


def error_signal_steps(traj: Trajectory) -> Set[int]:
    """Steps whose content (output or observation) carries an error signal."""
    hits = set()
    for s in traj.steps:
        if carries_error_signal(s.output_text) or carries_error_signal(s.observation):
            hits.add(s.index)
    return hits


def failure_neighborhood(traj: Trajectory, cfg: CauseFlowConfig) -> Set[int]:
    """Observable failure neighborhood: F(tau) +/- guard, error steps +/- guard."""
    nb: Set[int] = set()
    anchors = {traj.failure_step} | error_signal_steps(traj)
    all_steps = {s.index for s in traj.steps}
    for a in anchors:
        for d in range(-cfg.guard_window, cfg.guard_window + 1):
            idx = a + d
            if idx in all_steps:
                nb.add(idx)
    return nb


# --------------------------------------------------------------------------
# Waste classification within episode-aligned windows
# --------------------------------------------------------------------------
def _jaccard(a: Counter, b: Counter) -> float:
    if not a and not b:
        return 0.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 0.0


def _classify_waste(traj: Trajectory, cfg: CauseFlowConfig) -> Dict[int, str]:
    """Classify each non-protected step's observation as waste or 'keep'.

    Judgement is made inside a sliding episode window (8 steps): a content
    block is  expired  if a later observation in the window supersedes it
    (high token overlap with a strictly later block),  redundant  if it
    repeats an earlier block in the window, and  useless  if it is dominated
    by sheer length without any overlap anchor (log dumps etc.).
    """
    reasons: Dict[int, str] = {}
    n = len(traj.steps)
    for i, s in enumerate(traj.steps):
        if not s.observation:
            continue
        window = traj.steps[max(0, i - cfg.episode_window): i + cfg.episode_window]
        cur = Counter(default_tokenize(s.observation))
        later = [Counter(default_tokenize(w.observation)) for w in window
                 if w.index > s.index and w.observation]
        if any(_jaccard(cur, l) >= cfg.redundancy_threshold for l in later):
            reasons[s.index] = "expired"       # superseded by a later step
        elif any(_jaccard(cur, l) >= cfg.redundancy_threshold * 0.6 for l in later):
            reasons[s.index] = "redundant"     # partial repetition in window
        elif len(cur) > 400 and not any(_jaccard(cur, l) > 0.05 for l in later):
            reasons[s.index] = "useless"       # unanchored log dump
    return reasons


# --------------------------------------------------------------------------
# The stage
# --------------------------------------------------------------------------
def compress(traj: Trajectory, cfg: CauseFlowConfig) -> CompressedTrajectory:
    """Run Stage 1: failure-preserving offline compression of `traj`."""
    protected = failure_neighborhood(traj, cfg)
    waste = _classify_waste(traj, cfg)

    kept: List[TokenCoord] = []
    n_original = 0
    removed: Counter = Counter()

    # Editable input segments are never candidates for removal.
    for seg in traj.editable_inputs:
        for j, tok in enumerate(seg.tokens):
            n_original += 1
            kept.append(TokenCoord(step=0, token_index=j, text=tok,
                                   origin="editable"))

    for s in traj.steps:
        out_toks = default_tokenize(s.output_text)
        obs_toks = default_tokenize(s.observation)
        n_original += len(out_toks) + len(obs_toks)
        # Agent outputs (reasoning + action) carry the decisions; keep them.
        for j, tok in enumerate(out_toks):
            kept.append(TokenCoord(step=s.index, token_index=j, text=tok,
                                   origin="action"))
        if s.index in protected:
            for j, tok in enumerate(obs_toks):
                kept.append(TokenCoord(step=s.index, token_index=j, text=tok,
                                       origin="observation"))
        else:
            reason = waste.get(s.index, "keep")
            if reason == "keep":
                for j, tok in enumerate(obs_toks):
                    kept.append(TokenCoord(step=s.index, token_index=j, text=tok,
                                           origin="observation"))
            else:
                removed[reason] += len(obs_toks)

    compressed = CompressedTrajectory(
        traj_id=traj.traj_id,
        kept=kept,
        removed_reasons=dict(removed),
        stats={
            "n_tokens_original": n_original,
            "n_tokens_kept": len(kept),
            "reduction_ratio": 1.0 - len(kept) / n_original if n_original else 0.0,
            "protected_steps": sorted(protected),
            "error_signal_steps": sorted(error_signal_steps(traj)),
        },
    )
    return compressed


def retention_check(traj: Trajectory, compressed: CompressedTrajectory,
                    annotation_step: int) -> bool:
    """Post-hoc verification that the annotated root-cause step survives.

    §3.2: all 235 annotated root-cause steps survive compression on the
    evaluation set; this helper verifies it for a single trajectory.
    """
    kept_steps = {c.step for c in compressed.kept}
    return annotation_step in kept_steps
