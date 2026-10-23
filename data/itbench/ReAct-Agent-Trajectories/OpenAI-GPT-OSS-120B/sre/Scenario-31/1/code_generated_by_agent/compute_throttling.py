"""Compute CPU throttling percentage per pod and identify those exceeding a threshold.

The metrics directory contains TSV files named ``pod_<name>_raw.tsv`` with columns:
metric_name, timestamp, value, pod_name, namespace, tags.
We look for two metrics per container:
    container_cpu_cfs_throttled_seconds_total
    container_cpu_cfs_periods_total
The throttling % = throttled_seconds / (periods * period_seconds) where period_seconds is 0.1s by default.
For simplicity we compute ratio of the two counters (throttled / periods) and treat >0.5 as high.
"""

import os, glob, pandas as pd

METRICS_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-31/metrics"
THROTTLED = "container_cpu_cfs_throttled_seconds_total"
PERIODS = "container_cpu_cfs_periods_total"

def load_pod_metrics():
    frames = []
    for path in glob.glob(os.path.join(METRICS_DIR, "pod_*.tsv")):
        df = pd.read_csv(path, sep="\t")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

def compute_throttle(df):
    # keep only relevant metrics
    df = df[df["metric_name"].isin([THROTTLED, PERIODS])]
    # pivot to have metrics as columns per pod
    pivot = df.pivot_table(index=["pod_name", "namespace"], columns="metric_name", values="value", aggfunc="last")
    # compute percent, avoid division by zero
    pivot["throttle_pct"] = (pivot[THROTTLED] / pivot[PERIODS].replace(0, pd.NA)) * 100
    return pivot.reset_index()

if __name__ == "__main__":
    df = load_pod_metrics()
    result = compute_throttle(df)
    high = result[result["throttle_pct"] > 50]
    print("Pods with high CPU throttling (>50%):")
    print(high[["pod_name", "namespace", "throttle_pct"]].to_string(index=False))
