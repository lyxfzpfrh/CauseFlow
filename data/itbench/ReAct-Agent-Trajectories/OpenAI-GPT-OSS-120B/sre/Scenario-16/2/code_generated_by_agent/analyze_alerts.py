import json, glob, os

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-16/alerts"
alert_files = sorted(glob.glob(os.path.join(BASE, "alerts_at_*.json")))

alerts = []
for f in alert_files:
    try:
        data = json.load(open(f))
    except Exception as e:
        continue
    for a in data:
        # consider only firing alerts in otel-demo namespace
        if a.get("state") != "firing":
            continue
        ns = a.get("labels", {}).get("namespace")
        if ns == "otel-demo":
            alerts.append({
                "alertname": a["labels"].get("alertname"),
                "service_name": a["labels"].get("service_name"),
                "severity": a["labels"].get("severity"),
                "activeAt": a.get("activeAt"),
                "description": a.get("annotations", {}).get("description", ""),
                "file": os.path.basename(f),
            })

# Print summary
print(json.dumps(alerts, indent=2))
