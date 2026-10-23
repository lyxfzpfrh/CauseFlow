"""Utility script to analyze alerts for the otel-demo namespace.

It loads all JSON alert snapshots from the scenario directory, extracts
alerts where the `namespace` label equals "otel-demo" (if present) and
collects the unique alert names and their states (firing/pending).

The script prints a summary JSON structure that can be consumed by the
agent to build the final diagnosis.
"""

import json
import glob
import os
from collections import defaultdict

SCENARIO_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-91"
ALERTS_GLOB = os.path.join(SCENARIO_DIR, "alerts", "alerts_at_*.json")

def load_alerts():
    alerts_by_name = defaultdict(list)
    for path in sorted(glob.glob(ALERTS_GLOB)):
        with open(path) as f:
            data = json.load(f)
        for alert in data:
            # Keep alerts that are either in otel-demo namespace or have no namespace label
            ns = alert.get("labels", {}).get("namespace")
            if ns and ns != "otel-demo":
                continue
            alerts_by_name[alert["labels"]["alertname"]].append(alert)
    return alerts_by_name

def summarize(alerts_by_name):
    summary = []
    for name, alerts in alerts_by_name.items():
        # Determine latest state based on snapshot timestamp ordering (file order)
        latest = alerts[-1]
        summary.append({
            "alertname": name,
            "state": latest["state"],
            "activeAt": latest.get("activeAt"),
            "count": len(alerts),
        })
    return summary

if __name__ == "__main__":
    alerts = load_alerts()
    print(json.dumps(summarize(alerts), indent=2))
