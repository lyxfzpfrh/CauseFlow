"""Hyperparameters of CauseFlow (paper §3.4, "Hyperparameters, models, and cost").

All defaults are the grid-searched values reported in the paper:
  fusion weights   w1, w2, w3 = (0.30, 0.25, 0.45)
  edge threshold   theta       = 0.50
  lambda balance   l1, l2      = (0.4, 0.6)
  source prefilter mu          = 32 candidates per target
  episode window               = 8 steps, guard window = 3 steps
  k (top-k candidates)         = 3
  edit budget beta             = 15% of the edited segment
  iteration cap (repair)       = 1
  EK-FAC damping               = 1e-3, one curvature update per trajectory
  occlusion batch size         = 64
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CauseFlowConfig:
    # ---- Stage 1: compression (§3.2) ----
    episode_window: int = 8          # episode-aligned reduction window
    guard_window: int = 3            # guard steps around failure neighborhood
    redundancy_threshold: float = 0.8  # Jaccard above which repeated content is redundant

    # ---- Stage 2: attribution (§3.3) ----
    lambda_sf: tuple = (0.4, 0.6)    # (lambda_1, lambda_2): cosine vs rollout in SF
    fusion_weights: tuple = (0.30, 0.25, 0.45)   # (w1, w2, w3) for SF/HS/KI
    edge_threshold: float = 0.50     # theta
    source_prefilter: int = 32       # mu: candidate sources kept per target
    max_targets_per_step: int = 64   # tractability cap on target tokens per
    #                                  step window (0 disables; raise for
    #                                  full-fidelity GPU runs)
    ekfac_damping: float = 1e-3
    occlusion_batch: int = 64

    # ---- Stage 3: reasoning and repair (§3.4) ----
    top_k: int = 3
    edit_budget_ratio: float = 0.15  # beta = 15% of the edited segment tokens
    iteration_cap: int = 1           # at most one further repair pass

    # ---- Models ----
    analyzer_model: str = "deepseek-ai/DeepSeek-V4"      # scoring engine (§3.3, Scoring engine)
    reasoner_model: str = "deepseek-chat"                # Stage-3 reasoner = B2's model
    reasoner_base_url: str = ""                          # OpenAI-compatible endpoint
    seed: int = 0

    # ---- Runtime switches (artifact convenience) ----
    use_mock_analyzer: bool = True    # deterministic mock internals (no GPU)
    use_mock_reasoner: bool = True    # deterministic heuristic reasoner (no API)

    def __post_init__(self):
        assert abs(sum(self.fusion_weights) - 1.0) < 1e-9, "w1+w2+w3 must equal 1"
