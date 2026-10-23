"""Simple script to generate agent_output.json for the incident.
It scans all alert JSON files, selects firing alerts in the otel-demo namespace,
creates entities for pods in CrashLoopBackOff or OOMKilled states, and builds a
basic propagation to the corresponding service. The output follows the required schema.
"""

import json, glob, os

BASE_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-5"


def load_firing_alerts(namespace="otel-demo"):
    """Load all firing alerts for a given namespace."""
    alert_files = sorted(glob.glob(os.path.join(BASE_DIR, "alerts", "alerts_at_*.json")))
    alerts = []
    for f in alert_files:
        try:
            data = json.load(open(f))
        except Exception:
            continue
        for a in data:
            if a.get("state") != "firing":
                continue
            lbl = a.get("labels", {})
            if lbl.get("namespace") != namespace:
                continue
            alerts.append({
                "alertname": lbl.get("alertname"),
                "severity": lbl.get("severity"),
                "pod": lbl.get("pod"),
                "description": a.get("annotations", {}).get("summary", ""),
                "activeAt": a.get("activeAt"),
            })
    return alerts


def main():
    alerts = load_firing_alerts()
    entities = []
    propagations = []
    alerts_explained = []

    for a in alerts:
        name = a["alertname"]
        alerts_explained.append({"alert": name, "explanation": "", "explained": False})
        # Detect pod failure alerts by name patterns
        if any(keyword in name for keyword in ["CrashLoopBackOff", "OOMKilled", "ContainerRestart", "ContainerFailed"]):
            pod = a.get("pod")
            if not pod:
                continue
            # Namespace is prefix before first '-'
            ns = pod.split("-")[0]
            entity_name = f"{ns}/Pod/{pod}"
            entities.append({
                "name": entity_name,
                "contributing_factor": True,
                "reasoning": f"Pod {pod} is in a failure state ({name}).",
                "evidence": f"Alert {name} firing for pod {pod} at {a.get('activeAt')}"
            })
            # Infer related Service (assume service name equals deployment prefix)
            svc = pod.split("-")[0]
            target = f"{ns}/Service/{svc}"
            propagations.append({
                "source": entity_name,
                "target": target,
                "condition": "Pod not running",
                "effect": "Service experiences errors/unavailability"
            })

    output = {
        "entities": entities,
        "propagations": propagations,
        "alerts_explained": alerts_explained,
    }
    out_path = os.path.join(os.getcwd(), "agent_output.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()

