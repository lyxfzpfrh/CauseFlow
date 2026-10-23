import json, os, glob

def load_oteldemo_alerts(alerts_dir):
    """Load all alert JSON files and return list of alerts in otel-demo namespace."""
    alerts = []
    for path in sorted(glob.glob(os.path.join(alerts_dir, 'alerts_at_*.json')):
        with open(path) as f:
            data = json.load(f)
        for a in data:
            # some alerts may not have namespace label; default to unknown
            ns = a.get('labels', {}).get('namespace')
            if ns == 'otel-demo':
                alerts.append({
                    'alertname': a['labels'].get('alertname'),
                    'entity': a['labels'].get('instance') or a['labels'].get('entity'),
                    'severity': a['labels'].get('severity'),
                    'state': a.get('state'),
                    'activeAt': a.get('activeAt')
                })
    return alerts

if __name__ == "__main__":
    alerts_dir = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-9/alerts"
    otel_alerts = load_oteldemo_alerts(alerts_dir)
    print(json.dumps(otel_alerts, indent=2))
