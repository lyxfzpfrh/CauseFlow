"""CauseFlow: token-level root-cause analysis and localized repair for LLM agents.

Reference implementation of the three-stage pipeline:

  Stage 1  Trajectory compression        (failure-preserving, offline)   -> §3.2
  Stage 2  Attribution analysis          (SF / HS / KI + fusion + trace) -> §3.3
  Stage 3  Reasoning and repair          (rank / locate / edit / verify) -> §3.4

The module layout mirrors the paper section by section; every equation in the
paper has a corresponding function whose docstring cites the equation number.
"""

__version__ = "0.1.0"
