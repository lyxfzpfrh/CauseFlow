"""Load and summarize firing alerts for the otel-demo namespace.

The snapshot data lives under a separate directory. This script reads all JSON
files in the `alerts/` folder of the snapshot, filters for alerts with
`state == "firing"` and `namespace == "otel-demo"`, and prints a concise list
of alert names together with any pod or service labels.
"""

import json, os
from collections import defaultdict

SNAPSHOT_ROOT = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-35"
ALERTS_DIR = os.path.join(SNAPSHOT_ROOT, "alerts")

def load_alerts():
    alerts = []
    for f in sorted(os.listdir(ALERTS_DIR)):
        if not f.endswith('.json'):
            continue
        with open(os.path.join(ALERTS_DIR, f)) as fp:
            data = json.load(fp)
            alerts.extend(data)
    return alerts

def main():
    alerts = load_alerts()
    summary = defaultdict(list)
    for a in alerts:
        if a.get('state') != 'firing':
            continue
        labels = a.get('labels', {})
        if labels.get('namespace') != 'otel-demo':
            continue
        name = labels.get('alertname')
        pod = labels.get('pod')
        svc = labels.get('service')
        summary[name].append((pod, svc))
    for name, items in summary.items():
        pods = {p for p, _ in items if p}
        svcs = {s for _, s in items if s}
        print(f"Alert: {name}")
        if pods:
            print('  Pods:', ', '.join(sorted(pods)))
        if svcs:
            print('  Services:', ', '.join(sorted(svcs)))
        print()

if __name__ == '__main__':
    main()

