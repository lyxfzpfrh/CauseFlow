"""Analyze alerts for otel-demo namespace.

Loads all JSON files under ./alerts directory, extracts alerts where the
`namespace` label is "otel-demo" (if present), and prints a summary table.
"""

import json, pathlib, sys

alerts_dir = pathlib.Path('alerts')
summary = []
for f in sorted(alerts_dir.glob('alerts_at_*.json')):
    try:
        with open(f) as jf:
            data = json.load(jf)
    except Exception:
        continue
    for a in data:
        lbl = a.get('labels', {})
        ns = lbl.get('namespace')
        if not ns and lbl.get('pod'):
            ns = 'otel-demo'
        if ns != 'otel-demo':
            continue
        summary.append({
            'time': f.name.split('alerts_at_')[1].replace('.json',''),
            'alertname': lbl.get('alertname'),
            'severity': lbl.get('severity'),
            'state': a.get('state'),
            'pod': lbl.get('pod'),
            'container': lbl.get('container'),
            'description': a.get('annotations', {}).get('description','')
        })

if not summary:
    print('No otel-demo alerts found')
    sys.exit(0)

# Aggregate counts per alertname
from collections import Counter
cnt = Counter(item['alertname'] for item in summary if item['alertname'])
print('Alert Summary (name: count)')
for name, c in cnt.most_common():
    print(f"{name}: {c}")
