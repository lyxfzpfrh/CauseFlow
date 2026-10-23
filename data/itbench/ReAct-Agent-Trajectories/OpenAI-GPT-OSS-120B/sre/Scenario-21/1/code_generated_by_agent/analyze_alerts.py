import json, glob, os

BASE_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-21"
alerts_dir = os.path.join(BASE_DIR, "alerts")

alerts = []
for path in glob.glob(os.path.join(alerts_dir, "*.json")):
    try:
        with open(path) as f:
            data = json.load(f)
        # data may be a list of alerts or contain a key 'alerts'
        if isinstance(data, dict) and "alerts" in data:
            data = data["alerts"]
        if isinstance(data, list):
            alerts.extend(data)
    except Exception:
        continue

filtered = []
for a in alerts:
    labels = a.get("labels", {})
    if labels.get("namespace") == "otel-demo" and a.get("state") == "firing":
        filtered.append({
            "alertname": labels.get("alertname"),
            "severity": labels.get("severity"),
            "instance": labels.get("instance"),
            "activeAt": a.get("activeAt"),
            "value": a.get("value"),
            "summary": a.get("annotations", {}).get("summary", "")
        })

print(json.dumps(filtered, indent=2))
