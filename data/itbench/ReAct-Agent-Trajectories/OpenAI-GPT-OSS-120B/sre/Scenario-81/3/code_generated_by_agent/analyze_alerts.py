"""Analyze alerts in otel-demo namespace.

The script loads all JSON files under ./alerts/, extracts alerts whose
`labels.namespace` (or `labels.k8s_namespace`) equals "otel-demo", and prints a
summary table: alertname, state, activeAt (or firing time), and count of
occurrences across snapshots.

It is used during the investigation to understand which alerts were firing
in the otel-demo namespace.
"""

import json
import pathlib
from collections import Counter, defaultdict

ALERTS_DIR = pathlib.Path("alerts")

def load_alerts():
    alerts = []
    for path in ALERTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            # each file is a list of alert dicts
            alerts.extend(data)
        except Exception as e:
            print(f"Failed to read {path}: {e}")
    return alerts

def filter_otel_demo(alerts):
    filtered = []
    for a in alerts:
        ns = a.get("labels", {}).get("namespace") or a.get("labels", {}).get("k8s_namespace")
        if ns == "otel-demo":
            filtered.append(a)
    return filtered

def summarize(alerts):
    # group by alertname and state
    summary = defaultdict(lambda: Counter())
    for a in alerts:
        name = a.get("labels", {}).get("alertname", "<unknown>")
        state = a.get("state", "unknown")
        summary[name][state] += 1
    return summary

def main():
    all_alerts = load_alerts()
    otel_alerts = filter_otel_demo(all_alerts)
    summary = summarize(otel_alerts)
    print("Alert summary for namespace otel-demo:")
    for name, cnts in summary.items():
        total = sum(cnts.values())
        print(f"- {name}: total snapshots={total}, states={dict(cnts)}")

if __name__ == "__main__":
    main()

