"""Data model shared by all three stages (paper §2.3, Problem Formulation).

A trajectory is  tau = <(x_1, y_1), ..., (x_n, y_n)>  (Eq. 1).  The input x_i
draws on the *editable input space*  I = P | D | R  (prompt segments, tool
descriptions, RAG chunks) plus the *dynamic context* (the previous output
y_{i-1}).  The root cause is defined over I (Eq. 2); the failure
manifestation F(tau) is, by convention, the final step.

Tokenization
------------
The default tokenizer is model-agnostic (whitespace + punctuation) so that the
pipeline runs on any plain-text trajectory without GPU access.  When a
transformers-backed analyzer is used, pass its tokenizer instead.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence, Dict, Any


# --------------------------------------------------------------------------
# Tokenization
# --------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def default_tokenize(text: str) -> List[str]:
    """Model-agnostic tokenization: word + punctuation tokens."""
    return _TOKEN_RE.findall(text)


# --------------------------------------------------------------------------
# Editable input space  I = P | D | R
# --------------------------------------------------------------------------
class EditableKind(str, Enum):
    SYSTEM_PROMPT = "system_prompt"        # P: prompt segments
    TASK_INSTRUCTION = "task_instruction"  # P
    TOOL_DESCRIPTION = "tool_description"  # D
    RAG_CHUNK = "rag_chunk"                # R


@dataclass
class EditableInput:
    """One member of the editable input space I (never removed by Stage 1)."""
    kind: EditableKind
    text: str
    name: str = ""                       # human-readable identifier
    tokens: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.tokens:
            self.tokens = default_tokenize(self.text)


# --------------------------------------------------------------------------
# Trajectory
# --------------------------------------------------------------------------
@dataclass
class Step:
    """One input-output interaction (x_i, y_i) of the agent."""
    index: int                            # 1-based step id
    input_text: str                       # x_i: static context assembled for the call
    output_text: str                      # y_i: LLM output (reasoning + action)
    observation: str = ""                 # environment feedback incurred by y_i
    segments: Dict[str, str] = field(default_factory=dict)
    # segments may carry structured parts, e.g. {"system": ..., "instruction": ...,
    # "rag": ..., "previous_output": ...}; loaders populate what they have.


@dataclass
class Trajectory:
    """tau = <(x_1,y_1),...,(x_n,y_n)> with editable inputs and a verdict."""
    traj_id: str
    steps: List[Step]
    editable_inputs: List[EditableInput] = field(default_factory=list)
    verdict: str = "fail"                 # environment verdict; "fail" for our input
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def n_steps(self) -> int:
        return len(self.steps)

    @property
    def failure_step(self) -> int:
        """F(tau): the failure manifestation, by convention the final step."""
        return self.steps[-1].index


# --------------------------------------------------------------------------
# Stage 1 output
# --------------------------------------------------------------------------
@dataclass
class TokenCoord:
    """Original (step, token) coordinate of a kept token (position map M)."""
    step: int
    token_index: int
    text: str
    origin: str            # "editable" | "action" | "observation" | "reasoning"


@dataclass
class CompressedTrajectory:
    """tau' plus the position map M from kept tokens to original coordinates."""
    traj_id: str
    kept: List[TokenCoord]                    # the compressed sequence, in order
    position_map: Dict[int, TokenCoord] = field(default_factory=dict)
    # key = index into `kept`
    removed_reasons: Dict[str, int] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.position_map:
            self.position_map = {i: c for i, c in enumerate(self.kept)}

    @property
    def reduction_ratio(self) -> float:
        n0 = self.stats.get("n_tokens_original")
        n1 = len(self.kept)
        if not n0:
            return 0.0
        return 1.0 - n1 / n0


# --------------------------------------------------------------------------
# Stage 2 output
# --------------------------------------------------------------------------
@dataclass
class AttributionRecord:
    """One (source token, target token) record, §3.3.1 field list."""
    source_step: int          # step the source token belongs to (0 = editable input)
    source_index: int         # token index within that step / editable segment
    source_token: str
    target_step: int
    target_index: int
    target_token: str
    semantic_flow: float = 0.0        # SF, Eq. (3)
    hessian_sensitivity: float = 0.0  # HS, Eq. (4) surrogate
    kl_impact: float = 0.0            # KI, Eq. (5)
    final_score: float = 0.0          # fused score, Eq. (6)


@dataclass
class CandidatePath:
    """A backward-traced path from F(tau) to a terminal source node."""
    records: List[AttributionRecord]          # ordered from failure backwards
    terminal_step: int
    terminal_token: str
    strength: float                           # geometric mean of final scores

    def to_step_candidates(self) -> List[int]:
        return [r.source_step for r in self.records if r.source_step > 0]


# --------------------------------------------------------------------------
# Stage 3 output
# --------------------------------------------------------------------------
ROOT_CAUSE_TYPES = (
    "missing constraint",
    "stale RAG",
    "tool ambiguity",
    "argument hallucination",
    "premature termination",
    "cascade",
)
SCAPEGOAT = "scapegoat"   # explicit non-root-cause flag


@dataclass
class Candidate:
    """One ranked root-cause candidate  (i_j, r_j, type_j, strength_j)."""
    step: int
    region: str                       # token region text ("" for zero-length)
    region_span: Optional[tuple] = None   # (start, end) token indices, or None
    type: Optional[str] = None        # one of ROOT_CAUSE_TYPES or SCAPEGOAT
    strength: float = 0.0
    confidence: float = 0.0           # temperature-scaled ranking confidence
    rationale: str = ""


class EditType(str, Enum):
    """Five-type edit taxonomy (paper Table: edit taxonomy for repair)."""
    ADD_CONSTRAINT = "add constraint"              # missing constraint
    REWRITE_AMBIGUITY = "rewrite ambiguity"        # tool ambiguity
    REPLACE_STALE_CHUNK = "replace stale chunk"    # stale RAG
    FIX_ARGUMENT_SCHEMA = "fix argument schema"    # argument hallucination
    ADD_VERIFICATION = "add verification"          # premature termination


EDIT_FOR_CAUSE: Dict[str, EditType] = {
    "missing constraint": EditType.ADD_CONSTRAINT,
    "tool ambiguity": EditType.REWRITE_AMBIGUITY,
    "stale RAG": EditType.REPLACE_STALE_CHUNK,
    "argument hallucination": EditType.FIX_ARGUMENT_SCHEMA,
    "premature termination": EditType.ADD_VERIFICATION,
    # cascade-type causes are repaired through the edit of the cause they
    # originate from (§3.4, Generate a localized edit).
    "cascade": None,
}


@dataclass
class LocalizedEdit:
    """A budgeted, intent-preserving edit over one editable input."""
    target_name: str                  # which editable input is edited
    edit_type: EditType
    diff: str                         # unified diff text
    inserted_tokens: int = 0
    budget: int = 0                   # beta = 15% of the edited segment
    within_budget: bool = True
    intent_preserved: Optional[bool] = None   # LLM judge verdict
    unrelated_untouched: bool = True


@dataclass
class RepairResult:
    verdict: str                      # "success" | "fail" | "not_reexecuted"
    edit: Optional[LocalizedEdit] = None
    divergence_step: Optional[int] = None    # first action-level departure
    passes_used: int = 0
    cost_usd: float = 0.0


@dataclass
class Diagnosis:
    """End-to-end output of the CauseFlow pipeline on one trajectory."""
    traj_id: str
    candidates: List[Candidate] = field(default_factory=list)
    paths: List[CandidatePath] = field(default_factory=list)
    edits: List[LocalizedEdit] = field(default_factory=list)
    repair: Optional[RepairResult] = None
    compression_stats: Dict[str, Any] = field(default_factory=dict)
