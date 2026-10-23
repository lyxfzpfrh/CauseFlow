"""Utility script to load and summarize alerts for the otel-demo namespace.
It reads all alert snapshots in the scenario directory and extracts key fields.
Running the script prints a concise count of each (alertname, state) pair.
"""

import json, os, glob
from collections import Counter

def load_alerts(alerts_dir: str):
    """Load alerts from all alerts_at_*.json files and return a list of dicts."""
    alerts = []
    for path in sorted(glob.glob(os.path.join(alerts_dir, 'alerts_at_*.json'))):
        with open(path) as f:
            data = json.load(f)
            for a in data:
                alerts.append({
                    'alertname': a['labels'].get('alertname'),
                    'namespace': a['labels'].get('namespace'),
                    'service_name': a['labels'].get('service_name'),
                    'severity': a['labels'].get('severity'),
                    'state': a.get('state'),
                    'activeAt': a.get('activeAt'),
                    'value': a.get('value')
                })
    return alerts

def filter_otel_demo(alerts):
    """Return only alerts that belong to the otel-demo namespace or have a service_name."""
    return [a for a in alerts if a.get('namespace') == 'otel-demo' or a.get('service_name')]

if __name__ == '__main__':
    alert_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-9/alerts'
    all_alerts = load_alerts(alert_dir)
    otel_alerts = filter_otel_demo(all_alerts)
    cnt = Counter((a['alertname'], a['state']) for a in otel_alerts)
    print('Alert summary (name, state):', cnt)
