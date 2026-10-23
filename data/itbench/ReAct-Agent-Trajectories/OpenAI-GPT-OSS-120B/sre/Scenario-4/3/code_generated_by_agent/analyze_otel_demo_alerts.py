"""Utility script to load and summarize firing alerts for the otel-demo namespace.

The snapshot directory contains many alert snapshots (alerts_at_*.json). This script
aggregates them, filters to alerts that are currently firing and belong to the
`otel-demo` namespace, and prints a simple count per alert name.
"""

import json, glob, os

SNAPSHOT_DIR = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-4'
ALERTS_DIR = os.path.join(SNAPSHOT_DIR, 'alerts')

def load_alerts():
    """Load all alert JSON files in chronological order and tag them with snapshot time."""
    alerts = []
    for path in sorted(glob.glob(os.path.join(ALERTS_DIR, 'alerts_at_*.json'))):
        with open(path, 'r') as f:
            data = json.load(f)
            snapshot = os.path.basename(path).replace('alerts_at_', '').replace('.json', '')
            for a in data:
                a['snapshot_time'] = snapshot
                alerts.append(a)
    return alerts

def filter_firing_namespace(alerts, namespace='otel-demo'):
    return [a for a in alerts if a.get('state') == 'firing' and a.get('labels', {}).get('namespace') == namespace]

def summarize(alerts):
    summary = {}
    for a in alerts:
        name = a.get('labels', {}).get('alertname')
        if name:
            summary[name] = summary.get(name, 0) + 1
    return summary

if __name__ == '__main__':
    all_alerts = load_alerts()
    firing = filter_firing_namespace(all_alerts)
    summ = summarize(firing)
    print('Firing alerts in otel-demo namespace:')
    for name, cnt in sorted(summ.items()):
        print(f'{name}: {cnt}')
