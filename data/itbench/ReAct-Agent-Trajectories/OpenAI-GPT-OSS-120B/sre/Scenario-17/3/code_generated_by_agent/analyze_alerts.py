import json, os, glob

# Directory with alerts
alert_dir = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-17/alerts'
alert_files = sorted(glob.glob(os.path.join(alert_dir, 'alerts_at_*.json')))

alerts = []
for f in alert_files:
    with open(f) as fp:
        data = json.load(fp)
        alerts.extend(data)

# Filter alerts in otel-demo namespace
otel_alerts = [a for a in alerts if a.get('labels', {}).get('namespace') == 'otel-demo']

# Summarize unique alert names and counts
summary = {}
for a in otel_alerts:
    name = a['labels'].get('alertname')
    summary.setdefault(name, {'count':0, 'states':set()})
    summary[name]['count'] += 1
    summary[name]['states'].add(a.get('state'))

print('OTEL DEMO ALERT SUMMARY:')
for name, info in summary.items():
    print(f"{name}: {info['count']} occurrences, states={list(info['states'])}")

# Write filtered alerts to a JSON for later use
out_path = '/root/projects/open_source/zero/leaderboard_results/react with code_openai_gpt-oss-120b_07ccdb1/Scenario-17/3/otel_alerts_filtered.json'
with open(out_path, 'w') as fp:
    json.dump(otel_alerts, fp, indent=2)
