"""Parse alert JSON files for the otel-demo namespace.

The script walks through the alerts directory, loads each JSON array, and
extracts alerts where the label `namespace` equals "otel-demo".  It prints a
JSON list of objects containing the alert name, state, and activation time.
"""

import json, pathlib, sys

def main():
    base = pathlib.Path("/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-35/alerts")
    result = []
    for file in sorted(base.glob('alerts_at_*.json')):
        try:
            data = json.loads(file.read_text())
        except Exception:
            continue
        for alert in data:
            labels = alert.get('labels', {})
            if labels.get('namespace') == 'otel-demo':
                result.append({
                    'file': file.name,
                    'alertname': labels.get('alertname'),
                    'state': alert.get('state'),
                    'activeAt': alert.get('activeAt')
                })
    json.dump(result, sys.stdout, indent=2)

if __name__ == "__main__":
    main()

