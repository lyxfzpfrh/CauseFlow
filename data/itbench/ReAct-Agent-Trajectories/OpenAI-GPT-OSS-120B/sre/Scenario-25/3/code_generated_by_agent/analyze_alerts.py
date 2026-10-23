import json, os, re
from pathlib import Path

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-25/alerts"

def load_alerts():
    alerts = []
    for f in Path(BASE).glob("alerts_at_*.json"):
        with open(f) as fh:
            data = json.load(fh)
            for a in data:
                a['snapshot'] = f.name  # keep source file
                alerts.append(a)
    return alerts

def filter_namespace(alerts, ns="otel-demo"):
    result = []
    for a in alerts:
        labels = a.get('labels', {})
        # some alerts may have 'namespace' label or use 'namespace' in annotations
        if labels.get('namespace') == ns:
            result.append(a)
        # also check if alertname contains namespace hint (e.g., PodCrashLooping)
        # not needed for now
    return result

if __name__ == "__main__":
    all_alerts = load_alerts()
    otel_alerts = filter_namespace(all_alerts)
    print(f"Total alerts: {len(all_alerts)}; otel-demo alerts: {len(otel_alerts)}")
    # Print unique alert names
    names = {a['labels'].get('alertname') for a in otel_alerts}
    print("Alert names in otel-demo:", sorted(names))
