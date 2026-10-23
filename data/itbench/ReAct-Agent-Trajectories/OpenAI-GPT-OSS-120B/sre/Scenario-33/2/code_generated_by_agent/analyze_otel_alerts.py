import json, glob, os
from collections import defaultdict

BASE = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-33/alerts'
alert_files = sorted(glob.glob(os.path.join(BASE, 'alerts_at_*.json')))

alerts_by_name = defaultdict(list)
for f in alert_files:
    with open(f) as fp:
        data = json.load(fp)
    for a in data:
        lbl = a.get('labels', {})
        if lbl.get('namespace') != 'otel-demo':
            continue
        name = lbl.get('alertname')
        alerts_by_name[name].append({
            'state': a.get('state'),
            'activeAt': a.get('activeAt'),
            'severity': lbl.get('severity'),
            'instance': lbl.get('instance'),
        })

# Summarize each alert: earliest activeAt, latest, count, current state
summary = {}
for name, items in alerts_by_name.items():
    times = [i['activeAt'] for i in items]
    times.sort()
    summary[name] = {
        'count': len(items),
        'first': times[0],
        'last': times[-1],
        'states': list({i['state'] for i in items}),
        'severities': list({i['severity'] for i in items}),
    }

print(json.dumps(summary, indent=2))
