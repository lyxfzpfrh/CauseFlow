"""Analyze alerts for otel-demo namespace and produce summary JSON.

The script scans all JSON files under the snapshot's alerts directory,
extracts alerts where the label `namespace` equals "otel-demo" (if present),
and writes a JSON file `agent_output.json` containing a minimal structure
required by the evaluation harness.

It also collects basic evidence strings for each alert (state, severity,
activeAt) to be used later in the final diagnosis.
"""

import json
import glob
import os
from collections import defaultdict

SNAPSHOT_ROOT = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-83"
ALERTS_DIR = os.path.join(SNAPSHOT_ROOT, "alerts")

def load_alerts():
    alerts = []
    for path in sorted(glob.glob(os.path.join(ALERTS_DIR, "alerts_at_*.json"))):
        with open(path) as f:
            data = json.load(f)
            alerts.extend(data)
    return alerts

def filter_otel_demo(alerts):
    otel = []
    for a in alerts:
        labels = a.get("labels", {})
        # Some alerts may not have namespace label; ignore those.
        if labels.get("namespace") == "otel-demo":
            otel.append(a)
    return otel

def summarize(alerts):
    summary = []
    for a in alerts:
        lbl = a.get("labels", {})
        name = lbl.get("alertname", "unknown")
        severity = lbl.get("severity", "unknown")
        state = a.get("state", "unknown")
        active = a.get("activeAt", "")
        ev = f"alert={name} severity={severity} state={state} activeAt={active}"
        summary.append({"alert": name, "state": state, "evidence": ev})
    return summary

def main():
    all_alerts = load_alerts()
    otel_alerts = filter_otel_demo(all_alerts)
    # Build output structure per specification (empty entities/propagations for now)
    out = {
        "entities": [],
        "propagations": [],
        "alerts_explained": []
    }
    for a in summarize(otel_alerts):
        out["alerts_explained"].append({
            "alert": a["alert"],
            "explanation": "",
            "explained": False
        })
    # Write to the required location
    out_path = os.path.join(SNAPSHOT_ROOT, "../leaderboard_results/react with code_openai_gpt-oss-120b_07ccdb1/Scenario-83/1/agent_output.json")
    # Ensure directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()

