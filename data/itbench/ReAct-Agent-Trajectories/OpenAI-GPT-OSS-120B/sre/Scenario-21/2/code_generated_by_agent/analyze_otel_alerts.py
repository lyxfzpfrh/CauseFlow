"""Utility to load and filter alerts for the otel-demo namespace.
It reads all alert JSON files in the snapshot and prints alerts that have
`namespace: otel-demo` label. This helps focus the investigation.
"""

import json, glob, os, sys

def load_alerts(alerts_dir: str):
    alerts = []
    for path in sorted(glob.glob(os.path.join(alerts_dir, 'alerts_at_*.json'))):
        with open(path) as f:
            data = json.load(f)
            alerts.extend(data)
    return alerts

def filter_otel_demo(alerts):
    return [a for a in alerts if a.get('labels', {}).get('namespace') == 'otel-demo']

if __name__ == '__main__':
    alerts_dir = sys.argv[1] if len(sys.argv) > 1 else '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-21/alerts'
    otel_alerts = filter_otel_demo(load_alerts(alerts_dir))
    print(json.dumps(otel_alerts, indent=2))

