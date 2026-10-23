import json, sys, os

def list_alert_names(filepath):
    with open(filepath) as f:
        data = json.load(f)
    names = [item.get('labels', {}).get('alertname', 'UNKNOWN') for item in data]
    return names

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse_alerts.py <alerts_file>")
        sys.exit(1)
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
    names = list_alert_names(file_path)
    for n in names:
        print(n)
