import json, os, glob

BASE_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-80"
alerts_path = os.path.join(BASE_DIR, "alerts")
alert_files = sorted(glob.glob(os.path.join(alerts_path, "alerts_at_*.json")))

def load_alerts():
    all_alerts = []
    for f in alert_files:
        try:
            data = json.load(open(f))
        except Exception:
            continue
        for a in data:
            a_copy = a.copy()
            a_copy["source_file"] = os.path.basename(f)
            all_alerts.append(a_copy)
    return all_alerts

def filter_by_namespace(alerts, ns="otel-demo"):
    return [a for a in alerts if a.get("labels", {}).get("namespace") == ns]

if __name__ == "__main__":
    alerts = load_alerts()
    otel_alerts = filter_by_namespace(alerts)
    # summarize count per alertname
    summary = {}
    for a in otel_alerts:
        name = a["labels"].get("alertname")
        summary.setdefault(name, 0)
        summary[name] += 1
    print("Alert summary for otel-demo:")
    for name, cnt in sorted(summary.items(), key=lambda x: -x[1]):
        print(f"{name}: {cnt}")
