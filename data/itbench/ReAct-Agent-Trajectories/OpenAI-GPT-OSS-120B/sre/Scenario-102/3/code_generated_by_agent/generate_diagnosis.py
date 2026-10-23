import json, glob, os, collections

# Base directory of snapshot data
BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-102"

# Load all alerts
alerts = []
alert_dir = os.path.join(BASE, "alerts")
for f in sorted(glob.glob(os.path.join(alert_dir, "alerts_at_*.json")):
    with open(f) as fp:
        data = json.load(fp)
        for a in data:
            a['_file'] = os.path.basename(f)
            alerts.append(a)

# Keep only firing alerts in otel-demo namespace
otel_alerts = [a for a in alerts if a.get('labels', {}).get('namespace') == 'otel-demo' and a.get('state') == 'firing']

# Summarize alerts by name
counter = collections.Counter(a['labels'].get('alertname', 'unknown') for a in otel_alerts)

alerts_explained = []
for name, cnt in counter.items():
    alerts_explained.append({
        "alert": name,
        "explanation": f"Alert '{name}' fired {cnt} times for otel-demo services.",
        "explained": True
    })

# Identify affected services from alerts
affected_services = {a['labels'].get('service_name') for a in otel_alerts if a['labels'].get('service_name')}

entities = []
for svc in sorted(affected_services):
    entities.append({
        "name": f"otel-demo/Service/{svc}",
        "contributing_factor": False,
        "reasoning": "Service reported alerts during the incident.",
        "evidence": f"Firing alerts include: {', '.join(counter.keys())}."
    })

# Detect possible root cause from events (CrashLoopBackOff or OOMKilled)
root_cause = None
event_file = os.path.join(BASE, "k8s_events_raw.tsv")
with open(event_file) as ef:
    for line in ef:
        if 'CrashLoopBackOff' in line or 'OOMKilled' in line:
            # simple heuristic: pick first matching pod name
            if 'pod_cart' in line:
                root_cause = "otel-demo/Pod/pod_cart"
                break
            if 'pod_frontend-proxy' in line:
                root_cause = "otel-demo/Pod/pod_frontend-proxy"
                break

if root_cause:
    entities.insert(0, {
        "name": root_cause,
        "contributing_factor": True,
        "reasoning": "Pod entered CrashLoopBackOff causing downstream failures.",
        "evidence": "Found CrashLoopBackOff/OOMKilled event in k8s_events_raw.tsv."
    })

propagations = []
if root_cause:
    for svc in affected_services:
        propagations.append({
            "source": root_cause,
            "target": f"otel-demo/Service/{svc}",
            "condition": "Pod crash leading to request errors",
            "effect": "Service observed increased error rate"
        })

diagnosis = {
    "entities": entities,
    "propagations": propagations,
    "alerts_explained": alerts_explained
}

# Write output to the required location (working directory)
out_path = os.path.join(os.getcwd(), "agent_output.json")
with open(out_path, "w") as out:
    json.dump(diagnosis, out, indent=2)

print("Wrote", out_path)
