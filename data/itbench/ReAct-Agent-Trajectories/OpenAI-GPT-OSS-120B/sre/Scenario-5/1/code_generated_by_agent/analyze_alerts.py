"""Analyze alerts for the otel-demo namespace.

This script reads all JSON alert files under the snapshot's ``alerts``
directory, extracts alerts that are currently ``firing`` and have a
``namespace`` label equal to ``otel-demo``.  It prints a JSON list of
objects with ``alertname``, ``severity``, ``state`` and the timestamp
when the alert became active.

The script is deliberately small so it can be executed quickly in the
restricted environment.
"""

import json, pathlib, sys

def main():
    base = pathlib.Path(__file__).parent.parent / "B96DF826-4BB2-4B62-97AB-6D84254C53D7" / "Scenario-5"
    alerts_dir = base / "alerts"
    result = []
    for file in sorted(alerts_dir.glob("*.json")):
        try:
            data = json.loads(file.read_text())
        except Exception:
            continue
        for alert in data:
            # Only consider firing alerts
            if alert.get("state") != "firing":
                continue
            labels = alert.get("labels", {})
            # Some alerts may not have a namespace label; skip those
            if labels.get("namespace") != "otel-demo":
                continue
            result.append({
                "alertname": labels.get("alertname"),
                "severity": labels.get("severity"),
                "state": alert.get("state"),
                "activeAt": alert.get("activeAt"),
            })
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()

