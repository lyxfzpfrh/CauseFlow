import json, os, sys

# Directory containing alert snapshot files
# Use absolute path to snapshot alerts directory
alerts_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-81/alerts'

def load_alerts():
    alerts = []
    for fname in sorted(os.listdir(alerts_dir)):
        if not fname.startswith('alerts_at_') or not fname.endswith('.json'):
            continue
        path = os.path.join(alerts_dir, fname)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                # Expect a list of alert objects
                if isinstance(data, list):
                    alerts.extend(data)
        except Exception as e:
            print(f"Failed to load {path}: {e}", file=sys.stderr)
    return alerts

def summarize_firing_alerts(alerts, namespace='otel-demo'):
    summary = []
    for a in alerts:
        # Alert structure may vary; look for common fields
        labels = a.get('labels', {})
        if labels.get('namespace') != namespace:
            continue
        state = a.get('state') or a.get('status')
        if state != 'firing':
            continue
        name = a.get('alertname') or a.get('labels', {}).get('alertname') or a.get('name')
        start = a.get('activeAt') or a.get('startsAt')
        summary.append({
            'alert': name,
            'start': start,
        })
    return summary

if __name__ == '__main__':
    all_alerts = load_alerts()
    firing = summarize_firing_alerts(all_alerts)
    print(json.dumps(firing, indent=2))
