"""Compute maximum CPU throttling percentage per pod in otel-demo namespace.

The script reads all pod metric TSV files under the scenario's metrics directory,
filters rows belonging to the "otel-demo" namespace, and merges the two
metrics required for throttling calculation:
  - container_cpu_cfs_throttled_periods_total
  - container_cpu_cfs_periods_total

For each pod and timestamp it computes:
    pct = throttled / periods * 100
It then reports the maximum observed percentage per pod. Pods with a high
percentage (e.g., >10%) are likely experiencing CPU throttling, which can lead
to request latency spikes and errors.

The output is printed as "pod_name max_throttle_pct" lines.
"""

import os
import glob
import pandas as pd

BASE_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-4/metrics"

def load_metrics():
    dfs = []
    for path in glob.glob(os.path.join(BASE_DIR, "pod_*_raw.tsv")):
        df = pd.read_csv(path, sep="\t")
        # Keep only otel-demo namespace
        df = df[df["namespace"] == "otel-demo"]
        if not df.empty:
            dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

def compute_max_throttle(df):
    # Select relevant metrics
    throttled = df[df["metric_name"] == "container_cpu_cfs_throttled_periods_total"][
        ["timestamp", "pod_name", "value"]
    ].rename(columns={"value": "throttled"})
    periods = df[df["metric_name"] == "container_cpu_cfs_periods_total"][
        ["timestamp", "pod_name", "value"]
    ].rename(columns={"value": "periods"})
    merged = pd.merge(throttled, periods, on=["timestamp", "pod_name"], how="inner")
    # Avoid division by zero
    merged = merged[merged["periods"] > 0]
    merged["pct"] = merged["throttled"] / merged["periods"] * 100
    max_pct = merged.groupby("pod_name")["pct"].max().reset_index()
    return max_pct

def main():
    df = load_metrics()
    if df.empty:
        print("No metric data found.")
        return
    max_pct = compute_max_throttle(df)
    # Print pods with highest throttling first
    for _, row in max_pct.sort_values("pct", ascending=False).iterrows():
        print(f"{row['pod_name']} {row['pct']:.2f}%")


if __name__ == "__main__":
    main()

