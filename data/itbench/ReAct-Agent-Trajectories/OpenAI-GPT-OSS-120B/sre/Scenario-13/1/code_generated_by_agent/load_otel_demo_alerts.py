import json, os, glob

def load_otel_demo_alerts(snapshot_dir):
    """Load alerts for namespace 'otel-demo' from snapshot.
    Returns list of dicts with alertname, service_name, severity, state, activeAt, value.
    """
    alerts = []
    pattern = os.path.join(snapshot_dir, 'alerts', 'alerts_at_*.json')
    for f in sorted(glob.glob(pattern)):
        try:
            data = json.load(open(f))
        except Exception:
            continue
        for a in data:
            labels = a.get('labels', {})
            if labels.get('namespace') == 'otel-demo':
                alerts.append({
                    'alertname': labels.get('alertname'),
                    'service_name': labels.get('service_name'),
                    'severity': labels.get('severity'),
                    'state': a.get('state'),
                    'activeAt': a.get('activeAt'),
                    'value': a.get('value'),
                })
    return alerts

if __name__ == '__main__':
    snapshot_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-13'
    print(json.dumps(load_otel_demo_alerts(snapshot_dir), indent=2))
