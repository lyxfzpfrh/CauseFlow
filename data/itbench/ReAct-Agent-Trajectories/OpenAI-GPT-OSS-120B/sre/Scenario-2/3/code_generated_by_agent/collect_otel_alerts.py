"""Collect firing alerts for the otel-demo namespace.

The script loads every alerts_at_*.json file under ./alerts, filters for alerts
with `labels.namespace == "otel-demo"` and `state == "firing"`, and writes a JSON
array to stdout. This is used for later reasoning.
"""

import json, pathlib, sys

def main():
    alerts_dir = pathlib.Path('alerts')
    result = []
    for f in sorted(alerts_dir.glob('alerts_at_*.json')):
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            print(f"Failed to parse {f}: {e}", file=sys.stderr)
            continue
        for a in data:
            lbl = a.get('labels', {})
            if lbl.get('namespace') == 'otel-demo' and a.get('state') == 'firing':
                result.append({
                    'alertname': lbl.get('alertname'),
                    'service_name': lbl.get('service_name'),
                    'severity': lbl.get('severity'),
                    'activeAt': a.get('activeAt')
                })
    json.dump(result, sys.stdout, indent=2)

if __name__ == '__main__':
    main()

