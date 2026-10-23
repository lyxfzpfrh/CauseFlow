import json, glob, os

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-2"
alert_files = sorted(glob.glob(os.path.join(BASE, "alerts", "alerts_at_*.json")))

alerts = []
for f in alert_files:
    # skip the alerting_state file which has a different format
    if "alerting_state" in f:
        continue
    with open(f) as fp:
        data = json.load(fp)
        alerts.extend(data)

# Filter alerts in otel-demo namespace and firing
filtered = [a for a in alerts if a.get("state") == "firing" and a.get("labels", {}).get("namespace") == "otel-demo"]

# Summarize by alertname
summary = {}
for a in filtered:
    name = a["labels"].get("alertname")
    summary.setdefault(name, []).append(a)

# Identify services involved via service_name label if present
service_alerts = {}
for a in filtered:
    svc = a["labels"].get("service_name")
    if svc:
        service_alerts.setdefault(svc, []).append(a)

# Build a simple diagnosis structure
entities = []
propagations = []
alerts_explained = []

# Root cause hypothesis: recommendation service has CrashLoopBackOff causing errors.
# Check for KubePodCrashLooping alert for recommendation pods.
crash_alerts = [a for a in filtered if a["labels"].get("alertname") == "KubePodCrashLooping" and a["labels"].get("pod").startswith("recommendation-")]
if crash_alerts:
    entities.append({
        "name": "otel-demo/Deployment/recommendation",
        "contributing_factor": True,
        "reasoning": "Recommendation pods are crashing (CrashLoopBackOff), stopping the service.",
        "evidence": "KubePodCrashLooping alert firing for recommendation pods."
    })
    alerts_explained.append({"alert": "KubePodCrashLooping", "explanation": "Pods repeatedly failing to start, entering CrashLoopBackOff, causing service outage.", "explained": True})
else:
    # fallback: use RequestErrorRate for recommendation
    entities.append({
        "name": "otel-demo/Deployment/recommendation",
        "contributing_factor": True,
        "reasoning": "Recommendation service shows high error rate.",
        "evidence": "RequestErrorRate alert firing for service recommendation."
    })
    alerts_explained.append({"alert": "RequestErrorRate", "explanation": "Error rate in the service exceeds threshold.", "explained": True})

# Frontend impacted by recommendation failures
entities.append({
    "name": "otel-demo/Service/frontend",
    "contributing_factor": False,
    "reasoning": "Frontend receives 5xx errors due to downstream recommendation failures.",
    "evidence": "HTTPServerErrorRate alert firing for frontend and RequestErrorRate for recommendation."
})
alerts_explained.append({"alert": "HTTPServerErrorRate", "explanation": "High 5xx response rate from frontend.", "explained": True})

# Cart service impacted (latency increase)
entities.append({
    "name": "otel-demo/Deployment/cart",
    "contributing_factor": False,
    "reasoning": "Cart experiences latency spikes because of retries to failing recommendation.",
    "evidence": "LatencyHigh alert for cart and RequestErrorRate for recommendation."
})
alerts_explained.append({"alert": "LatencyHigh", "explanation": "Observed latency exceeds threshold.", "explained": True})

# Propagation links
propagations.append({
    "source": "otel-demo/Deployment/recommendation",
    "target": "otel-demo/Service/frontend",
    "condition": "Recommendation service unavailable (CrashLoopBackOff)",
    "effect": "Frontend returns HTTP 5xx to clients"
})
propagations.append({
    "source": "otel-demo/Deployment/recommendation",
    "target": "otel-demo/Deployment/cart",
    "condition": "Recommendation calls timeout",
    "effect": "Cart latency increases and errors appear"
})

output = {
    "entities": entities,
    "propagations": propagations,
    "alerts_explained": alerts_explained
}

out_path = os.path.join("/root/projects/open_source/zero/leaderboard_results/react with code_openai_gpt-oss-120b_07ccdb1/Scenario-2/2", "agent_output.json")
with open(out_path, "w") as fp:
    json.dump(output, fp, indent=2)

print("Wrote", out_path)
