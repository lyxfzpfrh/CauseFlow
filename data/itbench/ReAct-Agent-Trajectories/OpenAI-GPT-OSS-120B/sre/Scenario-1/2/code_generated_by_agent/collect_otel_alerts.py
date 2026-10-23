"""Collect all firing alerts for the otel-demo namespace across the snapshot.

The script iterates over every alerts_at_*.json file, extracts alerts with
state == "firing" and labels.namespace == "otel-demo". It groups them by
alertname and service_name (if present) and prints a JSON structure that can be
used by the final diagnosis.
"""

import json, glob, os, sys
from collections import defaultdict

BASE = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-1'
alert_files = sorted(glob.glob(os.path.join(BASE, 'alerts', 'alerts_at_*.json')))

group = defaultdict(list)
for fp in alert_files:
    with open(fp) as f:
        try:
            alerts = json.load(f)
        except Exception as e:
            continue
        for a in alerts:
            if a.get('state') != 'firing':
                continue
            ns = a.get('labels', {}).get('namespace')
            if ns != 'otel-demo':
                continue
            key = (a['labels'].get('alertname'), a['labels'].get('service_name'))
            group[key].append({
                'severity': a['labels'].get('severity'),
                'description': a.get('annotations', {}).get('description', ''),
                'activeAt': a.get('activeAt')
            })

# Output JSON for downstream use
out = []
for (alertname, service), items in sorted(group.items()):
    out.append({
        'alertname': alertname,
        'service_name': service,
        'count': len(items),
        'first_activeAt': items[0]['activeAt'] if items else None,
        'severity': items[0]['severity'] if items else None,
        'description': items[0]['description'] if items else ''
    })

print(json.dumps(out, indent=2))
