"""Utility script to load all alert JSON files from the snapshot and
extract firing alerts in the `otel-demo` namespace.

The script is used during the investigation to produce a concise list of
alert names, timestamps and states that we will later reference in the
final diagnosis.
"""

import json
import pathlib
from typing import List, Dict

SNAPSHOT_ROOT = pathlib.Path("/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-24")
ALERTS_DIR = SNAPSHOT_ROOT / "alerts"

def load_alerts() -> List[Dict]:
    """Load all alert JSON files and return a flat list of alert dicts."""
    alerts = []
    for file in sorted(ALERTS_DIR.glob("alerts_at_*.json")):
        try:
            data = json.loads(file.read_text())
        except Exception:
            continue
        alerts.extend(data)
    return alerts

def filter_otel_demo_firing(alerts: List[Dict]) -> List[Dict]:
    """Return alerts that are in namespace 'otel-demo' and currently firing."""
    result = []
    for a in alerts:
        labels = a.get("labels", {})
        if labels.get("namespace") != "otel-demo":
            continue
        if a.get("state") != "firing":
            continue
        result.append({
            "alertname": labels.get("alertname"),
            "service": labels.get("service_name") or labels.get("service"),
            "activeAt": a.get("activeAt"),
            "severity": labels.get("severity"),
        })
    return result

if __name__ == "__main__":
    all_alerts = load_alerts()
    otel_alerts = filter_otel_demo_firing(all_alerts)
    print(json.dumps(otel_alerts, indent=2))

