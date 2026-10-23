"""Analyze alerts for otel-demo namespace.

The script loads all JSON files under ./alerts, extracts alerts where the
`labels` dict contains a `namespace` key equal to "otel-demo" (or where the
`alertname` indicates a namespace‑wide issue). It prints a summary list of
alert names, states, and timestamps for further investigation.
"""

import json, pathlib, sys

def load_alerts(dir_path: pathlib.Path):
    alerts = []
    for f in sorted(dir_path.glob('alerts_at_*.json')):
        try:
            data = json.loads(f.read_text())
            alerts.extend(data)
        except Exception as e:
            print(f"Failed to load {f}: {e}", file=sys.stderr)
    return alerts

def filter_otel(alerts):
    result = []
    for a in alerts:
        lbl = a.get('labels', {})
        # Some alerts may not have explicit namespace label; keep generic ones
        if lbl.get('namespace') == 'otel-demo' or a['labels'].get('alertname') in {'Watchdog'}:
            result.append(a)
    return result

def main():
    alerts_dir = pathlib.Path('alerts')
    all_alerts = load_alerts(alerts_dir)
    otel_alerts = filter_otel(all_alerts)
    for a in otel_alerts:
        name = a['labels'].get('alertname')
        state = a.get('state')
        time = a.get('activeAt') or a.get('timestamp')
        print(f"{name}\t{state}\t{time}")

if __name__ == "__main__":
    main()

