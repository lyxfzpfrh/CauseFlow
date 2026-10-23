"""Simple script to aggregate alerts from the snapshot.
It loads all JSON files in ./alerts/, extracts alerts where the label
`namespace` equals "otel-demo" and are in state "firing". It prints a
summary of alert names with count and first/last activeAt timestamps.
"""

import json, os, glob, datetime

def parse_iso(ts: str) -> datetime.datetime:
    # Python 3.11 can parse isoformat with Z by replacing Z with +00:00
    return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))

alerts_dir = "./alerts"
summary = {}
for path in sorted(glob.glob(os.path.join(alerts_dir, "*.json")):
    with open(path) as f:
        data = json.load(f)
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

# Print results
for name, info in summary.items():
    print(f"{name}: count={info['count']}, first={info['first']}, last={info['last']}")
