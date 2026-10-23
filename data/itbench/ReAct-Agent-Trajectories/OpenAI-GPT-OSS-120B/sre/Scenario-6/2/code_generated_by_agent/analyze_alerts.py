import json, glob, os

def load_alerts(dir_path):
    alerts = []
    for file in sorted(glob.glob(os.path.join(dir_path, 'alerts_at_*.json'))):
        with open(file) as f:
            data = json.load(f)
            alerts.extend(data)
    return alerts

def filter_namespace(alerts, namespace='otel-demo'):
    filtered = []
    for a in alerts:
        lbl = a.get('labels', {})
        # Some alerts may have 'namespace' label
        if lbl.get('namespace') == namespace:
            filtered.append(a)
    return filtered

if __name__ == '__main__':
    base = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-6'
    alerts = load_alerts(os.path.join(base, 'alerts'))
    otel_alerts = filter_namespace(alerts, 'otel-demo')
    # Keep only firing alerts
    otel_alerts = [a for a in otel_alerts if a.get('state') == 'firing']
    # Summarize unique alert names
    names = sorted({a.get('labels', {}).get('alertname') for a in otel_alerts})
    summary = {'unique_alertnames': names, 'count': len(otel_alerts)}
    print(json.dumps({'summary': summary, 'alerts': otel_alerts}, indent=2))
