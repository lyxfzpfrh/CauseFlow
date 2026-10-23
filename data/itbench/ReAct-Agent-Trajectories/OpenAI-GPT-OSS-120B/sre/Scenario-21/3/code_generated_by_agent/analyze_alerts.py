import json, os, glob

def load_firing_alerts(base_dir):
    alerts = []
    for path in sorted(glob.glob(os.path.join(base_dir, 'alerts', '*.json'))):
        try:
            with open(path) as f:
                raw = f.read().strip()
                # File may be a JSON array or a single JSON object per line
                if raw.startswith('['):
                    data = json.loads(raw)
                else:
                    # treat each line as a JSON object
                    data = [json.loads(line) for line in raw.splitlines() if line]
        except Exception:
            continue
        for a in data:
            if not isinstance(a, dict):
                continue
            if a.get('state') != 'firing':
                continue
            labels = a.get('labels', {})
            if labels.get('namespace') != 'otel-demo':
                continue
            alerts.append({
                'alertname': labels.get('alertname'),
                'instance': labels.get('instance'),
                'severity': labels.get('severity'),
                'state': a.get('state'),
                'activeAt': a.get('activeAt'),
                'annotations': a.get('annotations', {}),
                'source_file': os.path.basename(path)
            })
    return alerts

if __name__ == '__main__':
    base = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-21'
    firing = load_firing_alerts(base)
    print(json.dumps(firing, indent=2))
