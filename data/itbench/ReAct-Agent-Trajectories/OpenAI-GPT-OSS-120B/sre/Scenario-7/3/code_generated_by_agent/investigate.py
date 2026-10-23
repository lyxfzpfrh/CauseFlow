import json, os, glob

def load_alerts(alerts_dir):
    """Load all alert JSON files in chronological order and return a flat list."""
    alerts = []
    for path in sorted(glob.glob(os.path.join(alerts_dir, 'alerts_at_*.json'))):
        with open(path) as f:
            data = json.load(f)
            alerts.extend(data)
    return alerts

def filter_namespace(alerts, ns='otel-demo'):
    """Return alerts that have a label 'namespace' matching the given namespace."""
    return [a for a in alerts if a.get('labels', {}).get('namespace') == ns]

def summarize(alerts):
    """Count alerts by alertname."""
    summary = {}
    for a in alerts:
        name = a['labels'].get('alertname')
        summary[name] = summary.get(name, 0) + 1
    return summary

if __name__ == '__main__':
    alerts_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-7/alerts'
    alerts = load_alerts(alerts_dir)
    ns_alerts = filter_namespace(alerts)
    print('Total alerts:', len(alerts))
    print('Namespace otel-demo alerts:', len(ns_alerts))
    print('Summary by name:', summarize(ns_alerts))
