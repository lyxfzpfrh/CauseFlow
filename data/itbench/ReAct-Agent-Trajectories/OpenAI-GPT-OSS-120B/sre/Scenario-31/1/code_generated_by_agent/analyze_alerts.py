"""Analyze alerts in the otel-demo namespace.

The script loads all JSON files under the `alerts/` directory of the snapshot,
extracts alerts with `state == "firing"` and `namespace == "otel-demo"` (if
the label is present), and prints a summary JSON list to stdout.

It is used by the investigation to identify which alerts are relevant for the
incident.
"""

import json
import os
import glob
from datetime import datetime

SNAPSHOT_ROOT = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-31"
ALERTS_DIR = os.path.join(SNAPSHOT_ROOT, "alerts")

def load_alerts() -> list:
    alerts = []
    for path in sorted(glob.glob(os.path.join(ALERTS_DIR, "alerts_at_*.json"))):
        with open(path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
            for a in data:
                labels = a.get("labels", {})
                ts = a.get("activeAt") or a.get("timestamp")
                alerts.append({"file": os.path.basename(path), "state": a.get("state"), "labels": labels, "timestamp": ts, "annotations": a.get("annotations", {})})
    return alerts

def filter_otel_demo(alerts: list) -> list:
    result = []
    for a in alerts:
        if a["state"] != "firing":
            continue
        if a["labels"].get("namespace") == "otel-demo":
            result.append(a)
    return result

def summarize(alerts: list) -> list:
    summary = {}
    for a in alerts:
        name = a["labels"].get("alertname", "Unknown")
        ts = a.get("timestamp")
        if name not in summary:
            summary[name] = {"first_seen": ts, "last_seen": ts, "count": 1}
        else:
            summary[name]["count"] += 1
            if ts and (summary[name]["first_seen"] is None or ts < summary[name]["first_seen"]):
                summary[name]["first_seen"] = ts
            if ts and (summary[name]["last_seen"] is None or ts > summary[name]["last_seen"]):
                summary[name]["last_seen"] = ts
    out = []
    for name, info in summary.items():
        out.append({"alertname": name, "first_seen": info["first_seen"], "last_seen": info["last_seen"], "count": info["count"]})
    return out

if __name__ == "__main__":
    all_alerts = load_alerts()
    otel_alerts = filter_otel_demo(all_alerts)
    summary = summarize(otel_alerts)
    print(json.dumps(summary, indent=2))
