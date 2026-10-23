"""Collect all alerts from the snapshot and produce a concise summary.

The script scans the alerts/ directory, loads each JSON file (a list of alerts),
and builds a list of dictionaries containing key fields. It then prints the
summary as JSON. This is used to understand which alerts are firing during the
incident.
"""

import json
import os
import sys

SNAPSHOT_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-105"
ALERTS_DIR = os.path.join(SNAPSHOT_DIR, "alerts")

summary = []
for fname in sorted(os.listdir(ALERTS_DIR)):
    if not fname.endswith('.json'):
        continue
    path = os.path.join(ALERTS_DIR, fname)
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        sys.stderr.write(f"Error reading {path}: {e}\n")
        continue
    for alert in data:
        labels = alert.get('labels', {})
        summary.append({
            'alertname': labels.get('alertname'),
            'namespace': labels.get('namespace'),
            'severity': labels.get('severity'),
            'state': alert.get('state'),
            'startsAt': alert.get('startsAt'),
            'endsAt': alert.get('endsAt'),
            'source_file': fname,
        })

print(json.dumps(summary, indent=2))

