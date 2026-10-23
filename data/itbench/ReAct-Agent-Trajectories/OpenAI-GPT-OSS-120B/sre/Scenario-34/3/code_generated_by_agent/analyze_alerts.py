"""Analyze alerts for otel-demo namespace.

This script loads all JSON alert snapshots under the scenario directory,
filters alerts where `labels.namespace == "otel-demo"`, and aggregates
them into a summary dictionary keyed by alert name.

The output is printed as JSON to stdout, suitable for further processing.
"""

import json
import glob
import os
from collections import defaultdict

SCENARIO_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-34"
ALERTS_GLOB = os.path.join(SCENARIO_DIR, "alerts", "alerts_at_*.json")

summary = defaultdict(lambda: {"count": 0, "states": set(), "first_active": None, "last_active": None})

for path in sorted(glob.glob(ALERTS_GLOB)):
    with open(path) as f:
        data = json.load(f)
    for alert in data:
        labels = alert.get("labels", {})
        if labels.get("namespace") != "otel-demo":
            continue
        name = labels.get("alertname", "unknown")
        entry = summary[name]
        entry["count"] += 1
        entry["states"].add(alert.get("state", ""))
        # Use activeAt timestamp for time range
        ts = alert.get("activeAt")
        if ts:
            if entry["first_active"] is None or ts < entry["first_active"]:
                entry["first_active"] = ts
            if entry["last_active"] is None or ts > entry["last_active"]:
                entry["last_active"] = ts

# Convert sets to sorted list for JSON serialisation
output = {
    name: {
        "count": v["count"],
        "states": sorted(v["states"]),
        "first_active": v["first_active"],
        "last_active": v["last_active"],
    }
    for name, v in summary.items()
}

print(json.dumps(output, indent=2))

