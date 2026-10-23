import json, glob, os

# Directory containing alert snapshots
alerts_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-6/alerts'

def load_alerts():
    alerts = []
for path in sorted(glob.glob(os.path.join(alerts_dir, 'alerts_at_*.json'))):
        with open(path) as f:
            data = json.load(f)
            alerts.extend(data)
    return alerts

def filter_namespace(alerts, ns='otel-demo'):
    result = []
    for a in alerts:
        lbl = a.get('labels', {})
        if lbl.get('namespace') == ns:
            result.append(a)
    return result

def summarize(alerts):
    # Count by alertname and severity
    summary = {}
    for a in alerts:
        name = a['labels'].get('alertname')
        sev = a['labels'].get('severity')
        key = f"{name}|{sev}"
        summary[key] = summary.get(key, 0) + 1
    return summary

if __name__ == '__main__':
    all_alerts = load_alerts()
    ns_alerts = filter_namespace(all_alerts)
    print('Total alerts in otel-demo:', len(ns_alerts))
    for k, v in summarize(ns_alerts).items():
        print(k, v)
