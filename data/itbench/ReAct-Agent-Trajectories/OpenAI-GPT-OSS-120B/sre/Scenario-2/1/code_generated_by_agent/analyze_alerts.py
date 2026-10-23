import json, os, re
import glob

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-2"
alert_files = sorted(glob.glob(os.path.join(BASE, "alerts", "*.json")))
alerts = []
for f in alert_files:
    try:
        data = json.load(open(f))
    except Exception:
        continue
    for a in data:
        # ensure labels dict
        lbl = a.get("labels", {})
        # default namespace to none
        ns = lbl.get("namespace", "none")
        alerts.append({
            "alertname": lbl.get("alertname", ""),
            "namespace": ns,
            "state": a.get("state", ""),
            "activeAt": a.get("activeAt", ""),
            "file": os.path.basename(f)
        })

# Filter for otel-demo namespace and firing state
filtered = [a for a in alerts if a["namespace"] == "otel-demo" and a["state"] == "firing"]
# Summarize counts per alertname
summary = {}
for a in filtered:
    summary.setdefault(a["alertname"], 0)
    summary[a["alertname"]] += 1
print(json.dumps({"summary": summary, "details": filtered}, indent=2))
