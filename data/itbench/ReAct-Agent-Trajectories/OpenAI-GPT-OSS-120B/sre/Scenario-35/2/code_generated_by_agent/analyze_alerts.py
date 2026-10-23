"""Analyze alerts for otel-demo namespace.

This script loads all JSON alert snapshots from the `alerts` directory,
extracts alerts that belong to the `otel-demo` namespace, and prints a
summary table of alert names, states, and timestamps.
"""

import json, os, re
from pathlib import Path

BASE = Path("/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-35")
alerts_dir = BASE / "alerts"

def load_alerts():
    alerts = []
    for p in sorted(alerts_dir.glob("alerts_at_*.json")):
        with open(p) as f:
            data = json.load(f)
        # Each file may contain a list of alerts or a dict with 'alerts'
        if isinstance(data, dict) and "alerts" in data:
            data = data["alerts"]
        for a in data:
            alerts.append(a)
    return alerts

def filter_otel_demo(alerts):
    otel = []
    for a in alerts:
        # Alert labels often contain namespace under "namespace" or "kubernetes_namespace"
        labels = a.get("labels", {})
        ns = labels.get("namespace") or labels.get("kubernetes_namespace")
        if ns == "otel-demo":
            otel.append(a)
    return otel

def summarize(alerts):
    for a in alerts:
        name = a.get("alertname") or a.get("labels", {}).get("alertname")
        state = a.get("state")
        start = a.get("startsAt")
        print(f"{name:30} {state:10} {start}")

if __name__ == "__main__":
    all_alerts = load_alerts()
    otel_alerts = filter_otel_demo(all_alerts)
    print(f"Total otel-demo alerts: {len(otel_alerts)}")
    summarize(otel_alerts)
