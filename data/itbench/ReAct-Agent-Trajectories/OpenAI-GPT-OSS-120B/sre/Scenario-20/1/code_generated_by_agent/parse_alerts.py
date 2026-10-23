import json, os, sys

def load_alerts(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def main():
    alerts_dir = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-20/alerts"
    # gather all alert files
    files = [f for f in os.listdir(alerts_dir) if f.endswith('.json')]
    all_alerts = []
    for f in sorted(files):
        path = os.path.join(alerts_dir, f)
        try:
            alerts = load_alerts(path)
            if isinstance(alerts, list):
                all_alerts.extend(alerts)
            else:
                all_alerts.append(alerts)
        except Exception as e:
            print(f"Failed to load {path}: {e}", file=sys.stderr)
    # filter otel-demo namespace
    otel_alerts = [a for a in all_alerts if a.get('labels', {}).get('namespace') == 'otel-demo']
    # summarise unique alertnames with state counts and example pods if present
    summary = {}
    for a in otel_alerts:
        name = a.get('labels', {}).get('alertname') or a.get('alertname')
        state = a.get('state')
        pod = a.get('labels', {}).get('pod')
        if not name:
            continue
        entry = summary.setdefault(name, {'firing':0, 'pending':0, 'inactive':0, 'example_pods':set()})
        entry[state] = entry.get(state,0)+1
        if pod:
            entry['example_pods'].add(pod)
    # convert sets to lists for JSON serialization
    for v in summary.values():
        v['example_pods'] = list(v['example_pods'])
    print(json.dumps({"total_alerts": len(otel_alerts), "summary": summary}, indent=2))

if __name__=="__main__":
    main()
