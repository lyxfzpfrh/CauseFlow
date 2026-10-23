"""Stage 3: Reasoning and Repair (paper §3.4)."""
from .reasoning import EvidenceBundle, MockReasoner, LLMReasoner, build_reasoner
from .edit import locate_editable, generate_edit
from .validation import Environment, divergence_step, validate_repair

__all__ = [
    "EvidenceBundle", "MockReasoner", "LLMReasoner", "build_reasoner",
    "locate_editable", "generate_edit",
    "Environment", "divergence_step", "validate_repair",
]
