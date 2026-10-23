"""Quick inspection of alert files for otel-demo namespace.

The alert JSON files have varying structures; this script loads each file,
extracts alerts where labels.namespace == 'otel-demo', and prints a concise
line: alertname, state, startsAt, endsAt.
"""

import json, pathlib, sys

ALERT_DIR = pathlib.Path("/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-7/alerts")

def load_alerts(path):
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "alerts" in data:
        return data["alerts"]
    return []

def main():
    for p in sorted(ALERT_DIR.glob("*.json")):
        alerts = load_alerts(p)
        for a in alerts:
            labels = a.get("labels", {})
            if labels.get("namespace") != "otel-demo":
                continue
            print(f"{p.name}\t{labels.get('alertname')}\t{a.get('state')}\t{a.get('startsAt')}\t{a.get('endsAt')}")

if __name__ == "__main__":
    main()

