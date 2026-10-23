import json, glob, os, subprocess, sys

ALERTS_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-1/alerts"

def load_all_alerts():
    alerts = []
    for path in sorted(glob.glob(os.path.join(ALERTS_DIR, "alerts_at_*.json"))):
        with open(path) as f:
            data = json.load(f)
        alerts.extend(data)
    return alerts

def filter_otel_demo(alerts):
    return [a for a in alerts if a.get('labels', {}).get('namespace') == 'otel-demo']

def summarize(alerts):
    summary = []
    for a in alerts:
        name = a['labels'].get('alertname')
        svc = a['labels'].get('service_name') or a['labels'].get('pod')
        summary.append({
            'alert': name,
            'service': svc,
            'severity': a['labels'].get('severity'),
            'state': a['state'],
            'activeAt': a['activeAt']
        })
    return summary

def main():
    alerts = load_all_alerts()
    otel_alerts = filter_otel_demo(alerts)
    # Simple diagnosis: assume services with high error rates are impacted, latency alerts indicate source
    impacted = set()
    for a in otel_alerts:
        if a['labels'].get('alertname') == 'RequestErrorRate':
            impacted.add(a['labels'].get('service_name'))
    # Identify root cause: latency on frontend-proxy suggests upstream issue
    root_causes = []
    for a in otel_alerts:
        if a['labels'].get('alertname') == 'RequestLatency' and a['labels'].get('service_name') == 'frontend-proxy':
            root_causes.append('frontend-proxy')
    # Build output JSON
    entities = []
    # Add root cause entity as contributing factor
    for rc in set(root_causes):
        entities.append({
            'name': f'otel-demo/Deployment/{rc}',
            'contributing_factor': True,
            'reasoning': f'{rc} shows latency above threshold, likely blocking downstream calls.',
            'evidence': 'RequestLatency alert firing for frontend-proxy.'
        })
    # Add impacted services
    for svc in impacted:
        entities.append({
            'name': f'otel-demo/Deployment/{svc}',
            'contributing_factor': False,
            'reasoning': f'{svc} has high request error rate, likely downstream effect.',
            'evidence': f'RequestErrorRate alert firing for {svc}.'
        })
    # Propagation links
    propagations = []
    for svc in impacted:
        propagations.append({
            'source': f'otel-demo/Deployment/frontend-proxy',
            'target': f'otel-demo/Deployment/{svc}',
            'condition': 'high latency in frontend-proxy causing timeouts',
            'effect': f'{svc} experiences increased error rate'
        })
    alerts_explained = []
    for a in otel_alerts:
        alerts_explained.append({
            'alert': a['labels'].get('alertname'),
            'explanation': a['annotations'].get('description',''),
            'explained': True
        })
    output = {
        'entities': entities,
        'propagations': propagations,
        'alerts_explained': alerts_explained
    }
    out_path = os.path.join(os.getcwd(), 'agent_output.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    # validate JSON with jq
    subprocess.run(['jq', '.','agent_output.json'], check=True)

if __name__ == '__main__':
    main()

