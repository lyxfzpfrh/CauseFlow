import json, os, glob
from datetime import datetime

# Directory containing alert snapshots
alerts_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-6/alerts'

def load_alerts():
    alerts = []
    for path in sorted(glob.glob(os.path.join(alerts_dir, 'alerts_at_*.json'))):
        with open(path) as f:
            data = json.load(f)
        # Assume each file contains a list of alerts or a dict with 'alerts'
        if isinstance(data, dict) and 'alerts' in data:
            alerts.extend(data['alerts'])
        elif isinstance(data, list):
            alerts.extend(data)
    return alerts

def filter_namespace(alerts, namespace='otel-demo'):
    filtered = []
    for a in alerts:
        labels = a.get('labels', {})
        if labels.get('namespace') == namespace:
            filtered.append(a)
    return filtered

def summarize(alerts):
    """Return a dict keyed by alertname with count and time range, plus sample labels.
    The sample includes service, deployment, pod if present for later analysis.
    """
    summary = {}
    for a in alerts:
        name = a.get('labels', {}).get('alertname', 'unknown')
        ts = a.get('activeAt') or a.get('startsAt')
        if not ts:
            continue
        ts = datetime.fromisoformat(ts.rstrip('Z'))
        entry = summary.setdefault(name, {
            'count': 0,
            'first': ts,
            'last': ts,
            'samples': []
        })
        entry['count'] += 1
        if ts < entry['first']:
            entry['first'] = ts
        if ts > entry['last']:
            entry['last'] = ts
        # capture a few representative label combos (up to 3)
        if len(entry['samples']) < 3:
            entry['samples'].append(a.get('labels', {}))
    return summary

if __name__ == '__main__':
    all_alerts = load_alerts()
    otel_alerts = filter_namespace(all_alerts)
    summary = summarize(otel_alerts)
    print(json.dumps({
        'total_alerts': len(otel_alerts),
        'summary': {k:{'count':v['count'],'first':v['first'].isoformat(),'last':v['last'].isoformat()} for k,v in summary.items()}
    }, indent=2))
