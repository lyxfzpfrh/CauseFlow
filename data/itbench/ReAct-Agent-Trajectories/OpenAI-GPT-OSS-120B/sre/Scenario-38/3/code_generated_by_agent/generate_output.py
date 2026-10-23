"""Generate the required agent_output.json for the incident.
The script analyses alerts (already loaded) and builds a minimal
causal model focusing on the otel-demo namespace.
"""

import json, glob, os, collections

SNAPSHOT_DIR = os.path.abspath('.')
ALERTS_DIR = os.path.join(SNAPSHOT_DIR, 'alerts')

def load_alerts():
    alerts = []
    for f in sorted(glob.glob(os.path.join(ALERTS_DIR, 'alerts_at_*.json'))):
        with open(f) as fp:
            alerts.extend(json.load(fp))
    return alerts

def namespace_alerts(alerts, ns='otel-demo'):
    return [a for a in alerts if a.get('labels', {}).get('namespace') == ns]

def main():
    alerts = load_alerts()
    ns_alerts = namespace_alerts(alerts)

    # Identify HPA maxed out alerts
    hpa_alerts = [a for a in ns_alerts if a['labels']['alertname'] == 'KubeHpaMaxedOut']
    hpas = sorted({a['labels'].get('horizontalpodautoscaler') for a in hpa_alerts})

    # Identify request error rate alerts
    err_alerts = [a for a in ns_alerts if a['labels']['alertname'] == 'RequestErrorRate']
    err_services = sorted({a['labels'].get('service_name') for a in err_alerts})

    # Build entities list
    entities = []
    # Contributing factors: each HPA that is maxed out
    for hpa in hpas:
        name = f"otel-demo/HorizontalPodAutoscaler/{hpa}"
        entities.append({
            "name": name,
            "contributing_factor": True,
            "reasoning": f"HPA {hpa} reached its max replica limit, preventing scaling.",
            "evidence": f"{len([a for a in hpa_alerts if a['labels'].get('horizontalpodautoscaler')==hpa])} KubeHpaMaxedOut alerts."
        })
    # Impacted services (derived)
    for svc in err_services:
        name = f"otel-demo/Service/{svc}"
        entities.append({
            "name": name,
            "contributing_factor": False,
            "reasoning": f"Service {svc} shows increased error rate due to insufficient replicas.",
            "evidence": f"{len([a for a in err_alerts if a['labels'].get('service_name')==svc])} RequestErrorRate alerts."
        })

    # Build propagation links from HPA to its Service (if names match)
    propagations = []
    for hpa in hpas:
        if hpa in err_services:
            propagations.append({
                "source": f"otel-demo/HorizontalPodAutoscaler/{hpa}",
                "target": f"otel-demo/Service/{hpa}",
                "condition": "HPA maxed out, cannot increase replicas",
                "effect": "Service experiences request errors"
            })

    # Alerts explained list (unique by alertname)
    alerts_explained = []
    seen = set()
    for a in ns_alerts:
        name = a['labels']['alertname']
        if name in seen:
            continue
        seen.add(name)
        explanation = ""
        explained = False
        if name == 'KubeHpaMaxedOut':
            explanation = "HPA cannot scale beyond max replicas, causing service pressure."
            explained = True
        elif name == 'RequestErrorRate':
            explanation = "High request error rate observed in affected services."
            explained = True
        elif name == 'CPUThrottlingHigh':
            explanation = "Collector pods experiencing CPU throttling."
            explained = True
        elif name == 'NoRequestsDetected':
            explanation = "No inbound requests detected for some services."
            explained = True
        elif name == 'InfoInhibitor':
            explanation = "Info level alert used as inhibitor."
            explained = True
        alerts_explained.append({
            "alert": name,
            "explanation": explanation,
            "explained": explained
        })

    output = {
        "entities": entities,
        "propagations": propagations,
        "alerts_explained": alerts_explained
    }

    out_path = os.path.join(SNAPSHOT_DIR, 'agent_output.json')
    with open(out_path, 'w') as fp:
        json.dump(output, fp, indent=2)

    # Validate JSON using jq
    os.system(f"jq . {out_path} > /dev/null")

if __name__ == '__main__':
    main()

