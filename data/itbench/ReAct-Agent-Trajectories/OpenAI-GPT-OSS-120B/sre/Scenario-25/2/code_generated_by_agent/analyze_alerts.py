"""Analyze alerts for otel-demo namespace.

This script loads all JSON files in the ./alerts directory, extracts alerts
that are currently firing and belong to the ``otel-demo`` namespace, and
produces a summary dictionary mapping ``alertname`` to a list of occurrences.

It prints a JSON representation of the summary to stdout so we can capture it
and use it for the final diagnosis.
"""

import json
import pathlib
import sys
from collections import defaultdict

def main():
    # The script is executed from the snapshot root directory.
    alerts_dir = pathlib.Path("./alerts")
    summary = defaultdict(list)
    for file in alerts_dir.glob("*.json"):
        try:
            data = json.load(open(file, "r"))
        except Exception:
            continue
        # Each file may contain a list of alerts
        if not isinstance(data, list):
            continue
        for alert in data:
            # keep only firing alerts in otel-demo namespace
            if alert.get("state") != "firing":
                continue
            labels = alert.get("labels", {})
            if labels.get("namespace") != "otel-demo":
                continue
            name = labels.get("alertname", "unknown")
            summary[name].append({
                "alertname": name,
                "service": labels.get("service_name", labels.get("service")),
                "severity": labels.get("severity"),
                "container": labels.get("container"),
                "pod": labels.get("pod"),
                "instance": labels.get("instance"),
                "file": file.name,
                "activeAt": alert.get("activeAt"),
            })
    # Output JSON summary
    json.dump(summary, sys.stdout, indent=2)

if __name__ == "__main__":
    main()
