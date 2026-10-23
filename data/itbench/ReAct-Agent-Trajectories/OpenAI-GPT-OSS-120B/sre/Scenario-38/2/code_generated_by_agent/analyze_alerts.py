import json, os
from pathlib import Path

SNAPSHOT_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-38"
ALERTS_DIR = os.path.join(SNAPSHOT_DIR, "alerts")

def load_alerts():
    alerts = []
    for file in sorted(Path(ALERTS_DIR).glob('alerts_at_*.json')):
        try:
            data = json.load(open(file))
        except Exception:
            continue
        if isinstance(data, list):
            alerts.extend(data)
    return alerts

def filter_otel_demo(alerts):
    out = []
    for a in alerts:
        lbl = a.get('labels', {})
        if lbl.get('namespace') == 'otel-demo':
            out.append(a)
        else:
            if 'otel-demo' in json.dumps(a):
                out.append(a)
    return out

def summarize(alerts):
    summary = []
    for a in alerts:
        lbl = a.get('labels', {})
        name = lbl.get('alertname')
        severity = lbl.get('severity')
        state = a.get('state')
        start = a.get('activeAt')
        summary.append({
            'alert': name,
            'severity': severity,
            'state': state,
            'start': start,
        })
    return summary

if __name__ == '__main__':
    alerts = load_alerts()
    otel = filter_otel_demo(alerts)
    for s in summarize(otel):
        print(s)
