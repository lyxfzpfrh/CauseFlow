import json, os, glob

def load_firing_alerts(alerts_dir, namespace_filter=None):
    """Load all firing alerts, optionally filtering by namespace.

    Returns a list of dicts with key fields for later analysis.
    """
    firing = []
    for path in sorted(glob.glob(os.path.join(alerts_dir, '*.json'))):
        try:
            data = json.load(open(path))
        except Exception:
            continue
        for a in data:
            if a.get('state') != 'firing':
                continue
            ns = a['labels'].get('namespace')
            if namespace_filter and ns != namespace_filter:
                continue
            firing.append({
                'alertname': a['labels'].get('alertname'),
                'severity': a['labels'].get('severity'),
                'instance': a['labels'].get('instance'),
                'namespace': ns,
                'service_name': a['labels'].get('service_name'),
                'description': a['annotations'].get('description'),
                'summary': a['annotations'].get('summary'),
                'activeAt': a.get('activeAt'),
            })
    return firing

if __name__ == '__main__':
    # Focus on otel-demo namespace as per investigation request
    alerts = load_firing_alerts('alerts', namespace_filter='otel-demo')
    for a in alerts:
        svc = f" service={a['service_name']}" if a.get('service_name') else ''
        print(f"{a['alertname']} ({a.get('severity')}){svc} - {a.get('summary')}")
