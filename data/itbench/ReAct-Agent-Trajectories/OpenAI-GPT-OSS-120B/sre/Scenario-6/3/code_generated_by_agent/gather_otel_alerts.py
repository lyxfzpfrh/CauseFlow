import json, glob, os

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-6/alerts"
alerts = []
for path in sorted(glob.glob(os.path.join(BASE, "alerts_at_*.json"))):
    with open(path) as f:
        data = json.load(f)
        for a in data:
            if a.get("labels", {}).get("namespace") == "otel-demo":
                alerts.append({
                    "alertname": a["labels"].get("alertname"),
                    "service": a["labels"].get("service_name"),
                    "severity": a["labels"].get("severity"),
                    "activeAt": a.get("activeAt"),
                })
# Summarize unique alerts per service
summary = {}
for a in alerts:
    key = (a["alertname"], a.get("service"))
    summary.setdefault(key, []).append(a)
# Output a concise report for manual inspection
report = {"total_alerts": len(alerts), "by_type": {k[0]: len(v) for k, v in summary.items()}, "by_service": {k[1] or "<none>": len(v) for k, v in summary.items()}}
print(json.dumps(report, indent=2))
