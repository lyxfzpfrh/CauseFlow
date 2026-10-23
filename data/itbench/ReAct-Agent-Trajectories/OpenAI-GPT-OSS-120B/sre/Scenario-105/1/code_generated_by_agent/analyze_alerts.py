"""Aggregates alerts for the otel-demo namespace.

The snapshot contains a series of files in ./alerts/ named
`alerts_at_<timestamp>.json`. Each file is a JSON array of alert objects.

This script loads all files, filters alerts whose `labels` contain a
`namespace` key equal to "otel-demo", and prints a summary table with
alertname, severity, state, and activeAt.
"""

import json, pathlib, sys

def load_alerts(dir_path: pathlib.Path):
    alerts = []
    for file in sorted(dir_path.glob('alerts_at_*.json')):
        try:
            data = json.loads(file.read_text())
        except Exception as e:
            print(f"Failed to parse {file}: {e}", file=sys.stderr)
            continue
        alerts.extend(data)
    return alerts

def main():
    alerts_dir = pathlib.Path('alerts')
    all_alerts = load_alerts(alerts_dir)
    # Primary filter: alerts that have a namespace label equal to otel-demo
    otel_alerts = [a for a in all_alerts if a.get('labels', {}).get('namespace') == 'otel-demo']
    # Fallback: some alerts may lack namespace label; include those where the pod or instance name contains the namespace prefix
    if not otel_alerts:
        otel_alerts = [a for a in all_alerts if any('otel-demo' in str(v) for v in a.get('labels', {}).values())]
    # Summarize
    for a in otel_alerts:
        lbl = a.get('labels', {})
        print(f"{lbl.get('alertname')} | {lbl.get('severity')} | {a.get('state')} | {a.get('activeAt')}")

if __name__ == "__main__":
    main()
