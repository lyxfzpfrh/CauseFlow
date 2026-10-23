import json, glob, os

# Base directory where snapshot data resides
BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-102"
alert_files = sorted(glob.glob(os.path.join(BASE, "alerts", "alerts_at_*.json")))
all_alerts = []
for f in alert_files:
    with open(f) as fp:
        data = json.load(fp)
        for a in data:
            a['source_file'] = os.path.basename(f)
            all_alerts.append(a)

# Filter alerts in otel-demo namespace
otel_alerts = [a for a in all_alerts if a.get('labels', {}).get('namespace') == 'otel-demo']

# Summarize by alertname
summary = {}
for a in otel_alerts:
    name = a['labels'].get('alertname', 'unknown')
    summary[name] = summary.get(name, 0) + 1

print('Total otel-demo alerts:', len(otel_alerts))
for n, cnt in summary.items():
    print(f"{n}: {cnt}")
