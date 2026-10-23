"""Extract alerts for the otel-demo namespace and summarize them.
This script reads all alerts JSON files in the snapshot directory and prints a
summary JSON list of alerts that have the label `namespace=otel-demo`.
"""

import json
from pathlib import Path

ALERTS_DIR = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-12/alerts'

def load_all_alerts():
    alerts = []
    for p in sorted(Path(ALERTS_DIR).glob('alerts_at_*.json')):
        with open(p) as f:
            data = json.load(f)
            for a in data:
                a['_source_file'] = p.name
                alerts.append(a)
    return alerts

def filter_otel_demo(alerts):
    return [a for a in alerts if a.get('labels', {}).get('namespace') == 'otel-demo']

if __name__ == '__main__':
    all_alerts = load_all_alerts()
    otel_alerts = filter_otel_demo(all_alerts)
    print(json.dumps(otel_alerts, indent=2))

