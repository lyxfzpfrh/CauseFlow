"""Analyze firing alerts for the otel-demo namespace.

The script scans all JSON files under the snapshot's ``alerts`` directory.
Each file contains a list of alert objects. We collect alerts that are
currently ``firing`` and belong to the ``otel-demo`` namespace. The output
is printed as JSON to STDOUT and includes:

* ``alert_counts`` – a mapping of alert name → occurrence count across all
  snapshots.
* ``services`` – for each alert name, a list of distinct ``service_name``
  values observed.

The script is small and uses only the Python standard library.
"""

import json
import glob
import os
import collections

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-20"
ALERT_DIR = os.path.join(BASE, "alerts")

alert_counts = collections.Counter()
service_map = collections.defaultdict(set)

for path in sorted(glob.glob(os.path.join(ALERT_DIR, "alerts_at_*.json"))):
    with open(path) as f:
        try:
            data = json.load(f)
        except Exception:
            continue
        for alert in data:
            if alert.get("state") != "firing":
                continue
            labels = alert.get("labels", {})
            if labels.get("namespace") != "otel-demo":
                continue
            name = labels.get("alertname")
            alert_counts[name] += 1
            svc = labels.get("service_name")
            if svc:
                service_map[name].add(svc)

result = {
    "alert_counts": dict(alert_counts),
    "services": {k: sorted(v) for k, v in service_map.items()},
}
# Print detailed per-service alert list for diagnosis
print(json.dumps(result, indent=2))
