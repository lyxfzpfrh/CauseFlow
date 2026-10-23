"""Generate incident diagnosis JSON for otel-demo namespace.

The script loads all firing alerts in the snapshot, extracts relevant Kubernetes
entities (services/deployments) and builds a minimal causal model. It then writes
the result to agent_output.json in the working directory.
"""

import json, os, glob
from collections import defaultdict

SNAPSHOT_ROOT = os.getenv('SNAPSHOT_ROOT', '.')
ALERTS_DIR = os.path.join(SNAPSHOT_ROOT, 'alerts')

def load_firing_alerts(namespace='otel-demo'):
    """Return list of firing alerts limited to the given namespace."""
    alerts = []
    for path in sorted(glob.glob(os.path.join(ALERTS_DIR, '*.json'))):
        try:
            data = json.load(open(path))
        except Exception:
            continue
        for a in data:
            if a.get('state') != 'firing':
                continue
            if a['labels'].get('namespace') != namespace:
                continue
            alerts.append({
                'alertname': a['labels'].get('alertname'),
                'service': a['labels'].get('service_name'),
                'severity': a['labels'].get('severity'),
                'summary': a['annotations'].get('summary'),
                'description': a['annotations'].get('description'),
                'activeAt': a.get('activeAt'),
            })
    return alerts

def build_entities(alerts):
    """Map service name to entity string 'otel-demo/Service/<name>'."""
    entities = {}
    for a in alerts:
        svc = a.get('service')
        if svc:
            entities[svc] = f"otel-demo/Service/{svc}"
    return entities

def main():
    alerts = load_firing_alerts()
    alerts_by_svc = defaultdict(list)
    for a in alerts:
        alerts_by_svc[a.get('service')].append(a)

    # Identify root cause: any critical alert service, else most alerts.
    root_cause = None
    for svc, lst in alerts_by_svc.items():
        if any(al['severity'] == 'critical' for al in lst):
            root_cause = svc
            break
    if not root_cause:
        root_cause = max(alerts_by_svc.items(), key=lambda kv: len(kv[1]))[0]

    entities_output = []
    for svc, name in build_entities(alerts).items():
        cf = (svc == root_cause)
        reasoning = "Root cause service causing errors" if cf else "Impacted downstream service"
        ev = ", ".join([f"{e['alertname']} ({e['severity']})" for e in alerts_by_svc.get(svc, [])])
        entities_output.append({
            "name": name,
            "contributing_factor": cf,
            "reasoning": reasoning,
            "evidence": ev,
        })

    # Propagation links from root cause to each impacted service
    propagations = []
    root_name = f"otel-demo/Service/{root_cause}" if root_cause else None
    for svc, name in build_entities(alerts).items():
        if svc == root_cause:
            continue
        propagations.append({
            "source": root_name,
            "target": name,
            "condition": f"{root_cause} service has high error rate",
            "effect": f"Downstream service {svc} shows elevated errors",
        })

    alerts_explained = []
    for a in alerts:
        alerts_explained.append({
            "alert": a['alertname'],
            "explanation": a['description'] or a['summary'],
            "explained": True,
        })

    output = {
        "entities": entities_output,
        "propagations": propagations,
        "alerts_explained": alerts_explained,
    }
    out_path = os.path.join(SNAPSHOT_ROOT, 'agent_output.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Wrote diagnosis to {out_path}")

if __name__ == '__main__':
    main()

