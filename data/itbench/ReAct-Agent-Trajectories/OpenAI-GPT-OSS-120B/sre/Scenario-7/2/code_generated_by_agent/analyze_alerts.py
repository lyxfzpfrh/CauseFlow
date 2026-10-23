"""Analyze alerts in the snapshot for otel-demo namespace.

This script loads all JSON alert snapshots from the `alerts/` directory,
extracts alert names and their associated Kubernetes objects (via the
`labels` field), and prints a summary of alerts that involve the
`otel-demo` namespace.

The output is a JSON list printed to stdout, each element containing:
  - alert: the alert name
  - namespace: extracted namespace (if any)
  - object: formatted as "namespace/Kind/name" when possible
  - state: alert state (firing/pending/etc.)
  - start: firstSeen timestamp
  - end: lastSeen timestamp (may be null)

The script is intended for interactive use by the agent; it can be
executed with `python analyze_alerts.py`.
"""

import json
import pathlib
from datetime import datetime

ALERTS_DIR = pathlib.Path("/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-7/alerts")

def load_alerts():
    alerts = []
    for p in ALERTS_DIR.glob("alerts_at_*.json"):
        try:
            data = json.loads(p.read_text())
            alerts.extend(data.get("alerts", []))
        except Exception:
            continue
    return alerts

def extract_entity(alert):
    # Alertmanager labels often contain namespace, pod, deployment, etc.
    labels = alert.get("labels", {})
    ns = labels.get("namespace") or labels.get("kubernetes_namespace")
    kind = None
    name = None
    # Prefer deployment, pod, service labels
    for k in ("deployment", "pod", "service", "statefulset", "daemonset"):
        if k in labels:
            kind = k.title()  # simple capitalization
            name = labels[k]
            break
    if ns and kind and name:
        return f"{ns}/{kind}/{name}"
    return None

def main():
    alerts = load_alerts()
    out = []
    for a in alerts:
        entity = extract_entity(a)
        # Only keep if namespace is otel-demo (or entity contains it)
        if entity and entity.startswith("otel-demo"):
            out.append({
                "alert": a.get("labels", {}).get("alertname"),
                "namespace": entity.split("/")[0],
                "object": entity,
                "state": a.get("state"),
                "start": a.get("activeAt"),
                "end": a.get("endedAt"),
            })
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()

