"""Parse alert JSON files in the snapshot and summarize alerts for otel-demo namespace.
Prints a JSON summary with total alerts and counts per alertname.
"""
import os, json, glob, sys

base_dir = os.path.dirname(__file__)
alerts_dir = os.path.join(base_dir, 'alerts')
alert_files = sorted(glob.glob(os.path.join(alerts_dir, 'alerts_at_*.json'))

alerts = []
for f in alert_files:
    try:
        data = json.load(open(f))
    except Exception as e:
        sys.stderr.write(f'Error loading {f}: {e}\n')
        continue
    for a in data:
        labels = a.get('labels', {})
        if labels.get('namespace') != 'otel-demo':
            continue
        alerts.append({
            'alertname': labels.get('alertname'),
            'state': a.get('state'),
            'severity': labels.get('severity'),
            'pod': labels.get('pod'),
            'container': labels.get('container'),
            'activeAt': a.get('activeAt')
        })

from collections import Counter
cnt = Counter([a['alertname'] for a in alerts])
summary = {'total_alerts': len(alerts), 'counts': dict(cnt)}
print(json.dumps(summary, indent=2))
