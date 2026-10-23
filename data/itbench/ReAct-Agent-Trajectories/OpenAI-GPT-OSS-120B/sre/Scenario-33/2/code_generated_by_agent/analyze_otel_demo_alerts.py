import json, glob, os

def load_otel_demo_alerts(alerts_dir):
    """Load all alert JSON files and return a list of firing alerts for namespace otel-demo."""
    alerts = []
    for path in sorted(glob.glob(os.path.join(alerts_dir, 'alerts_at_*.json'))):
        try:
            data = json.load(open(path))
        except Exception:
            continue
        for a in data:
            labels = a.get('labels', {})
            if labels.get('namespace') == 'otel-demo' and a.get('state') == 'firing':
                alerts.append({
                    'alertname': labels.get('alertname'),
                    'severity': labels.get('severity'),
                    'instance': labels.get('instance'),
                    'description': a.get('annotations', {}).get('description', ''),
                    'summary': a.get('annotations', {}).get('summary', ''),
                    'activeAt': a.get('activeAt')
                })
    return alerts

if __name__ == '__main__':
    alerts_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-33/alerts'
    alerts = load_otel_demo_alerts(alerts_dir)
    # Summarize per alert name with count and example entity
    summary = {}
    for a in alerts:
        name = a['alertname']
        if name not in summary:
            summary[name] = {'count': 0, 'example_instance': a['instance']}
        summary[name]['count'] += 1
    print('Firing otel-demo alerts summary:')
    for name, info in summary.items():
        print(f"- {name}: count={info['count']}, example_instance={info['example_instance']}")
