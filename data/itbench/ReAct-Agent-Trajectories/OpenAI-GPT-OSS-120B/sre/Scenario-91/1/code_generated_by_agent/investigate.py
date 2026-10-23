import json, os, re, glob

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-91"
alerts_dir = os.path.join(BASE, "alerts")
firing = []
for path in sorted(glob.glob(os.path.join(alerts_dir, "alerts_at_*.json")):
    with open(path) as f:
        data = json.load(f)
    for a in data:
        if a.get("state") != "firing":
            continue
        ns = a.get("labels", {}).get("namespace")
        if ns == "otel-demo":
            firing.append({
                "alertname": a["labels"].get("alertname"),
                "severity": a["labels"].get("severity"),
                "instance": a["labels"].get("instance"),
                "pod": a["labels"].get("pod"),
                "time": a.get("activeAt")
            })
# Summarize unique alerts
summary = {}
for f in firing:
    key = (f["alertname"], f.get("severity"))
    summary.setdefault(key, []).append(f)
print(json.dumps({"summary": summary}, default=str, indent=2))
