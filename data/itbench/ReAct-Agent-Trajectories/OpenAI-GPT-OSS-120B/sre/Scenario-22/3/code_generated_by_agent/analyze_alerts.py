import json, glob, os
from pathlib import Path

SNAPSHOT_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-22"

def load_alerts():
    alerts = []
    for path in Path(SNAPSHOT_DIR, "alerts").glob("alerts_at_*.json"):
        with open(path) as f:
            data = json.load(f)
            # each file contains a list of alerts
            alerts.extend(data)
    return alerts

def filter_otel_demo(alerts):
    return [a for a in alerts if a.get('labels', {}).get('namespace') == 'otel-demo']

def summarize(alerts):
    # group by alertname and state
    summary = {}
    for a in alerts:
        name = a.get('labels', {}).get('alertname', 'unknown')
        state = a.get('state', 'unknown')
        key = (name, state)
        summary.setdefault(key, 0)
        summary[key] += 1
    return summary

if __name__ == "__main__":
    all_alerts = load_alerts()
    otel_alerts = filter_otel_demo(all_alerts)
    print("Total otel-demo alerts:", len(otel_alerts))
    for (name, state), cnt in summarize(otel_alerts).items():
        print(f"{name} [{state}]: {cnt}")
