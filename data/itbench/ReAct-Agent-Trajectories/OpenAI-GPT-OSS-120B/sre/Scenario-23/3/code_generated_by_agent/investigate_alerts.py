import json, os, glob
from datetime import datetime

BASE_DIR = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-23'
alerts_path = os.path.join(BASE_DIR, 'alerts')

def parse_iso(ts: str):
    # handle Z suffix
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))

alert_records = []
for file in sorted(glob.glob(os.path.join(alerts_path, 'alerts_at_*.json')):
    with open(file) as f:
        data = json.load(f)
    for a in data:
        if a.get('state') != 'firing':
            continue
        labels = a.get('labels', {})
        if labels.get('namespace') != 'otel-demo':
            continue
        alert_records.append({
            'alertname': labels.get('alertname'),
            'service_name': labels.get('service_name'),
            'severity': labels.get('severity'),
            'activeAt': parse_iso(a['activeAt']),
            'value': a.get('value'),
        })

# Aggregate by alertname+service
summary = {}
for rec in alert_records:
    key = (rec['alertname'], rec.get('service_name'))
    if key not in summary:
        summary[key] = {
            'first': rec['activeAt'],
            'last': rec['activeAt'],
            'count': 1,
            'severity': rec['severity']
        }
    else:
        summary[key]['count'] += 1
        if rec['activeAt'] < summary[key]['first']:
            summary[key]['first'] = rec['activeAt']
        if rec['activeAt'] > summary[key]['last']:
            summary[key]['last'] = rec['activeAt']

if __name__ == '__main__':
    for (name, svc), info in summary.items():
        svc_display = svc if svc else '(global)'
        print(f"{name} ({svc_display}) severity={info['severity']} count={info['count']} first={info['first']} last={info['last']}")
