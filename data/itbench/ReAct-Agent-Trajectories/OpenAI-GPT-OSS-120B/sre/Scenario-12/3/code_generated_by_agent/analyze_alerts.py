"""Simple script to load all alert JSON files from the snapshot and extract alerts
that belong to the `otel-demo` namespace (if they have a `namespace` label).

The script prints a JSON list of alerts with the fields: alertname, severity,
state, activeAt, and any relevant labels (including namespace).
"""

import json
import pathlib
import sys

def load_alerts(alerts_dir: pathlib.Path):
    alerts = []
    for file in sorted(alerts_dir.glob('alerts_at_*.json')):
        try:
            data = json.loads(file.read_text())
        except Exception as e:
            print(f"Failed to parse {file}: {e}", file=sys.stderr)
            continue
        for alert in data:
            alerts.append(alert)
    return alerts

def summarize_otel_demo(alerts):
    """Return a dict mapping alertname to a list of occurrences for otel-demo namespace."""
    summary = {}
    for a in alerts:
        lbl = a.get('labels', {})
        if lbl.get('namespace') != 'otel-demo':
            continue
        name = lbl.get('alertname')
        entry = {
            'severity': lbl.get('severity'),
            'state': a.get('state'),
            'activeAt': a.get('activeAt'),
        }
        summary.setdefault(name, []).append(entry)
    return summary

if __name__ == '__main__':
    alerts_dir = pathlib.Path('/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-12/alerts')
    all_alerts = load_alerts(alerts_dir)
    otel_summary = summarize_otel_demo(all_alerts)
    json.dump(otel_summary, sys.stdout, indent=2)
