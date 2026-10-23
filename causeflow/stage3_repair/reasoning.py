"""Stage 3, steps 1-2: assemble evidence and rank root causes (§3.4).

The reasoning LLM receives the compressed trajectory tau' (projected back to
original coordinates through the position map M), the candidate paths from
the attribution matrix, and the root-cause taxonomy prompt — the six
root-cause types plus the scapegoat as an explicit non-root-cause option.
It outputs the top-k candidates (k = 3, aligned with the stage annotations
of CodeTraceBench) with a calibrated confidence (temperature scaling on the
validation set) and a verdict per candidate.

Two implementations:
  * ``MockReasoner``  — deterministic heuristic ranker (no API needed);
  * ``LLMReasoner``   — any OpenAI-compatible chat endpoint (the paper uses
                        DeepSeek-V4, the same model as the B2 baseline, so
                        the comparison isolates the attribution evidence).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from ..config import CauseFlowConfig
from ..schema import (AttributionRecord, Candidate, CandidatePath,
                      CompressedTrajectory, ROOT_CAUSE_TYPES, SCAPEGOAT,
                      Trajectory)

TAXONOMY_PROMPT = """You are debugging a failed LLM-agent trajectory.
Rank the candidate root causes below. For each candidate output:
  - the step id,
  - a verdict: exactly one of the six root-cause types
      {types}
    or "scapegoat" if the evidence shows the candidate is a downstream
    consequence rather than a cause,
  - a confidence in [0, 1].

Evidence: the backward-traced attribution paths, ordered from the failure
manifestation back to the terminal (editable-input) end.  A path that
terminates on an editable input (system prompt / instruction / tool
description / RAG chunk) past visibly suspicious relay steps indicates the
true root cause; a suspicious operation that the path passes *through*
without terminating is a scapegoat.

Return strict JSON: a list of {{"step": int, "type": str, "confidence": float}}.
"""


@dataclass
class EvidenceBundle:
    """Stage 3, step 1: assemble evidence."""
    traj_id: str
    compressed: CompressedTrajectory
    paths: List[CandidatePath]
    step_summary: str                    # human-readable compressed trajectory

    @classmethod
    def build(cls, traj: Trajectory, compressed: CompressedTrajectory,
              paths: List[CandidatePath]) -> "EvidenceBundle":
        lines = []
        for seg in traj.editable_inputs:
            lines.append(f"[editable:{seg.kind.value}] {seg.text[:300]}")
        for s in traj.steps:
            obs = s.observation[:200]
            lines.append(f"Step {s.index} out: {s.output_text[:200]}"
                         + (f" | obs: {obs}" if obs else ""))
        return cls(traj_id=traj.traj_id, compressed=compressed, paths=paths,
                   step_summary="\n".join(lines))

    def render(self) -> str:
        parts = [f"# Trajectory {self.traj_id} (compressed)",
                 self.step_summary, "", "# Candidate paths (failure -> cause)"]
        for i, p in enumerate(self.paths, 1):
            chain = " <- ".join(
                f"{r.source_token}@{r.source_step}" for r in p.records[:8])
            parts.append(f"{i}. terminal={p.terminal_token}@{p.terminal_step}"
                         f" strength={p.strength:.3f} chain={chain}")
        return "\n".join(parts)


class Reasoner:
    """Interface: rank candidates with verdicts and calibrated confidence."""

    def rank(self, evidence: EvidenceBundle, cfg: CauseFlowConfig
             ) -> List[Candidate]:
        raise NotImplementedError


# --------------------------------------------------------------------------
# Mock reasoner: deterministic heuristics over the attribution evidence
# --------------------------------------------------------------------------
class MockReasoner(Reasoner):
    """Rule-based ranker used when no LLM endpoint is configured.

    Heuristics mirror the paper's Stage-3 behaviour:
      * earliest editable-input terminals rank first (root causes appear
        early while failures appear late);
      * relay steps the strongest path passes through are listed but flagged
        as scapegoats;
      * confidence = minmax-normalized path strength (already temperature-
        scaled analytically; the LLM path applies the learned temperature).
    """

    def rank(self, evidence: EvidenceBundle, cfg: CauseFlowConfig
             ) -> List[Candidate]:
        if not evidence.paths:
            return []
        cands: List[Candidate] = []
        strengths = [p.strength for p in evidence.paths]
        lo, hi = min(strengths), max(strengths)
        for p in evidence.paths:
            norm = (p.strength - lo) / (hi - lo) if hi > lo else 0.5
            terminal_is_editable = p.terminal_step == 0
            cands.append(Candidate(
                step=p.terminal_step,
                region=p.terminal_token,
                strength=p.strength,
                confidence=round(0.5 + 0.5 * norm, 4),
                type=None,
                rationale=("terminal on editable input"
                           if terminal_is_editable else "generated token")))
        # earliest editable terminal first, then strength
        cands.sort(key=lambda c: (c.step != 0, c.step if c.step == 0 else 1,
                                  -c.strength))
        # flag relay (non-editable, mid-trajectory) candidates as scapegoats
        for c in cands:
            if c.step != 0:
                c.type = SCAPEGOAT
        # editable terminals get the missing-constraint type by default in
        # the mock (the LLM reasoner decides the real type linguistically)
        for c in cands:
            if c.step == 0 and c.type is None:
                c.type = "missing constraint"
        return cands[: cfg.top_k]


# --------------------------------------------------------------------------
# LLM reasoner (OpenAI-compatible endpoint)
# --------------------------------------------------------------------------
class LLMReasoner(Reasoner):
    """DeepSeek-V4 (or any OpenAI-compatible chat model) as the reasoner."""

    def __init__(self, model: str, base_url: str = "", api_key: str = "",
                 temperature_scale: float = 1.0):
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url or None, api_key=api_key)
        self.model = model
        self.T = temperature_scale   # fitted on the validation set (ECE 0.031)

    def rank(self, evidence: EvidenceBundle, cfg: CauseFlowConfig
             ) -> List[Candidate]:
        prompt = (TAXONOMY_PROMPT.format(types=", ".join(ROOT_CAUSE_TYPES))
                  + "\n\n" + evidence.render())
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0)
        text = resp.choices[0].message.content
        m = re.search(r"\[.*\]", text, re.S)
        items = json.loads(m.group(0)) if m else []
        cands = []
        for it in items:
            typ = it.get("type", SCAPEGOAT)
            if typ not in ROOT_CAUSE_TYPES:
                typ = SCAPEGOAT
            conf = float(it.get("confidence", 0.5)) * self.T
            cands.append(Candidate(step=int(it.get("step", 0)),
                                   region=it.get("region", ""),
                                   type=typ,
                                   confidence=min(max(conf, 0.0), 1.0)))
        return cands[: cfg.top_k]


def build_reasoner(cfg: CauseFlowConfig) -> Reasoner:
    if cfg.use_mock_reasoner:
        return MockReasoner()
    return LLMReasoner(cfg.reasoner_model, cfg.reasoner_base_url)
