"""Analysis script for otel-demo incident.
Loads all alert JSON files, extracts alerts related to otel-demo namespace,
and prints a summary useful for the final diagnosis.
"""

import json, glob, os

SNAPSHOT_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-20"
ALERTS_DIR = os.path.join(SNAPSHOT_DIR, "alerts")

def load_alerts():
    alerts = []
    for path in sorted(glob.glob(os.path.join(ALERTS_DIR, "alerts_at_*.json")):
        with open(path) as f:
            data = json.load(f)
            for a in data:
                a["snapshot_time"] = os.path.basename(path).split("alerts_at_")[1].replace('.json','')
                alerts.append(a)
    return alerts

def filter_otel_demo(alerts):
    # keep alerts that have namespace label otel-demo or refer to a pod/service in that namespace
    res = []
    for a in alerts:
        lbl = a.get("labels", {})
        if lbl.get("namespace") == "otel-demo":
            res.append(a)
            continue
        # check pod or service label containing otel-demo prefix
        if lbl.get("pod", "").startswith("otel-demo/") or lbl.get("service", "").startswith("otel-demo/"):
            res.append(a)
            continue
        # sometimes object name is in 'name' label
        if lbl.get("name", "").startswith("otel-demo/"):
            res.append(a)
    return res

def main():
    alerts = load_alerts()
    otel_alerts = filter_otel_demo(alerts)
    # summarize by alertname
    summary = {}
    for a in otel_alerts:
        name = a["labels"].get("alertname", "unknown")
        summary.setdefault(name, 0)
        summary[name] += 1
    print("Alert summary for otel-demo namespace:")
    for name, cnt in summary.items():
        print(f"{name}: {cnt}")

if __name__ == "__main__":
    main()

