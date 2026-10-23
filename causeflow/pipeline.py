"""The end-to-end CauseFlow pipeline (paper §3.1 Overview).

    failed trajectory tau
        -> Stage 1  compress            (failure-preserving, offline)   §3.2
        -> Stage 2  attribute           (SF / HS / KI -> edges -> trace) §3.3
        -> Stage 3  reason and repair   (rank / locate / edit / verify)  §3.4
        -> Diagnosis: top-k candidates + localized repair edits

Solid arrows in Figure 2 carry data (the function returns below); dashed
arrows (trace and retry paths) are the backward tracing of Stage 2 and the
at-most-one further repair pass of Stage 3.
"""
from __future__ import annotations

from typing import List, Optional

from .config import CauseFlowConfig
from .schema import Candidate, Diagnosis, LocalizedEdit, Trajectory
from .stage1_compression import compress, retention_check
from .stage2_attribution import Analyzer, build_analyzer, attribute
from .stage3_repair import (Environment, EvidenceBundle, build_reasoner,
                            generate_edit, validate_repair)


class CauseFlow:
    """The three-stage pipeline."""

    def __init__(self, cfg: Optional[CauseFlowConfig] = None,
                 analyzer: Optional[Analyzer] = None,
                 reasoner=None, intent_judge=None):
        self.cfg = cfg or CauseFlowConfig()
        self.analyzer = analyzer or build_analyzer(self.cfg)
        self.reasoner = reasoner or build_reasoner(self.cfg)
        self.intent_judge = intent_judge

    # ------------------------------------------------------------------
    def diagnose(self, traj: Trajectory) -> Diagnosis:
        """Localization: top-k candidate root causes with evidence."""
        # Stage 1
        compressed = compress(traj, self.cfg)
        # Stage 2
        att = attribute(traj, compressed, self.analyzer, self.cfg)
        # Stage 3, steps 1-2
        evidence = EvidenceBundle.build(traj, compressed, att.paths)
        candidates = self.reasoner.rank(evidence, self.cfg)
        return Diagnosis(
            traj_id=traj.traj_id,
            candidates=candidates,
            paths=att.paths,
            compression_stats=compressed.stats)

    # ------------------------------------------------------------------
    def repair(self, traj: Trajectory,
               environment: Optional[Environment] = None) -> Diagnosis:
        """Localization + localized repair (and re-execution when the
        environment exists)."""
        diag = self.diagnose(traj)
        for cand in diag.candidates[:1]:           # top-ranked candidate
            edit = generate_edit(traj, cand, self.cfg,
                                 intent_judge=self.intent_judge)
            if edit is None:
                continue
            diag.edits.append(edit)
            diag.repair = validate_repair(traj, edit, environment, self.cfg)
            break
        return diag

    # ------------------------------------------------------------------
    def retention_report(self, traj: Trajectory,
                         annotation_step: Optional[int] = None) -> dict:
        """Stage-1 post-hoc retention check (§3.2): does the annotated
        root-cause step (and the failure manifestation) survive compression?"""
        compressed = compress(traj, self.cfg)
        report = dict(compressed.stats)
        if annotation_step is not None:
            report["root_cause_step_retained"] = retention_check(
                traj, compressed, annotation_step)
        report["failure_step_retained"] = retention_check(
            traj, compressed, traj.failure_step)
        return report
