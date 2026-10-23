"""The scoring engine: analyzers expose model internals to the signals (§3.3).

All three signals read model internals — final-layer hidden states, per-layer
attention, curvature, and output distributions — so they are computed by a
locally hosted open-weight *analyzer*.  Given the recorded step input, the
analyzer teacher-forces the recorded step output and evaluates SF, HS, and KI
along the forced pass; KI re-queries the analyzer under occlusion of the
source token.  When the trajectory was produced by an open-weight backbone,
the analyzer is that backbone; for closed-source backbones it is an
open-weight proxy (the analyzer contract, §3.3 "Scoring engine").

Two implementations are provided:

  * ``MockAnalyzer``     — deterministic pseudo-internals (no GPU, no
                           weights); the whole pipeline runs end to end
                           anywhere without weights.
  * ``HFAnalyzer``       — a ``transformers`` causal LM with
                           ``output_hidden_states=True, output_attentions=True``
                           (requires torch + GPU).
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np


@dataclass
class ForcedPass:
    """Internals of one teacher-forced window (tokens in causal order)."""
    tokens: List[str]
    hidden: np.ndarray              # (n, d) final-layer hidden states
    attn_layers: List[np.ndarray]   # L matrices (n, n), head-averaged, row-stochastic
    logprobs: np.ndarray            # (n, vocab) next-token distributions (log)


class Analyzer:
    """Interface consumed by signals.py (the analyzer contract)."""

    def forced_pass(self, tokens: Sequence[str]) -> ForcedPass:
        raise NotImplementedError

    def occluded_pass(self, tokens: Sequence[str],
                      occlude_index: int) -> ForcedPass:
        """Teacher-forced pass with token `occlude_index` deleted (KI)."""
        reduced = [t for i, t in enumerate(tokens) if i != occlude_index]
        return self.forced_pass(reduced)

    def token_similarity(self, a: str, b: str) -> float:
        """Cheap salience for the mu-prefilter (embedding cosine)."""
        ha = self._embed(a)
        hb = self._embed(b)
        denom = (np.linalg.norm(ha) * np.linalg.norm(hb)) or 1.0
        return float(np.dot(ha, hb) / denom)

    def embed(self, token: str) -> np.ndarray:
        """Cached token embedding (vectorized prefilter uses this)."""
        return self._embed(token)

    # -- internals ---------------------------------------------------------
    def _embed(self, token: str) -> np.ndarray:
        raise NotImplementedError

    def curvature_channel(self, src_idx: int, tgt_idx: int, fp: ForcedPass):
        """Gauss-Newton channel g_{s->t} used by the HS surrogate.

        The gradient of the target loss at position `tgt_idx` flowing through
        the source position `src_idx`; HS = ||g||^2 / (d + damping).
        """
        raise NotImplementedError


# --------------------------------------------------------------------------
# Mock analyzer: deterministic pseudo-internals
# --------------------------------------------------------------------------
def _stable_hash(token: str, salt: str = "") -> int:
    h = hashlib.sha256((salt + token).encode("utf-8")).hexdigest()
    return int(h[:16], 16)


class MockAnalyzer(Analyzer):
    """Deterministic pseudo-internals, seeded per token string.

    Hidden states: 32-d vectors seeded per token, made context sensitive by
    mixing in a fraction of the previous token's vector (a crude residual
    stream).  Attention: row-stochastic lower-triangular matrices whose
    affinities are ReLU dot-products of the hidden states (vectorized, no
    per-pair hashing).  Distributions: softmax over a 64-symbol pseudo
    vocabulary derived from the hidden state.  No semantic claims — the mock
    exists so that the *machinery* (rollout, fusion, tracing, repair) is
    executable and testable without weights.
    """

    def __init__(self, dim: int = 32, n_layers: int = 4, vocab: int = 64,
                 seed: int = 0):
        self.dim, self.n_layers, self.vocab, self.seed = dim, n_layers, vocab, seed
        self._cache: dict = {}
        self._W = np.random.default_rng(
            _stable_hash("W", salt=str(self.seed))).standard_normal(
                (self.dim, self.vocab))

    def _embed(self, token: str) -> np.ndarray:
        if token not in self._cache:
            rng = np.random.default_rng(_stable_hash(token, salt=f"e{self.seed}"))
            v = rng.standard_normal(self.dim)
            self._cache[token] = v / (np.linalg.norm(v) or 1.0)
        return self._cache[token]

    def forced_pass(self, tokens: Sequence[str]) -> ForcedPass:
        tokens = list(tokens)
        n = len(tokens)
        E = np.stack([self._embed(t) for t in tokens]) if n else \
            np.zeros((0, self.dim))
        # crude residual mixing (context sensitivity)
        hidden = np.zeros_like(E)
        for i in range(n):
            v = E[i] if i == 0 else 0.7 * E[i] + 0.3 * hidden[i - 1]
            hidden[i] = v / (np.linalg.norm(v) or 1.0)

        attn_layers = []
        for l in range(self.n_layers):
            aff = np.maximum(0.0, hidden @ hidden.T)      # (n, n)
            aff *= (1.0 + 0.15 * l)                       # layer variation
            A = np.tril(0.1 + aff)                        # causal mask
            A /= A.sum(axis=1, keepdims=True)
            attn_layers.append(A)

        logits = hidden @ self._W
        logprobs = logits - np.log(np.exp(logits).sum(axis=1, keepdims=True))
        return ForcedPass(tokens=tokens, hidden=hidden,
                          attn_layers=attn_layers, logprobs=logprobs)

    def curvature_channel(self, src_idx: int, tgt_idx: int, fp: ForcedPass):
        """Mock Gauss-Newton channel: hidden-state coupling at the two positions."""
        return float(np.dot(fp.hidden[src_idx], fp.hidden[tgt_idx]))


# --------------------------------------------------------------------------
# HF analyzer: real model internals (torch + transformers)
# --------------------------------------------------------------------------
class HFAnalyzer(Analyzer):
    """Open-weight causal-LM analyzer (the paper's scoring engine).

    Requires: ``torch``, ``transformers``.  ``model_name`` defaults to the
    paper's analyzer (DeepSeek-V4); on ITBench trajectories the analyzer is
    the backbone itself (GPT-OSS-120B).  Attention rollout needs per-layer
    head-averaged attention over the full window, so windows are capped at
    ``max_window`` tokens (the prefilter keeps them small).
    """

    def __init__(self, model_name: str, device: str = "cuda",
                 max_window: int = 2048, dtype: str = "bfloat16"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=getattr(torch, dtype), device_map=device,
            attn_implementation="eager")   # eager: attentions must be returned
        self.model.eval()
        self.max_window = max_window

    def _ids(self, tokens: Sequence[str]):
        ids = self.tok(list(tokens), add_special_tokens=False,
                       return_tensors="pt")["input_ids"][0]
        return ids[: self.max_window]

    def forced_pass(self, tokens: Sequence[str]) -> ForcedPass:
        torch = self.torch
        ids = self._ids(tokens).to(self.model.device)
        with torch.no_grad():
            out = self.model(ids.unsqueeze(0), output_hidden_states=True,
                             output_attentions=True)
        hidden = out.hidden_states[-1][0].float().cpu().numpy()
        attn_layers = [a[0].float().mean(dim=0).cpu().numpy()
                       for a in out.attentions]     # head-average per layer
        logprobs = torch.log_softmax(out.logits[0].float(), dim=-1).cpu().numpy()
        return ForcedPass(tokens=list(tokens), hidden=hidden,
                          attn_layers=attn_layers, logprobs=logprobs)

    def _embed(self, token: str) -> np.ndarray:
        torch = self.torch
        ids = self._ids([token]).to(self.model.device)
        with torch.no_grad():
            out = self.model.model.embed_tokens(ids)
        return out[0].float().cpu().numpy().mean(axis=0)

    def curvature_channel(self, src_idx: int, tgt_idx: int, fp: ForcedPass):
        """Real Gauss-Newton channel: d l_tgt / d e_src via input embeddings.

        One autograd pass over the window: the loss is the NLL of the
        recorded token at `tgt_idx`; the channel is the gradient w.r.t. the
        input embedding at `src_idx`.  Squared and damped by signals.py this
        is the diagonal Gauss-Newton surrogate of Eq. (5).
        """
        torch = self.torch
        tokens = fp.tokens
        ids = self._ids(tokens).to(self.model.device)
        emb_layer = self.model.get_input_embeddings()

        def forward(ids):
            e = emb_layer(ids)
            out = self.model(inputs_embeds=e.unsqueeze(0),
                             output_hidden_states=False,
                             output_attentions=False)
            return out.logits[0]

        ids = ids.detach()
        with torch.enable_grad():
            e = emb_layer(ids).detach().requires_grad_(True)
            out = self.model(inputs_embeds=e.unsqueeze(0))
            logits = out.logits[0]
            # teacher-forced NLL of the recorded token at tgt_idx
            target_id = ids[min(tgt_idx, ids.shape[0] - 1)]
            loss = torch.nn.functional.cross_entropy(
                logits[min(tgt_idx, logits.shape[0] - 1)].unsqueeze(0),
                target_id.unsqueeze(0))
            g, = torch.autograd.grad(loss, e)
        return float(g[src_idx].float().norm().item())


def build_analyzer(cfg):
    """Factory from a CauseFlowConfig."""
    if cfg.use_mock_analyzer:
        return MockAnalyzer(seed=cfg.seed)
    return HFAnalyzer(cfg.analyzer_model)
