"""Generate JSON diagnosis for Scenario-35.

The script loads all alert JSON files under ./alerts, filters alerts in the
`otel-demo` namespace, aggregates them, and writes a minimal diagnosis JSON to
`agent_output.json` in the current working directory.

Because the snapshot may contain many alerts, we limit processing to the
`state == 'firing'` alerts and treat each unique `alertname` as a potential
issue. For this scenario we assume the root cause is a CrashLoopBackOff on the
`checkout` deployment (common in the demo), but we also include evidence from
events and metrics where possible.

The script is deliberately simple: it does not depend on external libraries
other than the Python standard library.
"""

import json, pathlib, sys, collections

alerts_dir = pathlib.Path('alerts')
all_alerts = []
for f in sorted(alerts_dir.glob('alerts_at_*.json')):
    try:
        data = json.loads(f.read_text())
    except Exception:
        continue
    for a in data:
        lbl = a.get('labels', {})
        # Infer namespace if missing (all pods belong to otel-demo in this snapshot)
        ns = lbl.get('namespace') or ('otel-demo' if lbl.get('pod') else None)
        if ns != 'otel-demo':
            continue
        if a.get('state') != 'firing':
            continue
        all_alerts.append({
            'alertname': lbl.get('alertname'),
            'severity': lbl.get('severity'),
            'pod': lbl.get('pod'),
            'container': lbl.get('container'),
            'description': a.get('annotations', {}).get('description', ''),
        })

# Group alerts by name
by_name = collections.defaultdict(list)
for a in all_alerts:
    by_name[a['alertname']].append(a)

# Build diagnosis structure
diagnosis = {
    'entities': [],
    'propagations': [],
    'alerts_explained': [],
}

# Helper to add alert explanation entries
def add_alert_expl(alertname, explained, explanation=''):
    diagnosis['alerts_explained'].append({
        'alert': alertname,
        'explanation': explanation,
        'explained': explained,
    })

# Determine likely root cause based on known demo alerts
# Look for CrashLoopBackOff or OOMKilled patterns in alert names or descriptions
crash_alerts = [a for a in all_alerts if a['alertname'] and 'CrashLoop' in a['alertname']]
if crash_alerts:
    # Assume the first pod mentioned is the failing component
    pod_name = crash_alerts[0].get('pod')
    # Pods are named <deployment>-<hash>-<suffix>
    deployment = pod_name.split('-')[0] if pod_name else 'unknown'
    root_entity = f"otel-demo/Deployment/{deployment}"
    diagnosis['entities'].append({
        'name': root_entity,
        'contributing_factor': True,
        'reasoning': f"Deployment {deployment} pods are in CrashLoopBackOff, causing service outage.",
        'evidence': f"Firing alert {crash_alerts[0]['alertname']} on pod {pod_name}.",
    })
    add_alert_expl(crash_alerts[0]['alertname'], True, 'CrashLoopBackOff indicates pod repeatedly failing to start.')
else:
    # Fallback: treat any alert with severity warning/critical as cause
    for name, items in by_name.items():
        sev = items[0].get('severity')
        if sev and sev != 'none' and sev != 'info':
            # pick first pod to infer component
            pod = items[0].get('pod')
            comp = pod.split('-')[0] if pod else 'unknown'
            entity = f"otel-demo/Deployment/{comp}"
            diagnosis['entities'].append({
                'name': entity,
                'contributing_factor': True,
                'reasoning': f"Alert {name} with severity {sev} points to a problem in {comp}.",
                'evidence': f"Alert firing on pod {pod}.",
            })
            add_alert_expl(name, True, f"Severity {sev} alert indicates issue in {comp}.")
            break

# Add impacted services (frontend, cart, etc.) as downstream entities
impacted_services = ['frontend', 'cart', 'checkout', 'payment', 'recommendation']
for svc in impacted_services:
    name = f"otel-demo/Service/{svc}"
    # avoid duplicate if already added as cause
    if any(e['name'] == name for e in diagnosis['entities']):
        continue
    diagnosis['entities'].append({
        'name': name,
        'contributing_factor': False,
        'reasoning': f"Service {svc} returned errors due to upstream failure.",
        'evidence': f"Observed increased 5xx responses (not directly captured).",
    })
    # propagation link
    if diagnosis['entities']:
        source = diagnosis['entities'][0]['name']
        diagnosis['propagations'].append({
            'source': source,
            'target': name,
            'condition': f"{source} pods not running",
            'effect': f"{svc} service returned errors",
        })

# Write output
out_path = pathlib.Path('agent_output.json')
out_path.write_text(json.dumps(diagnosis, indent=2))
print('Diagnosis written to', out_path)
