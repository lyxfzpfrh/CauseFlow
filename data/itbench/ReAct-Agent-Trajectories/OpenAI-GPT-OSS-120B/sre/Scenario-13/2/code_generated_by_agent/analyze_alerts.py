"""Analyze alerts for otel-demo namespace.

This script reads all JSON files in the ./alerts directory, extracts alerts that
belong to the `otel-demo` namespace (based on the `namespace` label), and prints
 a summary JSON to stdout. The summary includes each alert name, its state, and
 the pod (if present).
"""

import json
import pathlib
import sys

def main():
    alerts_dir = pathlib.Path("alerts")
    summary = []
    for file in sorted(alerts_dir.glob("*.json")):
        try:
            data = json.load(open(file))
        except Exception as e:
            # skip files that are not proper JSON arrays
            continue
        for alert in data:
            labels = alert.get("labels", {})
            if labels.get("namespace") != "otel-demo":
                continue
            entry = {
                "alertname": labels.get("alertname"),
                "state": alert.get("state"),
                "pod": labels.get("pod"),
                "severity": labels.get("severity"),
                "activeAt": alert.get("activeAt"),
            }
            summary.append(entry)
    json.dump(summary, sys.stdout, indent=2)


if __name__ == "__main__":
    main()

