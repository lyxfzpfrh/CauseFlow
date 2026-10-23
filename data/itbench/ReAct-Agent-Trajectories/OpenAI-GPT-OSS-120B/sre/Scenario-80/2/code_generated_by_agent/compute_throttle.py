import pandas as pd, glob, os
BASE = "/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-80/metrics"
files = glob.glob(os.path.join(BASE, "pod_checkout-*.tsv"))
for f in files:
    df = pd.read_csv(f, sep='\t')
    # filter cpu throttling metrics
    throttled = df[df['metric_name']=='container_cpu_cfs_throttled_periods_total']
    total = df[df['metric_name']=='container_cpu_cfs_periods_total']
    if not throttled.empty and not total.empty:
        # take latest value
        th = throttled.iloc[-1]['value']
        tot = total.iloc[-1]['value']
        pct = (th / tot) * 100 if tot>0 else 0
        print(f"{os.path.basename(f)} throttling {pct:.1f}%")
