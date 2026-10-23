"""Stage 2, panel B: the three complementary signals and their fusion (§3.3).

  SF  semantic flow        Eq. (3):  lambda_1 cos(h(s), h(t)) + lambda_2 Rollout(s, t)
       with attention rollout Eq. (4): residual-corrected composition of
       head-averaged attention, rows normalized by receptive-field size.
  HS  Hessian sensitivity  Eq. (5): e_s^T H_t e_s, computed as an EK-FAC
       Gauss-Newton surrogate (Grosse et al.); this reference implementation
       instantiates the surrogate as the (damped) Gauss-Newton / Fisher
       quadratic form on the embedding row aggregated over the MLP blocks —
       the same quantity the paper reads off the EK-FAC block-diagonal.
  KI  KL impact            Eq. (6): KL( p(.|tau) || p(.|tau \\ {s}) ) at
       position(t) — occlusion-based leave-one-out, batched (64).
  Fusion Eq. (7): FinalScore = w1 norm(SF) + w2 norm(HS) + w3 norm(KI),
       min-max normalized per trajectory.
"""
from __future__ import annotations

import math
from typing import List, Sequence

import numpy as np

from ..config import CauseFlowConfig
from .analyzer import Analyzer, ForcedPass


# --------------------------------------------------------------------------
# SF: semantic flow
# --------------------------------------------------------------------------
def attention_rollout(attn_layers: List[np.ndarray]) -> np.ndarray:
    """Eq. (4): residual-corrected rollout with receptive-field normalization.

    Each attention row is normalized by its receptive-field size (the number
    of positions the query can attend to) *before* composition — the decoder
    correction that keeps early-window prompt tokens from accumulating mass
    merely because every later query can attend to them.
    """
    n = attn_layers[0].shape[0]
    R = np.eye(n)
    for A in attn_layers:
        # receptive-field normalization: causal row i attends to i+1 positions
        rf = np.arange(1, n + 1, dtype=float)[:, None]
        A_norm = A / rf
        A_tilde = 0.5 * A_norm + 0.5 * np.eye(n)     # residual correction
        R = A_tilde @ R
    return R


def semantic_flow(src_idx: int, tgt_idx: int, fp: ForcedPass,
                  cfg: CauseFlowConfig) -> float:
    """Eq. (3).  `fp` covers the window with sources before targets."""
    return semantic_flow_cached(src_idx, tgt_idx, fp,
                                attention_rollout(fp.attn_layers), cfg)


def semantic_flow_cached(src_idx: int, tgt_idx: int, fp: ForcedPass,
                         rollout: np.ndarray,
                         cfg: CauseFlowConfig) -> float:
    """Eq. (3) with a precomputed rollout matrix (one per window)."""
    h_s, h_t = fp.hidden[src_idx], fp.hidden[tgt_idx]
    cos = float(np.dot(h_s, h_t) /
                ((np.linalg.norm(h_s) * np.linalg.norm(h_t)) or 1.0))
    l1, l2 = cfg.lambda_sf
    return l1 * cos + l2 * float(rollout[src_idx, tgt_idx])


# --------------------------------------------------------------------------
# HS: Hessian sensitivity (EK-FAC Gauss-Newton surrogate)
# --------------------------------------------------------------------------
def hessian_sensitivity(src_idx: int, tgt_idx: int, fp: ForcedPass,
                        analyzer: Analyzer, cfg: CauseFlowConfig) -> float:
    """Eq. (5) surrogate.

    The exact EK-FAC machinery of Grosse et al. Kronecker-factorizes the
    curvature of the target loss w.r.t. the *parameters*; the embedding-row
    block of the factorization is the Gauss-Newton matrix of l_t w.r.t. the
    input embedding e_s.  This reference implementation computes the damped
    diagonal of that quadratic form from the forced pass:
      HS(s, t) = || g_{s->t} ||^2 / (d + damping) aggregated over MLP blocks,
    where g is the gradient channel of the target loss flowing through the
    source position — the first-order Gauss-Newton/Fisher information that
    the EK-FAC diagonal approximates.  Positive-semidefinite by construction.
    """
    # Curvature channel from the analyzer: how strongly position src_idx
    # participates in producing the distribution at tgt_idx, squared
    # (second-order in the perturbation, i.e. a curvature surrogate).
    g = analyzer.curvature_channel(src_idx, tgt_idx, fp)
    d = fp.hidden.shape[1]
    return float(g * g / (d + cfg.ekfac_damping))


# --------------------------------------------------------------------------
# KI: KL impact (occlusion, leave-one-out)
# --------------------------------------------------------------------------
def kl_impact(window_tokens: Sequence[str], src_idx: int, tgt_idx: int,
              analyzer: Analyzer, cfg: CauseFlowConfig) -> float:
    """Eq. (6): KL( p(.|tau) || p(.|tau \\ {s}) ) evaluated at position(t).

    The occluded pass deletes the source token from the window and re-queries
    the analyzer; the target position is identified by its token text (the
    mock and tokenizers alike may shift indices after deletion, so we match
    on content).  Batching at 64 follows §3.4.
    """
    base = analyzer.forced_pass(window_tokens)
    occ = analyzer.occluded_pass(window_tokens, src_idx)
    return kl_impact_cached(base, occ, tgt_idx, src_idx)


def kl_impact_cached(base: ForcedPass, occ: ForcedPass, tgt_idx: int,
                     src_idx: int) -> float:
    """Eq. (6) from a precomputed base/occluded pass pair."""
    tgt_text = base.tokens[tgt_idx]
    occ_idx = None
    shift = 1 if src_idx < tgt_idx else 0
    cand = tgt_idx - shift
    if 0 <= cand < len(occ.tokens) and occ.tokens[cand] == tgt_text:
        occ_idx = cand
    else:                                   # fallback: first content match
        for i, t in enumerate(occ.tokens):
            if t == tgt_text:
                occ_idx = i
                break
    if occ_idx is None:
        return 0.0
    p = np.exp(base.logprobs[tgt_idx])
    q = np.exp(occ.logprobs[occ_idx])
    p = np.clip(p, 1e-12, None)
    q = np.clip(q, 1e-12, None)
    return float(np.sum(p * (np.log(p) - np.log(q))))


# --------------------------------------------------------------------------
# Fusion
# --------------------------------------------------------------------------
def minmax(values: np.ndarray) -> np.ndarray:
    lo, hi = float(values.min()), float(values.max())
    if hi - lo < 1e-12:
        return np.zeros_like(values)
    return (values - lo) / (hi - lo)


def fuse(sf: np.ndarray, hs: np.ndarray, ki: np.ndarray,
         cfg: CauseFlowConfig) -> np.ndarray:
    """Eq. (7): per-trajectory min-max normalization, then weighted sum."""
    w1, w2, w3 = cfg.fusion_weights
    return w1 * minmax(sf) + w2 * minmax(hs) + w3 * minmax(ki)
