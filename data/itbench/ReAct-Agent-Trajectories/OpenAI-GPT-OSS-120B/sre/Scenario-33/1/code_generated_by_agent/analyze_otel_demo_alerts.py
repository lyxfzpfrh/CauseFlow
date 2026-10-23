"""List unique firing alert names in the otel-demo namespace.
Scans all alerts_at_*.json files under the snapshot alerts directory and prints each alert name.
"""

import json, glob, os, sys

def main():
    # Snapshot alerts directory (absolute path)
    alerts_dir = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-33/alerts"
    names = set()
    for path in sorted(glob.glob(os.path.join(alerts_dir, "alerts_at_*.json"))):
        try:
            data = json.load(open(path))
        except Exception:
            continue
        for a in data:
            if a.get("state") != "firing":
                continue
            lbl = a.get("labels", {})
            if lbl.get("namespace") != "otel-demo":
                continue
            names.add(lbl.get("alertname", ""))
    for n in sorted(names):
        print(n)

if __name__ == "__main__":
    main()
