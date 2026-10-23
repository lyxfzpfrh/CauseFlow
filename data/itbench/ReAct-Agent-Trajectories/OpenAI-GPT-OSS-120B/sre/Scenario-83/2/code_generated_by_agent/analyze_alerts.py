import json, glob, os

# Directory containing the snapshot data
SNAPSHOT_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-83"

def load_otel_demo_alerts():
    """Load all alerts for the otel-demo namespace from the snapshot files."""
    alerts = []
    pattern = os.path.join(SNAPSHOT_DIR, "alerts", "alerts_at_*.json")
    for path in sorted(glob.glob(pattern)):
        with open(path) as f:
            data = json.load(f)
        for a in data:
            ns = a.get('labels', {}).get('namespace')
            if ns != 'otel-demo':
                continue
            alerts.append({
                'alertname': a['labels'].get('alertname'),
                'severity': a['labels'].get('severity'),
                'state': a.get('state'),
                'activeAt': a.get('activeAt'),
                'value': a.get('value'),
                'annotations': a.get('annotations', {}),
                'file': os.path.basename(path)
            })
    return alerts

def summarize_alerts(alerts):
    """Group alerts by name and report count, severity list, first/last timestamps."""
    summary = {}
    for a in alerts:
        name = a['alertname']
        entry = summary.setdefault(name, {'count': 0, 'first': a['activeAt'], 'last': a['activeAt'], 'severities': set()})
        entry['count'] += 1
        entry['severities'].add(a['severity'])
        if a['activeAt'] < entry['first']:
            entry['first'] = a['activeAt']
        if a['activeAt'] > entry['last']:
            entry['last'] = a['activeAt']
    for v in summary.values():
        v['severities'] = list(v['severities'])
    return summary

if __name__ == '__main__':
    alerts = load_otel_demo_alerts()
    print(json.dumps(summarize_alerts(alerts), indent=2))
