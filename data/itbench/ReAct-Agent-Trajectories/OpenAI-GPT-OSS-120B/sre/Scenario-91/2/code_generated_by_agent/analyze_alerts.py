"""Analyze alerts for otel-demo namespace.

This script loads all JSON alert snapshots from the `alerts/` directory,
filters alerts whose `labels.namespace` is `otel-demo`, and aggregates
them by `alertname`. It prints a summary useful for the final diagnosis.
"""

import json, pathlib, collections

BASE = pathlib.Path('.')
ALERTS_DIR = BASE / "alerts"

def load_alerts():
    alerts = []
    for p in ALERTS_DIR.glob('alerts_at_*.json'):
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            continue
        alerts.extend(data)
    return alerts

def filter_otel_demo(alerts):
    return [a for a in alerts if a.get('labels', {}).get('namespace') == 'otel-demo']

def summarize(alerts):
    counter = collections.Counter()
    for a in alerts:
        name = a.get('labels', {}).get('alertname')
        if name:
            counter[name] += 1
    return counter

if __name__ == '__main__':
    all_alerts = load_alerts()
    otel_alerts = filter_otel_demo(all_alerts)
    summary = summarize(otel_alerts)
    print('Total otel-demo alerts:', len(otel_alerts))
    for name, cnt in summary.most_common():
        print(f'{name}: {cnt}')
