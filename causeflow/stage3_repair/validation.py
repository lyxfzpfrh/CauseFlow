"""Stage 3, step 5: validate the repair by re-execution (§3.4).

Where an environment exists (the ITBench gym for RQ2), the repaired task is
re-executed; success flips the verdict, failure feeds the new trajectory
back into the candidate paths for at most one further pass (iteration cap
1).  The divergence step — the first step at which the repaired execution
departs from the failed one, judged at the *action level* (a change of the
issued tool call or of its arguments) rather than the token level — is
recorded as the consistency check of §4.2.3.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

from ..config import CauseFlowConfig
from ..schema import LocalizedEdit, RepairResult, Trajectory


class Environment(Protocol):
    """Re-execution oracle E(tau | delta) (Eq. 2)."""

    def execute(self, traj: Trajectory, edit: LocalizedEdit) -> Trajectory:
        """Re-run the task under the edited input; return the new trajectory
        whose `verdict` field is 'success' or 'fail'."""
        ...


def action_signature(step) -> str:
    """Action-level signature of a step: the tool call + its arguments.

    Cosmetic wording changes in the reasoning text do not count as
    divergence; only a changed tool call or changed arguments do.
    """
    out = step.output_text
    # crude but deterministic: first code-ish / imperative line of the output
    for line in out.splitlines():
        line = line.strip()
        if line and (line.startswith(("kubectl", "python", "bash", "sh",
                                      "git", "curl", "pip", "npm", "cd"))
                     or line.startswith("```")):
            return line
    return out.strip().splitlines()[0] if out.strip() else ""


def divergence_step(failed: Trajectory, repaired: Trajectory) -> Optional[int]:
    """First step at which two executions depart at the action level."""
    for a, b in zip(failed.steps, repaired.steps):
        if action_signature(a) != action_signature(b):
            return a.index
    if failed.n_steps != repaired.n_steps:
        return min(failed.n_steps, repaired.n_steps) + 1
    return None


def validate_repair(failed: Trajectory, edit: LocalizedEdit,
                    environment: Optional[Environment],
                    cfg: CauseFlowConfig,
                    repair_pass=None) -> RepairResult:
    """Re-execute under the edit; at most one further pass on failure."""
    if environment is None:
        return RepairResult(verdict="not_reexecuted", edit=edit, passes_used=0)

    current = failed
    passes = 0
    total_cost = 0.0
    while passes <= cfg.iteration_cap:
        new_traj = environment.execute(current, edit)
        passes += 1
        div = divergence_step(failed, new_traj)
        if new_traj.verdict == "success":
            return RepairResult(verdict="success", edit=edit,
                                divergence_step=div, passes_used=passes,
                                cost_usd=total_cost)
        if passes > cfg.iteration_cap:
            break
        # feed the new trajectory back for (at most) one further pass
        if repair_pass is not None:
            edit, cost = repair_pass(new_traj)
            total_cost += cost
        else:
            break
    return RepairResult(verdict="fail", edit=edit, passes_used=passes,
                        cost_usd=total_cost)
