import json, glob, os

def load_alerts(dir_path):
    alerts = []
    for file in sorted(glob.glob(os.path.join(dir_path, "alerts_at_*.json"))):
        with open(file) as f:
            data = json.load(f)
            alerts.extend(data)
    return alerts

def filter_by_namespace(alerts, namespace="otel-demo"):
    filtered = []
    for a in alerts:
        # Some alerts may have a 'namespace' label
        ns = a.get('labels', {}).get('namespace')
        if ns == namespace:
            filtered.append(a)
    return filtered

if __name__ == "__main__":
    alerts_dir = "./alerts"
    all_alerts = load_alerts(alerts_dir)
    otel_alerts = filter_by_namespace(all_alerts)
    # Print summary
    print(f"Total alerts: {len(all_alerts)}; otel-demo alerts: {len(otel_alerts)}")
    # Group by alertname
    from collections import Counter
    cnt = Counter(a['labels']['alertname'] for a in otel_alerts)
    for name, c in cnt.most_common():
        print(name, c)
