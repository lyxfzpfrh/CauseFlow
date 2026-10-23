import json, glob, os

def load_alerts(base_dir):
    alerts = []
    pattern = os.path.join(base_dir, "alerts", "alerts_at_*.json")
    for fn in sorted(glob.glob(pattern)):
        with open(fn) as f:
            data = json.load(f)
            alerts.extend(data)
    return alerts

def summarize_alerts(alerts, namespace="otel-demo"):
    # filter firing alerts in given namespace (or non-namespaced alerts keep)
    result = []
    for a in alerts:
        if a.get("state") != "firing":
            continue
        lbl = a.get("labels", {})
        if lbl.get("namespace") and lbl["namespace"] != namespace:
            continue
        result.append({
            "alertname": lbl.get("alertname"),
            "service": lbl.get("service_name"),
            "severity": lbl.get("severity"),
            "activeAt": a.get("activeAt"),
            "description": a.get("annotations", {}).get("description", ""),
        })
    return result

if __name__ == "__main__":
    base = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-23"
    alerts = load_alerts(base)
    summary = summarize_alerts(alerts)
    print(json.dumps(summary, indent=2))
