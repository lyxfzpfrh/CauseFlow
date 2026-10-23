"""Evaluation protocol of the paper (§4.1, §4.2).

Localization metrics (RQ1 / RQ3 / RQ4):
  * step-level Top-1 / Top-3 accuracy;
  * F1 computed set-level under the official evaluation protocol: the
    annotations of the evaluated split name a fixed number of distinct
    incorrect steps in total (56 for the 235-trajectory evaluation set),
    and each run scores precision over its delivered candidate steps and
    recall over these positives, with F1 as their harmonic mean:
        P = TP / pred,   R = TP / n_pos,   F1 = 2 TP / (pred + n_pos)
    where TP = delivered candidates that hit an annotated positive and
    pred = the number of delivered candidates.

Significance and effect sizes:
  * paired McNemar (exact) on per-trajectory binary top-1 outcomes,
    with Holm correction across the pairwise comparisons;
  * Cliff's delta for paired binary outcomes == correctness margin / N;
  * Wilson 95% confidence intervals for repair rates;
  * expected calibration error (ECE) before/after temperature scaling.
"""
from __future__ import annotations

import math
from math import comb
from typing import Dict, List, Sequence, Tuple


# --------------------------------------------------------------------------
# Localization metrics
# --------------------------------------------------------------------------
def topk_accuracy(preds: Sequence[Sequence[int]], golds: Sequence[int],
                  k: int) -> float:
    """Fraction of trajectories whose gold step is in the top-k predictions."""
    assert len(preds) == len(golds)
    if not preds:
        return 0.0
    hits = sum(1 for p, g in zip(preds, golds)
               if p is not None and len(p) >= 1 and g in p[:k])
    return hits / len(preds)


def prf_setlevel(tp: int, pred: int, n_pos: int) -> Tuple[float, float, float]:
    """P, R, F1 from one run's records on the set-level basis: tp delivered
    candidates hit an annotated positive, pred candidates delivered in
    total, n_pos distinct annotated positives."""
    return tp / pred, tp / n_pos, 2 * tp / (pred + n_pos)


def localization_report(preds: Sequence[Sequence[int]],
                        golds: Sequence[int],
                        positives: int = 0) -> Dict[str, float]:
    """Top-1 / Top-3 accuracy over the evaluated trajectories.

    `positives` (distinct annotated incorrect steps) is reported alongside
    for the set-level F1 protocol; per-run (TP, pred) records are needed to
    score precision and recall, so the F1 fields are only filled by the
    harnesses that track delivered candidates (see evaluation/exp_data.py).
    """
    n = len(golds)
    t1 = sum(1 for p, g in zip(preds, golds)
             if p is not None and len(p) >= 1 and g == p[0])
    t3 = sum(1 for p, g in zip(preds, golds)
             if p is not None and g in p[:3])
    return {"N": n, "top1_hits": t1, "top3_hits": t3,
            "top1": t1 / n, "top3": t3 / n,
            "positives": positives}


# --------------------------------------------------------------------------
# Significance tests
# --------------------------------------------------------------------------
def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar p-value from discordant counts (b, c)."""
    if b + c == 0:
        return 1.0
    n = b + c
    p = 2 * sum(comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n
    return min(p, 1.0)


def holm(pvals: Dict[str, float]) -> Dict[str, float]:
    """Holm step-down adjusted p-values."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted, running = {}, 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)      # enforce monotonicity
        adjusted[name] = running
    return adjusted


def cliffs_delta_paired_binary(correct_a: Sequence[bool],
                               correct_b: Sequence[bool]) -> float:
    """Cliff's delta for paired binary outcomes = correctness margin / N
    (the attainable effect size at this paired-binary scale, §4.2.1)."""
    n = len(correct_a)
    if n == 0:
        return 0.0
    margin = sum(1 for a, b in zip(correct_a, correct_b) if a and not b) - \
             sum(1 for a, b in zip(correct_a, correct_b) if b and not a)
    return margin / n


def wilson_ci(k: int, n: int, z: float = 1.959963985) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion k/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / den, (c + h) / den)


def two_proportion_z(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-proportion z statistic (repair rate vs identity flip rate)."""
    pp = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    return (k1 / n1 - k2 / n2) / se if se else 0.0


# --------------------------------------------------------------------------
# Calibration
# --------------------------------------------------------------------------
def ece(confidences: Sequence[float], corrects: Sequence[bool],
        bins: int = 10) -> float:
    """Expected calibration error (equal-width confidence bins)."""
    n = len(confidences)
    if n == 0:
        return 0.0
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(confidences) if lo <= c < hi or
               (b == bins - 1 and c == 1.0)]
        if not idx:
            continue
        acc = sum(1 for i in idx if corrects[i]) / len(idx)
        conf = sum(confidences[i] for i in idx) / len(idx)
        total += len(idx) / n * abs(conf - acc)
    return total
