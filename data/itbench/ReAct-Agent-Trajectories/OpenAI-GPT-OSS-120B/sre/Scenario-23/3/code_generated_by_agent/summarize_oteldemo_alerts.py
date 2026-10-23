"""Summarize firing alerts for namespace otel-demo.
The script scans all JSON alert files under the snapshot's alerts/ directory,
collects alerts with state "firing" and namespace "otel-demo", and prints a
compact summary useful for the diagnosis.
"""

import json, glob, os
from datetime import datetime

BASE = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-23'
ALERT_DIR = os.path.join(BASE, 'alerts')

def iso(ts: str):
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))

records = []
for path in sorted(glob.glob(os.path.join(ALERT_DIR, '*.json')):
    try:
        data = json.load(open(path))
    except Exception:
        continue
    for a in data:
        if a.get('state') != 'firing':
            continue
        lbl = a.get('labels', {})
        if lbl.get('namespace') != 'otel-demo':
            continue
        records.append({
            'alertname': lbl.get('alertname'),
            'service': lbl.get('service_name'),
            'severity': lbl.get('severity'),
            'activeAt': iso(a['activeAt']),
        })

# aggregate
summary = {}
for r in records:
    key = (r['alertname'], r.get('service'))
    if key not in summary:
        summary[key] = {'count': 1, 'first': r['activeAt'], 'last': r['activeAt'], 'severity': r['severity']}
    else:
        summary[key]['count'] += 1
        if r['activeAt'] < summary[key]['first']:
            summary[key]['first'] = r['activeAt']
        if r['activeAt'] > summary[key]['last']:
            summary[key]['last'] = r['activeAt']

if __name__ == '__main__':
    for (name, svc), s in summary.items():
        svc_disp = svc if svc else '(global)'
        print(f"{name} {svc_disp} sev={s['severity']} cnt={s['count']} [{s['first']} - {s['last']}]" )
