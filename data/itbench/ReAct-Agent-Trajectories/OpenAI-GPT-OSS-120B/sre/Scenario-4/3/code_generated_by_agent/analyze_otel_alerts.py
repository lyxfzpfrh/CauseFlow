"""Aggregate firing alerts for the otel-demo namespace.

The snapshot stores alerts under a sibling directory:
    /root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-4/alerts
Each file is a JSON array of alert objects. This script loads all files, selects
alerts where `labels.namespace == "otel-demo"` and `state == "firing"`, then prints a
summary of alert names with total count and the time range (first/last activeAt).
"""

import json, glob, os, datetime

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-4"
ALERTS_DIR = os.path.join(BASE, "alerts")

def parse_iso(ts: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))

summary = {}
for path in sorted(glob.glob(os.path.join(ALERTS_DIR, "*.json"))):
    with open(path) as f:
        try:
            data = json.load(f)
        except Exception:
            continue
    for alert in data:
        lbl = alert.get('labels', {})
        if lbl.get('namespace') != 'otel-demo':
            continue
        if alert.get('state') != 'firing':
            continue
        name = lbl.get('alertname', '<no-name>')
        at = parse_iso(alert.get('activeAt'))
        entry = summary.setdefault(name, {'count': 0, 'first': at, 'last': at})
        entry['count'] += 1
        if at < entry['first']:
            entry['first'] = at
        if at > entry['last']:
            entry['last'] = at

for name, info in sorted(summary.items()):
    print(f"{name}: count={info['count']}, first={info['first'].isoformat()}, last={info['last'].isoformat()}")
