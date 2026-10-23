"""List unique firing alert names for the otel-demo namespace.
The snapshot alerts are under ../../B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-33/alerts.
"""

import json, glob, os

def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-33/alerts"))
    names = set()
    for path in sorted(glob.glob(os.path.join(base, "alerts_at_*.json"))):
        try:
            data = json.load(open(path))
        except Exception:
            continue
        for a in data:
            if a.get("state") != "firing":
                continue
            lbl = a.get("labels", {})
            if lbl.get("namespace") == "otel-demo":
                names.add(lbl.get("alertname", ""))
    for n in sorted(names):
        print(n)

if __name__ == "__main__":
    main()
