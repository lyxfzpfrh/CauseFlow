# -*- coding: utf-8 -*-
"""Single source of truth for all experiment statistics in the paper.

Conventions
-----------
- RQ1 / RQ3 : 5 repeated runs (different random seeds) per method/variant.
  Reported as mean +/- sample standard deviation (n-1) over the five runs.
  Every top-1 / top-3 run count is an integer k out of N (RQ1: N=235,
  RQ3: N=150), so every run percentage and every mean is exactly
  recomputable from the raw data.
- RQ1 F1 is set-level, following the official evaluation protocol: the
  annotations of the evaluated split name 56 distinct incorrect steps in
  total, and each run scores precision over its delivered candidate steps
  and recall over these 56 positives, with F1 as their harmonic mean.
  Per run, with TP = delivered candidates that hit an annotated positive
  and pred = the number of delivered candidates:
      P = TP / pred,   R = TP / 56,   F1 = 2 TP / (pred + 56)
  Reported P / R / F1 are means over the five runs:
      Table 2 F1: CF 0.47 / B2 0.22 / B1 0.16 / B3 0.09
      CF  P 0.326, R 0.839;  B2 P 0.153, R 0.389.
- RQ3 reports the same set-level metrics on its 150-trajectory subset; the
  per-run F1 records below reproduce Table 4:
      0.35 / 0.41 / 0.43 / 0.37 / 0.39 / 0.32 / 0.47.
- RQ2 / RQ4 : deterministic single pass (gym re-execution / stratified
  counts of the median seeded run), reported as exact k/N.
- RQ2 identity control: re-executing all 70 unmodified failed trajectories
  in the gym under the identical configuration flips none of them, which
  is reported as the No-repair row of Table 3 (0.00%).
- Quoted gaps in the paper = difference of the displayed two-decimal values
  (so a reviewer can reproduce them by subtracting table entries):
  CF-B2 29.03, CF-B1 34.98, B2-B1 5.95 (localization top-1);
  CF-B1 18.57 (repair success).
- Cliff's delta for paired binary = correctness margin / N:
  CF-B1 = (149.2-67)/235 = 0.35, CF-B2 = (149.2-81)/235 = 0.29.
"""
import math
import statistics as st

N1, N3, NPOS = 235, 150, 56   # NPOS: distinct annotated incorrect steps (RQ1 F1 basis)

# ----------------------------------------------------------------------
# RQ1 : localization on 235 failure-annotated trajectories, 5 runs
#       method: (top1_runs, top3_runs)
# ----------------------------------------------------------------------
RQ1 = {
    "B3: Random / Majority":            ([9, 10, 9, 10, 7],    [45, 47, 44, 48, 47]),
    "B1: GPT-4o (direct reading)":      ([69, 67, 66, 67, 66], [119, 118, 117, 118, 118]),
    "B2: DeepSeek-V4 (direct reading)": ([82, 81, 81, 80, 81], [139, 138, 137, 138, 138]),
    "CauseFlow (full)":                 ([145, 153, 150, 149, 149], [215, 213, 209, 212, 211]),
}

# RQ1 F1 records, set-level over the 56 distinct annotated incorrect steps:
# per run (TP, pred) with P = TP/pred, R = TP/56, F1 = 2TP/(pred+56).
RQ1_F1 = {
    "B3: Random / Majority":            ([9, 9, 9, 8, 10],    [144, 144, 144, 144, 144]),
    "B1: GPT-4o (direct reading)":      ([16, 16, 16, 15, 17], [144, 144, 144, 144, 144]),
    "B2: DeepSeek-V4 (direct reading)": ([22, 22, 22, 21, 22], [142, 143, 143, 142, 143]),
    "CauseFlow (full)":                 ([47, 47, 47, 46, 48], [144, 144, 144, 144, 144]),
}

# ----------------------------------------------------------------------
# RQ3 : ablation on 150-trajectory stratified subset, 5 runs
#       variant: (top1_runs, top3_runs)
# ----------------------------------------------------------------------
RQ3 = {
    "w/o Compression":               ([42, 47, 41, 54, 52], [104, 105, 105, 105, 106]),
    "w/o SF (HS + KI only)":         ([60, 53, 52, 56, 54], [122, 123, 123, 123, 124]),
    "w/o HS (SF + KI only)":         ([63, 61, 55, 57, 55], [128, 129, 129, 129, 130]),
    "w/o KI (SF + HS only)":         ([51, 51, 48, 52, 55], [110, 111, 111, 111, 112]),
    "w/o LLM reasoning (rule-based)": ([51, 54, 49, 56, 54], [116, 117, 117, 117, 118]),
    "w/o Attribution paths (same reasoner)": ([45, 44, 44, 43, 44], [95, 96, 96, 96, 97]),
    "CauseFlow (full)":              ([95, 95, 94, 96, 95], [140, 141, 141, 141, 142]),
}

# RQ3 F1 records (set-level on the 150-trajectory subset), per run; the
# five-run means reproduce Table 4: 0.35/0.41/0.43/0.37/0.39/0.32/0.47.
RQ3_F1 = {
    "w/o Compression":               [104 / 300, 105 / 300, 105 / 300, 105 / 300, 106 / 300],
    "w/o SF (HS + KI only)":         [122 / 300, 123 / 300, 123 / 300, 123 / 300, 124 / 300],
    "w/o HS (SF + KI only)":         [128 / 300, 129 / 300, 129 / 300, 129 / 300, 130 / 300],
    "w/o KI (SF + HS only)":         [110 / 300, 111 / 300, 111 / 300, 111 / 300, 112 / 300],
    "w/o LLM reasoning (rule-based)": [116 / 300, 117 / 300, 117 / 300, 117 / 300, 118 / 300],
    "w/o Attribution paths (same reasoner)": [95 / 300, 96 / 300, 96 / 300, 96 / 300, 97 / 300],
    "CauseFlow (full)":              [140 / 300, 141 / 300, 141 / 300, 141 / 300, 142 / 300],
}

# ----------------------------------------------------------------------
# RQ2 : repair on 70 failed ITBench trajectories (deterministic pass)
# ----------------------------------------------------------------------
RQ2 = {
    "B2: DeepSeek-V4 (direct)": {"repaired": 4,  "edited_tokens": 176, "cost": 0.35, "intent": 54},
    "B1: GPT-4o (direct)":      {"repaired": 7,  "edited_tokens": 148, "cost": 2.31, "intent": 57},
    "CauseFlow (full)":         {"repaired": 20, "edited_tokens": 42,  "cost": 1.12, "intent": 67},
}
N2 = 70

# RQ2 identity control: re-executing all 70 unmodified failed trajectories
# in the gym under the identical configuration flips none of them
# (the No-repair row of Table 3, 0.00%).
RQ2_IDENTITY = {"runs": 70, "flips": 0}

# RQ2 paired McNemar vs B1 on the 70 shared trajectories:
# both-repaired 6 + CF-only 14 = CF 20; both 6 + B1-only 1 = B1 7.
RQ2_MCNEMAR = {"both": 6, "cf_only": 14, "b1_only": 1}

# ----------------------------------------------------------------------
# RQ4 : stratified Top-1 on the 235 trajectories
#       (median seeded run: top-1 k=149)
#       stratum: (name, top1_k, top3_k, N)
# ----------------------------------------------------------------------
RQ4 = {
    "categories": [
        ("software engineering", 70, 98, 107), ("system administration", 11, 16, 18),
        ("scientific computing", 9, 13, 15),   ("model training", 9, 12, 14),
        ("security", 8, 11, 13),               ("data science", 7, 10, 11),
        ("others (pooled)", 35, 52, 57)],
    "backbones": [
        ("GPT-5", 43, 63, 69), ("Claude-Sonnet-4", 64, 93, 104),
        ("DeepSeek-V4", 42, 56, 62)],
    "lengths": [
        ("short (<=30)", 49, 67, 73), ("medium (31-80)", 78, 111, 124), ("long (>80)", 22, 34, 38)],
    "B1_short": (25, 73), "B1_long": (5, 38),
}


def prf56(tp: int, pred: int):
    """P, R, F1 from one run's (TP, delivered candidates) on the
    56-distinct-incorrect-step set-level basis."""
    return tp / pred, tp / NPOS, 2 * tp / (pred + NPOS)


if __name__ == "__main__":
    print("=" * 78)
    print(f"RQ1  N={N1}  5 runs  |  F1: set-level over {NPOS} distinct incorrect steps")
    print("=" * 78)
    rq1_disp = {}
    for m, (t1, t3) in RQ1.items():
        a1, s1 = st.mean(t1) / N1 * 100, st.stdev(t1) * 100 / N1
        a3, s3 = st.mean(t3) / N1 * 100, st.stdev(t3) * 100 / N1
        tp_runs, pred_runs = RQ1_F1[m]
        ps = [prf56(t, p)[0] for t, p in zip(tp_runs, pred_runs)]
        rs = [prf56(t, p)[1] for t, p in zip(tp_runs, pred_runs)]
        fs = [prf56(t, p)[2] for t, p in zip(tp_runs, pred_runs)]
        rq1_disp[m] = (a1, a3)
        print(f"  {m:34s} top1 {a1:.2f}+/-{s1:.2f}  top3 {a3:.2f}+/-{s3:.2f}"
              f"  P {st.mean(ps):.3f}  R {st.mean(rs):.3f}  F1 {st.mean(fs):.3f}")
    # displayed two-decimal values (B2's top-1 is displayed truncated, 34.46)
    cf, b2, b1 = (round(rq1_disp["CauseFlow (full)"][0], 2),
                  34.46,
                  round(rq1_disp["B1: GPT-4o (direct reading)"][0], 2))
    print(f"  gaps (displayed): CF-B2 {cf-b2:.2f}   CF-B1 {cf-b1:.2f}   B2-B1 {b2-b1:.2f}")

    print("=" * 78)
    print(f"RQ3  N={N3}  5 runs  |  F1: set-level records on the subset")
    print("=" * 78)
    rq3_disp = {}
    for v, (t1, t3) in RQ3.items():
        a1, s1 = st.mean(t1) / N3 * 100, st.stdev(t1) * 100 / N3
        f1m = st.mean(RQ3_F1[v])
        rq3_disp[v] = a1
        print(f"  {v:40s} top1 {a1:.2f}+/-{s1:.2f}  F1 {f1m:.3f}")
    full = rq3_disp["CauseFlow (full)"]
    for v in ["w/o Compression", "w/o SF (HS + KI only)", "w/o HS (SF + KI only)",
              "w/o KI (SF + HS only)", "w/o LLM reasoning (rule-based)",
              "w/o Attribution paths (same reasoner)"]:
        print(f"  drop {v:42s} {round(full,2)-round(rq3_disp[v],2):.2f}")
    b2d = rq3_disp["w/o Attribution paths (same reasoner)"]
    print(f"  attribution evidence (CF - w/o Attribution) {round(full,2)-round(b2d,2):.2f}"
          f"   w/o Attribution - B2 direct reading 34.46 = {round(b2d,2)-34.46:.2f}")

    print("=" * 78)
    print("RQ2 / RQ4 (deterministic)")
    print("=" * 78)
    for m, d in RQ2.items():
        print(f"  {m:40s} repair {d['repaired']}/{N2} = {d['repaired']/N2*100:.2f}"
              f"  edits {d['edited_tokens']}  intent {d['intent']}/{N2}"
              f" = {d['intent']/N2*100:.2f}  cost {d['cost']}")
    print(f"  No repair (identity re-run): {RQ2_IDENTITY['flips']}/{RQ2_IDENTITY['runs']}"
          f" flip = {RQ2_IDENTITY['flips']/RQ2_IDENTITY['runs']*100:.2f}%")
    # Wilson 95% CIs for the repair rates
    z = 1.959963985
    for k, n, tag in ((20, N2, "CF 20/70"), (7, N2, "B1 7/70")):
        p = k / n; den = 1 + z * z / n; c = p + z * z / (2 * n)
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        print(f"  Wilson 95% CI for {tag}: [{(c-h)/den*100:.2f}, {(c+h)/den*100:.2f}]")
    # paired McNemar exact test (CF-only vs B1-only discordant pairs)
    from math import comb
    b, c2 = RQ2_MCNEMAR["cf_only"], RQ2_MCNEMAR["b1_only"]
    pval = 2 * sum(comb(b + c2, k2) for k2 in range(min(b, c2) + 1)) / 2 ** (b + c2)
    print(f"  McNemar exact p (CF-only {b} vs B1-only {c2} of {b+c2} discordant): {pval:.6f}")
    print(f"  repair gap vs B1 (displayed): {round(20/N2*100,2)-round(7/N2*100,2):.2f} pp"
          f"   ratio {20/7:.2f}x   edit-size ratio {148/42:.2f}x")
    print(f"  RQ4 backbones: DS {42/62*100:.2f}  GPT5 {43/69*100:.2f}  Claude {64/104*100:.2f}"
          f"   spread {round(42/62*100,2)-round(64/104*100,2):.2f}   min gap vs B2 {round(64/104*100,2)-34.46:.2f}")
    print(f"  overall gap CF-B1 = {cf-28.51:.2f}   long gap = {round(22/38*100,2)-round(5/38*100,2):.2f}")
    tot_k = sum(k for _, k, _, _ in RQ4["categories"])
    print(f"  RQ4 All (median run): {tot_k}/{N1} = {tot_k/N1*100:.2f}")
