"""Alert analysis script for Scenario-91.

Purpose: Load all alert JSON snapshots from the scenario directory, filter
to alerts that pertain to the `otel-demo` namespace, and produce a summary
list that can be used in the final diagnosis.

The script is deliberately lightweight and uses only the Python standard
library. It writes its output to `filtered_alerts.json` in the current
working directory.
"""

import json
import glob
import os
from typing import List, Dict, Any

SCENARIO_DIR = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-91"
ALERTS_GLOB = os.path.join(SCENARIO_DIR, "alerts", "alerts_at_*.json")


def load_alerts() -> List[Dict[str, Any]]:
    """Load alerts from all snapshot files and return a flat list."""
    alerts: List[Dict[str, Any]] = []
    for path in sorted(glob.glob(ALERTS_GLOB)):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            alerts.extend(data)
    return alerts


def filter_otel_demo(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only alerts that have a namespace label of `otel-demo`.

    Many alerts in the demo environment do not include an explicit
    ``namespace`` label; in that case we keep the alert because it may be a
    generic system alert (e.g., Watchdog). The caller can decide how to treat
    those.
    """
    filtered: List[Dict[str, Any]] = []
    for a in alerts:
        labels = a.get("labels", {})
        ns = labels.get("namespace")
        if ns is None or ns == "otel-demo":
            filtered.append(a)
    return filtered


def main() -> None:
    alerts = load_alerts()
    otel_alerts = filter_otel_demo(alerts)
    out_path = os.path.join(os.getcwd(), "filtered_alerts.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(otel_alerts, f, indent=2)
    print(f"Wrote {len(otel_alerts)} alerts to {out_path}")


if __name__ == "__main__":
    main()

