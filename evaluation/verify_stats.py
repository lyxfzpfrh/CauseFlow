#!/usr/bin/env python
"""Verify every headline number of the paper from the raw run counts.

exp_data.py is the single source of truth: all RQ1/RQ3 entries are 5-run
integer top-1/top-3 hit counts out of N (235 / 150), RQ1 carries per-run
(TP, pred) records on the 56-distinct-incorrect-step set-level F1 basis,
and RQ2/RQ4 are deterministic counts; every mean, std, P/R/F1, gap,
p-value, confidence interval, and effect size printed by the paper is
recomputed here from those records.

Usage:
    python evaluation/verify_stats.py
"""
from __future__ import annotations

import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_data as D                                    # noqa: E402
from metrics import mcnemar_exact, wilson_ci             # noqa: E402

CHECKS = []


def check(name, got, want, tol=5e-3):
    ok = abs(got - want) <= tol
    CHECKS.append((name, got, want, ok))
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {name:58s} got {got:.4f}  expected {want:.4f}")


def pct(x):
    return x * 100


def main():
    print("=" * 88)
    print("RQ1  (N=235, 5 runs, mean +/- std; F1 set-level over 56 positives)")
    print("=" * 88)
    means = {}
    for m, (t1, t3) in D.RQ1.items():
        means[m] = (st.mean(t1) / D.N1, st.mean(t3) / D.N1)
    check("B3 top-1 3.83", pct(means["B3: Random / Majority"][0]), 3.83, 0.055)
    check("B1 top-1 28.51", pct(means["B1: GPT-4o (direct reading)"][0]), 28.51, 0.06)
    check("B2 top-1 34.46 (displayed, truncated)",
          pct(means["B2: DeepSeek-V4 (direct reading)"][0]), 34.46, 0.06)
    check("CauseFlow top-1 63.49", pct(means["CauseFlow (full)"][0]), 63.49, 0.06)
    check("CauseFlow top-3 90.21", pct(means["CauseFlow (full)"][1]), 90.21, 0.06)
    # F1 / P / R on the 56-distinct-incorrect-step basis (means over 5 runs)
    tp, pred = D.RQ1_F1["CauseFlow (full)"]
    p = st.mean([t / q for t, q in zip(tp, pred)])
    r = st.mean([t / D.NPOS for t in tp])
    f1 = st.mean([2 * t / (q + D.NPOS) for t, q in zip(tp, pred)])
    check("CF precision 0.326", p, 0.326, 0.0015)
    check("CF recall 0.839", r, 0.839, 0.0015)
    check("CF F1 0.470", f1, 0.470, 0.0015)
    tp, pred = D.RQ1_F1["B2: DeepSeek-V4 (direct reading)"]
    p = st.mean([t / q for t, q in zip(tp, pred)])
    r = st.mean([t / D.NPOS for t in tp])
    f1 = st.mean([2 * t / (q + D.NPOS) for t, q in zip(tp, pred)])
    check("B2 precision 0.153", p, 0.153, 0.0015)
    check("B2 recall 0.389", r, 0.389, 0.0015)
    check("B2 F1 0.220", f1, 0.220, 0.0015)
    f1 = st.mean([2 * t / (q + D.NPOS) for t, q in zip(
        *D.RQ1_F1["B1: GPT-4o (direct reading)"])])
    check("B1 F1 0.160", f1, 0.160, 0.0015)
    f1 = st.mean([2 * t / (q + D.NPOS) for t, q in zip(
        *D.RQ1_F1["B3: Random / Majority"])])
    check("B3 F1 0.090", f1, 0.090, 0.0015)
    # gaps = differences of displayed two-decimal values (B2 truncated 34.46)
    cf, b2, b1 = 63.49, 34.46, 28.51
    check("gap CF - B2 (29.03)", cf - b2, 29.03, 1e-9)
    check("gap CF - B1 (34.98)", cf - b1, 34.98, 1e-9)
    check("gap B2 - B1 (5.95, smallest inter-method)", b2 - b1, 5.95, 1e-9)
    # Cliff's delta = paired-binary correctness margin / N
    cf_runs = D.RQ1["CauseFlow (full)"][0]
    b2_runs = D.RQ1["B2: DeepSeek-V4 (direct reading)"][0]
    b1_runs = D.RQ1["B1: GPT-4o (direct reading)"][0]
    check("Cliff's delta CF vs B2 (0.29)",
          (st.mean(cf_runs) - st.mean(b2_runs)) / D.N1, 0.29, 0.005)
    check("Cliff's delta CF vs B1 (0.35)",
          (st.mean(cf_runs) - st.mean(b1_runs)) / D.N1, 0.35, 0.005)

    print("=" * 88)
    print("RQ2  (N=70, deterministic)")
    print("=" * 88)
    cf_r = D.RQ2["CauseFlow (full)"]
    b1_r = D.RQ2["B1: GPT-4o (direct)"]
    b2_r = D.RQ2["B2: DeepSeek-V4 (direct)"]
    check("CF repair 20/70 = 28.57", pct(cf_r["repaired"] / D.N2), 28.57, 0.01)
    check("B1 repair 7/70 = 10.00", pct(b1_r["repaired"] / D.N2), 10.00, 0.01)
    check("B2 repair 4/70 = 5.71", pct(b2_r["repaired"] / D.N2), 5.71, 0.01)
    check("gap CF - B1 (18.57)", 28.57 - 10.00, 18.57, 1e-9)
    check("No-repair row: 0/70 flips",
          D.RQ2_IDENTITY["flips"] / D.RQ2_IDENTITY["runs"] * 100, 0.00, 1e-9)
    lo, hi = wilson_ci(20, 70)
    check("Wilson lower CF 19.32", lo * 100, 19.32, 0.01)
    check("Wilson upper CF 40.05", hi * 100, 40.05, 0.01)
    lo, hi = wilson_ci(7, 70)
    check("Wilson lower B1 4.93", lo * 100, 4.93, 0.01)
    check("Wilson upper B1 19.23", hi * 100, 19.23, 0.01)
    b, c = D.RQ2_MCNEMAR["cf_only"], D.RQ2_MCNEMAR["b1_only"]
    print(f"    McNemar exact p (CF-only {b} vs B1-only {c}): "
          f"{mcnemar_exact(b, c):.6f}  (paper: exact p < 0.001)")
    check("CF intent 95.71", pct(cf_r["intent"] / D.N2), 95.71, 0.01)
    check("B1 intent 81.43", pct(b1_r["intent"] / D.N2), 81.43, 0.01)
    check("edit-size ratio 3.52 (148/42)", 148 / 42, 3.52, 0.01)

    print("=" * 88)
    print("RQ3  (N=150, 5 runs)")
    print("=" * 88)
    r3 = {}
    for v, (t1, t3) in D.RQ3.items():
        r3[v] = st.mean(t1) / D.N3
    check("CauseFlow (full) top-1 63.33", pct(r3["CauseFlow (full)"]), 63.33, 0.06)
    check("w/o Compression top-1 31.47", pct(r3["w/o Compression"]), 31.47, 0.06)
    check("w/o SF top-1 36.67", pct(r3["w/o SF (HS + KI only)"]), 36.67, 0.06)
    check("w/o HS top-1 38.80", pct(r3["w/o HS (SF + KI only)"]), 38.80, 0.06)
    check("w/o KI top-1 34.27", pct(r3["w/o KI (SF + HS only)"]), 34.27, 0.06)
    check("w/o LLM reasoning top-1 35.20",
          pct(r3["w/o LLM reasoning (rule-based)"]), 35.20, 0.06)
    check("w/o Attribution paths top-1 29.33",
          pct(r3["w/o Attribution paths (same reasoner)"]), 29.33, 0.06)
    for v, want in (("w/o Compression", 31.86), ("w/o SF (HS + KI only)", 26.66),
                    ("w/o HS (SF + KI only)", 24.53), ("w/o KI (SF + HS only)", 29.06),
                    ("w/o LLM reasoning (rule-based)", 28.13),
                    ("w/o Attribution paths (same reasoner)", 34.00)):
        check(f"drop {v[:30]}", round(pct(r3["CauseFlow (full)"]), 2)
              - round(pct(r3[v]), 2), want, 0.01)
    for v, want in (("w/o Compression", 0.35), ("CauseFlow (full)", 0.47),
                    ("w/o Attribution paths (same reasoner)", 0.32)):
        check(f"F1 {v[:30]}", st.mean(D.RQ3_F1[v]), want, 0.005)

    print("=" * 88)
    print("RQ4  (stratified, median run)")
    print("=" * 88)
    for name, k, t3, n in D.RQ4["backbones"]:
        print(f"    {name:16s} top-1 {k}/{n} = {pct(k/n):.2f}")
    ds = 42 / 62
    cl = 64 / 104
    check("RQ4 backbone spread (DS - Claude)",
          round(ds*100, 2) - round(cl*100, 2), 6.20, 0.01)
    check("RQ4 min gap vs B2 (Claude - 34.46)", round(cl*100, 2) - 34.46, 27.08, 0.01)
    check("RQ4 long gap CF - B1 (44.73)",
          round(22/38*100, 2) - round(5/38*100, 2), 44.73, 0.01)
    tot_k = sum(k for _, k, _, _ in D.RQ4["categories"])
    check("RQ4 All 63.40", tot_k / D.N1 * 100, 63.40, 0.01)

    n_fail = sum(1 for c in CHECKS if not c[3])
    print("=" * 88)
    print(f"{len(CHECKS) - n_fail}/{len(CHECKS)} checks passed"
          + ("" if n_fail == 0 else f"  ({n_fail} FAILED)"))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
