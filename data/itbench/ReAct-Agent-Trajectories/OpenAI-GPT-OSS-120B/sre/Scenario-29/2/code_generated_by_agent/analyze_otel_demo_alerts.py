"""Collect and summarize all alerts for the otel-demo namespace.

The script scans every *.json file under the ``alerts`` directory.  Some
files contain a top‑level ``alerts`` list, others are plain lists of alert
objects.  It extracts alerts whose ``labels.namespace`` equals ``otel-demo``
and builds a summary mapping alert name → list of occurrences (state and
timestamp).  The result is written to ``otel_demo_alerts_summary.json``
in the current working directory.
"""

import json, glob, os, datetime

ALERT_DIR = "./alerts"
out_path = "otel_demo_alerts_summary.json"

def parse_ts(ts: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))

summary = {}

for path in sorted(glob.glob(os.path.join(ALERT_DIR, "*.json"))):
    with open(path) as f:
        data = json.load(f)
    # data may be a dict with "alerts" key or a raw list
    alerts = data if isinstance(data, list) else data.get("alerts", [])
    for a in alerts:
        ns = a.get("labels", {}).get("namespace")
        if ns != "otel-demo":
            continue
        name = a.get("labels", {}).get("alertname", "unknown")
        ts = a.get("activeAt") or a.get("startsAt")
        dt = parse_ts(ts) if ts else None
        entry = summary.setdefault(name, [])
        entry.append({"state": a.get("state", "unknown"), "timestamp": dt.isoformat() if dt else None, "service": a.get("labels", {}).get("service_name")})

with open(out_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(f"Wrote summary of {len(summary)} alert types to {out_path}")
