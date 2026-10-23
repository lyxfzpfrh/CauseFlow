import json, os, glob

BASE_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-102"
alert_files = sorted(glob.glob(os.path.join(BASE_DIR, "alerts", "alerts_at_*.json")))

alerts = []
for f in alert_files:
    with open(f) as fp:
        data = json.load(fp)
        for a in data:
            a_copy = a.copy()
            a_copy["source_file"] = os.path.basename(f)
            alerts.append(a_copy)

# Filter alerts that mention otel-demo namespace via any label value containing 'otel-demo'
filtered = [a for a in alerts if any('otel-demo' in str(v) for v in a.get('labels', {}).values())]

# Summarize by alertname
summary = {}
for a in filtered:
    name = a['labels'].get('alertname', 'unknown')
    summary.setdefault(name, 0)
    summary[name] += 1

print('Total alerts:', len(alerts))
print('Filtered otel-demo alerts:', len(filtered))
print('Summary by alertname:')
for k, v in summary.items():
    print(k, v)
