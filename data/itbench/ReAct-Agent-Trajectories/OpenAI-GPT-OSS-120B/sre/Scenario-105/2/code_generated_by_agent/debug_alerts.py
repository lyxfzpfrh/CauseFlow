import json, os, sys
SNAPSHOT = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-105"
ALERT_DIR = os.path.join(SNAPSHOT, "alerts")
for fn in sorted(os.listdir(ALERT_DIR))[:1]:
    path = os.path.join(ALERT_DIR, fn)
    data = json.load(open(path))
    print('type of data', type(data))
    if isinstance(data, list) and data:
        print('first element type', type(data[0]))
        print('repr', repr(data[0])[:200])
