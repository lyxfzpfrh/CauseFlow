"""Compute CPU throttling percentage for otel-demo pods.

Loads metric TSV files, calculates throttle_pct = throttled_periods / periods * 100
for each pod and prints those > 10% (high throttling).
"""

import pandas as pd, glob, os

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-91/metrics"

def load_metrics():
    dfs = []
    for path in glob.glob(os.path.join(BASE, "pod_*.tsv")):
        df = pd.read_csv(path, sep="\t")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

def main():
    df = load_metrics()
    # filter relevant columns
    df = df[df["namespace"] == "otel-demo"]
    # pivot to have metric names as columns per pod
    piv = df.pivot_table(index=["pod_name", "namespace"], columns="metric_name", values="value", aggfunc="max")
    if "container_cpu_cfs_throttled_periods_total" in piv.columns and "container_cpu_cfs_periods_total" in piv.columns:
        piv["throttle_pct"] = piv["container_cpu_cfs_throttled_periods_total"] / piv["container_cpu_cfs_periods_total"] * 100
        high = piv[piv["throttle_pct"] > 10]
        for (pod, ns), row in high.iterrows():
            print(f"{ns}/{pod}: {row['throttle_pct']:.1f}% throttling")

if __name__ == "__main__":
    main()
