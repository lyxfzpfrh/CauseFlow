"""Simple script to aggregate alerts from the snapshot and filter to otel-demo namespace.

It loads all JSON files under the alerts/ directory, extracts each alert's labels,
and keeps only those where the ``namespace`` label equals ``otel-demo``.
It then prints a summary JSON list to stdout.
"""

import json
import os
import sys

SNAPSHOT_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-105"
ALERTS_DIR = os.path.join(SNAPSHOT_DIR, "alerts")

alerts = []
for fname in sorted(os.listdir(ALERTS_DIR)):
    if not fname.endswith('.json'):
        continue
    path = os.path.join(ALERTS_DIR, fname)
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        sys.stderr.write(f"Failed to load {path}: {e}\n")
        continue
    for a in data:
        labels = a.get('labels', {})
        if labels.get('namespace') == 'otel-demo':
            alerts.append({
                'alertname': labels.get('alertname'),
                'severity': labels.get('severity'),
                'instance': labels.get('instance'),
                'state': a.get('state'),
                'startsAt': a.get('startsAt'),
                'endsAt': a.get('endsAt'),
                'annotations': a.get('annotations', {}),
                'source_file': fname,
            })

print(json.dumps(alerts, indent=2))

