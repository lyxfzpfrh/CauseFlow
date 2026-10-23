"""Aggregate alerts for the otel-demo namespace.

The snapshot contains many JSON files in the ./alerts directory. Each file is a list of
alert objects from Alertmanager. This script loads all files, selects alerts where
`labels.namespace == "otel-demo"` and state is "firing", then prints a concise summary:
alertname, count, first and last activeAt timestamps.
"""

import json, glob, datetime, os

def parse_iso(ts: str) -> datetime.datetime:
    # Replace trailing Z with +00:00 for fromisoformat compatibility
    return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))

alerts_dir = os.path.join(os.getcwd(), "alerts")
summary = {}

for path in sorted(glob.glob(os.path.join(alerts_dir, "*.json"))):
    # Each file contains a JSON array; load incrementally to avoid memory spikes.
    with open(path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            continue
    for alert in data:
        labels = alert.get("labels", {})
        if labels.get("namespace") != "otel-demo":
            continue
        if alert.get("state") != "firing":
            continue
        name = labels.get("alertname", "<no-name>")
        at = parse_iso(alert.get("activeAt"))
        entry = summary.setdefault(name, {"count": 0, "first": at, "last": at})
        entry["count"] += 1
        if at < entry["first"]:
            entry["first"] = at
        if at > entry["last"]:
            entry["last"] = at

for name, info in sorted(summary.items()):
    print(f"{name}: count={info['count']}, first={info['first'].isoformat()}, last={info['last'].isoformat()}")
