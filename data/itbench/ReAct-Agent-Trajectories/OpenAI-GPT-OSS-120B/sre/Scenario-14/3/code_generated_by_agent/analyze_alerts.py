import json, os, glob

# Directory containing alert snapshots
BASE_DIR = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-14/alerts'

def load_alerts():
    alerts = []
    for path in sorted(glob.glob(os.path.join(BASE_DIR, 'alerts_at_*.json')):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            continue
        for a in data.get('data', {}).get('alerts', []):
            # keep only firing alerts in otel-demo namespace
            if a.get('state') == 'firing' and a.get('labels', {}).get('namespace') == 'otel-demo':
                alerts.append({
                    'alertname': a['labels'].get('alertname'),
                    'service': a['labels'].get('service_name'),
                    'severity': a['labels'].get('severity'),
                    'value': a.get('value'),
                    'description': a.get('annotations', {}).get('description'),
                    'activeAt': a.get('activeAt')
                })
    return alerts

if __name__ == '__main__':
    alerts = load_alerts()
    # Output as JSON list for downstream processing
    print(json.dumps(alerts, indent=2))
