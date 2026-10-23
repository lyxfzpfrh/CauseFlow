"""Compute CPU throttling percentages for all pods during incident window.

Outputs pods where throttling exceeds 20% (a typical threshold). This helps
identify pods causing high latency or error rate alerts.
"""

import os, glob, pandas as pd
from datetime import datetime

BASE = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-1/metrics'
START = datetime.fromisoformat('2025-12-15T17:20:00+00:00')
END = datetime.fromisoformat('2025-12-15T18:30:00+00:00')

def load_metric(file_path, metric_name):
    df = pd.read_csv(file_path, sep='\t', comment='#', header=None,
                     names=['metric','timestamp','value','pod','namespace','tags'])
    df = df[(df['metric']==metric_name)]
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df[(df['timestamp']>=START) & (df['timestamp']<=END)]
    return df.set_index('timestamp')['value']

results = []
for pod_file in glob.glob(os.path.join(BASE, 'pod_*_raw.tsv')):
    pod = os.path.basename(pod_file).split('_raw.tsv')[0]
    try:
        throttled = load_metric(pod_file, 'container_cpu_cfs_throttled_periods_total')
        total = load_metric(pod_file, 'container_cpu_cfs_periods_total')
        if throttled.empty or total.empty:
            continue
        common = throttled.index.intersection(total.index)
        if common.empty:
            continue
        pct = (throttled.loc[common] / total.loc[common]) * 100
        max_pct = pct.max()
        if max_pct > 20:
            results.append((pod, max_pct))
    except Exception:
        continue

for pod, pct in sorted(results, key=lambda x: x[1], reverse=True):
    print(f"{pod}: max CPU throttle {pct:.1f}%")
