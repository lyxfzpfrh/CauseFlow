"""Stage 2: Attribution Analysis (paper §3.3)."""
from .segmentation import segment, prefilter, StepPair
from .signals import semantic_flow, hessian_sensitivity, kl_impact, fuse
from .analyzer import Analyzer, MockAnalyzer, HFAnalyzer, build_analyzer
from .tracing import attribute, trace_backward, AttributionResult

__all__ = [
    "segment", "prefilter", "StepPair",
    "semantic_flow", "hessian_sensitivity", "kl_impact", "fuse",
    "Analyzer", "MockAnalyzer", "HFAnalyzer", "build_analyzer",
    "attribute", "trace_backward", "AttributionResult",
]
