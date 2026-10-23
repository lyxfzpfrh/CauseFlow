"""Extract alerts specific to the otel-demo namespace.

Iterates over all JSON files in the snapshot's alerts directory and collects
alerts where the ``namespace`` label equals ``otel-demo``. Prints a JSON array
with key fields for downstream analysis.
"""

import json, os, sys

SNAPSHOT = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-105"
ALERT_DIR = os.path.join(SNAPSHOT, "alerts")

results = []
for fn in sorted(os.listdir(ALERT_DIR)):
    if not fn.endswith('.json'):
        continue
    path = os.path.join(ALERT_DIR, fn)
    try:
        data = json.load(open(path))
    except Exception as e:
        sys.stderr.write(f"skip {fn}: {e}\n")
        continue
    for alert in data:
        labels = alert.get('labels', {})
        if labels.get('namespace') == 'otel-demo':
            results.append({
                'alertname': labels.get('alertname'),
                'severity': labels.get('severity'),
                'instance': labels.get('instance'),
                'state': alert.get('state'),
                'startsAt': alert.get('startsAt'),
                'endsAt': alert.get('endsAt'),
                'source_file': fn,
            })

print(json.dumps(results, indent=2))

