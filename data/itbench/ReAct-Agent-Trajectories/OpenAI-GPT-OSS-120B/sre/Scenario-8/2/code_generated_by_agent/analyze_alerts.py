import json, os, glob

def load_otel_demo_alerts(alerts_dir):
    alerts = []
    for path in sorted(glob.glob(os.path.join(alerts_dir, 'alerts_at_*.json'))):
        with open(path) as f:
            data = json.load(f)
        for a in data:
            # some alerts may lack namespace label; skip those not in otel-demo
            ns = a.get('labels', {}).get('namespace')
            if ns == 'otel-demo':
                alerts.append({
                    'name': a['labels'].get('alertname'),
                    'state': a.get('state'),
                    'severity': a['labels'].get('severity'),
                    'activeAt': a.get('activeAt'),
                    'description': a.get('annotations', {}).get('description'),
                })
    return alerts

if __name__ == '__main__':
    alerts_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-8/alerts'
    otel_alerts = load_otel_demo_alerts(alerts_dir)
    # Print summary JSON to stdout
    print(json.dumps(otel_alerts, indent=2))
