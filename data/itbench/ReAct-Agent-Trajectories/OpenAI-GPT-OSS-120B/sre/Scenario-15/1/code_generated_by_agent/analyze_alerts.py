import json, glob, os

BASE_DIR = '/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-15'
alerts_path = os.path.join(BASE_DIR, 'alerts')
alert_files = sorted(glob.glob(os.path.join(alerts_path, 'alerts_at_*.json')))

def load_alerts():
    all_alerts = []
    for f in alert_files:
        with open(f) as fp:
            data = json.load(fp)
            for a in data:
                a['_source_file'] = os.path.basename(f)
                all_alerts.append(a)
    return all_alerts

def filter_otel_demo(alerts):
    return [a for a in alerts if a.get('labels', {}).get('namespace') == 'otel-demo']

if __name__ == '__main__':
    alerts = load_alerts()
    otel_alerts = filter_otel_demo(alerts)
    # Summarize and collect up to 2 examples per alertname
    summary = {}
    examples = {}
    for a in otel_alerts:
        name = a['labels'].get('alertname')
        state = a.get('state')
        summary.setdefault(name, {'firing':0, 'pending':0, 'inactive':0})
        summary[name][state] = summary[name].get(state,0)+1
        examples.setdefault(name, [])
        if len(examples[name]) < 2:
            examples[name].append({
                'alertname': name,
                'pod': a['labels'].get('pod'),
                'instance': a['labels'].get('instance'),
                'severity': a['labels'].get('severity'),
                'state': state,
                'activeAt': a.get('activeAt'),
                'description': a.get('annotations',{}).get('description')
            })
    output = {'summary': summary, 'examples': examples}
    print(json.dumps(output, indent=2))
