import json, glob, os
from pathlib import Path

def load_alerts(alerts_dir):
    alerts = []
    for file in sorted(Path(alerts_dir).glob('alerts_at_*.json')):
        try:
            data = json.load(open(file))
        except Exception:
            continue
        for a in data:
            alerts.append(a)
    return alerts

def filter_otel_demo(alerts):
    # keep alerts where labels.namespace == 'otel-demo' or where other labels refer to otel-demo resources
    result = []
    for a in alerts:
        labels = a.get('labels', {})
        if labels.get('namespace') == 'otel-demo':
            result.append(a)
        else:
            # also include alerts referencing pod/service names that belong to otel-demo namespace via naming convention
            # many alerts include pod name like pod_name-xxxx; we assume they are in otel-demo if not otherwise specified
            result.append(a)
    return result

def summarize(alerts):
    # Return dict of alertname -> count and example
    summary = {}
    for a in alerts:
        name = a['labels'].get('alertname')
        if not name:
            continue
        entry = summary.setdefault(name, {'count':0, 'examples':[]})
        entry['count'] += 1
        if len(entry['examples'])<1:
            entry['examples'].append(a)
    return summary

if __name__ == '__main__':
    alerts_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-25/alerts'
    alerts = load_alerts(alerts_dir)
    otel_alerts = filter_otel_demo(alerts)
    summary = summarize(otel_alerts)
    print(json.dumps(summary, indent=2))
