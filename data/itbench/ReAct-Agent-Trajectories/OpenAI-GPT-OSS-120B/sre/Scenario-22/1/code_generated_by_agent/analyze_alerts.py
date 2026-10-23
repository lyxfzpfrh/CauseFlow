"""Analyze alerts in the snapshot focusing on the otel-demo namespace.

The script loads all JSON files under the `alerts/` directory, extracts alerts
where the label `namespace` equals "otel-demo" and the alert is currently
`firing`. It then prints a JSON summary suitable for later inclusion in the
final diagnosis.

Output format (printed to stdout):
[
  {
    "alertname": "<name>",
    "severity": "<severity>",
    "instance": "<instance>",
    "pod": "<pod>",
    "service": "<service>",
    "state": "firing",
    "activeAt": "<timestamp>"
  }, ...
]

The script is deliberately lightweight and uses only the standard library.
"""

import json
import os
import sys
from pathlib import Path

def main(base_dir: str = "./alerts") -> None:
    alerts_dir = Path(base_dir)
    if not alerts_dir.is_dir():
        sys.stderr.write(f"Alerts directory {base_dir} not found\n")
        sys.exit(1)

    results = []
    for file_path in sorted(alerts_dir.glob("*.json")):
        try:
            data = json.load(open(file_path))
        except Exception as e:
            # skip malformed files
            continue
        for alert in data:
            labels = alert.get("labels", {})
            if labels.get("namespace") != "otel-demo":
                continue
            if alert.get("state") != "firing":
                continue
            # collect key fields
            entry = {
                "alertname": labels.get("alertname"),
                "severity": labels.get("severity"),
                "instance": labels.get("instance"),
                "pod": labels.get("pod"),
                "service": labels.get("service"),
                "state": alert.get("state"),
                "activeAt": alert.get("activeAt"),
            }
            results.append(entry)

    json.dump(results, sys.stdout, indent=2)


if __name__ == "__main__":
    # allow passing custom alerts directory as first arg
    main(sys.argv[1] if len(sys.argv) > 1 else "./alerts")
