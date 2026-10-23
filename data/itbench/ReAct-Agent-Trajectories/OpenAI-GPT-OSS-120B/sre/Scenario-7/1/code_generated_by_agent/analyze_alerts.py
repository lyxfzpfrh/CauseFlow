import json, os, re
from pathlib import Path

BASE = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-7'
alerts_dir = Path(BASE) / 'alerts'

def load_all_alerts():
    alerts = []
    for f in sorted(alerts_dir.glob('alerts_at_*.json')):
        with open(f) as fh:
            data = json.load(fh)
            alerts.extend(data)
    return alerts

def filter_by_namespace(alerts, ns='otel-demo'):
    result = []
    for a in alerts:
        lbl = a.get('labels', {})
        if lbl.get('namespace') == ns:
            result.append(a)
    return result

if __name__ == '__main__':
    all_alerts = load_all_alerts()
    otel_alerts = filter_by_namespace(all_alerts)
    print(f"Total alerts: {len(all_alerts)}, otel-demo alerts: {len(otel_alerts)}")
    # Summarize by alertname
    # Summarize firing alerts for otel-demo namespace
    from collections import defaultdict
    alert_info = defaultdict(list)
    for a in otel_alerts:
        if a.get('state') != 'firing':
            continue
        name = a['labels'].get('alertname')
        severity = a['labels'].get('severity')
        active = a.get('activeAt')
        alert_info[name].append({'severity': severity, 'activeAt': active})
    for name, entries in alert_info.items():
        print(f"{name}: {len(entries)} firing instances; first at {entries[0]['activeAt']}")
