"""Analyze alerts for otel-demo namespace.
Loads all JSON files in ./alerts (relative to snapshot dir), extracts alerts where the 'labels.namespace' == 'otel-demo'.
Prints a JSON summary of alert names and firing periods.
"""

import json, os, re
from datetime import datetime

# Assume this script is run from the snapshot directory where ./alerts exists.
alert_dir = "./alerts"
filename_pat = re.compile(r"alerts_at_(.+)\.json")

alerts = {}
for fname in sorted(os.listdir(alert_dir)):
    if not fname.startswith("alerts_at_"):
        continue
    with open(os.path.join(alert_dir, fname)) as f:
        data = json.load(f)
    m = filename_pat.search(fname)
    snap_time = None
    if m:
        # filename uses '-' for ':' in ISO timestamps
        iso = m.group(1).replace('-', ':')
        try:
            snap_time = datetime.fromisoformat(iso)
        except Exception:
            snap_time = None
    for a in data:
        lbl = a.get('labels', {})
        if lbl.get('namespace') != 'otel-demo':
            continue
        name = lbl.get('alertname', 'unknown')
        alerts.setdefault(name, []).append({'state': a.get('state'), 'time': snap_time})

summary = []
for name, recs in alerts.items():
    recs.sort(key=lambda x: x['time'] or datetime.min)
    periods = []
    cur = None
    for r in recs:
        if r['state'] == 'firing':
            if cur is None:
                cur = {'start': r['time'], 'end': r['time']}
            else:
                cur['end'] = r['time']
        else:
            if cur:
                periods.append(cur)
                cur = None
    if cur:
        periods.append(cur)
    summary.append({'alert': name, 'periods': periods})

print(json.dumps(summary, default=str, indent=2))
