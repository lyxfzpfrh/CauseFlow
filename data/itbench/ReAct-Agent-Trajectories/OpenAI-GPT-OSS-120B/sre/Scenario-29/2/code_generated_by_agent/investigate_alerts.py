"""Investigate alerts for otel-demo namespace.

This script loads all JSON alert snapshots in the alerts/ directory,
extracts alerts that belong to the "otel-demo" namespace, and prints a
summary table of each alert name, its latest state (firing/pending),
first seen time and last seen time.

The output is written to a JSON file `alert_summary.json` in the current
working directory for later consumption.
"""

import json
import os
import glob
from datetime import datetime

ALERTS_DIR = "./alerts"
output_path = "alert_summary.json"

def parse_timestamp(ts: str) -> datetime:
    # timestamps are ISO8601 with possible Z suffix
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

alerts_by_name = {}

for path in sorted(glob.glob(os.path.join(ALERTS_DIR, "alerts_at_*.json"))):
    with open(path) as f:
        data = json.load(f)
    # data format: list of alerts with fields like "labels", "state", "activeAt", "endsAt"
    for alert in data.get("alerts", []):
        # Filter for otel-demo namespace if present in labels
        ns = alert.get("labels", {}).get("namespace")
        if ns != "otel-demo":
            continue
        name = alert.get("labels", {}).get("alertname", "unknown")
        entry = alerts_by_name.setdefault(name, {"states": [], "first_seen": None, "last_seen": None})
        state = alert.get("state")
        entry["states"].append(state)
        # use activeAt or startsAt timestamp
        ts = alert.get("activeAt") or alert.get("startsAt")
        if ts:
            dt = parse_timestamp(ts)
            if entry["first_seen"] is None or dt < entry["first_seen"]:
                entry["first_seen"] = dt
            if entry["last_seen"] is None or dt > entry["last_seen"]:
                entry["last_seen"] = dt

# Build summary list
summary = []
for name, info in alerts_by_name.items():
    # Determine latest state by most recent timestamp (approx using last_seen)
    latest_state = info["states"][-1] if info["states"] else "unknown"
    summary.append({
        "alert": name,
        "latest_state": latest_state,
        "first_seen": info["first_seen"].isoformat() if info["first_seen"] else None,
        "last_seen": info["last_seen"].isoformat() if info["last_seen"] else None,
    })

with open(output_path, "w") as f:
    json.dump(summary, f, indent=2)

print(f"Wrote {len(summary)} otel-demo alerts to {output_path}")
