import json, glob, os

def load_otel_demo_alerts(alerts_dir):
    """Load all alerts from JSON files and return those in otel-demo namespace.
    Returns a list of alert dicts.
    """
    alerts = []
    for path in sorted(glob.glob(os.path.join(alerts_dir, "alerts_at_*.json"))):
        with open(path) as f:
            data = json.load(f)
        for a in data:
            if a.get('labels', {}).get('namespace') == 'otel-demo':
                alerts.append(a)
    return alerts

def summarize_alerts(alerts):
    """Return a dict mapping alertname to list of services involved."""
    summary = {}
    for a in alerts:
        name = a['labels'].get('alertname')
        svc = a['labels'].get('service_name') or a['labels'].get('pod')
        summary.setdefault(name, set()).add(svc)
    return {k: list(v) for k, v in summary.items()}

if __name__ == "__main__":
    alerts_dir = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-1/alerts"
    alerts = load_otel_demo_alerts(alerts_dir)
    print(json.dumps(summarize_alerts(alerts), indent=2))
