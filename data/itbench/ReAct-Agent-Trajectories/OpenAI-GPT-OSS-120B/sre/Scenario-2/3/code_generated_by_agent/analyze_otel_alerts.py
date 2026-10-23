"""Load all alert JSON files and produce a summary of firing alerts for the otel-demo namespace.

The script:
  * Reads every alerts_at_*.json file in the ./alerts directory.
  * Filters alerts where `labels.namespace` == "otel-demo" and `state` == "firing".
  * Counts occurrences per `alertname` and prints a table: alertname, count, firstSeen, lastSeen.
"""

import json, pathlib, sys
from collections import defaultdict
from datetime import datetime

def load_all_alerts(alerts_dir: pathlib.Path):
    alerts = []
    for file in sorted(alerts_dir.glob('alerts_at_*.json')):
        try:
            data = json.loads(file.read_text())
            alerts.extend(data)
        except Exception as e:
            print(f"Error reading {file}: {e}", file=sys.stderr)
    return alerts

def summarize(alerts):
    summary = defaultdict(lambda: {'count':0, 'first':None, 'last':None})
    for a in alerts:
        lbl = a.get('labels', {})
        if lbl.get('namespace') != 'otel-demo' or a.get('state') != 'firing':
            continue
        name = lbl.get('alertname')
        ts = a.get('activeAt') or a.get('timestamp')
        if ts:
            try:
                t = datetime.fromisoformat(ts.rstrip('Z'))
            except Exception:
                t = None
        else:
            t = None
        entry = summary[name]
        entry['count'] += 1
        if t:
            if entry['first'] is None or t < entry['first']:
                entry['first'] = t
            if entry['last'] is None or t > entry['last']:
                entry['last'] = t
    return summary

def main():
    alerts_dir = pathlib.Path('alerts')
    all_alerts = load_all_alerts(alerts_dir)
    summ = summarize(all_alerts)
    for name, data in sorted(summ.items(), key=lambda x: -x[1]['count']):
        first = data['first'].isoformat() if data['first'] else 'N/A'
        last = data['last'].isoformat() if data['last'] else 'N/A'
        print(f"{name}\t{data['count']}\t{first}\t{last}")

if __name__ == '__main__':
    main()

