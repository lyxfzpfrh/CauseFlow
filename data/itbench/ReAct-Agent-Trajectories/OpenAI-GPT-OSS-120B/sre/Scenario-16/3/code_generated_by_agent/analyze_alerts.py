import json, glob, os

BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-16"
alert_files = sorted(glob.glob(os.path.join(BASE, "alerts", "alerts_at_*.json")))

alerts = []
for f in alert_files:
    with open(f) as fp:
        data = json.load(fp)
        alerts.extend(data)

# Filter alerts that refer to the otel-demo namespace. Many alerts have a "namespace" label.
oteldemo_alerts = [a for a in alerts if a.get('labels', {}).get('namespace') == 'otel-demo']

print(f"Total alerts: {len(alerts)}; otel-demo alerts: {len(oteldemo_alerts)}")
# Show distinct alertnames
names = sorted({a['labels'].get('alertname') for a in oteldemo_alerts})
print("Alertnames:", names)

