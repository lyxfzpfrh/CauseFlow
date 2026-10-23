import json, os, glob

BASE_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-4"
ALERTS_DIR = os.path.join(BASE_DIR, "alerts")

def load_alerts():
    alerts = []
    for path in sorted(glob.glob(os.path.join(ALERTS_DIR, "alerts_at_*.json"))):
        with open(path) as f:
            data = json.load(f)
        for a in data:
            # include namespace label if present
            ns = a.get('labels', {}).get('namespace')
            if ns == 'otel-demo':
                alerts.append({
                    'alertname': a['labels'].get('alertname'),
                    'state': a.get('state'),
                    'severity': a['labels'].get('severity'),
                    'activeAt': a.get('activeAt'),
                    'pod': a['labels'].get('pod'),
                    'service': a['labels'].get('service')
                })
    return alerts

if __name__ == '__main__':
    alerts = load_alerts()
    # Print summary of firing alerts
    firing = [a for a in alerts if a['state'] == 'firing']
    print('Total otel-demo alerts:', len(alerts))
    print('Firing alerts:', len(firing))
    for a in firing:
        print(a)
