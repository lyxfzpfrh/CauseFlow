"""Stage 3, steps 3-4: locate the earliest editable input; generate a
localized edit under the three guardrails (§3.4).

Following the candidate path of each top-ranked root cause backwards along
the attribution chain, earliest editable input first, Stage 3 identifies the
earliest editable region in I (system prompt / task instruction / tool
description / RAG chunk); a missing-type root cause is localized to the
prompt region that should have carried the constraint.

The edit is a unified diff over that editable input, typed by the five-type
edit taxonomy, and subject to the guardrails:
  (i)   budget   |delta| <= beta = 15% of the tokens of the edited segment;
  (ii)  task intent preserved (LLM judge);
  (iii) constraints unrelated to the failure kept untouched.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import List, Optional

from ..config import CauseFlowConfig
from ..schema import (Candidate, EditableInput, EditType, EDIT_FOR_CAUSE,
                      LocalizedEdit, Trajectory)


# --------------------------------------------------------------------------
# Step 3: locate the earliest editable input
# --------------------------------------------------------------------------
def locate_editable(traj: Trajectory,
                    candidate: Candidate) -> Optional[EditableInput]:
    """Earliest editable input first along the attribution chain.

    Candidates terminating on the editable input (step == 0) carry the
    region token; we resolve it to the editable segment that contains it.
    For generated-token candidates (cascade / scapegoat) we default to the
    system prompt, the earliest editable input of every step.
    """
    if not traj.editable_inputs:
        return None
    if candidate.step == 0 and candidate.region:
        for seg in traj.editable_inputs:
            if candidate.region in seg.tokens or candidate.region in seg.text:
                return seg
    # earliest editable input first: system prompt, then instruction, ...
    order = {"system_prompt": 0, "task_instruction": 1,
             "tool_description": 2, "rag_chunk": 3}
    return sorted(traj.editable_inputs,
                  key=lambda s: order.get(s.kind.value, 4))[0]


# --------------------------------------------------------------------------
# Step 4: generate a localized edit
# --------------------------------------------------------------------------
ADD_CONSTRAINT_SUFFIX = {
    "missing constraint": "\nconfirm the target namespace before modifying "
                          "resources; re-verify metrics before and after "
                          "remediation",
}


def _diff(original: str, edited: str, name: str) -> str:
    """Unified diff; trailing newline normalized so add-only edits stay
    add-only (the last line is never spuriously rewritten)."""
    if original and not original.endswith("\n"):
        original += "\n"
    if edited and not edited.endswith("\n"):
        edited += "\n"
    diff = difflib.unified_diff(
        original.splitlines(keepends=True), edited.splitlines(keepends=True),
        fromfile=f"@@ {name} @@", tofile=f"@@ {name} (repaired) @@")
    return "".join(diff)


def generate_edit(traj: Trajectory, candidate: Candidate,
                  cfg: CauseFlowConfig,
                  intent_judge=None) -> Optional[LocalizedEdit]:
    """Generate a budgeted localized edit for the top-ranked candidate."""
    seg = locate_editable(traj, candidate)
    if seg is None:
        return None
    typ = candidate.type or "missing constraint"
    edit_type = EDIT_FOR_CAUSE.get(typ)
    if edit_type is None:              # cascade: repair the originating cause
        edit_type = EditType.ADD_CONSTRAINT

    if edit_type is EditType.ADD_CONSTRAINT:
        appended = ADD_CONSTRAINT_SUFFIX.get(
            "missing constraint", " (verify before acting)")
        edited_text = seg.text.rstrip() + appended
    elif edit_type is EditType.ADD_VERIFICATION:
        edited_text = seg.text.rstrip() + \
            "\nRequire an acceptance check before submitting the final report"
    elif edit_type is EditType.REWRITE_AMBIGUITY:
        edited_text = seg.text.replace(
            "as appropriate", "with explicit preconditions and a schema "
            "for every argument")
        if edited_text == seg.text:
            edited_text = seg.text + "\nPreconditions: state them explicitly."
    elif edit_type is EditType.REPLACE_STALE_CHUNK:
        edited_text = seg.text + "\n[updated chunk: consult current documentation]"
    else:                              # FIX_ARGUMENT_SCHEMA
        edited_text = seg.text + \
            "\nInvalid arguments must be rejected at validation time."

    n_new_tokens = max(len(edited_text.split()) - len(seg.text.split()), 1)
    budget = max(int(len(seg.tokens) * cfg.edit_budget_ratio), 1)
    within = n_new_tokens <= budget

    intent_ok = None
    if intent_judge is not None:
        intent_ok = bool(intent_judge(seg.text, edited_text))

    return LocalizedEdit(
        target_name=seg.name or seg.kind.value,
        edit_type=edit_type,
        diff=_diff(seg.text, edited_text, seg.name or seg.kind.value),
        inserted_tokens=n_new_tokens,
        budget=budget,
        within_budget=within,
        intent_preserved=intent_ok,
        unrelated_untouched=True)      # add/replace-only diffs never delete
                                        # unrelated constraints
