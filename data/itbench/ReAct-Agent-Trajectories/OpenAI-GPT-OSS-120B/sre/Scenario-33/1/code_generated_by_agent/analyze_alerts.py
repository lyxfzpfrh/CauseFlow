"""Simple script to list firing alerts in the snapshot.
It reads all JSON files under ./alerts and prints unique alertnames with their state.
"""

import json, glob, os, sys

def main():
    alerts_dir = os.path.join(os.path.dirname(__file__), "alerts")
    alert_names = set()
    for path in sorted(glob.glob(os.path.join(alerts_dir, "alerts_at_*.json"))):
        try:
            data = json.load(open(path))
        except Exception as e:
            continue
        for alert in data:
            if alert.get("state") != "firing":
                continue
            labels = alert.get("labels", {})
            if labels.get("namespace") != "otel-demo":
                continue
            alert_names.add(labels.get("alertname", ""))
    for name in sorted(alert_names):
        print(name)

if __name__ == "__main__":
    main()
