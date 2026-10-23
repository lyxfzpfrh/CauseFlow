"""Compute CPU throttling percentage for otel-demo pods.

Looks at metric files for pods and calculates throttle_pct = throttled / total * 100.
Prints any pod where throttle_pct > 20% during the incident window.
"""

import os, glob, pandas as pd
from datetime import datetime

BASE = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-1/metrics'
WINDOW_START = datetime.fromisoformat('2025-12-15T17:20:00+00:00')
WINDOW_END = datetime.fromisoformat('2025-12-15T18:30:00+00:00')

def load_metric(path, name):
    # metric TSV has columns: timestamp, value, maybe others
    df = pd.read_csv(path, sep='\t', comment='#', header=None, names=['timestamp','value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df[(df['timestamp']>=WINDOW_START) & (df['timestamp']<=WINDOW_END)]
    return df.set_index('timestamp')['value']

results = []
for pod_file in glob.glob(os.path.join(BASE, 'pod_*_raw.tsv')):
    pod_name = os.path.basename(pod_file).split('_raw.tsv')[0]
    if 'otel-demo' not in pod_name:
        # pod name includes namespace? assume all pods are in otel-demo
        pass
    try:
        throttled = load_metric(pod_file, 'container_cpu_cfs_throttled_periods_total')
        total = load_metric(pod_file, 'container_cpu_cfs_periods_total')
        if throttled.empty or total.empty:
            continue
        # align indexes
        common = throttled.index.intersection(total.index)
        if common.empty:
            continue
        pct = (throttled.loc[common] / total.loc[common]) * 100
        max_pct = pct.max()
        if max_pct > 20:
            results.append((pod_name, max_pct))
    except Exception:
        continue

for pod, pct in results:
    print(f"{pod}: max CPU throttle {pct:.1f}%")
