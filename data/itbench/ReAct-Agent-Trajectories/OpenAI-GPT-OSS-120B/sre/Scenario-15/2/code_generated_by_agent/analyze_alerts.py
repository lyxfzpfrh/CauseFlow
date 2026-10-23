"""Analyze alerts for otel-demo namespace.

Loads all JSON alert files from the snapshot directory, extracts alerts that
have the label `namespace=otel-demo`, and prints a summary table:
  alertname, severity, state, first_active, last_active
The script is used to understand which alerts were firing during the
incident and to drive the diagnosis.
"""

import json
import os
import glob
from datetime import datetime

SNAPSHOT_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-15"
ALERTS_DIR = os.path.join(SNAPSHOT_DIR, "alerts")

def parse_iso(ts: str) -> datetime:
    """Parse ISO timestamp with optional nanoseconds."""
    # strip trailing Z if present
    if ts.endswith("Z"):
        ts = ts[:-1]
    # datetime.fromisoformat handles up to microseconds; trim extra digits
    if "." in ts:
        base, frac = ts.split(".", 1)
        frac = (frac + "000000")[:6]  # keep microseconds
        ts = f"{base}.{frac}"
    return datetime.fromisoformat(ts)

def load_alerts():
    alerts = []
    for path in sorted(glob.glob(os.path.join(ALERTS_DIR, "alerts_at_*.json"))):
        with open(path) as f:
            data = json.load(f)
        for a in data:
            # filter only otel-demo namespace alerts
            if a.get("labels", {}).get("namespace") != "otel-demo":
                continue
            alerts.append({
                "alertname": a["labels"].get("alertname"),
                "severity": a["labels"].get("severity"),
                "state": a.get("state"),
                "activeAt": parse_iso(a.get("activeAt")),
                "file": os.path.basename(path),
            })
    return alerts

def summarize(alerts):
    # group by alertname+severity
    summary = {}
    for a in alerts:
        key = (a["alertname"], a["severity"])
        rec = summary.setdefault(key, {"first": a["activeAt"], "last": a["activeAt"], "states": set()})
        if a["activeAt"] < rec["first"]:
            rec["first"] = a["activeAt"]
        if a["activeAt"] > rec["last"]:
            rec["last"] = a["activeAt"]
        rec["states"].add(a["state"])
    # print
    print("AlertName   Severity   FirstActive            LastActive             States")
    for (name, sev), rec in sorted(summary.items()):
        print(f"{name:12} {sev:8} {rec['first']} {rec['last']} {','.join(sorted(rec['states']))}")

if __name__ == "__main__":
    alerts = load_alerts()
    summarize(alerts)
