"""Aggregate firing alerts for the otel-demo namespace.

The snapshot contains many alert JSON files under alerts/*.json. This script
collects all alerts with state "firing" and namespace "otel-demo" and prints a
summary useful for the final diagnosis.
"""

import json, glob, os
from collections import defaultdict

BASE = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-1'
alert_paths = sorted(glob.glob(os.path.join(BASE, 'alerts', 'alerts_at_*.json')))

alerts_by_name = defaultdict(list)

for path in alert_paths:
    with open(path) as f:
        data = json.load(f)
        for a in data:
            if a.get('state') != 'firing':
                continue
            ns = a.get('labels', {}).get('namespace')
            if ns != 'otel-demo':
                continue
            name = a['labels'].get('alertname')
            svc = a['labels'].get('service_name') or 'N/A'
            alerts_by_name[(name, svc)].append({
                'severity': a['labels'].get('severity'),
                'description': a.get('annotations', {}).get('description', ''),
                'activeAt': a.get('activeAt')
            })

print('Aggregated firing alerts for otel-demo:')
for (name, svc), items in sorted(alerts_by_name.items(), key=lambda x: x[0]):
    first = items[0]['activeAt']
    print(f"- {name} on {svc}: {len(items)} occurrences, first at {first}")
